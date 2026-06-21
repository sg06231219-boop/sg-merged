"""扫描引擎核心 - 异步HTTP客户端与任务调度"""

import asyncio
import time
import httpx
from typing import Optional

from . import checks
from .models import CheckResult, ScanReport


DEFAULT_CONFIG = {
    "timeout": 10,
    "concurrency": 10,
    "max_requests": 200,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "follow_redirects": True,
    "verify_ssl": False,
    "delay": 0,
    "risk_level": "medium",
    "custom_headers": {},
    "cookies": {},
    "proxy": None,
}


class Scanner:
    """漏洞扫描器主引擎"""

    def __init__(self, config: dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self._semaphore = None

    async def __aenter__(self):
        limits = httpx.Limits(
            max_connections=self.config["concurrency"],
            max_keepalive_connections=5,
        )
        timeout = httpx.Timeout(self.config["timeout"])
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=self.config["follow_redirects"],
            verify=self.config["verify_ssl"],
            headers={"User-Agent": self.config["user_agent"], **self.config["custom_headers"]},
            cookies=self.config["cookies"],
            proxy=self.config["proxy"],
        )
        self._semaphore = asyncio.Semaphore(self.config["concurrency"])
        self.request_count = 0
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带限流和计数的HTTP请求"""
        if self.request_count >= self.config["max_requests"]:
            raise RuntimeError("max requests reached")
        async with self._semaphore:
            if self.config["delay"] > 0:
                await asyncio.sleep(self.config["delay"])
            self.request_count += 1
            return await self.client.request(method, url, **kwargs)

    async def scan(self, target_url: str) -> ScanReport:
        """执行完整扫描"""
        start = time.time()
        report = ScanReport(
            target_url=target_url,
            scan_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url
        report.target_url = target_url

        check_modules = [
            checks.check_headers,
            checks.check_info,
            checks.check_sensitive,
        ]
        if self.config["risk_level"] in ("medium", "high"):
            check_modules.append(checks.check_redirect)
        if self.config["risk_level"] == "high":
            check_modules.extend([checks.check_sqli, checks.check_xss])

        tasks = [check_fn(target_url, self) for check_fn in check_modules]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results_list:
            if isinstance(result, Exception):
                report.results.append(CheckResult(
                    check_name="error", severity="info",
                    title="check error: " + str(result),
                    description=str(result),
                ))
            elif isinstance(result, list):
                report.results.extend(result)

        report.duration_seconds = round(time.time() - start, 2)
        report.total_requests = self.request_count
        report.summary = self._build_summary(report.results)
        return report

    def _build_summary(self, results: list) -> dict:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for r in results:
            counts[r.severity] = counts.get(r.severity, 0) + 1
        return {
            "total": len(results),
            "by_severity": counts,
            "risk_score": (
                counts["critical"] * 10 +
                counts["high"] * 5 +
                counts["medium"] * 2 +
                counts["low"] * 1
            ),
        }



