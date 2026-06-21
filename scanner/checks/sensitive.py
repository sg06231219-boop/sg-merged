"""敏感文件/路径暴露检测"""

import asyncio
from ..models import CheckResult, build_test_url

SENSITIVE_PATHS = {
    # Git泄露
    "/.git/config": ("Git泄露", "high", ".git/config accessible, repo info exposed"),
    "/.git/HEAD": ("Git泄露", "critical", ".git/HEAD accessible, full source code dump possible"),
    "/.git/index": ("Git泄露", "high", ".git/index accessible, file index exposed"),
    # 环境变量
    "/.env": ("环境变量泄露", "critical", ".env file accessible, DB passwords/API keys may be exposed"),
    "/.env.local": ("环境变量泄露", "critical", ".env.local accessible"),
    "/.env.production": ("环境变量泄露", "critical", "production env vars exposed"),
    "/.env.backup": ("环境变量泄露", "high", "env backup file accessible"),
    "/config/.env": ("环境变量泄露", "high", "config dir .env accessible"),
    # 备份文件
    "/backup": ("备份文件", "medium", "backup directory accessible"),
    "/backup.zip": ("备份文件", "high", "full site backup downloadable"),
    "/backup.sql": ("备份文件", "critical", "database backup downloadable"),
    "/dump.sql": ("备份文件", "critical", "database dump downloadable"),
    "/database.sql": ("备份文件", "critical", "database SQL file downloadable"),
    # 配置文件
    "/wp-config.php.bak": ("配置文件", "high", "WordPress config backup accessible"),
    "/wp-config.php~": ("配置文件", "high", "WordPress config editor backup accessible"),
    "/config.php.bak": ("配置文件", "high", "PHP config backup accessible"),
    "/config.json": ("配置文件", "medium", "JSON config directly accessible"),
    "/web.config": ("配置文件", "medium", "IIS web.config accessible"),
    "/.htaccess": ("配置文件", "low", "Apache .htaccess accessible"),
    # 调试
    "/phpinfo.php": ("信息泄露", "medium", "PHP info page exposes server config"),
    "/info.php": ("信息泄露", "medium", "PHP info page accessible"),
    "/server-status": ("信息泄露", "medium", "Apache server status accessible"),
    "/server-info": ("信息泄露", "medium", "Apache server info accessible"),
    "/.DS_Store": ("信息泄露", "low", "macOS .DS_Store exposes dir structure"),
    # Spring Boot
    "/actuator": ("信息泄露", "medium", "Spring Boot Actuator accessible"),
    "/actuator/health": ("信息泄露", "low", "Spring Boot health endpoint"),
    "/actuator/env": ("信息泄露", "high", "Spring Boot environment endpoint - may leak credentials"),
    "/actuator/mappings": ("信息泄露", "medium", "Spring Boot route mappings exposed"),
    # 调试端点
    "/debug": ("调试端点", "medium", "debug endpoint accessible"),
    "/api/debug": ("调试端点", "medium", "API debug endpoint accessible"),
    # 管理后台
    "/admin": ("管理后台", "medium", "admin panel discoverable"),
    "/administrator": ("管理后台", "medium", "Joomla admin panel"),
    "/wp-admin": ("管理后台", "low", "WordPress admin panel"),
    "/wp-login.php": ("管理后台", "low", "WordPress login page"),
    "/login": ("登录页面", "low", "login page accessible"),
    # API文档
    "/swagger-ui.html": ("API文档", "medium", "Swagger UI accessible"),
    "/swagger/index.html": ("API文档", "medium", "Swagger API docs accessible"),
    "/api-docs": ("API文档", "medium", "API docs endpoint accessible"),
    "/graphql": ("API端点", "medium", "GraphQL endpoint accessible"),
    "/api/v1": ("API端点", "low", "API v1 endpoint"),
    "/api/v2": ("API端点", "low", "API v2 endpoint"),
    # CI/CD
    "/.github": ("CI泄露", "low", "GitHub Actions workflow dir"),
    "/.gitlab-ci.yml": ("CI泄露", "medium", "GitLab CI config accessible"),
    "/Dockerfile": ("CI泄露", "low", "Dockerfile accessible - build info leaked"),
    "/docker-compose.yml": ("CI泄露", "medium", "Docker Compose config accessible"),
    # 其他
    "/robots.txt": ("信息泄露", "info", "robots.txt accessible (may expose sensitive paths)"),
    "/sitemap.xml": ("信息泄露", "info", "sitemap accessible"),
    "/crossdomain.xml": ("信息泄露", "low", "Flash crossdomain policy accessible"),
    "/.well-known/security.txt": ("安全策略", "info", "security contact info"),
}


async def check_sensitive(target_url: str, scanner) -> list:
    """敏感文件/路径暴露检测"""
    results = []
    sem = asyncio.Semaphore(15)

    async def check_path(path: str, info: tuple):
        async with sem:
            try:
                test_url = build_test_url(target_url, path)
                resp = await scanner.request("GET", test_url)
                content_type = resp.headers.get("content-type", "").lower()

                is_accessible = False
                evidence = "Status: " + str(resp.status_code) + "\nContent-Type: " + content_type

                if resp.status_code == 200:
                    if "text/html" in content_type and len(resp.text) < 200:
                        is_accessible = False
                    elif "text/html" in content_type:
                        not_found = ["not found", "404", "does not exist", "doesn't exist", "page not found"]
                        text_lower = resp.text[:500].lower()
                        if any(ind in text_lower for ind in not_found):
                            is_accessible = False
                        else:
                            is_accessible = True
                    else:
                        is_accessible = True

                elif resp.status_code == 403:
                    evidence += "\n(403 Forbidden - path exists but access denied)"
                    if info[1] in ("high", "critical"):
                        is_accessible = True

                if is_accessible:
                    results.append(CheckResult(
                        check_name="sensitive", severity=info[1],
                        title="Exposed: " + path + " (" + info[0] + ")",
                        description="Path " + path + " is externally accessible.\nType: " + info[0] + "\n" + info[2],
                        evidence=evidence,
                        recommendation="1. Block hidden files in web server (location ~ /\\. { deny all; })\n2. Move sensitive files outside web root\n3. Use .gitignore to prevent commits of sensitive files",
                        cwe_id="CWE-538" if info[1] in ("high", "critical") else "CWE-200",
                    ))
            except Exception:
                pass

    tasks = [check_path(path, info) for path, info in SENSITIVE_PATHS.items()]
    await asyncio.gather(*tasks)
    return results
