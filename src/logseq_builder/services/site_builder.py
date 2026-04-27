import re
from pathlib import Path

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

    def build(self, config: SiteConfig, logseq_assets_dir: Path) -> None:
        pages = [p for p in self._reader.find_all() if p.is_public]

        if not pages:
            raise ValueError("No public pages found in the Logseq directory.")

        # Process regular pages
        resolver = LinkResolver(pages, config.home_slug)
        all_asset_filenames: list[str] = []
        for page in pages:
            page.html_content = self._process_page(page, resolver, config)
            all_asset_filenames.extend(page.asset_filenames)

        # Process journal pages (blog)
        journal_pages: list[Page] = []
        if config.enable_journals:
            journal_pages = list(self._reader.find_journals())
            if journal_pages:
                journal_resolver = LinkResolver(pages + journal_pages, config.home_slug)
                for page in journal_pages:
                    page.html_content = self._process_page(page, journal_resolver, config)
                    all_asset_filenames.extend(page.asset_filenames)

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
        self._writer.copy_assets(unique_assets, logseq_assets_dir)

    def _process_page(self, page: Page, resolver: LinkResolver, config: SiteConfig) -> str:
        if page.format == "org":
            preprocessed, assets = resolver.preprocess_org(page.raw_content)
        else:
            preprocessed, assets = resolver.preprocess_md(page.raw_content)
        page.asset_filenames = assets
        html = self._converter.convert(preprocessed, page.format)
        if config.flatten_headings_from is not None:
            html = _flatten_headings(html, config.flatten_headings_from)
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


def _flatten_headings(html: str, from_level: int) -> str:
    """Replace <hN> tags (N >= from_level) with <p> in the generated HTML."""
    for level in range(from_level, 7):
        html = re.sub(
            rf"<h{level}[^>]*>(.*?)</h{level}>",
            r"<p>\1</p>",
            html,
            flags=re.DOTALL,
        )
    return html
