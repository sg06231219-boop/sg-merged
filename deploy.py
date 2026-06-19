"""
deploy.py — 启动器：同时启动服务器和 Cloudflare Tunnel
使用 DETACHED_PROCESS 确保子进程独立于 PowerShell 进程存活
"""
import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
TOOLS_DIR = PROJECT_DIR / "tools"

# 1. 杀旧进程
print("[1] 清理旧进程...")
os.system('netstat -ano | findstr ":8880" > nul && for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8880" ^| findstr "LISTENING"\') do taskkill /F /PID %a 2>nul')
time.sleep(1)

# 2. 启动 uvicorn（DETACHED）
print("[2] 启动服务器 (localhost:8880)...")
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "apis.app:app", "--host", "0.0.0.0", "--port", "8880"],
    cwd=str(PROJECT_DIR),
    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print(f"   服务器 PID: {server.pid}")

# 3. 等待服务器就绪
print("[3] 等待服务器就绪...")
for i in range(30):
    time.sleep(1)
    try:
        import urllib.request
        r = urllib.request.urlopen("http://127.0.0.1:8880/api/v1/health", timeout=2)
        if r.status == 200:
            print(f"   ✅ 服务器就绪!")
            break
    except Exception:
        if i < 29:
            continue
        print("   ❌ 服务器启动超时!")
        sys.exit(1)

# 4. 启动 Cloudflare Tunnel (DETACHED)
cloudflared = TOOLS_DIR / "cloudflared.exe"
if not cloudflared.exists():
    print("   ❌ 找不到 tools/cloudflared.exe")
    sys.exit(1)

print("[4] 启动 Cloudflare Tunnel...")
import subprocess
tunnel = subprocess.Popen(
    [str(cloudflared), "tunnel", "--url", "http://localhost:8880", "--no-autoupdate"],
    cwd=str(PROJECT_DIR),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
)
print(f"   隧道 PID: {tunnel.pid}")

# 5. 等待隧道 URL
print("[5] 等待公网地址...")
import threading
import queue

url_queue = queue.Queue()

def read_output():
    try:
        for line in tunnel.stdout:
            print(f"   [tunnel] {line.rstrip()}")
            if "trycloudflare.com" in line:
                url_queue.put(line.strip())
    except Exception:
        pass

reader = threading.Thread(target=read_output, daemon=True)
reader.start()

for i in range(30):
    try:
        url_line = url_queue.get(timeout=1)
        # 提取 URL
        import re
        match = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', url_line)
        if match:
            public_url = match.group(0)
            print(f"\n{'='*60}")
            print(f"  🎉 公网地址: {public_url}")
            print(f"{'='*60}")
            
            # 保存到文件
            (PROJECT_DIR / "public_url.txt").write_text(public_url)
            print(f"\n  📝 地址已保存到 public_url.txt")
            break
    except queue.Empty:
        if i == 29:
            print("   ⚠️ 未能获取隧道 URL（可能网络问题）")
        continue

print(f"\n  服务器 PID: {server.pid} | 隧道 PID: {tunnel.pid}")
print(f"  进程已独立运行，关闭此窗口不影响服务")
input("\n按 Enter 退出（服务会继续运行）...")