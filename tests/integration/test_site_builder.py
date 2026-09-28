from pathlib import Path
import pytest

from logseq_builder.adapters.logseq_reader import LogseqReader
from logseq_builder.adapters.pandoc_converter import PandocConverter
from logseq_builder.adapters.static_writer import StaticWriter
from logseq_builder.domain.page import SHARE_BUTTONS, SiteConfig
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

    def test_creates_print_css_linked_for_print_only(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        assert (output_dir / "print.css").exists()
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert '<link rel="stylesheet" href="print.css" media="print">' in html

    def test_print_footer_has_site_title_and_address(self, logseq_dir, output_dir):
        config = SiteConfig(title="Mon Site", home_slug="accueil", base_url="https://exemple.fr")
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert '<footer class="print-footer" hidden>' in html
        assert "Mon Site — exemple.fr" in html

    def test_page_has_share_bar_with_print_button(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert 'class="share-bar"' in html
        assert "data-share-print" in html
        assert 'data-share-pattern="https://wa.me/?text={text}%20{url}"' in html

    def test_share_links_use_canonical_url_when_base_url_set(self, logseq_dir, output_dir):
        config = SiteConfig(title="Mon Site", home_slug="accueil", base_url="https://exemple.fr")
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert "https://www.facebook.com/sharer/sharer.php?u=https%3A//exemple.fr/dragons.html" in html

    def test_disabled_share_buttons_are_not_rendered(self, logseq_dir, output_dir):
        share = dict.fromkeys(SHARE_BUTTONS, True) | {"facebook": False, "print": False}
        config = SiteConfig(title="Mon Site", home_slug="accueil", share=share)
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert "facebook.com/sharer" not in html
        assert "data-share-print" not in html
        assert "share-bar__separator" not in html
        assert "wa.me" in html

    def test_random_menu_entry_renders_labelled_random_link(self, logseq_dir, output_dir):
        menu = [{"label": "Accueil", "slug": "accueil"}, {"label": "Au pif", "random": True}]
        config = SiteConfig(title="Mon Site", home_slug="accueil", menu=menu)
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert "data-random-page" in html
        assert "Au pif" in html

    def test_no_random_link_without_random_menu_entry(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert "data-random-page" not in html

    def test_tree_view_sets_body_class(self, logseq_dir, output_dir, config):
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert '<body class="tree-view">' in html

    def test_vertical_share_layout_adds_modifier_class(self, logseq_dir, output_dir):
        config = SiteConfig(title="Mon Site", home_slug="accueil", share_layout="vertical")
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert 'class="share-bar share-bar--vertical"' in html

    def test_share_bar_hidden_when_every_button_is_off(self, logseq_dir, output_dir):
        config = SiteConfig(title="Mon Site", home_slug="accueil", share=dict.fromkeys(SHARE_BUTTONS, False))
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert 'class="share-bar"' not in html

    def test_print_only_bar_has_no_share_label(self, logseq_dir, output_dir):
        share = dict.fromkeys(SHARE_BUTTONS, False) | {"print": True}
        config = SiteConfig(title="Mon Site", home_slug="accueil", share=share)
        build(logseq_dir, output_dir, config)
        html = (output_dir / "dragons.html").read_text(encoding="utf-8")
        assert "data-share-print" in html
        assert "share-bar__label" not in html

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

    def test_broken_links_empty_when_all_links_resolve(self, logseq_dir, output_dir, config):
        builder = SiteBuilder(
            reader=LogseqReader(logseq_dir),
            converter=PandocConverter(),
            writer=StaticWriter(output_dir),
        )
        builder.build(config, logseq_dir / "assets")
        assert builder.broken_links == []

    def test_broken_links_reports_unresolved_page(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "Accueil.org").write_text(
            "#+PUBLIC: true\n* Bienvenue\nVoir [[Page Fantome]] pour plus.\n",
            encoding="utf-8",
        )
        out = tmp_path / "out"
        builder = SiteBuilder(
            reader=LogseqReader(tmp_path),
            converter=PandocConverter(),
            writer=StaticWriter(out),
        )
        builder.build(SiteConfig(title="T", home_slug="accueil"), tmp_path / "assets")
        assert builder.broken_links == [("Accueil", "Page Fantome")]

    def test_copies_external_static_dir(self, logseq_dir, output_dir, tmp_path):
        external = tmp_path / "external"
        (external / "lugny").mkdir(parents=True)
        (external / "lugny" / "map.svg").write_text("<svg></svg>", encoding="utf-8")

        config = SiteConfig(title="Mon Site", home_slug="accueil", external_static_dirs=[str(external)])
        build(logseq_dir, output_dir, config)

        assert (output_dir / "lugny" / "map.svg").exists()

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
