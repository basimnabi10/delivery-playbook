# Delivery Hub template

The template that every project's Delivery Hub is built from, in the current CodingCops design. One HTML file comes out, with inline styles and script, ready to publish.

| File | What it is |
| --- | --- |
| `page.html` | The page skeleton. The build fills its placeholders |
| `hub.css` | The stylesheet: tokens, light and dark themes, every component |
| `hub.js` | The client script: the timeline chart, the page router, the filters, the copy buttons. It reads the data block embedded in the page and makes no network calls |
| `assets/` | The CodingCops logo, light and dark (PNG). Shown by default. A trademark: the MIT license does not cover it |
| `design.md` | The design spec: principles, page anatomy, tokens, components, responsive rules, accessibility, content rules |
| `sample/` | A complete fictional project (Acme Portal), valid in strict mode. It is the worked example of every data file, and the fixture the self-test builds from |

## Building

From a delivery repo (the scripts are in `scripts/`):

```
python3 scripts/build.py                     # writes out/preview/index.html
python3 scripts/check_render.py              # static checks on that page
python3 scripts/build.py --mode strict --write-published   # when publishing
```

`build.py` runs `validate.py` first and stops if it fails. It reads only `hub/` files and the root control files, and it embeds the data the chart uses in the page, checked against `schemas/hub-block.schema.json`. A wrong number is fixed in the data file, never in the HTML.

To see the template without a project: `python3 scripts/build.py --sample --out /tmp/sample-hub/index.html`, then open the file.

## What the page reads

| Section | Source |
| --- | --- |
| Masthead, at a glance, release blocks | `product/hub/versions.yml` and `releases/`, plus `state.yml` and `project.yml` |
| Last week | the latest file in `project/hub/weeks/` |
| What the product does today | `product/hub/capabilities.yml` |
| Delivery timeline | `project/hub/phases.yml`, `milestones.yml`, `weekly-prs.yml` |
| Security and data handling | `product/hub/security.yml` |
| Try-it prompts and known limitations | `qa/hub/try-it-prompts.yml`, `known-limitations.yml`, referred to by id from each release |
| Sprints page | `project/hub/sprints.yml`, when `project.yml` says `sprints.used: true` |
| Hours page | `project/hub/hours.yml`, when `registry.yml` says `pages.hours.enabled: true` |

The full map is in [the repo layout](../../onboarding/repo-layout.md).

## Settings: the `hub:` block in `project.yml`

All optional. Without them the page uses the project name and sensible defaults.

| Key | Default | What it does |
| --- | --- | --- |
| `title` | `<product> Release Notes` | The browser tab title |
| `product` | `project.name` | The product name on the page |
| `client` | `project.client` | Used in the footer |
| `prepared_by` | `CodingCops` | The "Prepared by" meta card |
| `brand.name` | `CodingCops` | The logo's text alternative, and the wordmark if there is no logo file |
| `brand.logo_light`, `brand.logo_dark` | the CodingCops logo in `assets/` | Paths, relative to the repo root, of your own image files to embed. With one, it is used for both themes. A different `brand.name` with no files shows a text wordmark |
| `lede` | generated | The paragraph under the title |
| `principles` | three generic ones | A list of `{label, text, tone: primary or go}` |
| `weekday` | `Monday` | The weekday in the "Updated weekly" note |
| `footer_notes` | three generic notes | A list of strings |
| `language` | `en` | The page's `lang` |

## What this does not do

`check_render.py` reads the HTML only. It cannot see the page at a screen width or in dark mode, so before publishing, look at the page in a browser at desktop and phone width, in light and dark, and with the keyboard.
