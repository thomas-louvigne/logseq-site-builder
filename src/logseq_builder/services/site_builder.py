from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..domain.page import Page, SiteConfig
from ..domain.paths import slugify
from ..ports.interfaces import ContentConverter, PageRepository, SiteWriter
from .html_transforms import postprocess
from .link_resolver import LinkResolver

ProgressCallback = Callable[[str], None]


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
        on_progress: ProgressCallback | None = None,
    ) -> None:
        pages = [p for p in self._reader.find_all() if p.is_public]
        if not pages:
            raise ValueError("No public pages found in the Logseq directory.")
        journal_pages = list(self._reader.find_journals()) if config.enable_journals else []

        self.broken_links = []
        assets: list[str] = []
        self._convert_pages(pages, pages, config, assets, on_progress)
        # Journals may link to regular pages, so they resolve against both sets.
        self._convert_pages(journal_pages, pages + journal_pages, config, assets, on_progress)
        self.used_assets = list(dict.fromkeys(assets))

        self._write_site(pages, journal_pages, config, logseq_assets_dir)

    def _convert_pages(
        self,
        pages: list[Page],
        link_targets: list[Page],
        config: SiteConfig,
        assets: list[str],
        on_progress: ProgressCallback | None,
    ) -> None:
        if not pages:
            return
        resolver = LinkResolver(link_targets, config.home_slug)
        # Each page's pandoc conversion is an independent subprocess call, so
        # threads give a near-linear speedup (the GIL is released while waiting
        # on the subprocess). Results are applied on the main thread, in
        # submission order, to keep on_progress and asset ordering deterministic.
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._convert_page, page, resolver, config) for page in pages]
            for page, future in zip(pages, futures):
                page.html_content = future.result()
                assets.extend(page.asset_filenames)
                if on_progress:
                    on_progress(page.title)
        self.broken_links.extend(resolver.broken_links)

    def _convert_page(self, page: Page, resolver: LinkResolver, config: SiteConfig) -> str:
        preprocessed, page.asset_filenames = resolver.preprocess(page.raw_content, page.format, page.title)
        html = self._converter.convert(preprocessed, page.format)
        return postprocess(html, page.format, config)

    def _write_site(
        self,
        pages: list[Page],
        journal_pages: list[Page],
        config: SiteConfig,
        logseq_assets_dir: Path,
    ) -> None:
        writer = self._writer
        writer.write_static_files()
        writer.write_404(config)

        home = _find_home(pages, config.home_slug)
        for page in pages:
            writer.write_page(page, config, is_home=(page is home))

        if config.enable_journals:
            for page in journal_pages:
                writer.write_page(page, config)
            writer.write_blog_index(journal_pages, config)
            if config.rss and journal_pages:
                writer.write_rss(journal_pages, config)

        writer.copy_assets(self.used_assets, logseq_assets_dir)

        writer.copy_pages_subdirs(logseq_assets_dir.parent / config.pages_directory)
        for external_dir in config.external_static_dirs:
            writer.copy_pages_subdirs(Path(external_dir), require_web_files=False)

        writer.write_sitemap(pages, journal_pages, config)
        writer.write_robots(config)
        writer.write_search_index(pages, journal_pages, config)


def _find_home(pages: list[Page], home_slug: str) -> Page:
    for page in pages:
        if page.slug == home_slug:
            return page
    # Fallback: match against the source filename stem (user may specify the
    # filename slug when the page has a #+TITLE that generates a different slug)
    for page in pages:
        if slugify(page.source_path.stem) == home_slug:
            return page
    return pages[0]
