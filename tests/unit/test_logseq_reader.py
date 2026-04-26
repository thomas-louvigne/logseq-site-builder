from pathlib import Path
import pytest

from logseq_builder.adapters.logseq_reader import (
    LogseqReader,
    _decode_logseq_filename,
    _parse_is_public,
    _parse_title,
)


class TestDecodeLogseqFilename:
    def test_simple(self):
        assert _decode_logseq_filename("Dragons") == "Dragons"

    def test_triple_lowbar_namespace(self):
        assert _decode_logseq_filename("Quete-tracogna___session-1") == "session-1"

    def test_no_namespace(self):
        assert _decode_logseq_filename("Gustave Coste") == "Gustave Coste"


class TestParseTitle:
    def test_from_title_directive(self):
        content = "#+TITLE: My Great Page\n* Content"
        assert _parse_title(content, "my-great-page") == "My Great Page"

    def test_from_filename(self):
        content = "* Content"
        assert _parse_title(content, "Dragons") == "Dragons"

    def test_filename_dashes_to_spaces(self):
        content = "* Content"
        assert _parse_title(content, "Gustave-Coste") == "Gustave Coste"


class TestParseIsPublic:
    def test_public_true(self):
        assert _parse_is_public("#+PUBLIC: true\n* Content", all_public=False) is True

    def test_public_false_absent(self):
        assert _parse_is_public("* Content", all_public=False) is False

    def test_all_public_override(self):
        assert _parse_is_public("* Content", all_public=True) is True

    def test_case_insensitive(self):
        assert _parse_is_public("#+public: TRUE\n* x", all_public=False) is True


@pytest.fixture
def fake_logseq_dir(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Home.org").write_text("#+PUBLIC: true\n* Welcome\nHello.", encoding="utf-8")
    (pages / "Private.org").write_text("* Secret content.", encoding="utf-8")
    (pages / "Notes.md").write_text("#+PUBLIC: true\n# Notes\nSome notes.", encoding="utf-8")
    return tmp_path


class TestLogseqReader:
    def test_finds_public_pages(self, fake_logseq_dir):
        reader = LogseqReader(fake_logseq_dir)
        public = [p for p in reader.find_all() if p.is_public]
        slugs = {p.slug for p in public}
        assert "home" in slugs
        assert "notes" in slugs

    def test_private_page_not_public(self, fake_logseq_dir):
        reader = LogseqReader(fake_logseq_dir)
        private = [p for p in reader.find_all() if p.slug == "private"]
        assert len(private) == 1
        assert private[0].is_public is False

    def test_all_public_flag(self, fake_logseq_dir):
        reader = LogseqReader(fake_logseq_dir, all_public=True)
        all_pages = list(reader.find_all())
        assert all(p.is_public for p in all_pages)

    def test_page_format_detected(self, fake_logseq_dir):
        reader = LogseqReader(fake_logseq_dir)
        pages = {p.slug: p for p in reader.find_all()}
        assert pages["home"].format == "org"
        assert pages["notes"].format == "md"

    def test_detects_all_public_from_config(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "Page.org").write_text("* Content", encoding="utf-8")
        config_dir = tmp_path / "logseq"
        config_dir.mkdir()
        (config_dir / "config.edn").write_text(
            "{:publishing/all-pages-public? true}", encoding="utf-8"
        )
        reader = LogseqReader(tmp_path)
        all_pages = list(reader.find_all())
        assert all(p.is_public for p in all_pages)

    def test_parses_default_home_from_config(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        config_dir = tmp_path / "logseq"
        config_dir.mkdir()
        (config_dir / "config.edn").write_text(
            '{:default-home {:page "Chroniques-Insoumises"}}', encoding="utf-8"
        )
        reader = LogseqReader(tmp_path)
        assert reader.default_home_slug == "chroniques-insoumises"

    def test_default_home_none_when_absent(self, fake_logseq_dir):
        reader = LogseqReader(fake_logseq_dir)
        assert reader.default_home_slug is None
