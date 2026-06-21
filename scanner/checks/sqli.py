"""SQL注入检测模块"""

import re
import time
from ..models import CheckResult, extract_params, inject_param

SQL_ERROR_PATTERNS = [
    r"SQL syntax.*MySQL", r"Warning.*mysql_", r"MySQLSyntaxErrorException",
    r"valid MySQL result", r"PostgreSQL.*ERROR", r"Warning.*\Wpg_",
    r"ORA-\d{5}", r"Oracle error", r"SQLite/JDBCDriver",
    r"System\.Data\.SQLite", r"Microsoft OLE DB.*SQL Server",
    r"Unclosed quotation mark", r"SQL command not properly ended",
    r"incorrect syntax near", r"Syntax error in string",
    r"DB2 SQL Error", r"Driver.*SQL Server", r"ODBC Driver.*SQL Server",
]

ERROR_PAYLOADS = [
    "'", '"', "')", '")', "`", "') --",
    "' OR '1'='1", "' OR 1=1 --", '" OR 1=1 --', "1' AND '1'='1",
]

TIME_PAYLOADS = [
    ("' OR SLEEP(3) --", 3.0, "MySQL SLEEP"),
    ("' OR pg_sleep(3) --", 3.0, "PostgreSQL pg_sleep"),
    ("'; WAITFOR DELAY '00:00:03' --", 3.0, "MSSQL WAITFOR"),
    ("' AND SLEEP(3) --", 3.0, "MySQL AND SLEEP"),
    ("' OR BENCHMARK(5000000,MD5(1)) --", 1.5, "MySQL BENCHMARK"),
]

COMPILED_ERRORS = [re.compile(p, re.IGNORECASE) for p in SQL_ERROR_PATTERNS]


async def check_sqli(target_url: str, scanner) -> list:
    """SQL注入检测主入口"""
    results = []
    params = extract_params(target_url)
    if not params:
        return results

    error_results = await _check_error_based(target_url, params, scanner)
    results.extend(error_results)
    if error_results:
        return results

    time_results = await _check_time_based(target_url, params, scanner)
    results.extend(time_results)
    return results


async def _check_error_based(url: str, params: dict, scanner) -> list:
    """错误注入检测"""
    for param_name in params:
        for payload in ERROR_PAYLOADS:
            test_url = inject_param(url, param_name, payload)
            try:
                resp = await scanner.request("GET", test_url)
                text = resp.text[:5000]
                for pattern in COMPILED_ERRORS:
                    if pattern.search(text):
                        return [CheckResult(
                            check_name="sqli", severity="critical",
                            title="SQL注入 - error-based (param: " + param_name + ")",
                            description="Parameter " + param_name + " reflects SQL errors when injecting [" + payload + "]. SQL injection confirmed.",
                            evidence="URL: " + test_url + "\nPattern: " + pattern.pattern + "\nResponse: " + text[:500],
                            recommendation="Use parameterized queries. Disable detailed error output in production.",
                            cvss_score=9.8, cwe_id="CWE-89",
                        )]
            except Exception:
                continue
    return []


async def _check_time_based(url: str, params: dict, scanner) -> list:
    """时间盲注检测"""
    results = []
    try:
        t0 = time.time()
        await scanner.request("GET", url)
        baseline = time.time() - t0
    except Exception:
        baseline = 1.0

    threshold = max(baseline * 3, 2.0)

    for param_name in params:
        for payload, expected_delay, db_type in TIME_PAYLOADS:
            test_url = inject_param(url, param_name, payload)
            try:
                t0 = time.time()
                await scanner.request("GET", test_url)
                elapsed = time.time() - t0
                if elapsed >= threshold and elapsed >= expected_delay * 0.7:
                    return [CheckResult(
                        check_name="sqli", severity="high",
                        title="SQL injection - time-based blind (param: " + param_name + ", " + db_type + ")",
                        description="Time delay detected: baseline=" + str(round(baseline, 2)) + "s, injected=" + str(round(elapsed, 2)) + "s. Possible " + db_type + " time-based SQLi.",
                        evidence="URL: " + test_url + "\nBaseline: " + str(round(baseline, 2)) + "s\nInjected: " + str(round(elapsed, 2)) + "s",
                        recommendation="Use parameterized queries. Set query timeout limits.",
                        cvss_score=7.5, cwe_id="CWE-89",
                    )]
            except Exception:
                continue
    return results
