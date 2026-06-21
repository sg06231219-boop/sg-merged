"""XSS跨站脚本检测模块"""

import re
from ..models import CheckResult, extract_params, inject_param

XSS_PAYLOADS = [
    '<script>alert("XSS")</script>',
    '"><script>alert("XSS")</script>',
    '<img src=x onerror=alert("XSS")>',
    '"><img src=x onerror=alert("XSS")>',
    '<svg/onload=alert("XSS")>',
    '"><svg/onload=alert("XSS")>',
    "' onfocus=alert('XSS') autofocus '",
    '"><body onload=alert("XSS")>',
    '<details open ontoggle=alert("XSS")>',
]

DOM_XSS_PATTERNS = [
    (r"document\.write\s*\(.*location\.", "document.write + location"),
    (r"\.innerHTML\s*=\s*.*location\.", "innerHTML + location"),
    (r"eval\s*\(.*location\.", "eval + location"),
    (r"setTimeout\s*\(.*location\.", "setTimeout + location"),
    (r"\.html\s*\(.*location\.", "jQuery.html + location"),
    (r"location\.hash", "location.hash unfiltered"),
]


async def check_xss(target_url: str, scanner) -> list:
    """XSS检测主入口"""
    results = []
    params = extract_params(target_url)

    if params:
        reflected = await _check_reflected(target_url, params, scanner)
        results.extend(reflected)

    try:
        resp = await scanner.request("GET", target_url)
        dom_results = _check_dom(resp.text)
        results.extend(dom_results)
    except Exception:
        pass

    return results


async def _check_reflected(url: str, params: dict, scanner) -> list:
    """反射型XSS检测"""
    for param_name in params:
        for payload in XSS_PAYLOADS:
            test_url = inject_param(url, param_name, payload)
            try:
                resp = await scanner.request("GET", test_url)
                if _is_reflected(payload, resp.text, resp.headers):
                    return [CheckResult(
                        check_name="xss", severity="high",
                        title="Reflected XSS (param: " + param_name + ")",
                        description="Parameter " + param_name + " value is reflected in the response without sanitization. Attacker can craft malicious links to execute arbitrary JavaScript in victims' browsers.",
                        evidence="URL: " + test_url + "\nPayload: " + payload,
                        recommendation="HTML-entity encode all output. Use Content-Security-Policy header. Set HttpOnly cookies. Use textContent instead of innerHTML.",
                        cvss_score=6.1, cwe_id="CWE-79",
                    )]
            except Exception:
                continue
    return []


def _is_reflected(payload: str, response: str, headers: dict) -> bool:
    """检查payload是否反射在响应中"""
    content_type = headers.get("content-type", "")
    if "html" not in content_type and "javascript" not in content_type:
        if "text/plain" not in content_type:
            return False
    if payload in response:
        encoded = payload.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        if encoded not in response:
            return True
    return False


def _check_dom(html: str) -> list:
    """DOM型XSS基础检测"""
    results = []
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for script in scripts:
        for pattern, description in DOM_XSS_PATTERNS:
            match = re.search(pattern, script, re.IGNORECASE)
            if match:
                results.append(CheckResult(
                    check_name="xss", severity="medium",
                    title="Potential DOM XSS - " + description,
                    description="Dangerous DOM manipulation pattern [" + description + "] found in JavaScript. If user input reaches this sink, DOM XSS is possible.",
                    evidence="Code: " + match.group(0)[:300],
                    recommendation="Avoid innerHTML/document.write. Use textContent. Sanitize with DOMPurify. Use Trusted Types API.",
                    cvss_score=4.0, cwe_id="CWE-79",
                ))
    return results
