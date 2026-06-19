# auto_site_builder 当前进度（2026-05-13 13:29 存档）

## ✅ 已完成

### 服务端
- FastAPI 后端运行在 8880 端口
- AI 后端：deepseek | 模板后端：jinja2
- 三种生成模式：landing / site / pricing

### PWA
- manifest.json + sw.js + 6个尺寸图标 + favicon
- index.html 已集成安装提示按钮
- ⚠️ 未手动验证：浏览器打开 http://localhost:8880 看右下角安装按钮

### Electron 桌面版
- 二进制：tools/electron/electron.exe (v35.0.0)
- 主进程：electron/main.js（自动启动 Python 后端 + BrowserWindow）
- 打包脚本：build-electron.bat
- ✅ 已启动验证：窗口正常运行

### CORS
- 已放行 serveo 域名

---

## ⏳ 等用户回来后继续

### 第一步：域名 → Cloudflare Tunnel
1. 用户告知已购买的域名
2. 确认域名 DNS 在 Cloudflare（或转移）
3. 运行：`tools/cloudflared.exe tunnel --url http://localhost:8880`
4. 配置 CNAME 记录指向隧道

### 第二步：验证 PWA
- 浏览器打开 http://localhost:8880 → 右下角安装按钮

### 第三步：打包 Electron
- 运行 `build-electron.bat` 生成 .exe

---

## 启动命令速查

| 用途 | 命令 |
|------|------|
| 启动后端 | `cd auto_site_builder && python -m uvicorn apis.app:app --host 0.0.0.0 --port 8880` |
| 启动 Electron | `tools\electron\electron.exe .` |
| 打包 Electron | `build-electron.bat` |
| 公网隧道 | `tools\cloudflared.exe tunnel --url http://localhost:8880` |