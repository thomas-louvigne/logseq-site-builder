import dataclasses
import shutil
import subprocess
import sys
from pathlib import Path

import click

from .adapters.edn_config_loader import generate_toml
from .adapters.logseq_reader import LogseqReader
from .adapters.pandoc_converter import PandocConverter
from .adapters.static_writer import StaticWriter
from .adapters.themes import builtin_theme_names, resolve_theme_css
from .adapters.toml_config_loader import CONFIG_FILENAME, load_toml_config
from .domain.page import SiteConfig
from .services.site_builder import SiteBuilder
from .services.site_config import build_site_config, resolve_home_slug


def _warn(message: str) -> None:
    click.echo(f"Warning: {message}", err=True)


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
    help=f"Do not generate {CONFIG_FILENAME} when it does not exist.",
)
@click.option(
    "--theme",
    default=None,
    help='Theme name (e.g. "dark") or path to a CSS file (relative to the Logseq dir).',
)
@click.option(
    "--check-links",
    is_flag=True,
    default=False,
    help="List internal links that point to no known page (would 404) in the terminal.",
)
@click.option(
    "--check-assets",
    is_flag=True,
    default=False,
    help="List files in the Logseq assets/ directory that no page references.",
)
@click.option(
    "--zip",
    "zip_output",
    is_flag=True,
    default=False,
    help="Zip the built site into <output_dir>.zip once the build is complete.",
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
    check_links: bool,
    check_assets: bool,
    zip_output: bool,
) -> None:
    """Build a static website from a Logseq knowledge base."""
    toml_path = input_dir / CONFIG_FILENAME
    if not toml_path.exists() and not no_init_toml:
        generated = generate_toml(input_dir)
        click.echo(f"Created {generated} from logseq/config.edn — edit it to customise your site.")

    toml = load_toml_config(input_dir)
    if toml_path.exists():
        click.echo(f"Loaded config from {toml_path}")
    site_section = toml.get("site", {})

    config, warnings = build_site_config(
        toml,
        title=site_title,
        default_title=input_dir.name,
        all_public=all_public,
        social_links=social_links,
    )
    for warning in warnings:
        _warn(warning)

    reader = LogseqReader(
        input_dir,
        all_public=config.all_public,
        pages_directory=config.pages_directory,
        journals_directory=config.journals_directory,
        hidden=config.hidden,
        journal_page_title_format=config.journal_page_title_format,
        journal_file_name_format=config.journal_file_name_format,
    )

    public_pages = [p for p in reader.find_all() if p.is_public]
    if not public_pages:
        click.echo("No public pages found. Use --all-public or add #+PUBLIC: true to pages.", err=True)
        sys.exit(1)

    home_slug, home_warning = resolve_home_slug(home_page or site_section.get("home_page"), public_pages)
    if home_warning:
        _warn(home_warning)
    config = dataclasses.replace(config, home_slug=home_slug)

    theme_css = _resolve_theme(theme or site_section.get("theme"), input_dir)

    builder = SiteBuilder(
        reader=reader,
        converter=PandocConverter(),
        writer=StaticWriter(output_dir, theme_css=theme_css),
    )

    click.echo(f"Building site from {input_dir} → {output_dir}")
    click.echo(f"  {len(public_pages)} public page(s) found")
    journal_count = sum(1 for _ in reader.find_journals()) if config.enable_journals else 0
    _echo_build_summary(config, journal_count)

    logseq_assets_dir = input_dir / "assets"
    total_pages = len(public_pages) + journal_count
    try:
        with click.progressbar(length=total_pages, label="Building", width=50) as bar:
            builder.build(config, logseq_assets_dir, on_progress=lambda _title: bar.update(1))
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Done. Site written to {output_dir}")
    if config.enable_journals and config.rss:
        click.echo(f"  RSS feed: {output_dir / 'feed.xml'}")

    if check_links:
        _report_broken_links(builder.broken_links)
    if check_assets:
        _report_unused_assets(logseq_assets_dir, builder.used_assets)
    if zip_output:
        archive_path = shutil.make_archive(str(output_dir), "zip", root_dir=output_dir)
        click.echo(f"  Zipped to {archive_path}")

    _notify_desktop(f"Build complete — {total_pages} page(s) → {output_dir}")


def _resolve_theme(theme: str | None, input_dir: Path) -> Path | None:
    if not theme:
        return None
    theme_css = resolve_theme_css(theme, input_dir)
    if theme_css is None:
        _warn(
            f"theme '{theme}' not found. "
            f"Built-in themes: {builtin_theme_names()}. "
            f"Falling back to default."
        )
    else:
        click.echo(f"  Theme: {theme_css.name}")
    return theme_css


def _echo_build_summary(config: SiteConfig, journal_count: int) -> None:
    if config.enable_journals:
        click.echo(f"  {journal_count} journal entry(ies) found")
    if config.hidden:
        click.echo(f"  {len(config.hidden)} hidden path(s): {config.hidden}")
    if config.external_static_dirs:
        click.echo(f"  {len(config.external_static_dirs)} external static dir(s) configured")
        for external_dir in config.external_static_dirs:
            if not Path(external_dir).is_dir():
                _warn(f"external_static_dirs path not found: {external_dir}")


def _notify_desktop(message: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(
            ["notify-send", "--icon=dialog-information", "logseq-builder", message],
            check=False,
        )


def _report_broken_links(broken_links: list[tuple[str, str]]) -> None:
    if not broken_links:
        click.echo("\nNo broken links found.")
        return

    click.echo(f"\n{len(broken_links)} broken link(s) found (would 404):")
    by_target: dict[str, list[str]] = {}
    for source, target in broken_links:
        by_target.setdefault(target, []).append(source)
    for target, sources in sorted(by_target.items()):
        click.echo(f"  [[{target}]]")
        for source in sources:
            click.echo(f"    referenced in: {source}")


def _report_unused_assets(logseq_assets_dir: Path, used_assets: list[str]) -> None:
    if not logseq_assets_dir.is_dir():
        return

    used = set(used_assets)
    on_disk = sorted(f.name for f in logseq_assets_dir.iterdir() if f.is_file())
    unused = [name for name in on_disk if name not in used]

    if not unused:
        click.echo("\nNo unused assets found.")
        return

    click.echo(f"\n{len(unused)} unused asset(s) found (not referenced by any page):")
    for name in unused:
        click.echo(f"  assets/{name}")
