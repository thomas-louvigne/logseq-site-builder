from pathlib import Path

from ..domain.page import Page, SiteConfig
from ..ports.interfaces import ContentConverter, PageRepository, SiteWriter
from .link_resolver import LinkResolver


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

        resolver = LinkResolver(pages, config.home_slug)
        all_asset_filenames: list[str] = []

        for page in pages:
            if page.format == "org":
                preprocessed, assets = resolver.preprocess_org(page.raw_content)
            else:
                preprocessed, assets = resolver.preprocess_md(page.raw_content)

            page.asset_filenames = assets
            all_asset_filenames.extend(assets)
            page.html_content = self._converter.convert(preprocessed, page.format)

        home = self._find_home(pages, config.home_slug)

        self._writer.write_static_files()

        for page in pages:
            self._writer.write_page(page, config, is_home=(page is home))

        unique_assets = list(dict.fromkeys(all_asset_filenames))
        self._writer.copy_assets(unique_assets, logseq_assets_dir)

    def _find_home(self, pages: list[Page], home_slug: str) -> Page:
        for page in pages:
            if page.slug == home_slug:
                return page
        return pages[0]
