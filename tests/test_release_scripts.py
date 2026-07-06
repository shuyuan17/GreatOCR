from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_install_bat_owns_all_install_work() -> None:
    content = (ROOT / "install.bat").read_text(encoding="utf-8")

    assert ":resolve_node" in content
    assert "node.exe" in content
    assert "npm-cli.js" in content
    assert "scripts\\install_frontend.mjs" in content
    assert ".greatocr-installed" in content


def test_start_bat_does_not_reinstall_dependencies() -> None:
    content = (ROOT / "start.bat").read_text(encoding="utf-8")

    assert ":resolve_node" in content
    assert "GREATOCR_SESSION_TOKEN" in content
    assert "VITE_GREAT_OCR_TOKEN" in content
    assert "node.exe" in content
    assert ".greatocr-installed" in content
    assert "npx pnpm" not in content
    assert "install -g pnpm" not in content
    assert "node_modules\\vite\\bin\\vite.js" in content


def test_session_token_flow_uses_startup_env_only() -> None:
    start_content = (ROOT / "start.bat").read_text(encoding="utf-8")
    serve_content = (ROOT / "scripts" / "serve.py").read_text(encoding="utf-8")
    main_content = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")

    assert "secrets.token_hex(32)" in start_content
    assert 'set "VITE_GREAT_OCR_TOKEN=%GREATOCR_SESSION_TOKEN%"' in start_content
    assert 'os.environ["GREATOCR_SESSION_TOKEN"]' in serve_content
    assert "secrets.token_hex" not in serve_content
    assert "generateSessionToken" not in main_content
    assert "VITE_GREAT_OCR_TOKEN" in main_content


def test_frontend_installer_targets_single_frontend_directory() -> None:
    content = (ROOT / "scripts" / "install_frontend.mjs").read_text(encoding="utf-8")

    assert 'const frontendDir = resolve(rootDir, "frontend")' in content
    assert "process.chdir(frontendDir)" not in content
    assert "--dir" in content
