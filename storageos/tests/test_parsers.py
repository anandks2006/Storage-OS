"""Tests for parsers: markdown, text, pdf."""
from parsers.markdown import parse_markdown
from parsers.text import parse_text
from parsers.pdf import parse_pdf


class TestMarkdownParser:
    def test_heading_extraction(self):
        content = "# Title\n\nPara 1.\n\n## Section\n\nPara 2.\n"
        nodes, passages = parse_markdown(content, "res-1", "ver-1")
        headings = [n for n in nodes if n.node_type == "heading"]
        assert len(headings) == 2
        assert headings[0].title == "Title"
        assert headings[0].level == 1
        assert headings[1].title == "Section"
        assert headings[1].level == 2

    def test_paragraph_extraction(self):
        content = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n"
        nodes, passages = parse_markdown(content, "res-1", "ver-1")
        assert len(passages) >= 2
        texts = [p[0] for p in passages]
        assert any("First paragraph" in t for t in texts)
        assert any("Second paragraph" in t for t in texts)

    def test_pre_heading_content(self):
        content = "Before heading.\n\n# Title\n\nAfter heading.\n"
        nodes, passages = parse_markdown(content, "res-1", "ver-1")
        assert len(passages) >= 2
        assert passages[0][0] == "Before heading."

    def test_no_headings(self):
        content = "Just plain text with no headings at all."
        nodes, passages = parse_markdown(content, "res-1", "ver-1")
        assert len(passages) == 1
        assert passages[0][0] == content.strip()


class TestTextParser:
    def test_paragraph_detection(self):
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n"
        nodes, passages = parse_text(content, "res-1", "ver-1")
        assert len(nodes) == 1
        assert nodes[0].node_type == "document"
        assert len(passages) == 3

    def test_empty_content(self):
        content = ""
        nodes, passages = parse_text(content, "res-1", "ver-1")
        assert len(nodes) == 1
        assert len(passages) == 0

    def test_single_paragraph(self):
        content = "Just one paragraph."
        nodes, passages = parse_text(content, "res-1", "ver-1")
        assert len(passages) == 1
        assert passages[0][0] == content


class TestPDFParser:
    def test_fallback_parsing(self, sample_pdf):
        nodes, passages = parse_pdf(sample_pdf, "res-1", "ver-1")
        assert len(nodes) >= 1
        assert nodes[0].node_type == "page"
        assert len(passages) >= 1
