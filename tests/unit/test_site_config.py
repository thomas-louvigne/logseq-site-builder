from pathlib import Path

from logseq_builder.domain.page import SHARE_BUTTONS, Page
from logseq_builder.services.site_config import build_site_config, resolve_home_slug


def _config(toml: dict):
    return build_site_config(toml, title=None, default_title="T", all_public=False, social_links=[])


def test_share_buttons_all_on_by_default():
    config, warnings = _config({})
    assert config.share == dict.fromkeys(SHARE_BUTTONS, True)
    assert warnings == []


def test_share_button_can_be_switched_off():
    config, _ = _config({"share": {"facebook": False, "print": False}})
    assert config.share["facebook"] is False
    assert config.share["print"] is False
    assert config.share["whatsapp"] is True


def test_unknown_share_key_warns():
    config, warnings = _config({"share": {"myspace": False}})
    assert "myspace" not in config.share
    assert len(warnings) == 1 and "myspace" in warnings[0]


def _page(title: str, slug: str, stem: str) -> Page:
    return Page(title=title, slug=slug, raw_content="", source_path=Path(f"/g/pages/{stem}.org"),
                format="org", is_public=True)


def test_home_by_filename_resolves_to_real_slug():
    pages = [_page("Autre", "autre", "autre"), _page("Mon Super Titre", "mon-super-titre", "ma-page")]
    assert resolve_home_slug("ma-page", pages) == ("mon-super-titre", None)


def test_unknown_home_warns():
    slug, warning = resolve_home_slug("nope", [_page("Autre", "autre", "autre")])
    assert slug == "nope" and warning
