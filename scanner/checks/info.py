"""信息泄露检测模块"""

import re
from ..models import CheckResult

TECH_FINGERPRINTS = {
    "jquery": (r"jquery[.\-\s]*(\d+\.\d+\.\d+)", "jQuery"),
    "bootstrap": (r"bootstrap[.\-\s]*(\d+\.\d+\.\d+)", "Bootstrap"),
    "vue": (r"vue[.\-\s]*(\d+\.\d+\.\d+)", "Vue.js"),
    "react": (r"react[.\-\s]*(\d+\.\d+\.\d+)", "React"),
    "angular": (r"angular[.\-\s]*(\d+\.\d+\.\d+)", "Angular"),
    "wordpress": (r"wp-content|wordpress", "WordPress"),
    "laravel": (r"laravel", "Laravel"),
    "django": (r"django|csrftoken", "Django"),
    "flask": (r"flask", "Flask"),
    "spring": (r"spring", "Spring Boot"),
    "express": (r"express", "Express.js"),
    "next": (r"__NEXT_DATA__|_next/", "Next.js"),
    "nuxt": (r"__NUXT__|_nuxt/", "Nuxt.js"),
}

COMMENT_PATTERNS = [
    (r"TODO.*(?:password|passwd|secret|key|token|api)", "high", "TODO comment exposes credential keywords"),
    (r"FIXME.*(?:vuln|injection|unsafe|dangerous)", "medium", "Comment marks known security flaws"),
    (r"(?:password|passwd|secret|api.?key|token)\s*[=:]\s*['\"]?\S+['\"]?", "critical", "Hardcoded credentials in HTML comment"),
    (r"<!--.*(?:debug|test|staging).*-->", "low", "Debug/test environment info exposed"),
    (r"<!--.*(?:SELECT|INSERT|UPDATE|DELETE)\s.*-->", "high", "SQL query exposed in HTML comment"),
    (r"<!--.*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.*-->", "medium", "Internal IP address in HTML comment"),
]


async def check_info(target_url: str, scanner) -> list:
    """信息泄露综合检测"""
    results = []
    try:
        resp = await scanner.request("GET", target_url)
        html = resp.text
        headers = {k.lower(): v for k, v in resp.headers.items()}
    except Exception:
        return results

    # 1. 技术栈指纹
    for tech_name, (pattern, display_name) in TECH_FINGERPRINTS.items():
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            version = match.group(1) if match.lastindex else "detected"
            results.append(CheckResult(
                check_name="info", severity="info",
                title="Tech fingerprint: " + display_name + " " + version,
                description="Detected " + display_name + ". Knowing the tech stack helps attackers find known vulnerabilities.",
                evidence="Match: " + match.group(0)[:200],
                recommendation="1. Remove unnecessary tech identifiers\n2. Keep frameworks up to date\n3. Use WAF to hide tech signatures",
                cwe_id="CWE-200",
            ))

    # 2. HTML注释中的敏感信息
    comments = re.findall(r'<!--(.*?)-->', html, re.DOTALL)
    for comment in comments:
        for pattern, severity, desc in COMMENT_PATTERNS:
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                matched_text = match.group(0)
                if severity == "critical":
                    results.append(CheckResult(
                        check_name="info", severity=severity,
                        title="Hardcoded credentials in HTML comment",
                        description="HTML comment contains hardcoded credentials visible to anyone viewing page source. This is a critical security issue.",
                        evidence="Comment: " + matched_text[:300],
                        recommendation="1. Immediately remove all credentials from HTML comments\n2. Use environment variables for sensitive config\n3. Reset exposed credentials immediately\n4. Add comment scanning to CI/CD",
                        cwe_id="CWE-798",
                    ))
                else:
                    results.append(CheckResult(
                        check_name="info", severity=severity,
                        title="Info disclosure in HTML comment - " + desc,
                        description="HTML comment exposes information useful to attackers.",
                        evidence="Comment: " + matched_text[:300],
                        recommendation="Clean HTML comments in production. Remove debug notes.",
                        cwe_id="CWE-200",
                    ))

    # 3. 目录列表暴露
    dir_listing = ["Index of /", "Directory Listing", "Parent Directory"]
    for indicator in dir_listing:
        if indicator in html:
            results.append(CheckResult(
                check_name="info", severity="medium",
                title="Directory listing exposed",
                description="Web server has directory listing enabled. Attackers can browse directory structure directly.",
                evidence="Found: " + indicator,
                recommendation="1. Nginx: autoindex off;\n2. Apache: Options -Indexes\n3. IIS: Disable directory browsing",
                cwe_id="CWE-548",
            ))
            break

    # 4. CORS配置
    acao = resp.headers.get("access-control-allow-origin", "")
    if acao == "*":
        results.append(CheckResult(
            check_name="info", severity="low",
            title="CORS: Access-Control-Allow-Origin: *",
            description="CORS allows any origin. While common for public APIs, verify this is intentional.",
            evidence="Access-Control-Allow-Origin: " + acao,
            recommendation="If not needed, restrict to specific domains instead of wildcard *.",
            cwe_id="CWE-942",
        ))

    # 5. Source Map暴露
    if ".map" in html or "sourceMappingURL" in html:
        results.append(CheckResult(
            check_name="info", severity="low",
            title="Frontend source map exposed",
            description="Page references source maps. Attackers can access unminified frontend source code.",
            evidence="Source map or sourceMappingURL found in page",
            recommendation="Remove .js.map files from production or block external access to them.",
            cwe_id="CWE-200",
        ))

    return results
