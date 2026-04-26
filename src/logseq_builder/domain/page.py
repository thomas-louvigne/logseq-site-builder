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

    @property
    def output_filename(self) -> str:
        return f"{self.slug}.html"


@dataclass
class SiteConfig:
    title: str
    base_url: str = ""
    social_links: dict[str, str] = field(default_factory=dict)
    home_slug: str = "index"
