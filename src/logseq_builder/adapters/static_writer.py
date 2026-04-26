import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..domain.page import Page, SiteConfig
from ..ports.interfaces import SiteWriter

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_STATIC_DIR = Path(__file__).parent.parent / "static"


class StaticWriter(SiteWriter):
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=True,
        )

    def write_page(self, page: Page, config: SiteConfig, is_home: bool = False) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("page.html")
        html = template.render(page=page, config=config)
        filename = "index.html" if is_home else page.output_filename
        (self._output_dir / filename).write_text(html, encoding="utf-8")

    def copy_assets(self, asset_filenames: list[str], logseq_assets_dir: Path) -> None:
        if not asset_filenames:
            return
        assets_out = self._output_dir / "assets"
        assets_out.mkdir(parents=True, exist_ok=True)
        for filename in asset_filenames:
            src = logseq_assets_dir / filename
            if src.exists():
                shutil.copy2(src, assets_out / filename)

    def write_static_files(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        js_out = self._output_dir / "js"
        js_out.mkdir(parents=True, exist_ok=True)

        css_src = _STATIC_DIR / "style.css"
        if css_src.exists():
            shutil.copy2(css_src, self._output_dir / "style.css")

        js_src = _STATIC_DIR / "js" / "main.js"
        if js_src.exists():
            shutil.copy2(js_src, js_out / "main.js")
