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


def test_tree_view_on_by_default_and_can_be_switched_off():
    assert _config({})[0].tree_view is True
    assert _config({"site": {"tree_view": False}})[0].tree_view is False


def test_legacy_bullet_threading_still_works_with_a_warning():
    config, warnings = _config({"site": {"bullet_threading": False}})
    assert config.tree_view is False
    assert len(warnings) == 1 and "tree_view" in warnings[0]


def test_share_layout_defaults_to_horizontal():
    config, _ = _config({})
    assert config.share_layout == "horizontal"


def test_share_layout_vertical_is_not_taken_for_a_button():
    config, warnings = _config({"share": {"layout": "vertical"}})
    assert config.share_layout == "vertical"
    assert "layout" not in config.share
    assert warnings == []


def test_invalid_share_layout_warns_and_falls_back():
    config, warnings = _config({"share": {"layout": "diagonal"}})
    assert config.share_layout == "horizontal"
    assert len(warnings) == 1 and "diagonal" in warnings[0]


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
