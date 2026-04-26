import re
import unicodedata
from pathlib import Path

from ..domain.page import Page

_IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".bmp", ".ico", ".tiff", ".tif", ".avif",
})

# Extensions that identify a non-page file target (to be treated as asset).
_PAGE_EXTENSIONS = frozenset({".org", ".md", ".html"})


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _looks_like_file(target: str) -> bool:
    """True when the target has a non-page file extension (e.g. .pdf, .map, .zip)."""
    suffix = Path(target.split("/")[-1]).suffix.lower()
    return bool(suffix) and suffix not in _PAGE_EXTENSIONS


# [[../assets/file]] or [[../assets/file][label]]
_ASSET_REL = re.compile(r"\[\[\.\./assets/([^\]]+)\](?:\[([^\]]+)\])?\]")
_LABELED_LINK = re.compile(r"\[\[([^\]]+)\]\[([^\]]+)\]\]")
_SIMPLE_LINK = re.compile(r"\[\[([^\]]+)\]\]")
_HASHTAG_COMPOUND = re.compile(r"#\[\[([^\]]+)\]\]")
# Matches #word hashtags — excludes #+directives, #[[compound]] (handled separately),
# and labels already inside generated links (preceded by [ in org ][#tag] or md [#tag]).
_HASHTAG_SIMPLE = re.compile(r"(?<![a-zA-Z0-9_\[])#([A-Za-z][A-Za-z0-9_-]*)")
_PROPERTIES_BLOCK = re.compile(r":PROPERTIES:.*?:END:", re.DOTALL)
_LOGBOOK_BLOCK = re.compile(r":LOGBOOK:.*?:END:", re.DOTALL)
_PUBLIC_DIRECTIVE = re.compile(r"#\+PUBLIC:[^\n]*\n?", re.IGNORECASE)


class LinkResolver:
    def __init__(self, pages: list[Page], home_slug: str) -> None:
        self._slug_map = self._build_slug_map(pages)
        self._home_slug = home_slug

    def _build_slug_map(self, pages: list[Page]) -> dict[str, str]:
        slug_map: dict[str, str] = {}
        for page in pages:
            slug_map[page.title.lower()] = page.slug
            slug_map[page.slug.lower()] = page.slug
        return slug_map

    def _slug_to_href(self, slug: str) -> str:
        filename = "index.html" if slug == self._home_slug else f"{slug}.html"
        # pandoc org parser requires "file:" prefix to emit a real <a> tag
        return f"file:{filename}"

    def _page_name_to_href(self, target: str) -> str:
        slug = self._slug_map.get(target.lower(), slugify(target))
        return self._slug_to_href(slug)

    def preprocess_org(self, content: str) -> tuple[str, list[str]]:
        """Clean and rewrite Logseq org content for pandoc.

        Returns (processed_content, list_of_asset_filenames).
        """
        assets: list[str] = []

        content = _PUBLIC_DIRECTIVE.sub("", content)
        content = _PROPERTIES_BLOCK.sub("", content)
        content = _LOGBOOK_BLOCK.sub("", content)

        def replace_asset(m: re.Match) -> str:
            filename, label = m.group(1), m.group(2)
            assets.append(filename)
            if label:
                return f"[[file:assets/{filename}][{label}]]"
            # No label → pandoc emits <img> for images, which is what we want.
            # file: prefix is required for pandoc to resolve the link at all.
            return f"[[file:assets/{filename}]]"

        content = _ASSET_REL.sub(replace_asset, content)

        # _LABELED_LINK first: [[page][label]] — must precede _HASHTAG_COMPOUND so
        # the resulting [[file:...][label]] is never re-processed by later patterns.
        def replace_labeled(m: re.Match) -> str:
            target, label = m.group(1), m.group(2)
            if target.startswith(("http://", "https://", "file:")):
                return f"[[{target}][{label}]]"
            if _looks_like_file(target):
                basename = Path(target).name
                assets.append(basename)
                return f"[[file:assets/{basename}][{label}]]"
            href = self._page_name_to_href(target)
            return f"[[{href}][{label}]]"

        content = _LABELED_LINK.sub(replace_labeled, content)

        # _HASHTAG_COMPOUND after _LABELED_LINK (safe: #[[tag]] has no ][ inside)
        # and before _SIMPLE_LINK (to prevent [[tag]] inside #[[tag]] being caught).
        # Result [[file:...][#tag]] is not re-caught because _SIMPLE_LINK requires ]]
        # immediately after the target, which won't match the ][label]] suffix.
        def replace_hashtag_compound(m: re.Match) -> str:
            tag = m.group(1)
            href = self._page_name_to_href(tag)
            return f"[[{href}][#{tag}]]"

        content = _HASHTAG_COMPOUND.sub(replace_hashtag_compound, content)

        def replace_simple(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith(("http://", "https://", "file:")):
                return f"[[{target}]]"
            if _looks_like_file(target):
                basename = Path(target).name
                assets.append(basename)
                return f"[[file:assets/{basename}]]"
            href = self._page_name_to_href(target)
            return f"[[{href}][{target}]]"

        content = _SIMPLE_LINK.sub(replace_simple, content)

        # _HASHTAG_SIMPLE last: #word has no overlap with [[...]] syntax.
        def replace_hashtag_simple(m: re.Match) -> str:
            tag = m.group(1)
            href = self._page_name_to_href(tag)
            return f"[[{href}][#{tag}]]"

        content = _HASHTAG_SIMPLE.sub(replace_hashtag_simple, content)

        return content, assets

    def preprocess_md(self, content: str) -> tuple[str, list[str]]:
        """Rewrite Logseq markdown content for pandoc."""
        assets: list[str] = []

        # [[../assets/file]] or [[../assets/file][label]]
        _md_asset = re.compile(r"\[\[\.\.\/assets\/([^\]]+)\](?:\[([^\]]+)\])?\]")
        _md_labeled = re.compile(r"\[\[([^\]]+)\]\[([^\]]+)\]\]")
        _md_simple = re.compile(r"\[\[([^\]]+)\]\]")

        def replace_asset(m: re.Match) -> str:
            filename, label = m.group(1), m.group(2)
            assets.append(filename)
            ext = Path(filename).suffix.lower()
            display = label or filename
            if ext in _IMAGE_EXTENSIONS:
                return f"![{display}](assets/{filename})"
            return f"[{display}](assets/{filename})"

        content = _md_asset.sub(replace_asset, content)

        def replace_labeled(m: re.Match) -> str:
            target, label = m.group(1), m.group(2)
            if target.startswith(("http://", "https://")):
                return f"[{label}]({target})"
            if _looks_like_file(target):
                basename = Path(target).name
                assets.append(basename)
                ext = Path(basename).suffix.lower()
                if ext in _IMAGE_EXTENSIONS:
                    return f"![{label}](assets/{basename})"
                return f"[{label}](assets/{basename})"
            href = self._page_name_to_href(target)
            return f"[{label}]({href})"

        content = _md_labeled.sub(replace_labeled, content)

        # Compound hashtag before simple link (same ordering logic as org).
        def replace_hashtag_compound_md(m: re.Match) -> str:
            tag = m.group(1)
            href = self._page_name_to_href(tag)
            return f"[#{tag}]({href})"

        content = _HASHTAG_COMPOUND.sub(replace_hashtag_compound_md, content)

        def replace_simple(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith(("http://", "https://")):
                return f"<{target}>"
            if target.startswith("assets/") or _looks_like_file(target):
                basename = Path(target).name
                assets.append(basename)
                ext = Path(basename).suffix.lower()
                if ext in _IMAGE_EXTENSIONS:
                    return f"![{basename}](assets/{basename})"
                return f"[{basename}](assets/{basename})"
            href = self._page_name_to_href(target)
            return f"[{target}]({href})"

        content = _md_simple.sub(replace_simple, content)

        def replace_hashtag_simple_md(m: re.Match) -> str:
            tag = m.group(1)
            href = self._page_name_to_href(tag)
            return f"[#{tag}]({href})"

        content = _HASHTAG_SIMPLE.sub(replace_hashtag_simple_md, content)

        return content, assets
