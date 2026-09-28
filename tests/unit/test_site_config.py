from pathlib import Path

from logseq_builder.domain.page import Page
from logseq_builder.services.site_config import resolve_home_slug


def _page(title: str, slug: str, stem: str) -> Page:
    return Page(title=title, slug=slug, raw_content="", source_path=Path(f"/g/pages/{stem}.org"),
                format="org", is_public=True)


def test_home_by_filename_resolves_to_real_slug():
    pages = [_page("Autre", "autre", "autre"), _page("Mon Super Titre", "mon-super-titre", "ma-page")]
    assert resolve_home_slug("ma-page", pages) == ("mon-super-titre", None)


def test_unknown_home_warns():
    slug, warning = resolve_home_slug("nope", [_page("Autre", "autre", "autre")])
    assert slug == "nope" and warning
