import re
from pathlib import Path

_EDN_COMMENT = re.compile(r";[^\n]*")


def _strip_comments(text: str) -> str:
    return _EDN_COMMENT.sub("", text)


def load_edn_config(logseq_dir: Path) -> dict:
    """Parse relevant keys from logseq/config.edn and return a TOML-shaped dict."""
    config_path = logseq_dir / "logseq" / "config.edn"
    if not config_path.exists():
        return {}
    text = _strip_comments(config_path.read_text(encoding="utf-8"))

    site: dict = {}

    m = re.search(r":publishing/all-pages-public\?\s+(true|false)", text)
    if m:
        site["all_public"] = m.group(1) == "true"

    m = re.search(r":default-home\s*\{[^}]*:page\s+\"([^\"]+)\"", text)
    if m:
        site["home_page"] = m.group(1)

    m = re.search(r":hidden\s*\[([^\]]*)\]", text, re.DOTALL)
    if m:
        site["hidden"] = re.findall(r'"([^"]*)"', m.group(1))

    m = re.search(r":feature/enable-journals\?\s+(true|false)", text)
    if m:
        site["enable_journals"] = m.group(1) == "true"

    m = re.search(r':pages-directory\s+"([^"]+)"', text)
    if m:
        site["pages_directory"] = m.group(1)

    m = re.search(r':journals-directory\s+"([^"]+)"', text)
    if m:
        site["journals_directory"] = m.group(1)

    m = re.search(r':journal/page-title-format\s+"([^"]+)"', text)
    if m:
        site["journal_page_title_format"] = m.group(1)

    m = re.search(r':journal/file-name-format\s+"([^"]+)"', text)
    if m:
        site["journal_file_name_format"] = m.group(1)

    return {"site": site} if site else {}


def generate_toml(logseq_dir: Path) -> Path:
    """Write logseq-site-builder.toml bootstrapped from config.edn values.

    Only writes keys that were actually found in config.edn; everything else
    is left as commented-out examples so the file stays minimal and readable.
    Returns the path of the written file.
    """
    site = load_edn_config(logseq_dir).get("site", {})

    def val(key: str, default: str, comment: str = "") -> str:
        if key not in site:
            return f"# {key} = {default}"
        raw = site[key]
        if isinstance(raw, bool):
            toml_val = "true" if raw else "false"
        elif isinstance(raw, list):
            toml_val = "[" + ", ".join(f'"{v}"' for v in raw) + "]"
        else:
            toml_val = f'"{raw}"'
        suffix = f"  # from {comment}" if comment else ""
        return f"{key} = {toml_val}{suffix}"

    lines = [
        "# logseq-site-builder.toml",
        "# Auto-generated from logseq/config.edn on first run. Edit freely.",
        "# Priority: CLI options > this file > logseq/config.edn",
        "# Full reference: logseq-site-builder.example.toml",
        "",
        "[site]",
        '# title       = "My Site"',
        '# author      = ""',
        '# description = ""',
        '# base_url    = "https://example.com"  # required for sitemap, canonical URLs and RSS',
        '# lang        = "en"                   # HTML lang attribute (e.g. "fr", "de")',
        "",
        val("home_page", '"home"', ":default-home"),
        val("all_public", "false", ":publishing/all-pages-public?"),
        val("hidden", "[]", ":hidden"),
        val("pages_directory", '"pages"', ":pages-directory"),
        val("journals_directory", '"journals"', ":journals-directory"),
        "",
        "# ── Theme ────────────────────────────────────────────────────────────────────",
        "# Built-in: \"default\", \"dark\", \"nord\"  |  or a path relative to this directory",
        '# theme = "default"',
        "",
        "# ── Blog ─────────────────────────────────────────────────────────────────────",
        "",
        val("enable_journals", "false", ":feature/enable-journals?"),
        '# blog_title = "Blog"',
        '# blog_slug  = "blog"',
        '# rss        = false',
        val("journal_page_title_format", '"dd-MM-yyyy"', ":journal/page-title-format"),
        val("journal_file_name_format", '"yyyy_MM_dd"', ":journal/file-name-format"),
        "",
        "# ── Navigation menu ──────────────────────────────────────────────────────────",
        "# [[menu]]",
        '# label = "Home"',
        '# slug  = "home"',
        "",
        "# ── Social links ─────────────────────────────────────────────────────────────",
        "# [social_networks]",
        '# GitHub = "https://github.com/your-username"',
        "",
    ]

    toml_path = logseq_dir / "logseq-site-builder.toml"
    toml_path.write_text("\n".join(lines), encoding="utf-8")
    return toml_path
