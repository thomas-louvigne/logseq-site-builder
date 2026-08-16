from bs4 import BeautifulSoup

from logseq_builder.services.site_builder import _sections_to_lists


class TestSectionsToLists:
    def test_leaves_levels_below_threshold_as_sections(self):
        html = (
            '<div class="page-body">'
            '<section class="level1" id="a"><h1>A</h1>'
            '<section class="level2" id="b"><h2>B</h2></section>'
            "</section></div>"
        )
        result = _sections_to_lists(html, 3)
        assert 'class="level1"' in result
        assert 'class="level2"' in result
        assert "<h1>" in result
        assert "<h2>" in result

    def test_converts_single_qualifying_section_to_li(self):
        html = '<div><section class="level3" id="c"><h3>C</h3><p>text</p></section></div>'
        result = _sections_to_lists(html, 3)
        soup = BeautifulSoup(result, "html.parser")
        li = soup.find("li")
        assert li is not None
        assert li["id"] == "c"
        assert li.find("p").get_text() == "C"
        assert "section" not in result

    def test_groups_consecutive_siblings_into_one_ul(self):
        html = (
            '<section class="level2" id="parent"><h2>Parent</h2>'
            '<section class="level3" id="c1"><h3>One</h3></section>'
            '<section class="level3" id="c2"><h3>Two</h3></section>'
            "</section>"
        )
        result = _sections_to_lists(html, 3)
        soup = BeautifulSoup(result, "html.parser")
        uls = soup.find_all("ul")
        assert len(uls) == 1
        assert len(uls[0].find_all("li", recursive=False)) == 2

    def test_nested_deeper_section_becomes_nested_ul(self):
        html = (
            '<section class="level3" id="c"><h3>C</h3>'
            '<section class="level4" id="d"><h4>D</h4></section>'
            "</section>"
        )
        result = _sections_to_lists(html, 3)
        soup = BeautifulSoup(result, "html.parser")
        outer_li = soup.find("li", id="c")
        assert outer_li is not None
        inner_ul = outer_li.find("ul")
        assert inner_ul is not None
        assert inner_ul.find("li", id="d") is not None

    def test_preserves_inline_formatting_in_heading(self):
        html = '<section class="level3" id="c"><h3>Some <em>emphasis</em> text</h3></section>'
        result = _sections_to_lists(html, 3)
        assert "<em>emphasis</em>" in result

    def test_existing_list_inside_qualifying_section_is_untouched(self):
        html = (
            '<section class="level3" id="c"><h3>C</h3>'
            "<ul><li>Plain bullet</li></ul>"
            "</section>"
        )
        result = _sections_to_lists(html, 3)
        soup = BeautifulSoup(result, "html.parser")
        li = soup.find("li", id="c")
        assert li.find("ul") is not None
        assert "Plain bullet" in result

    def test_no_qualifying_sections_is_a_noop(self):
        html = '<div class="page-body"><p>Just a paragraph.</p></div>'
        result = _sections_to_lists(html, 3)
        assert "<p>Just a paragraph.</p>" in result
        assert "<ul>" not in result
