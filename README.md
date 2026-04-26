# 🧱 logseq-site-builder

Converts a [Logseq](https://logseq.com/) knowledge base into a static website (HTML + CSS + vanilla JS).

> 🤖 **Vibecoded** — ce projet a été entièrement généré par vibe coding avec Claude. Le code source est lisible et modifiable, mais l'architecture et les choix d'implémentation ont émergé de la collaboration humain-IA plutôt que d'une conception traditionnelle.

## ⚙️ How it works

```
Logseq (pages/*.org or *.md)
        │
        ▼
  LogseqReader        → reads files, detects #+PUBLIC, parses config.edn
        │
        ▼
  LinkResolver        → converts [[wiki links]] into valid HTML links
        │
        ▼
  PandocConverter     → transforms org/markdown into HTML fragments
        │
        ▼
  StaticWriter        → assembles pages via Jinja2, copies assets
        │
        ▼
  Static site (index.html, pages, style.css, js/, assets/)
```

## 📦 Requirements

- Python 3.11+
- [pandoc](https://pandoc.org/installing.html) installed on the system

```bash
# Debian/Ubuntu
sudo apt install pandoc

# macOS
brew install pandoc
```

## 🚀 Installation

```bash
git clone https://github.com/thomas-louvigne/logseq-site-builder.git
cd logseq-site-builder
pip install -e .
```

## 🔧 Configuration

On the **first run**, the builder automatically generates a `logseq-site-builder.toml` file at the root of your Logseq project, pre-filled with values read from `logseq/config.edn`. You can then edit it freely to customise your site.

To skip this behaviour, pass `--no-init-toml`.

> 📋 A fully documented reference is available in [`logseq-site-builder.example.toml`](logseq-site-builder.example.toml) — it lists every available key with descriptions and defaults.

### Priority order

Settings are resolved from lowest to highest priority:

1. `logseq/config.edn` — automatically read, no setup required
2. `logseq-site-builder.toml` — project-level overrides
3. CLI options — highest priority

This means you rarely need to duplicate values already present in `config.edn`.

### Keys auto-imported from `config.edn`

| `config.edn` key | TOML key | Description |
|---|---|---|
| `:publishing/all-pages-public?` | `[site] all_public` | Publish all pages without `#+PUBLIC` |
| `:default-home {:page "..."}` | `[site] home_page` | Home page slug |
| `:hidden [...]` | `[site] hidden` | Paths to exclude from the build |
| `:feature/enable-journals?` | `[site] enable_journals` | Enable blog/journal section |
| `:pages-directory` | `[site] pages_directory` | Pages folder (default: `pages`) |
| `:journals-directory` | `[site] journals_directory` | Journals folder (default: `journals`) |
| `:journal/page-title-format` | `[site] journal_page_title_format` | Date display format |
| `:journal/file-name-format` | `[site] journal_file_name_format` | Journal filename date format |

## 📄 Published pages

By default, only pages marked `#+PUBLIC: true` are included:

```org
#+PUBLIC: true

* Page content...
```

If `logseq/config.edn` contains `:publishing/all-pages-public? true`, all pages are published automatically. The `--all-public` CLI flag forces the same behaviour.

### 🙈 Hiding pages

Set `:hidden` in `config.edn` or `hidden` in the TOML to exclude specific files or directories (paths are relative to the Logseq project root):

```toml
[site]
hidden = ["/private", "/drafts/secret.org"]
```

## 🏠 Home page

The home page (`index.html`) is determined in this priority order:

1. `--home-page` CLI option
2. `[site] home_page` in `logseq-site-builder.toml`
3. `:default-home` in `logseq/config.edn`
4. Auto-detection (page named `index`, `home`, or `accueil`)
5. First page found

## 📝 Blog (journal entries)

When `enable_journals = true`, the builder reads journal files from the `journals/` directory and generates a blog section.

```toml
[site]
enable_journals = true
blog_title      = "Blog"
blog_slug       = "blog"

# Date formats use Java/Logseq notation (auto-read from config.edn if present)
journal_page_title_format = "dd-MM-yyyy"   # display title of each post
journal_file_name_format  = "yyyy_MM_dd"   # journal filename pattern
```

This produces:
- One HTML page per journal entry (e.g. `journal-2024-01-15.html`)
- A blog index page at `blog.html` listing all entries newest-first
- A "Blog" entry automatically added to the nav menu (if not already present)

### 📡 RSS feed

Enable RSS generation with the `rss` flag:

```toml
[site]
enable_journals = true
rss             = true
base_url        = "https://example.com"   # required for absolute URLs in the feed
```

This generates `feed.xml` (RSS 2.0) and adds a `<link rel="alternate">` tag to every page `<head>`.

## 🔗 Links and assets

The builder handles Logseq-specific syntax:

| Logseq syntax | Output |
|---|---|
| `[[Page name]]` | `<a href="page-name.html">Page name</a>` |
| `[[page][label]]` | `<a href="page.html">label</a>` |
| `[[../assets/image.jpg]]` | `<img src="assets/image.jpg">` + file copied |
| `[[../assets/document.pdf]]` | `<a href="assets/document.pdf" download>document.pdf</a>` |
| `#[[compound tag]]` | plain text (tag removed) |
| `:PROPERTIES: ... :END:` | removed |

Non-image asset links (PDF, ZIP, etc.) automatically get a `download` attribute.

## 🗂️ Generated site structure

```
output/
├── index.html          ← home page
├── my-page.html        ← other pages (flat URL structure, no subdirectories)
├── blog.html           ← blog index (when enable_journals = true)
├── journal-2024-01-15.html
├── feed.xml            ← RSS feed (when rss = true)
├── style.css
├── js/
│   └── main.js
└── assets/             ← images and files referenced in Logseq
    └── image.jpg
```

## 🏗️ Architecture

The project follows a **ports/adapters** (hexagonal) architecture:

```
src/logseq_builder/
├── domain/
│   └── page.py              # Entities: Page, SiteConfig
├── ports/
│   └── interfaces.py        # Abstract interfaces (ABC)
├── adapters/
│   ├── edn_config_loader.py # Parses logseq/config.edn
│   ├── toml_config_loader.py# Merges EDN + TOML config
│   ├── logseq_reader.py     # Reads Logseq files, journal support
│   ├── pandoc_converter.py  # org/md → HTML via pandoc
│   └── static_writer.py     # Writes site output (Jinja2)
├── services/
│   ├── site_builder.py      # Build pipeline orchestration
│   └── link_resolver.py     # Wiki link transformation
└── templates/               # Jinja2 templates (base, page, blog, rss)
```

## 🧪 Tests

```bash
pip install -e ".[dev]"
python3 -m pytest
```

## 🖥️ CLI reference

```bash
logseq-builder <logseq_dir> <output_dir> [OPTIONS]
```

### Options

| Option | Description |
|---|---|
| `--site-title TEXT` | Site title (default: directory name) |
| `--home-page SLUG` | Page to use as `index.html` (default: read from `config.edn`) |
| `--all-public` | Publish all pages, ignore `#+PUBLIC: true` |
| `--social NAME:URL` | Social link in the nav menu (repeatable) |
| `--no-init-toml` | Do not generate `logseq-site-builder.toml` on first run |

### Examples

```bash
# Minimal — home page is read from logseq/config.edn (:default-home)
logseq-builder ~/my-logseq ~/Sites/my-site

# With title and social links
logseq-builder ~/my-logseq ~/Sites/my-site \
  --site-title "My Wiki" \
  --social "Mastodon:https://mastodon.social/@me" \
  --social "GitHub:https://github.com/me"

# Publish everything, no #+PUBLIC filter
logseq-builder ~/my-logseq ~/Sites/my-site --all-public
```

### 👁️ Local preview

```bash
cd ~/Sites/my-site
python3 -m http.server 8080
# Open http://localhost:8080
```
