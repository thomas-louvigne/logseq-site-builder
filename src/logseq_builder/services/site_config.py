"""Assemble a SiteConfig from the merged TOML/EDN dict and CLI overrides."""

from collections.abc import Iterable
from typing import Literal

from ..domain.page import SHARE_BUTTONS, SHARE_LAYOUTS, Page, ShareLayout, SiteConfig
from ..domain.paths import slugify

_HOME_CANDIDATE_SLUGS = ["index", "home", "accueil", "readme"]
_HOME_CANDIDATE_TITLES = ["index", "home", "accueil"]


def build_site_config(
    toml: dict,
    *,
    title: str | None,
    default_title: str,
    all_public: bool,
    social_links: Iterable[str],
) -> tuple[SiteConfig, list[str]]:
    """Return the config (home_slug still unresolved, see `resolve_home_slug`)
    and any warnings to show the user."""
    site = toml.get("site", {})
    warnings: list[str] = []

    socials, social_warnings = _merge_social_links(toml.get("social_networks", {}), social_links)
    warnings += social_warnings

    share_table = dict(toml.get("share", {}))
    share_layout, layout_warnings = _parse_share_layout(share_table.pop("layout", "horizontal"))
    share, share_warnings = _parse_share(share_table)
    warnings += layout_warnings + share_warnings

    enable_journals: bool = site.get("enable_journals", False)
    blog_title: str = site.get("blog_title", "Blog")
    blog_slug: str = site.get("blog_slug", "blog")
    menu: list[dict[str, str]] = toml.get("menu", [])
    if enable_journals and not any(item.get("slug") == blog_slug for item in menu):
        menu = list(menu) + [{"label": blog_title, "slug": blog_slug}]

    config = SiteConfig(
        title=title or site.get("title") or default_title,
        author=site.get("author", ""),
        description=site.get("description", ""),
        base_url=site.get("base_url", "").rstrip("/"),
        lang=site.get("lang", "en"),
        social_links=socials,
        menu=menu,
        org_listify_headings_from=_parse_listify(site.get("org_listify_headings_from", "auto")),
        all_public=all_public or site.get("all_public", False),
        hidden=site.get("hidden", []),
        pages_directory=site.get("pages_directory", "pages"),
        journals_directory=site.get("journals_directory", "journals"),
        enable_journals=enable_journals,
        journal_page_title_format=site.get("journal_page_title_format", "dd-MM-yyyy"),
        journal_file_name_format=site.get("journal_file_name_format", "yyyy_MM_dd"),
        blog_title=blog_title,
        blog_slug=blog_slug,
        rss=site.get("rss", False),
        bullet_threading=site.get("bullet_threading", True),
        random_page=site.get("random_page", True),
        external_static_dirs=[
            entry["path"] for entry in toml.get("external_static_dirs", []) if entry.get("path")
        ],
        share=share,
        share_layout=share_layout,
    )
    return config, warnings


def _parse_share_layout(raw: object) -> tuple[ShareLayout, list[str]]:
    if raw in SHARE_LAYOUTS:
        return raw, []  # type: ignore[return-value]
    expected = " or ".join(f"'{layout}'" for layout in SHARE_LAYOUTS)
    return "horizontal", [f"ignoring [share] layout '{raw}' (expected {expected})"]


def _parse_share(raw: dict) -> tuple[dict[str, bool], list[str]]:
    """Every share-bar button defaults to on; [share] only lists the ones to change."""
    warnings = [
        f"ignoring unknown [share] key '{key}' (expected one of: {', '.join(SHARE_BUTTONS)})"
        for key in raw
        if key not in SHARE_BUTTONS
    ]
    return {name: bool(raw.get(name, True)) for name in SHARE_BUTTONS}, warnings


def _merge_social_links(
    base: dict[str, str], cli_entries: Iterable[str]
) -> tuple[dict[str, str], list[str]]:
    socials = dict(base)
    warnings = []
    for entry in cli_entries:
        if ":" not in entry:
            warnings.append(f"ignoring malformed --social '{entry}' (expected NAME:URL)")
            continue
        name, _, url = entry.partition(":")
        socials[name.strip()] = url.strip()
    return socials, warnings


def _parse_listify(raw: object) -> int | Literal["auto"] | None:
    if raw is None or raw is False:
        return None
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value == "auto":
            return "auto"
        if value in ("false", "off", "none", ""):
            return None
    return int(raw)  # type: ignore[arg-type]


def resolve_home_slug(requested: str | None, public_pages: list[Page]) -> tuple[str, str | None]:
    """Return (home_slug, warning). Without an explicit request, pick the most
    home-like public page."""
    if not requested:
        return _auto_detect_home(public_pages), None

    home_slug = slugify(requested)
    public_slugs = {p.slug for p in public_pages}
    if home_slug in public_slugs:
        return home_slug, None
    # Matched by filename (page has a #+TITLE giving another slug): use the
    # page's real slug so links to it point at index.html too.
    for page in public_pages:
        if slugify(page.source_path.stem) == home_slug:
            return page.slug, None
    return home_slug, (
        f"no public page matches home_page='{requested}' (slug: '{home_slug}').\n"
        f"  Available slugs: {sorted(public_slugs)}"
    )


def _auto_detect_home(pages: list[Page]) -> str:
    slugs = {p.slug for p in pages}
    for candidate in _HOME_CANDIDATE_SLUGS:
        if candidate in slugs:
            return candidate
    titles_lower = {p.title.lower(): p for p in pages}
    for candidate in _HOME_CANDIDATE_TITLES:
        if candidate in titles_lower:
            return titles_lower[candidate].slug
    return pages[0].slug
