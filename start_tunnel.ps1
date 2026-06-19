$projectDir = "C:\Users\LYS\.qclaw\workspace\auto_site_builder"
$logFile = "$projectDir\tunnel_stderr.txt"
Remove-Item $logFile -ErrorAction SilentlyContinue

$proc = Start-Process -FilePath "$projectDir\tools\cloudflared.exe" `
    -ArgumentList "tunnel","--url","http://localhost:8880" `
    -RedirectStandardError $logFile `
    -PassThru -WindowStyle Hidden

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep 1
    if ((Test-Path $logFile) -and ((Get-Content $logFile -Raw) -match 'https://[\w-]+\.trycloudflare\.com')) {
        $url = $Matches[0]
        Write-Host "隧道地址: $url"
        $url | Out-File "$projectDir\public_url.txt" -Encoding UTF8
        Write-Host "PID: $($proc.Id)"
        exit 0
    }
}
Write-Host "超时，PID: $($proc.Id)"