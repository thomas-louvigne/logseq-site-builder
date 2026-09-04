import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..domain.page import Page, SiteConfig
from ..ports.interfaces import ContentConverter, PageRepository, SiteWriter
from .link_resolver import LinkResolver, _IMAGE_EXTENSIONS, slugify


class SiteBuilder:
    def __init__(
        self,
        reader: PageRepository,
        converter: ContentConverter,
        writer: SiteWriter,
    ) -> None:
        self._reader = reader
        self._converter = converter
        self._writer = writer
        self.broken_links: list[tuple[str, str]] = []
        self.used_assets: list[str] = []

    def build(
        self,
        config: SiteConfig,
        logseq_assets_dir: Path,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        pages = [p for p in self._reader.find_all() if p.is_public]

        if not pages:
            raise ValueError("No public pages found in the Logseq directory.")

        self.broken_links = []

        # Process regular pages
        resolver = LinkResolver(pages, config.home_slug)
        all_asset_filenames: list[str] = []
        self._process_pages(pages, resolver, config, all_asset_filenames, on_progress)
        self.broken_links.extend(resolver.broken_links)

        # Process journal pages (blog)
        journal_pages: list[Page] = []
        if config.enable_journals:
            journal_pages = list(self._reader.find_journals())
            if journal_pages:
                journal_resolver = LinkResolver(pages + journal_pages, config.home_slug)
                self._process_pages(journal_pages, journal_resolver, config, all_asset_filenames, on_progress)
                self.broken_links.extend(journal_resolver.broken_links)

        home = self._find_home(pages, config.home_slug)

        self._writer.write_static_files()
        self._writer.write_404(config)

        for page in pages:
            self._writer.write_page(page, config, is_home=(page is home))

        if config.enable_journals:
            for page in journal_pages:
                self._writer.write_page(page, config)
            self._writer.write_blog_index(journal_pages, config)
            if config.rss and journal_pages:
                self._writer.write_rss(journal_pages, config)

        unique_assets = list(dict.fromkeys(all_asset_filenames))
        self.used_assets = unique_assets
        self._writer.copy_assets(unique_assets, logseq_assets_dir)

        pages_dir = logseq_assets_dir.parent / config.pages_directory
        self._writer.copy_pages_subdirs(pages_dir)

        for external_dir in config.external_static_dirs:
            self._writer.copy_pages_subdirs(Path(external_dir), require_web_files=False)

        self._writer.write_sitemap(pages, journal_pages, config)
        self._writer.write_robots(config)
        self._writer.write_search_index(pages, journal_pages, config)

    def _process_pages(
        self,
        pages: list[Page],
        resolver: LinkResolver,
        config: SiteConfig,
        all_assets: list[str],
        on_progress: Callable[[str], None] | None,
    ) -> None:
        # Each page's pandoc conversion is an independent subprocess call, so
        # threads give a near-linear speedup (the GIL is released while waiting
        # on the subprocess). Results are applied on the main thread, in
        # submission order, to keep on_progress and asset ordering deterministic.
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._process_page, page, resolver, config) for page in pages]
            for page, future in zip(pages, futures):
                page.html_content = future.result()
                all_assets.extend(page.asset_filenames)
                if on_progress:
                    on_progress(page.title)

    def _process_page(self, page: Page, resolver: LinkResolver, config: SiteConfig) -> str:
        if page.format == "org":
            preprocessed, assets = resolver.preprocess_org(page.raw_content, page.title)
        else:
            preprocessed, assets = resolver.preprocess_md(page.raw_content, page.title)
        page.asset_filenames = assets
        html = self._converter.convert(preprocessed, page.format)
        if page.format == "org" and config.org_listify_headings_from is not None:
            if config.org_listify_headings_from == "auto":
                html = _auto_listify(html)
            else:
                html = _sections_to_lists(html, config.org_listify_headings_from)
        if config.bullet_threading:
            html = _add_collapsible_tree(html)
        return _add_download_to_asset_links(html)

    def _find_home(self, pages: list[Page], home_slug: str) -> Page:
        for page in pages:
            if page.slug == home_slug:
                return page
        # Fallback: match against the source filename stem (user may specify the
        # filename slug when the page has a #+TITLE that generates a different slug)
        for page in pages:
            if slugify(page.source_path.stem) == home_slug:
                return page
        return pages[0]


def _add_download_to_asset_links(html: str) -> str:
    """Add download attribute to non-image asset links."""
    def add_download(m: re.Match) -> str:
        tag = m.group(0)
        href_match = re.search(r'href="([^"]*)"', tag)
        if not href_match:
            return tag
        href = href_match.group(1)
        if not href.startswith("assets/"):
            return tag
        if Path(href).suffix.lower() in _IMAGE_EXTENSIONS:
            return tag
        if "download" in tag:
            return tag
        return tag[:-1] + " download>"

    return re.sub(r"<a\b[^>]*>", add_download, html)


_SECTION_LEVEL_RE = re.compile(r"^level(\d+)$")
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def _section_level(node: object) -> int | None:
    """Return N for a <section class="levelN">, else None."""
    if not isinstance(node, Tag) or node.name != "section":
        return None
    for css_class in node.get("class", []):
        match = _SECTION_LEVEL_RE.match(css_class)
        if match:
            return int(match.group(1))
    return None


def _section_to_li(soup: BeautifulSoup, section: Tag, qualifies: Callable[[object], bool]) -> Tag:
    """Unwrap a heading section into a <li>, recursing into deeper sections first
    so they become nested <ul>s instead of losing their own threading."""
    _sections_to_lists_in(soup, section, qualifies)

    li = soup.new_tag("li")
    if section_id := section.get("id"):
        li["id"] = section_id

    heading = section.find(lambda t: isinstance(t, Tag) and t.name in _HEADING_TAGS, recursive=False)
    if heading is not None:
        p = soup.new_tag("p")
        for child in list(heading.contents):
            p.append(child.extract())
        heading.decompose()
        li.append(p)

    for child in list(section.contents):
        li.append(child.extract())
    return li


def _sections_to_lists_in(soup: BeautifulSoup, container: Tag, qualifies: Callable[[object], bool]) -> None:
    """Replace runs of consecutive heading sections matching `qualifies` among
    `container`'s direct children with a <ul> of <li> items, preserving any
    other content in place."""
    children = list(container.contents)
    i = 0
    while i < len(children):
        if not qualifies(children[i]):
            # Not a qualifying section itself, but one could be nested inside
            # (e.g. a <div> wrapper, or a heading section left as-is).
            if isinstance(children[i], Tag):
                _sections_to_lists_in(soup, children[i], qualifies)
            i += 1
            continue
        # Collect a run of consecutive qualifying sections, tolerating the
        # whitespace-only text nodes Pandoc leaves between sibling tags.
        run = []
        whitespace = []
        j = i
        while j < len(children):
            node = children[j]
            if qualifies(node):
                run.append(node)
                j += 1
            elif isinstance(node, str) and not node.strip():
                whitespace.append(node)
                j += 1
            else:
                break
        ul = soup.new_tag("ul")
        for section in run:
            ul.append(_section_to_li(soup, section, qualifies))
        run[0].insert_before(ul)
        for section in run:
            section.extract()
        for node in whitespace:
            node.extract()
        i = j


def _at_least_level(from_level: int) -> Callable[[object], bool]:
    def qualifies(node: object) -> bool:
        level = _section_level(node)
        return level is not None and level >= from_level

    return qualifies


def _sections_to_lists(html: str, from_level: int) -> str:
    """Render org headings (`*` level >= from_level) as plain nested bullet
    lists instead of Pandoc's <section class="levelN"> heading structure, so
    they get normal bullet threading like any other nested block rather than
    the separate heading-section threading rules. Driven by the
    `org_listify_headings_from` config, which only applies to org pages."""
    soup = BeautifulSoup(html, "html.parser")
    _sections_to_lists_in(soup, soup, _at_least_level(from_level))
    return str(soup)


def _sections_to_normal_in(soup: BeautifulSoup, container: Tag, level: int) -> None:
    """Unwrap every `level`-heading section under `container` into plain
    <p> text, dropping the heading markup entirely (used when a page has
    only one heading level and there's nothing above it to nest bullets
    under)."""
    for child in list(container.contents):
        if _section_level(child) == level:
            heading = child.find(lambda t: isinstance(t, Tag) and t.name in _HEADING_TAGS, recursive=False)
            if heading is not None:
                p = soup.new_tag("p")
                for node in list(heading.contents):
                    p.append(node.extract())
                heading.replace_with(p)
            child.unwrap()
        elif isinstance(child, Tag):
            _sections_to_normal_in(soup, child, level)


def _is_leaf_heading(node: object) -> bool:
    """A heading section is `*`'s "last level" for its own branch when it has
    no nested heading sections of its own — regardless of what depth other
    branches on the page reach. Level 1 never qualifies: it's the page's
    outline root and always stays a real heading (see `_auto_listify`)."""
    level = _section_level(node)
    if level is None or level <= 1:
        return False
    return not any(_section_level(child) is not None for child in node.contents)


def _auto_listify(html: str) -> str:
    """The `org_listify_headings_from = "auto"` mode: per org page, flatten
    every heading section that has no sub-headings of its own (the deepest
    `*` level reached by that particular branch) into a bullet list, while
    branches with sub-headings keep their own heading real. If the whole
    page only uses one heading level (no nesting anywhere), there's nothing
    for it to nest under, so it's rendered as plain text instead."""
    soup = BeautifulSoup(html, "html.parser")
    levels = {lvl for lvl in (_section_level(t) for t in soup.find_all(True)) if lvl is not None}
    if not levels:
        return html
    if len(levels) == 1:
        _sections_to_normal_in(soup, soup, next(iter(levels)))
    else:
        _sections_to_lists_in(soup, soup, _is_leaf_heading)
    return str(soup)


def _wrap_as_details(soup: BeautifulSoup, summary_nodes: list, rest_nodes: list) -> Tag:
    details = soup.new_tag("details")
    details["open"] = ""
    summary = soup.new_tag("summary")
    for node in summary_nodes:
        summary.append(node)
    details.append(summary)
    for node in rest_nodes:
        details.append(node)
    return details


def _make_collapsible(soup: BeautifulSoup, node: object) -> None:
    """Wrap any <li> or heading <section> that has nested content into a
    <details><summary> so the tree view can fold/unfold that branch. Leaves
    (no nested content) are left untouched — nothing to collapse."""
    if not isinstance(node, Tag):
        return
    if node.name == "li":
        _make_collapsible_li(soup, node)
    elif _section_level(node) is not None:
        _make_collapsible_section(soup, node)
    else:
        for child in list(node.contents):
            _make_collapsible(soup, child)


def _make_collapsible_li(soup: BeautifulSoup, li: Tag) -> None:
    children = list(li.contents)
    split = next(
        (i for i, c in enumerate(children) if isinstance(c, Tag) and c.name in ("ul", "ol")),
        None,
    )
    if split is None:
        for child in children:
            _make_collapsible(soup, child)
        return
    summary_nodes = [c.extract() for c in children[:split]]
    rest_nodes = [c.extract() for c in children[split:]]
    for node in rest_nodes:
        _make_collapsible(soup, node)
    li.append(_wrap_as_details(soup, summary_nodes, rest_nodes))


def _make_collapsible_section(soup: BeautifulSoup, section: Tag) -> None:
    children = list(section.contents)
    heading_idx = next(
        (i for i, c in enumerate(children) if isinstance(c, Tag) and c.name in _HEADING_TAGS),
        None,
    )
    if heading_idx is None:
        for child in children:
            _make_collapsible(soup, child)
        return
    rest = children[heading_idx + 1 :]
    has_content = any(isinstance(c, Tag) or (isinstance(c, str) and c.strip()) for c in rest)
    if not has_content:
        return
    heading = children[heading_idx].extract()
    rest_nodes = [c.extract() for c in rest]
    for node in rest_nodes:
        _make_collapsible(soup, node)
    section.append(_wrap_as_details(soup, [heading], rest_nodes))


def _add_collapsible_tree(html: str) -> str:
    """Wrap every branch of the outline (list items and heading sections that
    have nested content) in a native <details>/<summary>, giving the tree-view
    bullet threading a click-to-collapse button on top of its guide lines."""
    soup = BeautifulSoup(html, "html.parser")
    _make_collapsible(soup, soup)
    return str(soup)
