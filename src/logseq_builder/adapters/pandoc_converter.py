import pypandoc

from ..ports.interfaces import ContentConverter

_PANDOC_FORMAT_MAP = {
    "org": "org",
    "md": "markdown",
}


class PandocConverter(ContentConverter):
    def convert(self, content: str, fmt: str) -> str:
        pandoc_fmt = _PANDOC_FORMAT_MAP.get(fmt, fmt)
        return pypandoc.convert_text(
            content,
            "html",
            format=pandoc_fmt,
            extra_args=["--no-highlight"],
        )
