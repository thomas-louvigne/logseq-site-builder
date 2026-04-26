from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from ..domain.page import Page, SiteConfig


class PageRepository(ABC):
    @abstractmethod
    def find_all(self) -> Iterator[Page]:
        ...


class ContentConverter(ABC):
    @abstractmethod
    def convert(self, content: str, fmt: str) -> str:
        ...


class SiteWriter(ABC):
    @abstractmethod
    def write_page(self, page: Page, config: SiteConfig, is_home: bool = False) -> None:
        ...

    @abstractmethod
    def copy_assets(self, asset_filenames: list[str], logseq_assets_dir: Path) -> None:
        ...

    @abstractmethod
    def write_static_files(self) -> None:
        ...
