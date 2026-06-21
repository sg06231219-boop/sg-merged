"""开放重定向检测模块"""

import re
from urllib.parse import urlparse
from ..models import CheckResult, extract_params, inject_param

REDIRECT_PARAM_NAMES = [
    "redirect", "redirect_uri", "redirect_url", "redirect_to",
    "url", "return_url", "return_to", "next", "goto", "to",
    "link", "target", "forward", "dest", "destination",
    "continue", "callback", "cb", "ref", "referer", "referrer",
    "origin", "source", "back", "back_url", "returnUrl",
    "redirectUrl", "redirectUri", "redir",
]

TEST_REDIRECT_URL = "https://evil-example.com"


async def check_redirect(target_url: str, scanner) -> list:
    """开放重定向检测"""
    results = []
    params = extract_params(target_url)
    suspect_params = [p for p in params if p.lower() in REDIRECT_PARAM_NAMES]

    if not suspect_params:
        return results

    for param_name in suspect_params:
        test_url = inject_param(target_url, param_name, TEST_REDIRECT_URL)
        try:
            resp = await scanner.request("GET", test_url, follow_redirects=False)

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location", "")
                parsed_loc = urlparse(location)

                if TEST_REDIRECT_URL in location or parsed_loc.netloc == urlparse(TEST_REDIRECT_URL).netloc:
                    results.append(CheckResult(
                        check_name="redirect", severity="medium",
                        title="Open Redirect (param: " + param_name + ")",
                        description="Parameter " + param_name + " controls redirect destination. Attackers can craft malicious links to redirect users to phishing sites.",
                        evidence="Test URL: " + test_url + "\nStatus: " + str(resp.status_code) + "\nLocation: " + location,
                        recommendation="1. Disallow full URL control in redirect params\n2. Use domain whitelist validation\n3. Use relative paths only\n4. Show confirmation page before redirect\n5. Use encrypted redirect tokens",
                        cvss_score=4.7, cwe_id="CWE-601",
                    ))
                elif "//" in location and location != resp.url:
                    results.append(CheckResult(
                        check_name="redirect", severity="low",
                        title="Suspicious redirect behavior (param: " + param_name + ")",
                        description="Parameter " + param_name + " triggered cross-origin redirect. Needs manual verification.",
                        evidence="Location: " + location,
                        recommendation="Verify redirect target whitelist is properly implemented.",
                        cvss_score=3.0, cwe_id="CWE-601",
                    ))

            elif resp.status_code == 200:
                js_redirect = _check_js_redirect(resp.text, TEST_REDIRECT_URL)
                if js_redirect:
                    results.append(CheckResult(
                        check_name="redirect", severity="medium",
                        title="JavaScript Open Redirect (param: " + param_name + ")",
                        description="Parameter value is written into JS redirect code, potentially enabling XSS/phishing.",
                        evidence="JS code: " + js_redirect[:200],
                        recommendation="Use server-side whitelist for redirect targets.",
                        cvss_score=4.7, cwe_id="CWE-601",
                    ))
        except Exception:
            continue

    return results


def _check_js_redirect(html: str, test_url: str) -> str:
    """检查JS层面的URL注入"""
    patterns = [
        r'window\.location\s*=\s*["\'].*' + re.escape(test_url),
        r'location\.href\s*=\s*["\'].*' + re.escape(test_url),
        r'location\.replace\s*\(\s*["\'].*' + re.escape(test_url),
        r'location\.assign\s*\(\s*["\'].*' + re.escape(test_url),
    ]
    for p in patterns:
        match = re.search(p, html, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""
