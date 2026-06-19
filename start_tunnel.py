"""独立启动 cloudflared 隧道（完全脱离父进程）"""
import subprocess
import time
import re
import os

PROJECT_DIR = r"C:\Users\LYS\.qclaw\workspace\auto_site_builder"
EXE = os.path.join(PROJECT_DIR, "tools", "cloudflared.exe")
LOG = os.path.join(PROJECT_DIR, "tunnel_stderr.txt")
URL_FILE = os.path.join(PROJECT_DIR, "public_url.txt")

# 清除旧日志
if os.path.exists(LOG):
    os.remove(LOG)

# DETACHED_PROCESS (0x00000008) + CREATE_NEW_PROCESS_GROUP (0x00000200)
# 这样 cloudflared 完全脱离父进程
DETACHED = 0x00000008 | 0x00000200

proc = subprocess.Popen(
    [EXE, "tunnel", "--url", "http://localhost:8880"],
    stderr=open(LOG, "w"),
    stdout=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
    creationflags=DETACHED,
    close_fds=True,
)

print(f"cloudflared PID: {proc.pid}")

# 等待 URL
for _ in range(20):
    time.sleep(1)
    if os.path.exists(LOG):
        with open(LOG, "r") as f:
            content = f.read()
        match = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', content)
        if match:
            url = match.group()
            with open(URL_FILE, "w") as f:
                f.write(url)
            print(f"✅ 隧道: {url}")
            break
else:
    print("⚠️ 超时，但进程可能仍在运行")