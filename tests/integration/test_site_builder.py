from pathlib import Path
import pytest

from logseq_builder.adapters.logseq_reader import LogseqReader
from logseq_builder.adapters.pandoc_converter import PandocConverter
from logseq_builder.adapters.static_writer import StaticWriter
from logseq_builder.domain.page import SiteConfig
from logseq_builder.services.site_builder import SiteBuilder


@pytest.fixture
def logseq_dir(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "hero.png").write_bytes(b"\x89PNG\r\n")

    (pages / "Accueil.org").write_text(
        "#+PUBLIC: true\n* Bienvenue\nCeci est la page d'accueil.\n"
        "Voir [[Dragons]] pour plus.\n[[../assets/hero.png]]",
        encoding="utf-8",
    )
    (pages / "Dragons.org").write_text(
        "#+PUBLIC: true\n* Les Dragons\nDescription des dragons.\n",
        encoding="utf-8",
    )
    (pages / "Secret.org").write_text("* Top secret", encoding="utf-8")
    return tmp_path


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def config():
    return SiteConfig(
        title="Mon Site",
        social_links={"Twitter": "https://twitter.com/test"},
        home_slug="accueil",
    )


def build(logseq_dir, output_dir, config):
    builder = SiteBuilder(
        reader=LogseqReader(logseq_dir),
        converter=PandocConverter(),
        writer=StaticWriter(output_dir),
    )
    builder.build(config, logseq_dir / "assets")
    return output_dir


class TestSiteBuilder:
    def test_creates_index_html(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "index.html").exists()

    def test_creates_page_html(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "dragons.html").exists()

    def test_private_page_excluded(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert not (output_dir / "secret.html").exists()

    def test_creates_style_css(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "style.css").exists()

    def test_creates_js_main(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "js" / "main.js").exists()

    def test_copies_referenced_asset(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "assets" / "hero.png").exists()

    def test_index_contains_site_title(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "index.html").read_text(encoding="utf-8")
        assert "Mon Site" in html

    def test_index_contains_social_link(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "index.html").read_text(encoding="utf-8")
        assert "https://twitter.com/test" in html

    def test_wiki_link_resolved_in_html(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "index.html").read_text(encoding="utf-8")
        assert "dragons.html" in html

    def test_home_link_in_nav(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert 'href="index.html"' in html

    def test_raises_on_no_public_pages(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "Secret.org").write_text("* Private", encoding="utf-8")
        out = tmp_path / "out"
        builder = SiteBuilder(
            reader=LogseqReader(tmp_path),
            converter=PandocConverter(),
            writer=StaticWriter(out),
        )
        with pytest.raises(ValueError, match="No public pages"):
            builder.build(SiteConfig(title="T"), tmp_path / "assets")
