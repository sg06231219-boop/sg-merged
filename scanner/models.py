"""数据模型与工具函数 - 避免循环导入"""

from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


@dataclass
class CheckResult:
    """单个漏洞检测结果"""
    check_name: str
    severity: str
    title: str
    description: str
    evidence: str = ""
    recommendation: str = ""
    cvss_score: float = 0.0
    cwe_id: str = ""


@dataclass
class ScanReport:
    """完整扫描报告"""
    target_url: str
    scan_time: str = ""
    duration_seconds: float = 0.0
    total_requests: int = 0
    results: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def extract_params(url: str) -> dict:
    """提取URL中的所有查询参数"""
    parsed = urlparse(url)
    return {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}


def inject_param(url: str, param: str, payload: str) -> str:
    """向URL的指定参数注入payload"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params[param] = [payload]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def build_test_url(base: str, path: str) -> str:
    """构建测试URL (处理路径拼接)"""
    base = base.rstrip("/")
    path = path.lstrip("/")
    return base + "/" + path
