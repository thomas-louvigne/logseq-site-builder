from pathlib import Path

THEMES_DIR = Path(__file__).parent.parent / "themes"
DEFAULT_THEME_CSS = THEMES_DIR / "default.css"


def builtin_theme_names() -> list[str]:
    return [p.stem for p in THEMES_DIR.glob("*.css")]


def resolve_theme_css(theme: str, logseq_dir: Path) -> Path | None:
    """Resolve a theme name or path to an absolute CSS file path.

    Resolution order:
    1. Built-in theme name (e.g. "dark" → themes/dark.css)
    2. Path relative to the Logseq project directory
    3. Absolute path
    """
    # Built-in theme by name (no extension, no path separators)
    if not theme.endswith(".css") and "/" not in theme and "\\" not in theme:
        candidate = THEMES_DIR / f"{theme}.css"
        if candidate.exists():
            return candidate

    candidate = logseq_dir / theme
    if candidate.exists():
        return candidate

    absolute = Path(theme)
    if absolute.is_absolute() and absolute.exists():
        return absolute

    return None
