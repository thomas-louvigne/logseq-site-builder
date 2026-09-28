import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..domain.page import Page, SiteConfig
from ..ports.interfaces import SiteWriter
from .themes import DEFAULT_THEME_CSS

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_STATIC_DIR = Path(__file__).parent.parent / "static"


class StaticWriter(SiteWriter):
    def __init__(self, output_dir: Path, theme_css: Path | None = None) -> None:
        self._output_dir = output_dir
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._theme_css = theme_css
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            # Autoescape HTML only; RSS/XML templates handle escaping themselves
            autoescape=select_autoescape(["html", "htm"]),
        )

    def _page_url(self, page: Page, config: SiteConfig) -> str:
        return "index.html" if page.slug == config.home_slug else page.output_filename

    def _write(self, filename: str, text: str) -> None:
        (self._output_dir / filename).write_text(text, encoding="utf-8")

    def _render(self, template_name: str, filename: str, **context: object) -> None:
        self._write(filename, self._env.get_template(template_name).render(**context))

    def write_page(self, page: Page, config: SiteConfig, is_home: bool = False) -> None:
        filename = "index.html" if is_home else page.output_filename
        self._render("page.html", filename, page=page, config=config, is_home=is_home, canonical_path=filename)

    def write_blog_index(self, journal_pages: list[Page], config: SiteConfig) -> None:
        filename = f"{config.blog_slug}.html"
        self._render("blog.html", filename, journal_pages=journal_pages, config=config, canonical_path=filename)

    def write_rss(self, journal_pages: list[Page], config: SiteConfig) -> None:
        self._render("rss.xml", "feed.xml", journal_pages=journal_pages, config=config)

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
        self._render("404.html", "404.html", config=config)

    def copy_pages_subdirs(self, pages_dir: Path, require_web_files: bool = True) -> None:
        if not pages_dir.is_dir():
            return
        for subdir in pages_dir.iterdir():
            if not subdir.is_dir():
                continue
            if require_web_files:
                has_web_files = any(
                    f.suffix in {".html", ".css"}
                    for f in subdir.rglob("*")
                    if f.is_file()
                )
                if not has_web_files:
                    continue
            dest = self._output_dir / subdir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(subdir, dest)

    def write_sitemap(self, pages: list[Page], journal_pages: list[Page], config: SiteConfig) -> None:
        if not config.base_url:
            return
        entries = []
        for page in pages:
            is_home = page.slug == config.home_slug
            entries.append({
                "filename": self._page_url(page, config),
                "date": page.date.isoformat() if page.date else None,
                "changefreq": "weekly",
                "priority": "1.0" if is_home else "0.8",
            })
        for page in journal_pages:
            entries.append({
                "filename": page.output_filename,
                "date": page.date.isoformat() if page.date else None,
                "changefreq": "never",
                "priority": "0.6",
            })

        self._render("sitemap.xml", "sitemap.xml", pages=entries, config=config)

    def write_robots(self, config: SiteConfig) -> None:
        lines = ["User-agent: *", "Allow: /"]
        if config.base_url:
            lines.append(f"Sitemap: {config.base_url}/sitemap.xml")
        self._write("robots.txt", "\n".join(lines) + "\n")

    def write_search_index(self, pages: list[Page], journal_pages: list[Page], config: SiteConfig) -> None:
        entries = [
            {"title": page.title, "url": self._page_url(page, config), "content": _strip_html(page.html_content)}
            for page in [*pages, *journal_pages]
        ]
        self._write("js/search.js", "window.__SEARCH_DATA__ = " + json.dumps(entries, ensure_ascii=False) + ";")

    def write_static_files(self) -> None:
        js_out = self._output_dir / "js"
        js_out.mkdir(parents=True, exist_ok=True)

        css_src = self._theme_css if self._theme_css is not None else DEFAULT_THEME_CSS
        if css_src.exists():
            shutil.copy2(css_src, self._output_dir / "style.css")
        # Theme-independent, so printing gets the same menu-free layout
        # whatever theme (built-in or custom) the site uses.
        shutil.copy2(_STATIC_DIR / "print.css", self._output_dir / "print.css")

        for js_name in ("main.js", "fuse.min.js"):
            js_src = _STATIC_DIR / "js" / js_name
            if js_src.exists():
                shutil.copy2(js_src, js_out / js_name)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()
