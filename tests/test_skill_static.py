import subprocess
import sys
import re
from pathlib import Path


SKILL_DIR = Path("skills/greatocr-document-reconstruction")


def read_frontmatter() -> dict[str, str]:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    header = text.split("---", 2)[1]
    pairs = {}
    for line in header.strip().splitlines():
        key, value = line.split(":", 1)
        pairs[key.strip()] = value.strip()
    return pairs


def test_skill_md_exists_with_only_name_and_description_frontmatter() -> None:
    frontmatter = read_frontmatter()

    assert set(frontmatter) == {"name", "description"}


def test_skill_name_is_lowercase_hyphen() -> None:
    assert read_frontmatter()["name"] == "greatocr-document-reconstruction"


def test_references_exist_and_are_linked() -> None:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert (SKILL_DIR / "references" / "default-questionnaire.md").is_file()
    assert (SKILL_DIR / "references" / "security-policy.md").is_file()
    assert "references/default-questionnaire.md" in skill_text
    assert "references/security-policy.md" in skill_text


def test_skill_files_do_not_contain_api_key_placeholder() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in SKILL_DIR.rglob("*") if path.is_file())

    assert re.search(r"sk-[A-Za-z0-9]{10,}", text) is None
    assert "API_KEY=" not in text


def test_run_script_dry_run_calls_greatocr_cli(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.7 sample")

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "run_greatocr.py"),
            str(pdf),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert "python -m greatocr.cli convert" in result.stdout
