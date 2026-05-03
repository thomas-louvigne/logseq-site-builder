import shutil
import subprocess
import sys
from pathlib import Path

import click

from .adapters.edn_config_loader import generate_toml
from .adapters.logseq_reader import LogseqReader
from .adapters.pandoc_converter import PandocConverter
from .adapters.static_writer import THEMES_DIR, StaticWriter
from .adapters.toml_config_loader import load_toml_config
from .domain.page import SiteConfig
from .services.link_resolver import slugify
from .services.site_builder import SiteBuilder

_TOML_FILENAME = "logseq-site-builder.toml"


def _resolve_theme_css(theme: str, logseq_dir: Path) -> Path | None:
    """Resolve a theme name or path to an absolute CSS file path.

    Resolution order:
    1. Built-in theme name (e.g. "dark" → themes/dark.css)
    2. Path relative to the Logseq project directory
    3. Absolute path
    """
    # Built-in theme by name (no extension, no path separators)
    if not theme.endswith(".css") and "/" not in theme and "\\" not in theme:
        candidate = THEMES_DIR / f"{theme}.css"
        if candidate.exists():
            return candidate

    # Relative path from logseq dir
    candidate = logseq_dir / theme
    if candidate.exists():
        return candidate

    # Absolute path
    absolute = Path(theme)
    if absolute.is_absolute() and absolute.exists():
        return absolute

    return None


@click.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--site-title", default=None, help="Title of the site (default: input dir name).")
@click.option("--home-page", default=None, help="Slug of the page to use as index.html.")
@click.option("--all-public", is_flag=True, default=False, help="Treat all pages as public.")
@click.option(
    "--social",
    "social_links",
    multiple=True,
    metavar="NAME:URL",
    help='Social link, e.g. --social "twitter:https://twitter.com/you"',
)
@click.option(
    "--no-init-toml",
    is_flag=True,
    default=False,
    help=f"Do not generate {_TOML_FILENAME} when it does not exist.",
)
@click.option(
    "--theme",
    default=None,
    help='Theme name (e.g. "dark") or path to a CSS file (relative to the Logseq dir).',
)
def main(
    input_dir: Path,
    output_dir: Path,
    site_title: str | None,
    home_page: str | None,
    all_public: bool,
    social_links: tuple[str, ...],
    no_init_toml: bool,
    theme: str | None,
) -> None:
    """Build a static website from a Logseq knowledge base."""
    toml_path = input_dir / _TOML_FILENAME
    if not toml_path.exists() and not no_init_toml:
        generated = generate_toml(input_dir)
        click.echo(f"Created {generated} from logseq/config.edn — edit it to customise your site.")

    toml = load_toml_config(input_dir)
    if toml_path.exists():
        click.echo(f"Loaded config from {toml_path}")

    site_section = toml.get("site", {})

    title = site_title or site_section.get("title") or input_dir.name
    author = site_section.get("author", "")
    description = site_section.get("description", "")
    base_url = site_section.get("base_url", "").rstrip("/")
    lang = site_section.get("lang", "en")

    if not all_public:
        all_public = site_section.get("all_public", False)

    parsed_socials: dict[str, str] = dict(toml.get("social_networks", {}))
    for entry in social_links:
        if ":" not in entry:
            click.echo(f"Warning: ignoring malformed --social '{entry}' (expected NAME:URL)", err=True)
            continue
        name, _, url = entry.partition(":")
        parsed_socials[name.strip()] = url.strip()

    menu: list[dict[str, str]] = toml.get("menu", [])

    raw_flatten = site_section.get("flatten_headings_from")
    flatten_headings_from: int | None = int(raw_flatten) if raw_flatten is not None else None

    # config.edn-sourced options (overridable in TOML)
    hidden: list[str] = site_section.get("hidden", [])
    pages_directory: str = site_section.get("pages_directory", "pages")
    journals_directory: str = site_section.get("journals_directory", "journals")
    enable_journals: bool = site_section.get("enable_journals", False)
    journal_page_title_format: str = site_section.get("journal_page_title_format", "dd-MM-yyyy")
    journal_file_name_format: str = site_section.get("journal_file_name_format", "yyyy_MM_dd")
    blog_title: str = site_section.get("blog_title", "Blog")
    blog_slug: str = site_section.get("blog_slug", "blog")
    rss: bool = site_section.get("rss", False)

    reader = LogseqReader(
        input_dir,
        all_public=all_public,
        pages_directory=pages_directory,
        journals_directory=journals_directory,
        hidden=hidden,
        journal_page_title_format=journal_page_title_format,
        journal_file_name_format=journal_file_name_format,
    )

    all_pages = list(reader.find_all())
    public_pages = [p for p in all_pages if p.is_public]

    if not public_pages:
        click.echo("No public pages found. Use --all-public or add #+PUBLIC: true to pages.", err=True)
        sys.exit(1)

    toml_home = site_section.get("home_page")
    raw_home = home_page or toml_home
    home_slug = slugify(raw_home) if raw_home else _auto_detect_home(public_pages)

    public_slugs = {p.slug for p in public_pages}
    public_filename_slugs = {slugify(p.source_path.stem) for p in public_pages}
    if raw_home and home_slug not in public_slugs and home_slug not in public_filename_slugs:
        click.echo(
            f"Warning: no public page matches home_page='{raw_home}' (slug: '{home_slug}').\n"
            f"  Available slugs: {sorted(public_slugs)}",
            err=True,
        )

    # Auto-add blog link to menu when journals are enabled and not already present
    if enable_journals and not any(item.get("slug") == blog_slug for item in menu):
        menu = list(menu) + [{"label": blog_title, "slug": blog_slug}]

    config = SiteConfig(
        title=title,
        author=author,
        description=description,
        base_url=base_url,
        lang=lang,
        social_links=parsed_socials,
        home_slug=home_slug,
        menu=menu,
        flatten_headings_from=flatten_headings_from,
        hidden=hidden,
        pages_directory=pages_directory,
        journals_directory=journals_directory,
        enable_journals=enable_journals,
        journal_page_title_format=journal_page_title_format,
        journal_file_name_format=journal_file_name_format,
        blog_title=blog_title,
        blog_slug=blog_slug,
        rss=rss,
    )

    logseq_assets_dir = input_dir / "assets"

    theme_str = theme or site_section.get("theme")
    theme_css: Path | None = None
    if theme_str:
        theme_css = _resolve_theme_css(theme_str, input_dir)
        if theme_css is None:
            built_in_names = [p.stem for p in THEMES_DIR.glob("*.css")]
            click.echo(
                f"Warning: theme '{theme_str}' not found. "
                f"Built-in themes: {built_in_names}. "
                f"Falling back to default.",
                err=True,
            )
        else:
            click.echo(f"  Theme: {theme_css.name}")

    builder = SiteBuilder(
        reader=reader,
        converter=PandocConverter(),
        writer=StaticWriter(output_dir, theme_css=theme_css),
    )

    click.echo(f"Building site from {input_dir} → {output_dir}")
    click.echo(f"  {len(public_pages)} public page(s) found")
    journal_count = 0
    if enable_journals:
        journal_count = sum(1 for _ in reader.find_journals())
        click.echo(f"  {journal_count} journal entry(ies) found")
    if hidden:
        click.echo(f"  {len(hidden)} hidden path(s): {hidden}")

    total_pages = len(public_pages) + journal_count
    try:
        with click.progressbar(length=total_pages, label="Building", width=50) as bar:
            def on_progress(title: str) -> None:
                bar.update(1)
            builder.build(config, logseq_assets_dir, on_progress=on_progress)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Site written to {output_dir}")
    if enable_journals and rss:
        click.echo(f"  RSS feed: {output_dir / 'feed.xml'}")

    if shutil.which("notify-send"):
        subprocess.run(
            ["notify-send", "--icon=dialog-information", "logseq-builder",
             f"Build complete — {total_pages} page(s) → {output_dir}"],
            check=False,
        )


def _auto_detect_home(pages) -> str:  # type: ignore[type-arg]
    priority = ["index", "home", "accueil", "readme"]
    slugs = {p.slug: p for p in pages}
    for candidate in priority:
        if candidate in slugs:
            return candidate
    titles_lower = {p.title.lower(): p for p in pages}
    for candidate in ["index", "home", "accueil"]:
        if candidate in titles_lower:
            return titles_lower[candidate].slug
    return pages[0].slug
