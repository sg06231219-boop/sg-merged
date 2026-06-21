"""报告生成模块 - 终端输出 / HTML报告 / JSON导出"""

import json
import os
from datetime import datetime
from .models import ScanReport, CheckResult

SEVERITY_STYLE = {
    "critical": ("RED_CIRCLE", "red", "CRITICAL"),
    "high": ("ORANGE_CIRCLE", "orange", "HIGH"),
    "medium": ("YELLOW_CIRCLE", "yellow", "MEDIUM"),
    "low": ("GREEN_CIRCLE", "green", "LOW"),
    "info": ("BLUE_CIRCLE", "blue", "INFO"),
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vulnerability Scan Report - {target}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; }}
.container {{ max-width:1200px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155; border-radius:12px; padding:30px; margin-bottom:24px; }}
.header h1 {{ font-size:28px; color:#f8fafc; }}
.header .meta {{ color:#94a3b8; margin-top:8px; font-size:14px; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:24px; }}
.summary-card {{ background:#1e293b; border:1px solid #334155; border-radius:10px; padding:20px; text-align:center; }}
.summary-card .count {{ font-size:36px; font-weight:700; margin-bottom:4px; }}
.summary-card .label {{ color:#94a3b8; font-size:13px; text-transform:uppercase; }}
.critical .count {{ color:#ef4444; }}
.high .count {{ color:#f97316; }}
.medium .count {{ color:#eab308; }}
.low .count {{ color:#22c55e; }}
.info .count {{ color:#3b82f6; }}
.risk-score .count {{ color:#f8fafc; }}
.finding {{ background:#1e293b; border:1px solid #334155; border-radius:10px; padding:20px; margin-bottom:16px; border-left:4px solid #64748b; }}
.finding.critical {{ border-left-color:#ef4444; }}
.finding.high {{ border-left-color:#f97316; }}
.finding.medium {{ border-left-color:#eab308; }}
.finding.low {{ border-left-color:#22c55e; }}
.finding.info {{ border-left-color:#3b82f6; }}
.finding-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
.finding-title {{ font-size:18px; font-weight:600; }}
.badge {{ display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }}
.badge.critical {{ background:#7f1d1d; color:#fca5a5; }}
.badge.high {{ background:#7c2d12; color:#fdba74; }}
.badge.medium {{ background:#713f12; color:#fde047; }}
.badge.low {{ background:#14532d; color:#86efac; }}
.badge.info {{ background:#1e3a5f; color:#93c5fd; }}
.finding-body {{ color:#cbd5e1; line-height:1.6; }}
.finding-body pre {{ background:#0f172a; border-radius:6px; padding:12px; margin:10px 0; overflow-x:auto; font-size:13px; border:1px solid #334155; }}
.finding-body h3 {{ color:#f1f5f9; margin:12px 0 6px; font-size:15px; }}
.recommendation {{ background:#0f2b1a; border:1px solid #166534; border-radius:6px; padding:12px; margin-top:12px; white-space:pre-line; font-size:13px; }}
.footer {{ text-align:center; color:#475569; padding:30px; font-size:12px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>Vulnerability Scan Report</h1>
<div class="meta">
  Target: {target}<br>
  Time: {scan_time}<br>
  Duration: {duration}s | Requests: {requests}
</div>
</div>
<div class="summary">
{summary_cards}
</div>
<div class="findings">
<h2 style="margin-bottom:16px; color:#f1f5f9;">Findings ({total})</h2>
{findings_html}
</div>
<div class="footer">
  VulnScanner v1.0.0 | Authorized testing only | Generated {gen_time}
</div>
</div>
</body>
</html>"""


class Reporter:
    """报告生成器"""

    def __init__(self, report: ScanReport):
        self.report = report

    def to_dict(self) -> dict:
        """导出为JSON兼容字典"""
        return {
            "target_url": self.report.target_url,
            "scan_time": self.report.scan_time,
            "duration_seconds": self.report.duration_seconds,
            "total_requests": self.report.total_requests,
            "summary": self.report.summary,
            "findings": [
                {
                    "check_name": r.check_name,
                    "severity": r.severity,
                    "title": r.title,
                    "description": r.description,
                    "evidence": r.evidence,
                    "recommendation": r.recommendation,
                    "cvss_score": r.cvss_score,
                    "cwe_id": r.cwe_id,
                }
                for r in self.report.results
            ],
        }

    def to_json(self, path: str = None) -> str:
        """导出JSON格式"""
        data = self.to_dict()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_html(self, path: str = None) -> str:
        """生成HTML报告"""
        report = self.report
        results = sorted(report.results, key=lambda r: {
            "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4
        }.get(r.severity, 5))

        severity_order = ["critical", "high", "medium", "low", "info"]
        labels = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO"}
        cards = []
        for sev in severity_order:
            count = report.summary["by_severity"].get(sev, 0)
            cards.append('<div class="summary-card ' + sev + '"><div class="count">' + str(count) + '</div><div class="label">' + labels[sev] + '</div></div>')
        cards.append('<div class="summary-card risk-score"><div class="count">' + str(report.summary["risk_score"]) + '</div><div class="label">RISK SCORE</div></div>')

        findings_parts = []
        for i, r in enumerate(results, 1):
            sev = r.severity
            badge_label = labels.get(sev, sev)
            rec_html = '<div class="recommendation"><strong>FIX:</strong>\n' + r.recommendation + '</div>' if r.recommendation else ""
            evidence_html = '<h3>EVIDENCE</h3><pre>' + r.evidence + '</pre>' if r.evidence else ""
            findings_parts.append("""
<div class="finding """ + sev + """">
<div class="finding-header">
<span class="finding-title">#""" + str(i) + """ """ + r.title + """</span>
<span class="badge """ + sev + """">""" + badge_label + """ """ + (str(r.cvss_score) if r.cvss_score else "") + """</span>
</div>
<div class="finding-body">
<p>""" + r.description + """</p>
""" + evidence_html + """
""" + rec_html + """
</div>
</div>""")

        total_vulns = sum(1 for r in results if r.severity != "info")
        html = HTML_TEMPLATE.format(
            target=report.target_url,
            scan_time=report.scan_time,
            duration=report.duration_seconds,
            requests=report.total_requests,
            summary_cards="\n".join(cards),
            findings_html="\n".join(findings_parts) if findings_parts else '<p style="color:#22c55e;text-align:center;padding:40px;">NO VULNERABILITIES FOUND</p>',
            total=str(len(results)) + " (" + str(total_vulns) + " actionable)",
            gen_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
        return html
