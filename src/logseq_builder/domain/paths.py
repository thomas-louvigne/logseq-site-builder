import re
import unicodedata
from pathlib import Path

IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".bmp", ".ico", ".tiff", ".tif", ".avif",
})


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")
