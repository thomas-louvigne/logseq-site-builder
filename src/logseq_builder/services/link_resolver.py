import re
import unicodedata

from ..domain.page import Page


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


_ASSET_REL = re.compile(r"\[\[\.\./assets/([^\]]+)\]\]")
_LABELED_LINK = re.compile(r"\[\[([^\]]+)\]\[([^\]]+)\]\]")
_SIMPLE_LINK = re.compile(r"\[\[([^\]]+)\]\]")
_HASHTAG_COMPOUND = re.compile(r"#\[\[([^\]]+)\]\]")
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
            filename = m.group(1)
            assets.append(filename)
            # No label → pandoc emits <img>, which is what we want for images.
            # file: prefix is required for pandoc to resolve the link at all.
            return f"[[file:assets/{filename}]]"

        content = _ASSET_REL.sub(replace_asset, content)

        # Must run before simple-link so #[[tag]] is not caught by [[...]] first
        content = _HASHTAG_COMPOUND.sub(lambda m: m.group(1), content)

        def replace_labeled(m: re.Match) -> str:
            target, label = m.group(1), m.group(2)
            if target.startswith(("http://", "https://")):
                return f"[[{target}][{label}]]"
            href = self._page_name_to_href(target)
            return f"[[{href}][{label}]]"

        content = _LABELED_LINK.sub(replace_labeled, content)

        def replace_simple(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith(("http://", "https://", "file:")):
                return f"[[{target}]]"
            href = self._page_name_to_href(target)
            return f"[[{href}][{target}]]"

        content = _SIMPLE_LINK.sub(replace_simple, content)

        return content, assets

    def preprocess_md(self, content: str) -> tuple[str, list[str]]:
        """Rewrite Logseq markdown content for pandoc."""
        assets: list[str] = []

        _md_asset = re.compile(r"\[\[\.\.\/assets\/([^\]]+)\]\]")
        _md_labeled = re.compile(r"\[\[([^\]]+)\]\[([^\]]+)\]\]")
        _md_simple = re.compile(r"\[\[([^\]]+)\]\]")

        def replace_asset(m: re.Match) -> str:
            filename = m.group(1)
            assets.append(filename)
            return f"![{filename}](assets/{filename})"

        content = _md_asset.sub(replace_asset, content)

        def replace_labeled(m: re.Match) -> str:
            target, label = m.group(1), m.group(2)
            if target.startswith(("http://", "https://")):
                return f"[{label}]({target})"
            href = self._page_name_to_href(target)
            return f"[{label}]({href})"

        content = _md_labeled.sub(replace_labeled, content)

        def replace_simple(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith(("http://", "https://")):
                return f"<{target}>"
            if target.startswith("assets/"):
                return f"![{target}]({target})"
            href = self._page_name_to_href(target)
            return f"[{target}]({href})"

        content = _md_simple.sub(replace_simple, content)

        return content, assets
