const { app, BrowserWindow, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let pythonServer = null;

function getPythonPath() {
  // Windows: 优先使用用户安装的 Python
  const candidates = [
    path.join(process.env.LOCALAPPDATA || '', 'Python', 'bin', 'python.exe'),
    path.join(process.env.USERPROFILE || '', 'AppData', 'Local', 'Python', 'bin', 'python.exe'),
    'python3',
    'python',
  ];
  return candidates;
}

function startPythonServer() {
  const pythonPaths = getPythonPath();
  const serverScript = path.join(__dirname, '..', 'apis', 'app.py');
  const workDir = path.join(__dirname, '..');

  console.log('[Electron] Starting Python server...');

  const child = spawn(pythonPaths[0], ['-m', 'uvicorn', 'apis.app:app', '--host', '127.0.0.1', '--port', '8880'], {
    cwd: workDir,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  child.stdout.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  child.stderr.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  child.on('error', (err) => {
    console.error('[Electron] Failed to start Python:', err.message);
  });

  child.on('exit', (code) => {
    console.log(`[Electron] Python server exited with code ${code}`);
    pythonServer = null;
  });

  return child;
}

function waitForServer(url, maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let retries = 0;
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode === 200) resolve(true);
        else retry();
      }).on('error', () => retry());
    };
    const retry = () => {
      retries++;
      if (retries >= maxRetries) reject(new Error('服务器启动超时'));
      else setTimeout(check, 500);
    };
    check();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: '自动独立站生成平台',
    icon: path.join(__dirname, '..', 'static', 'icons', 'icon-512x512.png'),
    backgroundColor: '#0f0c29',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.setMenuBarVisibility(false);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 阻止外部链接导航，用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.loadURL('http://127.0.0.1:8880');
}

app.whenReady().then(async () => {
  // 启动 Python 后端
  pythonServer = startPythonServer();

  try {
    await waitForServer('http://127.0.0.1:8880/api/v1/health');
    console.log('[Electron] Python server ready!');
    createWindow();
  } catch (err) {
    console.error('[Electron] Server failed to start:', err.message);
    createWindow();
    mainWindow?.webContents?.on('did-finish-load', () => {
      mainWindow.webContents.executeJavaScript(
        `document.body.innerHTML = '<div style=\"text-align:center;padding:80px;color:#f44336\"><h2>⚠️ 后端服务启动失败</h2><p>请确认 Python 已安装且 uvicorn 可运行</p></div>'`
      );
    });
  }
});

app.on('window-all-closed', () => {
  if (pythonServer) {
    pythonServer.kill();
    pythonServer = null;
  }
  app.quit();
});

app.on('before-quit', () => {
  if (pythonServer) {
    pythonServer.kill();
    pythonServer = null;
  }
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});