import datetime
import re
from pathlib import Path
from typing import Iterator

from ..domain.page import Page
from ..ports.interfaces import PageRepository
from ..services.link_resolver import slugify

_PUBLIC_TRUE = re.compile(r"#\+PUBLIC:\s*true", re.IGNORECASE)
_TITLE_DIRECTIVE = re.compile(r"#\+TITLE:\s*(.+)", re.IGNORECASE)


def _decode_logseq_filename(stem: str) -> str:
    """Decode Logseq triple-lowbar filename encoding (namespace separator '/')."""
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


def _java_date_fmt_to_strftime(fmt: str) -> str:
    """Convert a Java/Logseq date format string to Python strftime format.

    Uses a single-pass regex so longer tokens are matched first and replaced
    text is never re-scanned.
    """
    tokens = [
        ("EEEE", "%A"),
        ("EEE",  "%a"),
        ("MMMM", "%B"),
        ("MMM",  "%b"),
        ("MM",   "%m"),
        ("M",    "%-m"),
        ("yyyy", "%Y"),
        ("yy",   "%y"),
        ("dd",   "%d"),
        # "do" = ordinal day (1st/2nd/…) — approximated as plain number
        ("do",   "%-d"),
        ("d",    "%-d"),
    ]
    pattern = "|".join(re.escape(t) for t, _ in tokens)
    token_map = dict(tokens)
    return re.sub(pattern, lambda m: token_map[m.group(0)], fmt)


class LogseqReader(PageRepository):
    def __init__(
        self,
        input_dir: Path,
        all_public: bool = False,
        pages_directory: str = "pages",
        journals_directory: str = "journals",
        hidden: list[str] | None = None,
        journal_page_title_format: str = "dd-MM-yyyy",
        journal_file_name_format: str = "yyyy_MM_dd",
    ) -> None:
        self._input_dir = input_dir
        self._all_public = all_public
        self._pages_dir = self._resolve_dir(pages_directory)
        self._journals_dir = self._resolve_dir(journals_directory)
        self._hidden = [h.lstrip("/") for h in (hidden or [])]
        self._title_fmt = _java_date_fmt_to_strftime(journal_page_title_format)
        self._file_name_fmt = _java_date_fmt_to_strftime(journal_file_name_format)

    def _resolve_dir(self, name: str) -> Path:
        candidate = self._input_dir / name
        return candidate if candidate.is_dir() else self._input_dir

    def _is_hidden(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self._input_dir).as_posix()
        except ValueError:
            return False
        return any(rel == h or rel.startswith(h.rstrip("/") + "/") for h in self._hidden)

    def find_all(self) -> Iterator[Page]:
        for path in sorted(self._pages_dir.iterdir()):
            if path.suffix not in (".org", ".md"):
                continue
            if self._is_hidden(path):
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

    def find_journals(self) -> Iterator[Page]:
        """Yield public journal pages sorted by date descending (newest first)."""
        if not self._journals_dir.is_dir():
            return
        pages: list[Page] = []
        for path in self._journals_dir.iterdir():
            if path.suffix not in (".org", ".md"):
                continue
            if self._is_hidden(path):
                continue
            date = self._parse_date(path.stem)
            if date is None:
                continue
            content = path.read_text(encoding="utf-8")
            if not _parse_is_public(content, self._all_public):
                continue
            title = self._format_title(date)
            slug = f"journal-{date.isoformat()}"
            pages.append(Page(
                title=title,
                slug=slug,
                raw_content=content,
                source_path=path,
                format="org" if path.suffix == ".org" else "md",
                is_public=True,
                date=date,
            ))
        yield from sorted(pages, key=lambda p: p.date, reverse=True)  # type: ignore[arg-type]

    def _parse_date(self, stem: str) -> datetime.date | None:
        try:
            return datetime.datetime.strptime(stem, self._file_name_fmt).date()
        except ValueError:
            return None

    def _format_title(self, date: datetime.date) -> str:
        try:
            return date.strftime(self._title_fmt)
        except Exception:
            return date.isoformat()
