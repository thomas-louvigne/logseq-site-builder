from pathlib import Path
from logseq_builder.domain.page import Page, SiteConfig


class TestPage:
    def _make(self, slug="my-page"):
        return Page(
            title="My Page",
            slug=slug,
            raw_content="",
            source_path=Path("/fake/my-page.org"),
            format="org",
            is_public=True,
        )

    def test_output_filename(self):
        page = self._make("my-page")
        assert page.output_filename == "my-page.html"

    def test_asset_filenames_default_empty(self):
        page = self._make()
        assert page.asset_filenames == []

    def test_html_content_default_empty(self):
        page = self._make()
        assert page.html_content == ""


class TestSiteConfig:
    def test_defaults(self):
        config = SiteConfig(title="Test Site")
        assert config.base_url == ""
        assert config.social_links == {}
        assert config.home_slug == "index"

    def test_social_links(self):
        config = SiteConfig(title="T", social_links={"twitter": "https://twitter.com/x"})
        assert config.social_links["twitter"] == "https://twitter.com/x"
