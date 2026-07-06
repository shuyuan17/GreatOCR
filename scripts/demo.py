"""GreatOCR 开发者 / 演示启动器（Developer Demo Launcher）。

用法:
    python scripts/demo.py

这是一个开发 / 演示用的便捷工具，用于在一次 Codex 任务完成后快速手动测试
GreatOCR。它会：

1. 检查 .venv 是否存在
2. 检查 Node.js 是否可用
3. 生成本次运行的 session token
4. 启动后端  : .venv/Scripts/python.exe scripts/serve.py
5. 启动前端  : frontend/node_modules/vite/bin/vite.js
6. 将同一个 token 传给 GREATOCR_SESSION_TOKEN 与 VITE_GREAT_OCR_TOKEN
7. 自动打开浏览器 http://localhost:5173
8. 在终端显示后端 / 前端地址与关闭方式
9. Ctrl+C 时尽量关闭前后端子进程

注意：本脚本不替代 install.bat / start.bat，仅用于开发期快速验证。
"""

from __future__ import annotations

import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8399
FRONTEND_HOST = "localhost"
FRONTEND_PORT = 5173


# --------------------------------------------------------------------------- #
# 环境探测
# --------------------------------------------------------------------------- #
def find_venv_python() -> Path | None:
    """定位虚拟环境里的 Python 解释器（兼容 Windows 与 POSIX）。"""
    candidates = [
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_node() -> str | None:
    """定位 Node.js 可执行文件。"""
    return shutil.which("node")


def find_vite_bin() -> Path:
    """定位 vite 的入口脚本。"""
    return PROJECT_ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"


# --------------------------------------------------------------------------- #
# 进程管理
# --------------------------------------------------------------------------- #
def terminate_tree(proc: subprocess.Popen) -> None:
    """尽量关闭整个子进程树（含孙进程，如 esbuild）。"""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        # taskkill /T 会连带结束子进程；/F 强制终止。
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            import os as _os
            import signal as _signal

            _os.killpg(_os.getpgid(proc.pid), _signal.SIGTERM)
        except Exception:
            proc.terminate()


def wait_for(proc: subprocess.Popen, timeout: float = 5.0) -> None:
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pass


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main() -> int:
    print("=" * 60)
    print("  GreatOCR - Developer Demo Launcher")
    print("=" * 60)
    print()

    # 1. 检查 .venv
    venv_python = find_venv_python()
    if venv_python is None:
        print("[ERROR] 未找到 .venv。请先运行 install.bat 完成安装。")
        return 1
    print(f"[1/4] .venv 检查通过: {venv_python}")

    # 2. 检查 Node.js
    node_exe = find_node()
    if node_exe is None:
        print("[ERROR] 未找到 Node.js。请安装 Node.js LTS 并加入 PATH。")
        return 1
    print(f"[2/4] Node.js 检查通过: {node_exe}")

    # 2.5 检查前端依赖（缺失时给出明确指引，避免晦涩报错）
    vite_bin = find_vite_bin()
    if not vite_bin.exists():
        print("[ERROR] 未找到 frontend/node_modules/vite。")
        print("        请先运行 install.bat 安装前端依赖。")
        return 1
    print(f"[3/4] 前端依赖检查通过: {vite_bin}")

    # 3. 生成本次运行的 session token
    token = secrets.token_hex(32)
    print(f"[4/4] 已生成本次 session token: {token[:8]}...（已隐藏）")
    print()

    # 6. 准备环境变量（同一个 token 传给前后端）
    backend_env = os.environ.copy()
    backend_env["GREATOCR_SESSION_TOKEN"] = token
    backend_env["GREATOCR_ALLOWED_ORIGIN"] = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

    frontend_env = os.environ.copy()
    frontend_env["VITE_GREAT_OCR_TOKEN"] = token

    # 4. 启动后端
    backend = subprocess.Popen(
        [str(venv_python), str(PROJECT_ROOT / "scripts" / "serve.py")],
        cwd=str(PROJECT_ROOT),
        env=backend_env,
    )

    # 5. 启动前端（从 frontend 目录运行，以便 vite 找到配置文件）
    frontend = subprocess.Popen(
        [node_exe, str(vite_bin), "--host", FRONTEND_HOST, "--open"],
        cwd=str(PROJECT_ROOT / "frontend"),
        env=frontend_env,
    )

    backend_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    frontend_url = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

    # 8. 终端信息展示
    print("-" * 60)
    print("  GreatOCR 开发 / 演示环境已启动")
    print("-" * 60)
    print(f"  Session token : {token[:8]}...（前后端共享）")
    print(f"  Backend URL   : {backend_url}")
    print(f"  Frontend URL  : {frontend_url}")
    print(f"  后端 PID      : {backend.pid}")
    print(f"  前端 PID      : {frontend.pid}")
    print()
    print("  浏览器将自动打开前端页面。")
    print("  按 Ctrl+C 关闭前后端进程。")
    print("-" * 60)

    # 9. 监听退出 / Ctrl+C
    try:
        while True:
            if backend.poll() is not None:
                print("\n[WARN] 后端进程已退出（返回码 "
                      f"{backend.returncode}）。前端仍在运行。")
                break
            if frontend.poll() is not None:
                print("\n[WARN] 前端进程已退出（返回码 "
                      f"{frontend.returncode}）。后端仍在运行。")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] 收到 Ctrl+C，正在关闭前后端...")

    print("[INFO] 正在终止子进程...")
    terminate_tree(frontend)
    terminate_tree(backend)
    wait_for(frontend)
    wait_for(backend)
    print("[INFO] 已退出。")
    return 0


if __name__ == "__main__":
    # 让 Ctrl+C 触发 KeyboardInterrupt 进入上面的清理逻辑。
    signal.signal(signal.SIGINT, signal.default_int_handler)
    sys.exit(main())
