import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..domain.page import Page, PageFormat
from ..domain.paths import is_image, slugify

# Extensions that identify a non-page file target (to be treated as asset).
_PAGE_EXTENSIONS = frozenset({".org", ".md", ".html"})


def _looks_like_file(target: str) -> bool:
    """True when the target has a non-page file extension (e.g. .pdf, .map, .zip)."""
    suffix = Path(target.split("/")[-1]).suffix.lower()
    # Reject suffixes that contain spaces or are longer than 8 chars — those are
    # names with dots that aren't extensions (e.g. "Dr. Livia Morozov" → ". Livia Morozov").
    if not re.match(r'^\.[a-z0-9]{1,8}$', suffix):
        return False
    return suffix not in _PAGE_EXTENSIONS


# [[../assets/file]] or [[../assets/file][label]]
_ASSET_REL = re.compile(r"\[\[\.\./assets/([^\]]+)\](?:\[([^\]]+)\])?\]")
_LABELED_LINK = re.compile(r"\[\[([^\]]+)\]\[([^\]]+)\]\]")
_SIMPLE_LINK = re.compile(r"\[\[([^\]]+)\]\]")
_HASHTAG_COMPOUND = re.compile(r"#\[\[([^\]]+)\]\]")
# Matches #word hashtags — excludes #+directives, #[[compound]] (handled separately),
# and labels already inside generated links (preceded by [ in org ][#tag] or md [#tag]).
_HASHTAG_SIMPLE = re.compile(r"(?<![a-zA-Z0-9_\[])#([^\W\d_][\w-]*)")
_PROPERTIES_BLOCK = re.compile(r":PROPERTIES:.*?:END:", re.DOTALL)
_LOGBOOK_BLOCK = re.compile(r":LOGBOOK:.*?:END:", re.DOTALL)
_MD_PROPERTIES_BLOCK = re.compile(r"^(?:[a-z][a-z0-9_-]*::[^\n]*\n?)+", re.IGNORECASE)
_PUBLIC_DIRECTIVE = re.compile(r"#\+PUBLIC:[^\n]*\n?", re.IGNORECASE)
_EMPTY_HEADING = re.compile(r"^\*+\s*$", re.MULTILINE)


def _clean_org(content: str) -> str:
    # _MD_PROPERTIES_BLOCK only matches at the very start of the file, so it
    # runs again once #+PUBLIC is gone in case properties followed it.
    for pattern in (
        _MD_PROPERTIES_BLOCK, _PUBLIC_DIRECTIVE, _MD_PROPERTIES_BLOCK,
        _PROPERTIES_BLOCK, _LOGBOOK_BLOCK, _EMPTY_HEADING,
    ):
        content = pattern.sub("", content)
    return content


def _clean_md(content: str) -> str:
    return _MD_PROPERTIES_BLOCK.sub("", content)


def _org_asset(path: str, label: str | None) -> str:
    # No label → pandoc emits <img> for images, which is what we want.
    # file: prefix is required for pandoc to resolve the link at all.
    return f"[[file:assets/{path}][{label}]]" if label else f"[[file:assets/{path}]]"


def _md_asset(path: str, label: str | None) -> str:
    bang = "!" if is_image(path) else ""
    return f"{bang}[{label or path}](assets/{path})"


@dataclass(frozen=True)
class _Syntax:
    """How one source format spells the links the resolver rewrites."""

    clean: Callable[[str], str]
    link: Callable[[str, str], str]  # (href, label)
    asset: Callable[[str, str | None], str]  # (path under assets/, label)
    bare_external: Callable[[str], str]  # unlabeled external URL
    external_prefixes: tuple[str, ...]
    page_href_prefix: str = ""
    # Extra prefixes that mark an unlabeled [[target]] as an asset.
    asset_prefixes: tuple[str, ...] = ()


_SYNTAXES: dict[PageFormat, _Syntax] = {
    "org": _Syntax(
        clean=_clean_org,
        link=lambda href, label: f"[[{href}][{label}]]",
        asset=_org_asset,
        bare_external=lambda target: f"[[{target}]]",
        external_prefixes=("http://", "https://", "file:"),
        # pandoc org parser requires "file:" prefix to emit a real <a> tag
        page_href_prefix="file:",
    ),
    "md": _Syntax(
        clean=_clean_md,
        link=lambda href, label: f"[{label}]({href})",
        asset=_md_asset,
        bare_external=lambda target: f"<{target}>",
        external_prefixes=("http://", "https://"),
        asset_prefixes=("assets/",),
    ),
}


class LinkResolver:
    def __init__(self, pages: list[Page], home_slug: str) -> None:
        self._slug_map = self._build_slug_map(pages)
        self._known_slugs = frozenset(page.slug for page in pages)
        self._home_slug = home_slug
        # (source_page_title, target) pairs for links that resolve to no known page.
        self.broken_links: list[tuple[str, str]] = []

    def _build_slug_map(self, pages: list[Page]) -> dict[str, str]:
        slug_map: dict[str, str] = {}
        for page in pages:
            slug_map[page.title.lower()] = page.slug
            slug_map[page.slug.lower()] = page.slug
        # A page whose #+TITLE differs from its filename can also be linked by
        # filename (e.g. [[ma-page]] → mon-super-titre.html). Titles and slugs
        # win on collision.
        for page in pages:
            slug_map.setdefault(slugify(page.source_path.stem), page.slug)
        return slug_map

    def _page_name_to_href(self, target: str, source: str) -> str:
        slug = self._slug_map.get(target.lower())
        if slug is None:
            # Case/accents/dashes may differ from the page title (e.g. "epoque-tracogna"
            # vs "Époque Tracogna") yet still resolve to the same page — slugify() folds
            # accents and normalizes separators the same way page slugs were generated.
            candidate = slugify(target)
            slug = self._slug_map.get(candidate, candidate)
            if slug not in self._known_slugs:
                self.broken_links.append((source, target))
        return "index.html" if slug == self._home_slug else f"{slug}.html"

    def preprocess_org(self, content: str, source: str = "") -> tuple[str, list[str]]:
        """Clean and rewrite Logseq org content for pandoc.

        Returns (processed_content, list_of_asset_filenames).
        """
        return self._preprocess(content, source, _SYNTAXES["org"])

    def preprocess_md(self, content: str, source: str = "") -> tuple[str, list[str]]:
        """Rewrite Logseq markdown content for pandoc."""
        return self._preprocess(content, source, _SYNTAXES["md"])

    def preprocess(self, content: str, fmt: PageFormat, source: str = "") -> tuple[str, list[str]]:
        return self._preprocess(content, source, _SYNTAXES[fmt])

    def _preprocess(self, content: str, source: str, syntax: _Syntax) -> tuple[str, list[str]]:
        assets: list[str] = []

        def asset(path: str, label: str | None) -> str:
            assets.append(path)
            return syntax.asset(path, label)

        def page_link(target: str, label: str) -> str:
            return syntax.link(syntax.page_href_prefix + self._page_name_to_href(target, source), label)

        content = syntax.clean(content)

        content = _ASSET_REL.sub(lambda m: asset(m.group(1), m.group(2)), content)

        # _LABELED_LINK first: [[page][label]] — must precede _HASHTAG_COMPOUND so
        # the resulting link is never re-processed by later patterns.
        def replace_labeled(m: re.Match) -> str:
            target, label = m.group(1), m.group(2)
            if target.startswith(syntax.external_prefixes):
                return syntax.link(target, label)
            if _looks_like_file(target):
                return asset(Path(target).name, label)
            return page_link(target, label)

        content = _LABELED_LINK.sub(replace_labeled, content)

        # _HASHTAG_COMPOUND after _LABELED_LINK (safe: #[[tag]] has no ][ inside)
        # and before _SIMPLE_LINK (to prevent [[tag]] inside #[[tag]] being caught).
        # The generated org [[file:...][#tag]] is not re-caught because _SIMPLE_LINK
        # requires ]] immediately after the target.
        content = _HASHTAG_COMPOUND.sub(lambda m: page_link(m.group(1), f"#{m.group(1)}"), content)

        def replace_simple(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith(syntax.external_prefixes):
                return syntax.bare_external(target)
            if target.startswith(syntax.asset_prefixes) or _looks_like_file(target):
                return asset(Path(target).name, None)
            return page_link(target, target)

        content = _SIMPLE_LINK.sub(replace_simple, content)

        # _HASHTAG_SIMPLE last: #word has no overlap with [[...]] syntax.
        content = _HASHTAG_SIMPLE.sub(lambda m: page_link(m.group(1), f"#{m.group(1)}"), content)

        return content, assets
