# start_deploy.ps1 - Auto Site Builder 一键部署脚本
# 用法: 右键此文件 → 使用 PowerShell 运行
# 或: powershell -ExecutionPolicy Bypass -File start_deploy.ps1

Write-Host @"
============================================================
  🚀 自动独立站生成平台 - 公网部署
============================================================
"@ -ForegroundColor Cyan

Set-Location $PSScriptRoot

# ── 1. 关闭旧端口 ──
$old = Get-NetTCPConnection -LocalPort 8880 -ErrorAction SilentlyContinue
if ($old) {
    Write-Host "[1] 关闭旧服务..." -ForegroundColor Yellow
    $old | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep 2
}

# ── 2. 启动服务器 ──
Write-Host "[2] 启动服务器 (localhost:8880)..." -ForegroundColor Green
$serverJob = Start-Job -Name "UVICORN" -ScriptBlock {
    Set-Location $using:PSScriptRoot
    & python -m uvicorn apis.app:app --host 0.0.0.0 --port 8880 2>&1 | Out-Null
}

Start-Sleep 5

# 检查服务器是否就绪
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8880/api/v1/health" -TimeoutSec 10
    Write-Host "   ✅ 服务器就绪 | AI=$($r.ai_backend) | 模板=$($r.template_backend)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 服务器启动失败!" -ForegroundColor Red
    exit 1
}

# ── 3. 启动 Cloudflare Tunnel ──
Write-Host "[3] 启动 Cloudflare 隧道..." -ForegroundColor Green

$ToolsDir = Join-Path $PSScriptRoot "tools"
$Cloudflared = Join-Path $ToolsDir "cloudflared.exe"

if (!(Test-Path $Cloudflared)) {
    Write-Host "   ❌ 找不到 cloudflared.exe，请先下载到 tools/" -ForegroundColor Red
    exit 1
}

# ── 4. 运行隧道并提取 URL ──
Write-Host "正在创建公网隧道..." -ForegroundColor Cyan
try {
    $result = & $Cloudflared tunnel --url http://localhost:8880 --no-autoupdate 2>&1
} catch {
    Write-Host "   隧道已停止" -ForegroundColor Yellow
}

# 清理
if ($serverJob.State -eq 'Running') {
    Stop-Job -Name "UVICORN" -ErrorAction SilentlyContinue
    Remove-Job -Name "UVICORN" -ErrorAction SilentlyContinue
}
Write-Host "部署已停止" -ForegroundColor Yellow
pause