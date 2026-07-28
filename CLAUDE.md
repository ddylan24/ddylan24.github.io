# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this is

This is a personal academic website built on the **[Academic Pages](https://github.com/academicpages/academicpages.github.io)** template — a fork (later detached) of the [Minimal Mistakes](https://mmistakes.github.io/minimal-mistakes/) Jekyll theme. It is a **static Jekyll site hosted on GitHub Pages** at `https://ddylan24.github.io` (owner: Dylan Durgin, Computer Engineering student at Virginia Tech).

The site is **data-driven**: content lives in structured Markdown/YAML/JSON files, and the theme (layouts, includes, Sass) transforms that content into static HTML on each push. There is no application server or database.

### Key architectural idea

Content is separated from presentation. When editing the site:
- **To change content** (publications, talks, bio, CV, blog posts) → edit files in the `_pages/`, `_publications/`, `_talks/`, `_teaching/`, `_portfolio/`, `_posts/`, and `_data/` directories.
- **To change appearance/behavior** → edit `_layouts/`, `_includes/`, `_sass/`, and `assets/`.
- **To change site-wide settings** → edit `_config.yml`.

## Repository structure

| Path | Purpose |
|------|---------|
| `_config.yml` | Main site configuration: title, author profile, social links, collections, plugins, defaults. **Not auto-reloaded** by `jekyll serve` — restart the server after editing. |
| `_config_docker.yml` | Overrides merged on top of `_config.yml` when running via Docker. |
| `_data/` | Structured site data: `navigation.yml` (top-nav menu), `authors.yml`, `ui-text.yml` (i18n strings), `cv.json` (data for the JSON-driven CV), `comments/`. |
| `_pages/` | Standalone pages (about/home, publications, talks, teaching, portfolio, CV, archives, guide). The home page is `about.md` (`permalink: /`). |
| `_publications/` | One Markdown file per publication (a Jekyll collection). |
| `_talks/` | One Markdown file per talk (a Jekyll collection). |
| `_teaching/` | One Markdown file per teaching entry (a Jekyll collection). |
| `_portfolio/` | One file per portfolio item (a Jekyll collection). |
| `_posts/` | Blog posts, named `YYYY-MM-DD-title.md`. |
| `_drafts/` | Unpublished blog drafts (not built unless `--drafts` is passed). |
| `_layouts/` | Page templates (`single`, `archive`, `talk`, `cv-layout`, `splash`, `default`, etc.). |
| `_includes/` | Reusable HTML/Liquid partials (masthead, footer, author profile, archive item renderers, analytics/comments providers, `head/`, `nav_list`, etc.). |
| `_sass/` | Sass partials — `theme/`, `layout/`, `include/`, and vendored `vendor/` (Susy, Breakpoint, Font Awesome). Compiled via `assets/css/main.scss`. |
| `assets/` | Compiled/served front-end assets: `css/`, `js/` (including bundled `js/main.min.js`), `fonts/`, `webfonts/`. |
| `images/` | Site images (profile avatar, theme screenshots, bio photos). |
| `files/` | Static downloads (PDFs, etc.). Served at `/files/...`. |
| `markdown_generator/` | Jupyter notebooks + Python scripts to generate publication/talk Markdown from TSV files. |
| `scripts/` | Helper scripts: `cv_markdown_to_json.py` + `update_cv_json.sh` convert `_pages/cv.md` into `_data/cv.json`. |
| `talkmap.ipynb` / `talkmap.py` / `talkmap/` | Generate an interactive map of talk locations from `_talks/` metadata. |
| `.github/workflows/scrape_talks.yml` | CI workflow that re-runs `talkmap.ipynb` when talk data changes and commits the result. |
| `.devcontainer/`, `Dockerfile`, `docker-compose.yaml` | Containerized local-dev setup. |

## Content conventions

Every content file starts with YAML front matter. Match the shape of the existing files in each collection.

**Publications** (`_publications/YYYY-MM-DD-slug.md`):
```yaml
---
title: "Paper Title"
collection: publications
category: manuscripts   # one of: books, manuscripts (Journal Articles), conferences — defined in _config.yml publication_category
permalink: /publication/YYYY-MM-DD-slug
excerpt: 'Short description.'
date: YYYY-MM-DD
venue: 'Journal or Conference'
paperurl: 'https://.../paper.pdf'
citation: 'Author. (Year). "Title." <i>Venue</i>. volume(issue).'
---
```

**Talks** (`_talks/YYYY-MM-DD-slug.md`): front matter with `title`, `collection: talks`, `type` ("Talk", "Tutorial", etc.), `permalink`, `venue`, `date`, `location`. The location string is what the talkmap geocodes.

**Teaching / Portfolio / Posts**: follow the pattern of existing files in each directory. Posts must be named `YYYY-MM-DD-title.md`.

Collection defaults (layout, `author_profile`, sharing, comments) are set in the `defaults:` block of `_config.yml`, so individual files usually only need their own metadata.

### Adding content in bulk

Rather than hand-writing many files, the `markdown_generator/` tooling converts a TSV of publications/talks into individual Markdown files:
- Edit `publications.tsv` / `talks.tsv`, then run the corresponding notebook (`publications.ipynb`, `talks.ipynb`) or Python script (`publications.py`, `talks.py`).

### The CV

Two CV variants exist; only one should be linked in `_data/navigation.yml` at a time:
- **Markdown CV** — `_pages/cv.md` (currently linked).
- **JSON CV** — `_pages/cv-json.md`, driven by `_data/cv.json`.

To regenerate the JSON from the Markdown CV, run `scripts/update_cv_json.sh` (wraps `scripts/cv_markdown_to_json.py`).

## Site configuration

- **Author profile / sidebar**: the `author:` block in `_config.yml`. Blank social/academic fields are hidden automatically.
- **Navigation menu**: `_data/navigation.yml` (`main:` list). Removing a link hides it from the header but does not remove the page.
- **Theme**: `site_theme` in `_config.yml` — options are `default`, `air`, `sunrise`, `mint`, `dirt`, `contrast`.
- **Plugins**: GitHub-Pages-compatible only (see `plugins:` / `whitelist:` in `_config.yml`): jekyll-feed, jekyll-gist, jekyll-paginate, jekyll-sitemap, jekyll-redirect-from, jemoji.

## Local development

The site requires **Ruby + Bundler** (Jekyll) and optionally **Node.js** (to rebuild JS assets).

**Standard flow:**
```bash
bundle install                       # install Ruby gems (delete Gemfile.lock and retry on errors)
bundle exec jekyll serve -l -H localhost   # serve at http://localhost:4000 with live reload
```
- Editing Markdown/HTML content triggers an automatic rebuild.
- Editing `_config.yml` (and other core config) requires **stopping and restarting** Jekyll.

**Docker (no local Ruby needed):**
```bash
chmod -R 777 .
docker compose up      # serves at http://localhost:4000
```

**VS Code Dev Container:** open the repo and "Reopen in Container" (`.devcontainer/`); it serves the site automatically.

## Front-end (JS) build

JavaScript is bundled and minified with `uglify-js` (via npm). If you edit files under `assets/js/`:
```bash
npm install
npm run build:js     # minifies + bundles into assets/js/main.min.js
# or, watch mode:
npm run watch:js
```
Do not hand-edit `assets/js/main.min.js` — it is generated. Source lives in `assets/js/_main.js` and `assets/js/plugins/`.

## Deployment

Deployment is **automatic** via GitHub Pages: every push to the default branch (`main`) triggers GitHub Pages to build and publish the site. There is no separate build/deploy command to run. Keep the site to the GitHub-Pages-supported Jekyll plugin set (above) so the remote build succeeds.

The `.github/workflows/scrape_talks.yml` Action runs on changes to talk data (`_talks/**`, `talkmap.ipynb`), re-executes the talkmap notebook, and commits the updated output back to the repo.

## Working in this repo (guidance for AI assistants)

- **Prefer editing content files over templates.** Most requests ("add a publication", "update my bio", "add a talk") are content changes in `_pages/`, `_data/`, or a collection directory — not theme changes.
- **Preserve YAML front matter structure.** Copy the shape of a sibling file in the same collection; a malformed front-matter block breaks the Jekyll build silently.
- **This is a customization of a shared upstream template.** Most files under `_layouts/`, `_includes/`, `_sass/`, and `assets/` are template internals. Touch them only when the task is genuinely about appearance/behavior, and keep changes minimal to ease future upstream syncing.
- **Note stale template placeholders.** Some config still carries template defaults (e.g. `url`, `repository`, and the `github` handle in `_config.yml` point at `academicpages/...`, and `name`/`description` may still read "Your Name"). If a task touches these, update them to the real owner's values (`ddylan24.github.io`, `ddylan24/ddylan24.github.io`, Dylan Durgin) rather than leaving the placeholder.
- **Don't add non-GitHub-Pages plugins** — they will not run on the hosted build.
- **Verify locally when possible** with `bundle exec jekyll serve` before pushing, since build errors only surface at deploy time otherwise.
```
