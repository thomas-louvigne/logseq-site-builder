import sys
from pathlib import Path

import click

from .adapters.logseq_reader import LogseqReader
from .adapters.pandoc_converter import PandocConverter
from .adapters.static_writer import StaticWriter
from .domain.page import SiteConfig
from .services.site_builder import SiteBuilder


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
def main(
    input_dir: Path,
    output_dir: Path,
    site_title: str | None,
    home_page: str | None,
    all_public: bool,
    social_links: tuple[str, ...],
) -> None:
    """Build a static website from a Logseq knowledge base."""
    title = site_title or input_dir.name

    parsed_socials: dict[str, str] = {}
    for entry in social_links:
        if ":" not in entry:
            click.echo(f"Warning: ignoring malformed --social '{entry}' (expected NAME:URL)", err=True)
            continue
        name, _, url = entry.partition(":")
        parsed_socials[name.strip()] = url.strip()

    reader = LogseqReader(input_dir, all_public=all_public)

    all_pages = list(reader.find_all())
    public_pages = [p for p in all_pages if p.is_public]

    if not public_pages:
        click.echo("No public pages found. Use --all-public or add #+PUBLIC: true to pages.", err=True)
        sys.exit(1)

    home_slug = home_page or reader.default_home_slug or _auto_detect_home(public_pages)

    config = SiteConfig(
        title=title,
        social_links=parsed_socials,
        home_slug=home_slug,
    )

    logseq_assets_dir = input_dir / "assets"

    builder = SiteBuilder(
        reader=LogseqReader(input_dir, all_public=all_public),
        converter=PandocConverter(),
        writer=StaticWriter(output_dir),
    )

    click.echo(f"Building site from {input_dir} → {output_dir}")
    click.echo(f"  {len(public_pages)} public page(s) found")

    try:
        builder.build(config, logseq_assets_dir)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Site written to {output_dir}")


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
