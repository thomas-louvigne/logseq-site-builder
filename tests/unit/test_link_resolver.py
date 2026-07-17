from pathlib import Path
import pytest

from logseq_builder.domain.page import Page
from logseq_builder.services.link_resolver import LinkResolver, slugify


def _make_page(title: str, slug: str | None = None) -> Page:
    s = slug or slugify(title)
    return Page(title=title, slug=s, raw_content="", source_path=Path("/fake"), format="org", is_public=True)


@pytest.fixture
def resolver():
    pages = [
        _make_page("Accueil", "accueil"),
        _make_page("Dragons"),
        _make_page("Gustave Coste", "gustave-coste"),
    ]
    return LinkResolver(pages, home_slug="accueil")


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_accented(self):
        assert slugify("Époque Tracogna") == "epoque-tracogna"

    def test_multiple_spaces(self):
        assert slugify("A  B   C") == "a-b-c"

    def test_special_chars(self):
        assert slugify("L'hiver & l'été") == "lhiver-lete"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"

    def test_underscores(self):
        assert slugify("my_page_name") == "my-page-name"


class TestLinkResolverOrg:
    def test_simple_link_to_known_page(self, resolver):
        content = "See [[Dragons]] for details."
        result, _ = resolver.preprocess_org(content)
        assert "[[file:dragons.html][Dragons]]" in result

    def test_simple_link_home(self, resolver):
        content = "Go back to [[Accueil]]."
        result, _ = resolver.preprocess_org(content)
        assert "[[file:index.html][Accueil]]" in result

    def test_labeled_link(self, resolver):
        content = "See [[Gustave Coste][le forgeron]]."
        result, _ = resolver.preprocess_org(content)
        assert "[[file:gustave-coste.html][le forgeron]]" in result

    def test_url_link_preserved(self, resolver):
        content = "Visit [[https://example.com]]."
        result, _ = resolver.preprocess_org(content)
        assert "[[https://example.com]]" in result

    def test_url_labeled_preserved(self, resolver):
        content = "Visit [[https://example.com][Example]]."
        result, _ = resolver.preprocess_org(content)
        assert "[[https://example.com][Example]]" in result

    def test_asset_link_extracted(self, resolver):
        content = "Image: [[../assets/dragon.png]]"
        result, assets = resolver.preprocess_org(content)
        assert "dragon.png" in assets
        assert "[[file:assets/dragon.png]]" in result

    def test_properties_block_stripped(self, resolver):
        content = ":PROPERTIES:\n:id: abc-123\n:END:\nSome content."
        result, _ = resolver.preprocess_org(content)
        assert ":PROPERTIES:" not in result
        assert "Some content." in result

    def test_public_directive_stripped(self, resolver):
        content = "#+PUBLIC: true\nContent."
        result, _ = resolver.preprocess_org(content)
        assert "#+PUBLIC:" not in result
        assert "Content." in result

    def test_hashtag_compound_removed(self, resolver):
        content = "Tag: #[[Silo-et-Corpo]]"
        result, _ = resolver.preprocess_org(content)
        assert "#[[" not in result
        assert "Silo-et-Corpo" in result

    def test_unknown_page_link_slugified(self, resolver):
        content = "See [[Unknown Page]]."
        result, _ = resolver.preprocess_org(content)
        assert "[[file:unknown-page.html][Unknown Page]]" in result
        assert resolver.broken_links == [("", "Unknown Page")]

    def test_multiple_assets_collected(self, resolver):
        content = "[[../assets/a.jpg]] and [[../assets/b.png]]"
        _, assets = resolver.preprocess_org(content)
        assert "a.jpg" in assets
        assert "b.png" in assets

    def test_hashtag_with_accented_chars(self, resolver):
        content = "* #quêtes"
        result, _ = resolver.preprocess_org(content)
        assert "[[file:quetes.html][#quêtes]]" in result

    def test_simple_link_with_dotted_name(self, resolver):
        content = "Parler à [[Dr. Livia Morozov]] pour plus d'infos."
        result, _ = resolver.preprocess_org(content)
        assert "[[file:dr-livia-morozov.html][Dr. Livia Morozov]]" in result
        assert "assets" not in result


class TestBrokenLinks:
    def test_known_link_not_flagged(self, resolver):
        resolver.preprocess_org("See [[Dragons]].")
        assert resolver.broken_links == []

    def test_unknown_link_flagged_with_source(self, resolver):
        resolver.preprocess_org("See [[Nowhere]].", source="Dragons")
        assert resolver.broken_links == [("Dragons", "Nowhere")]

    def test_unknown_labeled_link_flagged(self, resolver):
        resolver.preprocess_org("See [[Nowhere][here]].", source="Dragons")
        assert resolver.broken_links == [("Dragons", "Nowhere")]

    def test_unknown_hashtag_flagged(self, resolver):
        resolver.preprocess_org("Tag: #nowhere", source="Dragons")
        assert resolver.broken_links == [("Dragons", "nowhere")]

    def test_markdown_unknown_link_flagged(self, resolver):
        resolver.preprocess_md("See [[Nowhere]].", source="Dragons")
        assert resolver.broken_links == [("Dragons", "Nowhere")]

    def test_multiple_pages_accumulate(self, resolver):
        resolver.preprocess_org("See [[Nowhere]].", source="Dragons")
        resolver.preprocess_org("See [[Elsewhere]].", source="Accueil")
        assert resolver.broken_links == [("Dragons", "Nowhere"), ("Accueil", "Elsewhere")]
