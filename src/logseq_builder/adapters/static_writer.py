import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..domain.page import Page, SiteConfig
from ..ports.interfaces import SiteWriter

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_STATIC_DIR = Path(__file__).parent.parent / "static"
THEMES_DIR = Path(__file__).parent.parent / "themes"


class StaticWriter(SiteWriter):
    def __init__(self, output_dir: Path, theme_css: Path | None = None) -> None:
        self._output_dir = output_dir
        self._theme_css = theme_css
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            # Autoescape HTML only; RSS/XML templates handle escaping themselves
            autoescape=select_autoescape(["html", "htm"]),
        )

    def write_page(self, page: Page, config: SiteConfig, is_home: bool = False) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("page.html")
        html = template.render(page=page, config=config, is_home=is_home)
        filename = "index.html" if is_home else page.output_filename
        (self._output_dir / filename).write_text(html, encoding="utf-8")

    def write_blog_index(self, journal_pages: list[Page], config: SiteConfig) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("blog.html")
        html = template.render(journal_pages=journal_pages, config=config)
        (self._output_dir / f"{config.blog_slug}.html").write_text(html, encoding="utf-8")

    def write_rss(self, journal_pages: list[Page], config: SiteConfig) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("rss.xml")
        xml = template.render(journal_pages=journal_pages, config=config)
        (self._output_dir / "feed.xml").write_text(xml, encoding="utf-8")

    def copy_assets(self, asset_filenames: list[str], logseq_assets_dir: Path) -> None:
        if not asset_filenames:
            return
        assets_out = self._output_dir / "assets"
        assets_out.mkdir(parents=True, exist_ok=True)
        for filename in asset_filenames:
            src = logseq_assets_dir / filename
            if src.exists():
                shutil.copy2(src, assets_out / filename)

    def write_404(self, config: SiteConfig) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("404.html")
        html = template.render(config=config)
        (self._output_dir / "404.html").write_text(html, encoding="utf-8")

    def copy_pages_subdirs(self, pages_dir: Path) -> None:
        if not pages_dir.is_dir():
            return
        for subdir in pages_dir.iterdir():
            if not subdir.is_dir():
                continue
            has_web_files = any(
                f.suffix in {".html", ".css"}
                for f in subdir.rglob("*")
                if f.is_file()
            )
            if has_web_files:
                dest = self._output_dir / subdir.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(subdir, dest)

    def write_sitemap(self, pages: list[Page], journal_pages: list[Page], config: SiteConfig) -> None:
        if not config.base_url:
            return
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("sitemap.xml")

        entries = []
        for page in pages:
            entries.append({
                "filename": "index.html" if page.slug == config.home_slug else page.output_filename,
                "date": page.date.isoformat() if page.date else None,
                "changefreq": "weekly",
                "priority": "1.0" if page.slug == config.home_slug else "0.8",
            })
        for page in journal_pages:
            entries.append({
                "filename": page.output_filename,
                "date": page.date.isoformat() if page.date else None,
                "changefreq": "never",
                "priority": "0.6",
            })

        xml = template.render(pages=entries, config=config)
        (self._output_dir / "sitemap.xml").write_text(xml, encoding="utf-8")

    def write_robots(self, config: SiteConfig) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        lines = ["User-agent: *", "Allow: /"]
        if config.base_url:
            lines.append(f"Sitemap: {config.base_url}/sitemap.xml")
        (self._output_dir / "robots.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_static_files(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        js_out = self._output_dir / "js"
        js_out.mkdir(parents=True, exist_ok=True)

        css_src = self._theme_css if self._theme_css is not None else _STATIC_DIR / "style.css"
        if css_src.exists():
            shutil.copy2(css_src, self._output_dir / "style.css")

        js_src = _STATIC_DIR / "js" / "main.js"
        if js_src.exists():
            shutil.copy2(js_src, js_out / "main.js")
