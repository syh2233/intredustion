const { app, BrowserWindow, shell, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');

let mainWindow = null;
let backendProcess = null;

const FLASK_HOST = process.env.FLASK_HOST || '127.0.0.1';
const FLASK_PORT = Number(process.env.FLASK_PORT || 5001);
const FLASK_URL = `http://${FLASK_HOST}:${FLASK_PORT}/`;

function waitForPort(host, port, timeoutMs) {
  const start = Date.now();

  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const socket = new net.Socket();

      socket.setTimeout(1000);
      socket.once('connect', () => {
        socket.destroy();
        resolve();
      });
      socket.once('timeout', () => {
        socket.destroy();
        retry();
      });
      socket.once('error', () => {
        socket.destroy();
        retry();
      });

      socket.connect(port, host);
    };

    const retry = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error(`Timeout waiting for ${host}:${port}`));
        return;
      }
      setTimeout(tryOnce, 300);
    };

    tryOnce();
  });
}

function getDataDir() {
  // Use per-user appData so the packaged app can write its DB/logs
  return app.getPath('userData');
}

function startBackend() {
  const webDir = path.resolve(__dirname, '..');
  const dataDir = getDataDir();

  const env = {
    ...process.env,
    FIRE_ALARM_DATA_DIR: dataDir,
    FIRE_ALARM_PORT: String(FLASK_PORT)
  };

  // Prefer packaged backend exe if present (for distributable builds)
  // electron-builder will place extraResources under process.resourcesPath
  const packagedExe = path.join(process.resourcesPath, 'backend', 'fire-alarm-web.exe');

  if (process.platform === 'win32' && fs.existsSync(packagedExe)) {
    backendProcess = spawn(packagedExe, [], {
      cwd: webDir,
      env,
      stdio: 'inherit'
    });
    return;
  }

  const python = process.env.PYTHON || 'python';
  backendProcess = spawn(python, ['app.py'], {
    cwd: webDir,
    env,
    stdio: 'inherit'
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.loadURL(FLASK_URL);
}

app.whenReady().then(async () => {
  startBackend();

  if (backendProcess) {
    backendProcess.on('exit', (code, signal) => {
      backendProcess = null;
      if (app.isReady()) {
        dialog.showErrorBox(
          '后端已退出',
          `后端进程已退出（code=${code}, signal=${signal}）。\n\n你可以：\n1) 在终端进入 web/ 运行 python app.py 查看报错\n2) 检查 Python 依赖是否已安装：pip install -r requirements.txt`
        );
      }
    });
  }

  try {
    await waitForPort(FLASK_HOST, FLASK_PORT, 30000);
  } catch (e) {
    dialog.showErrorBox(
      '无法连接本地服务',
      `Electron 未能在 30 秒内连接到 ${FLASK_URL}\n\n错误：${e.message}`
    );
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch (_) {
      // ignore
    }
  }
});
