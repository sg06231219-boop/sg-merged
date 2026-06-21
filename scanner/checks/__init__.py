"""漏洞检测模块集合

每个模块导出一个 check_xxx 异步函数，接收 (url, scanner) 参数，
返回 CheckResult 列表。
"""
from .sqli import check_sqli
from .xss import check_xss
from .headers import check_headers
from .sensitive import check_sensitive
from .redirect import check_redirect
from .info import check_info

__all__ = [
    'check_sqli', 'check_xss', 'check_headers',
    'check_sensitive', 'check_redirect', 'check_info',
]
