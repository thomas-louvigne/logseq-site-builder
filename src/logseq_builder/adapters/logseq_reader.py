import re
from pathlib import Path
from typing import Iterator

from ..domain.page import Page
from ..ports.interfaces import PageRepository
from ..services.link_resolver import slugify

_PUBLIC_TRUE = re.compile(r"#\+PUBLIC:\s*true", re.IGNORECASE)
_TITLE_DIRECTIVE = re.compile(r"#\+TITLE:\s*(.+)", re.IGNORECASE)
_ALL_PUBLIC_EDN = re.compile(r":publishing/all-pages-public\?\s+true")
_DEFAULT_HOME_EDN = re.compile(r'^[^;]*:default-home\s*\{[^}]*:page\s+"([^"]+)"', re.MULTILINE)


def _decode_logseq_filename(stem: str) -> str:
    """Decode Logseq triple-lowbar filename encoding.

    In :triple-lowbar format, '___' encodes the namespace separator '/'.
    We flatten namespaces to a single slug level.
    """
    parts = stem.split("___")
    return parts[-1]


def _parse_title(content: str, filename_stem: str) -> str:
    m = _TITLE_DIRECTIVE.search(content)
    if m:
        return m.group(1).strip()
    readable = _decode_logseq_filename(filename_stem).replace("-", " ").replace("_", " ")
    return readable.strip()


def _parse_is_public(content: str, all_public: bool) -> bool:
    if all_public:
        return True
    return bool(_PUBLIC_TRUE.search(content))


class LogseqReader(PageRepository):
    def __init__(self, input_dir: Path, all_public: bool = False) -> None:
        self._input_dir = input_dir
        config_text = self._read_config(input_dir)
        self._all_public = all_public or bool(_ALL_PUBLIC_EDN.search(config_text))
        self.default_home_slug = self._parse_default_home(config_text)

    def _read_config(self, input_dir: Path) -> str:
        config_path = input_dir / "logseq" / "config.edn"
        if config_path.exists():
            return config_path.read_text(encoding="utf-8")
        return ""

    def _parse_default_home(self, config_text: str) -> str | None:
        m = _DEFAULT_HOME_EDN.search(config_text)
        if m:
            return slugify(m.group(1))
        return None

    def _pages_dir(self) -> Path:
        pages = self._input_dir / "pages"
        if pages.is_dir():
            return pages
        return self._input_dir

    def find_all(self) -> Iterator[Page]:
        pages_dir = self._pages_dir()
        for path in sorted(pages_dir.iterdir()):
            if path.suffix not in (".org", ".md"):
                continue
            content = path.read_text(encoding="utf-8")
            is_public = _parse_is_public(content, self._all_public)
            title = _parse_title(content, path.stem)
            slug = slugify(title)
            yield Page(
                title=title,
                slug=slug,
                raw_content=content,
                source_path=path,
                format="org" if path.suffix == ".org" else "md",
                is_public=is_public,
            )
