import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageFormat = Literal["org", "md"]

# Buttons of the share bar under each page title, in display order; each one
# can be switched off from the [share] table of logseq-site-builder.toml.
SHARE_BUTTONS = ("native", "whatsapp", "facebook", "x", "bluesky", "linkedin", "email", "copy_link", "print")
# "horizontal": a row under the title; "vertical": a column pinned to the
# right edge of the screen (falls back to the row on narrow screens).
ShareLayout = Literal["horizontal", "vertical"]
SHARE_LAYOUTS: tuple[ShareLayout, ...] = ("horizontal", "vertical")


@dataclass
class Page:
    title: str
    slug: str
    raw_content: str
    source_path: Path
    format: PageFormat
    is_public: bool
    html_content: str = ""
    description: str = ""
    icon: str = ""
    asset_filenames: list[str] = field(default_factory=list)
    date: datetime.date | None = None  # set for journal/blog posts
    headline: str = ""  # journal posts only: title parsed from the entry's own content

    @property
    def output_filename(self) -> str:
        return f"{self.slug}.html"


@dataclass
class SiteConfig:
    title: str
    author: str = ""
    description: str = ""
    base_url: str = ""
    social_links: dict[str, str] = field(default_factory=dict)
    home_slug: str = "index"
    menu: list[dict[str, str | bool]] = field(default_factory=list)
    org_listify_headings_from: int | Literal["auto"] | None = "auto"
    # From config.edn
    all_public: bool = False
    hidden: list[str] = field(default_factory=list)
    pages_directory: str = "pages"
    journals_directory: str = "journals"
    # Blog / journals feature
    enable_journals: bool = False
    journal_page_title_format: str = "dd-MM-yyyy"
    journal_file_name_format: str = "yyyy_MM_dd"
    blog_title: str = "Blog"
    blog_slug: str = "blog"
    rss: bool = False
    lang: str = "en"
    tree_view: bool = True
    external_static_dirs: list[str] = field(default_factory=list)
    share: dict[str, bool] = field(default_factory=lambda: dict.fromkeys(SHARE_BUTTONS, True))
    share_layout: ShareLayout = "horizontal"
