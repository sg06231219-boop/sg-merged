"""安全响应头检测模块"""

import re
from ..models import CheckResult

SECURITY_HEADERS = {
    "Strict-Transport-Security": {
        "severity": "medium",
        "title": "Missing HSTS header",
        "desc": "Strict-Transport-Security header not set. Browsers may connect via insecure HTTP, risking MITM attacks.",
        "fix": 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";',
        "cwe": "CWE-319",
    },
    "Content-Security-Policy": {
        "severity": "medium",
        "title": "Missing CSP header",
        "desc": "Content-Security-Policy header not set. No restrictions on resource loading, increasing XSS and data injection risks.",
        "fix": "add_header Content-Security-Policy \"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'\";",
        "cwe": "CWE-1021",
    },
    "X-Frame-Options": {
        "severity": "low",
        "title": "Missing X-Frame-Options header",
        "desc": "X-Frame-Options header not set. Site may be embedded in iframes, risking clickjacking attacks.",
        "fix": 'add_header X-Frame-Options "DENY";',
        "cwe": "CWE-1021",
    },
    "X-Content-Type-Options": {
        "severity": "low",
        "title": "Missing X-Content-Type-Options header",
        "desc": "X-Content-Type-Options header not set. Browser may perform MIME type sniffing, risking MIME confusion attacks.",
        "fix": 'add_header X-Content-Type-Options "nosniff";',
        "cwe": "CWE-436",
    },
    "Referrer-Policy": {
        "severity": "info",
        "title": "Missing Referrer-Policy header",
        "desc": "Referrer-Policy header not set. Browser may leak full URLs (including sensitive parameters) in cross-origin requests.",
        "fix": 'add_header Referrer-Policy "strict-origin-when-cross-origin";',
        "cwe": "CWE-200",
    },
    "Permissions-Policy": {
        "severity": "info",
        "title": "Missing Permissions-Policy header",
        "desc": "Permissions-Policy header not set. Cannot restrict browser features (camera/mic/geolocation).",
        "fix": 'add_header Permissions-Policy "camera=(), microphone=(), geolocation=()";',
        "cwe": "CWE-276",
    },
}

INFO_LEAK_HEADERS = {
    "Server": "Server header leaks web server software/version",
    "X-Powered-By": "X-Powered-By header exposes backend tech stack",
    "X-AspNet-Version": "X-AspNet-Version header exposes ASP.NET version",
    "X-AspNetMvc-Version": "X-AspNetMvc-Version header exposes ASP.NET MVC version",
    "X-Generator": "X-Generator header exposes CMS/generator info",
}


async def check_headers(target_url: str, scanner) -> list:
    """安全响应头检测"""
    results = []
    try:
        resp = await scanner.request("GET", target_url)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        is_https = target_url.startswith("https://")

        for header_name, config in SECURITY_HEADERS.items():
            lower = header_name.lower()
            if lower not in headers:
                if header_name == "Strict-Transport-Security" and not is_https:
                    continue
                results.append(CheckResult(
                    check_name="headers", severity=config["severity"],
                    title=config["title"],
                    description=config["desc"],
                    recommendation="Nginx: " + config["fix"],
                    cwe_id=config["cwe"],
                ))
            else:
                if header_name == "Content-Security-Policy":
                    value = headers[lower]
                    if "unsafe-inline" in value:
                        results.append(CheckResult(
                            check_name="headers", severity="low",
                            title="CSP contains 'unsafe-inline'",
                            description="CSP allows inline scripts, weakening XSS protection.",
                            recommendation="Move inline scripts to external files or use nonce/hash.",
                            evidence="CSP: " + value[:200], cwe_id="CWE-1021",
                        ))
                    if "unsafe-eval" in value:
                        results.append(CheckResult(
                            check_name="headers", severity="low",
                            title="CSP contains 'unsafe-eval'",
                            description="CSP allows eval(), enabling dynamic code execution attacks.",
                            recommendation="Avoid eval()/new Function(). Remove unsafe-eval from CSP.",
                            evidence="CSP: " + value[:200], cwe_id="CWE-95",
                        ))
                if header_name == "Strict-Transport-Security":
                    m = re.search(r'max-age=(\d+)', headers[lower])
                    if m and int(m.group(1)) < 31536000:
                        results.append(CheckResult(
                            check_name="headers", severity="info",
                            title="HSTS max-age < 1 year",
                            description="Current max-age=" + m.group(1) + "s. Recommend at least 31536000 (1 year).",
                            recommendation='add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";',
                            cwe_id="CWE-319",
                        ))

        for header_name, desc in INFO_LEAK_HEADERS.items():
            lower = header_name.lower()
            if lower in headers:
                results.append(CheckResult(
                    check_name="headers", severity="low",
                    title=header_name + " header exposed",
                    description=desc + "\nCurrent: " + headers[lower],
                    evidence=header_name + ": " + headers[lower],
                    recommendation="Hide this header: server_tokens off; (Nginx) or remove from app config.",
                    cwe_id="CWE-200",
                ))

        set_cookie = resp.headers.get("set-cookie", "")
        if set_cookie:
            missing = []
            if "HttpOnly" not in set_cookie:
                missing.append("HttpOnly")
            if "Secure" not in set_cookie and is_https:
                missing.append("Secure")
            if "SameSite" not in set_cookie:
                missing.append("SameSite=Lax")
            if missing:
                results.append(CheckResult(
                    check_name="headers", severity="medium",
                    title="Cookie missing flags: " + ", ".join(missing),
                    description="Session cookie lacks critical security flags: JS readable (no HttpOnly), insecure transmission (no Secure), CSRF vulnerable (no SameSite).",
                    evidence="Set-Cookie: " + set_cookie[:200],
                    recommendation="Set: HttpOnly; Secure; SameSite=Lax",
                    cwe_id="CWE-614",
                ))
    except Exception:
        pass
    return results
