from bs4 import BeautifulSoup

from logseq_builder.services.site_builder import _add_collapsible_tree, _auto_listify, _sections_to_lists


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


class TestAutoListify:
    def test_deepest_level_becomes_bullets_shallower_stays_heading(self):
        html = (
            '<section class="level1" id="titre"><h1>titre</h1>'
            '<section class="level2" id="a"><h2>pas titre</h2><p>text</p></section>'
            '<section class="level2" id="b"><h2>pas titre</h2><p>text</p></section>'
            "</section>"
        )
        result = _auto_listify(html)
        soup = BeautifulSoup(result, "html.parser")
        assert soup.find("h1") is not None
        assert soup.find("h2") is None
        lis = soup.find_all("li")
        assert len(lis) == 2

    def test_three_levels_only_deepest_becomes_bullets(self):
        html = (
            '<section class="level1" id="a"><h1>A</h1>'
            '<section class="level2" id="b"><h2>B</h2>'
            '<section class="level3" id="c"><h3>C</h3></section>'
            "</section></section>"
        )
        result = _auto_listify(html)
        soup = BeautifulSoup(result, "html.parser")
        assert soup.find("h1") is not None
        assert soup.find("h2") is not None
        assert soup.find("h3") is None
        assert soup.find("li", id="c") is not None

    def test_single_level_becomes_plain_paragraphs_not_bullets(self):
        html = (
            '<section class="level1" id="titre"><h1>titre</h1><p>some text</p></section>'
            '<section class="level1" id="titre2"><h1>titre2</h1><p>more text</p></section>'
        )
        result = _auto_listify(html)
        soup = BeautifulSoup(result, "html.parser")
        assert soup.find("h1") is None
        assert soup.find("ul") is None
        assert soup.find("section") is None
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        assert paragraphs == ["titre", "some text", "titre2", "more text"]

    def test_no_headings_is_a_noop(self):
        html = '<div class="page-body"><p>Just a paragraph.</p></div>'
        result = _auto_listify(html)
        assert "<p>Just a paragraph.</p>" in result
        assert "<ul>" not in result


class TestAddCollapsibleTree:
    def test_leaf_li_is_untouched(self):
        html = "<ul><li>Leaf</li></ul>"
        result = _add_collapsible_tree(html)
        assert "<details>" not in result
        assert "<li>Leaf</li>" in result

    def test_li_with_nested_list_becomes_details(self):
        html = "<ul><li><p>Parent</p><ul><li>Child</li></ul></li></ul>"
        result = _add_collapsible_tree(html)
        soup = BeautifulSoup(result, "html.parser")
        li = soup.find("li")
        details = li.find("details", recursive=False)
        assert details is not None
        assert details["open"] == ""
        summary = details.find("summary")
        assert summary.find("p").get_text() == "Parent"
        assert details.find("ul").find("li").get_text() == "Child"

    def test_bare_text_before_nested_list_goes_in_summary(self):
        html = "<ul><li>Parent<ul><li>Child</li></ul></li></ul>"
        result = _add_collapsible_tree(html)
        soup = BeautifulSoup(result, "html.parser")
        summary = soup.find("summary")
        assert summary.get_text() == "Parent"

    def test_leaf_section_is_untouched(self):
        html = '<section class="level1" id="a"><h1>A</h1></section>'
        result = _add_collapsible_tree(html)
        assert "<details>" not in result
        assert "<h1>A</h1>" in result

    def test_section_with_nested_section_becomes_details(self):
        html = (
            '<section class="level1" id="a"><h1>A</h1>'
            '<section class="level2" id="b"><h2>B</h2></section>'
            "</section>"
        )
        result = _add_collapsible_tree(html)
        soup = BeautifulSoup(result, "html.parser")
        outer = soup.find("section", id="a")
        details = outer.find("details", recursive=False)
        assert details is not None
        assert details.find("summary").find("h1").get_text() == "A"
        assert details.find("section", id="b") is not None

    def test_ids_are_preserved_on_the_original_element(self):
        html = '<ul><li id="x"><p>Parent</p><ul><li id="y">Child</li></ul></li></ul>'
        result = _add_collapsible_tree(html)
        soup = BeautifulSoup(result, "html.parser")
        assert soup.find("li", id="x") is not None
        assert soup.find("li", id="y") is not None

    def test_combines_with_listified_headings(self):
        html = (
            '<section class="level3" id="c"><h3>Parent</h3>'
            '<section class="level4" id="d"><h4>Child</h4></section>'
            "</section>"
        )
        listified = _sections_to_lists(html, 3)
        result = _add_collapsible_tree(listified)
        soup = BeautifulSoup(result, "html.parser")
        parent_li = soup.find("li", id="c")
        details = parent_li.find("details", recursive=False)
        assert details is not None
        assert details.find("li", id="d") is not None
