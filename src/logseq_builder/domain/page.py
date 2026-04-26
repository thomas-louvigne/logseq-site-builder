import datetime
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Page:
    title: str
    slug: str
    raw_content: str
    source_path: Path
    format: str  # "org" | "md"
    is_public: bool
    html_content: str = ""
    asset_filenames: list[str] = field(default_factory=list)
    date: datetime.date | None = None  # set for journal/blog posts

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
    menu: list[dict[str, str]] = field(default_factory=list)
    flatten_headings_from: int | None = None
    # From config.edn
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
