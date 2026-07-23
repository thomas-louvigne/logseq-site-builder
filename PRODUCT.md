# Product

## Register

product

## Users

The Logseq user who builds their own site and is also its primary reader. They are the builder AND the audience — someone publishing their knowledge base for self-reference first, with public access as a side effect. They are typically technically fluent (comfortable with CLI, TOML config, Org/Markdown), curious, and use Logseq as an active thinking tool rather than a finished publishing platform.

Secondary: occasional outside visitors who land on a specific note — a colleague, someone from a linked post, a search engine visitor. They arrive for one page and may explore adjacent notes if the navigation invites it.

## Product Purpose

logseq-site-builder converts a Logseq knowledge base into a static website (HTML + CSS + vanilla JS). It exists so that Logseq users can share their notes publicly without a backend, without a CMS, and without abandoning their existing note-taking workflow. Success looks like: the user runs one CLI command and gets a fast, readable site that feels like a natural extension of their Logseq graph — not like a generic blog or a corporate wiki.

Two surfaces, one product:

- **Generated site theme** — the HTML/CSS/JS template readers see. This is where most design work lives.
- **CLI / tooling DX** — terminal output, error messages, config schema, documentation. Functional clarity over decoration.

## Brand Personality

Alive, curious, exploratory. The site should feel like a living document someone is actively tending — not a finished artifact, not a polished product page. The personality is the knowledge worker's personality: interested, interconnected, always-a-work-in-progress.

## Anti-references

No strong negative references. Avoid drifting toward:
- Corporate PKM tool aesthetic (Notion, Obsidian Publish) — this is someone's personal space, not a product
- Sterile developer docs (Docusaurus, GitBook) — the tool should disappear, not brand itself

## Design Principles

1. **The tool disappears, the knowledge stays** — Every UI element exists to surface content and connections. The chrome is invisible. The notes are the product.
2. **Interconnection is the feature** — Wiki links, page relationships, and cross-references are the core value of Logseq. Navigation should make following connections feel like discovery, not navigation.
3. **Personal without being precious** — This is someone's active thinking space. It should feel inhabited and alive, not polished for a launch or staged for an audience.
4. **Density is a virtue** — The builder is a knowledge worker. Dense, scannable information is a feature. Whitespace is earned, not defaulted to.
5. **Evolving, not finished** — A digital garden grows and changes. The design should support a sense of organic growth rather than published-artifact completeness.

## Accessibility & Inclusion

WCAG AA. Minimum 4.5:1 contrast for body text, 3:1 for large text. Full keyboard navigation. Screen reader compatible markup. Reduced motion support for any animations added to the generated theme.
