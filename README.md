# logseq-site-builder

Transforme une base de connaissances [Logseq](https://logseq.com/) en site web statique (HTML + CSS + JS vanilla).

## Fonctionnement

```
Logseq (pages/*.org ou *.md)
        │
        ▼
  LogseqReader        → lit les fichiers, détecte #+PUBLIC, parse config.edn
        │
        ▼
  LinkResolver        → convertit [[liens wiki]] en liens HTML valides
        │
        ▼
  PandocConverter     → transforme org/markdown en fragments HTML
        │
        ▼
  StaticWriter        → assemble les pages via Jinja2, copie les assets
        │
        ▼
  Site statique (index.html, pages, style.css, js/, assets/)
```

## Prérequis

- Python 3.11+
- [pandoc](https://pandoc.org/installing.html) installé sur le système

```bash
# Debian/Ubuntu
sudo apt install pandoc

# macOS
brew install pandoc
```

## Installation

```bash
git clone https://codeberg.org/thomas-babord/logseq-site-builder.git
cd logseq-site-builder
pip install -e .
```

## Utilisation

```bash
logseq-builder <dossier_logseq> <dossier_sortie> [OPTIONS]
```

### Options

| Option | Description |
|---|---|
| `--site-title TEXT` | Titre du site (défaut : nom du dossier) |
| `--home-page SLUG` | Page à utiliser comme `index.html` (défaut : lu dans `config.edn`) |
| `--all-public` | Publier toutes les pages, ignorer `#+PUBLIC: true` |
| `--social NAME:URL` | Lien réseau social dans le menu (répétable) |

### Exemples

```bash
# Minimal — la page d'accueil est lue dans logseq/config.edn (:default-home)
logseq-builder ~/mon-logseq ~/Sites/mon-site

# Avec titre et liens sociaux
logseq-builder ~/mon-logseq ~/Sites/mon-site \
  --site-title "Mon Wiki" \
  --social "Mastodon:https://mastodon.social/@moi" \
  --social "GitHub:https://github.com/moi"

# Tout publier, sans filtre #+PUBLIC
logseq-builder ~/mon-logseq ~/Sites/mon-site --all-public
```

### Prévisualiser en local

```bash
cd ~/Sites/mon-site
python3 -m http.server 8080
# Ouvrir http://localhost:8080
```

## Structure du site généré

```
sortie/
├── index.html        ← page d'accueil
├── ma-page.html      ← autres pages (URL plate, sans sous-dossiers)
├── style.css
├── js/
│   └── main.js
└── assets/           ← images et fichiers référencés dans Logseq
    └── image.jpg
```

## Pages publiées

Par défaut, seules les pages marquées `#+PUBLIC: true` sont incluses :

```org
#+PUBLIC: true

* Contenu de la page...
```

Si `logseq/config.edn` contient `:publishing/all-pages-public? true`, toutes les pages sont publiées automatiquement. L'option `--all-public` permet de forcer ce comportement depuis la ligne de commande.

## Page d'accueil

La page d'accueil (`index.html`) est déterminée dans cet ordre de priorité :

1. Option `--home-page` passée en ligne de commande
2. Clé `:default-home` dans `logseq/config.edn`
3. Détection automatique (page nommée `index`, `home` ou `accueil`)
4. Première page trouvée

## Liens et assets Logseq

Le builder gère les spécificités de la syntaxe Logseq :

| Syntaxe Logseq | Résultat |
|---|---|
| `[[Nom de page]]` | `<a href="nom-de-page.html">Nom de page</a>` |
| `[[page][label]]` | `<a href="page.html">label</a>` |
| `[[../assets/image.jpg]]` | `<img src="assets/image.jpg">` + copie du fichier |
| `#[[tag composé]]` | texte brut (tag supprimé) |
| `:PROPERTIES: ... :END:` | supprimé |

## Architecture

Le projet suit une architecture **ports/adapters** (hexagonale) avec les principes SOLID :

```
src/logseq_builder/
├── domain/
│   └── page.py              # Entités : Page, SiteConfig
├── ports/
│   └── interfaces.py        # Interfaces abstraites (ABC)
├── adapters/
│   ├── logseq_reader.py     # Lecture des fichiers Logseq
│   ├── pandoc_converter.py  # Conversion org/md → HTML via pandoc
│   └── static_writer.py     # Écriture du site (Jinja2)
├── services/
│   ├── site_builder.py      # Orchestration du pipeline
│   └── link_resolver.py     # Transformation des liens wiki
└── templates/               # Templates Jinja2 (base, page, partials)
```

## Tests

```bash
pip install -e ".[dev]"
python3 -m pytest
```

50 tests couvrant les unités (`link_resolver`, `logseq_reader`, `page`) et l'intégration complète (build d'un mini-site en dossier temporaire).
