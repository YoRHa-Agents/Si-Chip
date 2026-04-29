# UI Review — Si-Chip Pages v0.1.1

**Date**: 2026-04-28
**Commit reviewed**: b0976b2
**Reviewer**: REV1 / DevolaFlow Review team
**Live URL**: https://yorha-agents.github.io/Si-Chip/
**Scope**: 5 surfaces — `/`, `/install/`, `/userguide/`, `/architecture/`, `/demo/` — plus shared layout, header, footer, `assets/css/nier.css`, `assets/js/nier.js`.
**Method**: Pre-fetched HTML snapshots in `/tmp/ui-audit/` (~16:32 UTC) cross-referenced against source-of-truth under `docs/`. Live HTTP probes for `sitemap.xml`, `robots.txt`, `favicon.ico`, external link targets, Google Fonts. Color contrast computed numerically via WCAG 2 relative-luminance formula.

## Summary

- Total findings: 27 (4 L0-seed confirmations + 23 new)
- By severity: 1 BLOCKER, 1 CRITICAL, 11 MAJOR, 11 MINOR, 3 INFO
- Overall gate: **FAIL** — the architecture page is effectively non-functional (mermaid diagrams render as raw source) and several WCAG AA contrast pairs fail. Treat as `CONVERGE` after S2 FIX lands the 3 highest-priority items below.

## Findings

### BLOCKER

#### B-001: Mermaid diagrams render as raw source on `/architecture/` and `/userguide/`

- **Where**: `docs/_layouts/default.html` (no mermaid.js include); `docs/architecture.md` lines 39-53, 75-87, 109-118, 140-151, 175-186 (5 fenced ```mermaid blocks); `docs/_userguide_body.md` (1 block, rendered around line 524 of `page_userguide.html`).
- **Description**: GitHub Pages ships **no** mermaid runtime. The layout `<head>` does not include `mermaid.min.js`, and there is no `mermaid.initialize()` call. Kramdown emits the fenced block as `<pre><code class="language-mermaid">…raw mermaid DSL…</code></pre>`, which then receives the `.language-mermaid` dashed-border fallback styling but never gets converted to an SVG diagram.
- **Evidence**:
  - `page_architecture.html` line 118 shows `<pre><code class="language-mermaid">flowchart LR\n    spec[".local/research/spec_v0.1.0.md&lt;br/&gt;(frozen)"]…</code></pre>` — visible to the user as literal mermaid syntax with `&lt;br/&gt;` HTML-escaped.
  - `page_userguide.html` line 524 same pattern.
  - `nier.css` lines 351-359 only style `.language-mermaid` as a fallback box; nothing executes the DSL.
  - No `<script src="…mermaid…">` in any rendered page.
- **Impact**: The `/architecture/` page is the headline visual artifact of the site (5 architecture diagrams). All 5 are unrendered. Users see escaped HTML entities (`&lt;br/&gt;`) inside a code block — clearly broken. The userguide loses the dogfood-loop diagram.
- **Fix**: Add to `docs/_layouts/default.html` immediately before the closing `</body>`:

```html
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: false, theme: document.body.dataset.theme === "night" ? "dark" : "default" });
  document.querySelectorAll("pre > code.language-mermaid").forEach((el, i) => {
    const div = document.createElement("div");
    div.className = "mermaid"; div.id = "mermaid-" + i;
    div.textContent = el.textContent;
    el.parentElement.replaceWith(div);
  });
  mermaid.run();
</script>
```

  Also re-run mermaid on theme toggle to redraw with the matching theme; or accept theme mismatch and document it. Add `subresource integrity` if reproducibility is required. Update `nier.js` `applyTheme()` to dispatch a custom event so the bootstrap can re-init.

### CRITICAL

#### C-001: Triple `<h1>` per page on `/`, `/architecture/`, `/demo/`

- **Where**: `docs/_layouts/default.html` line 19 emits `<h1 class="page-title">{{ page.title | default: site.title }}</h1>` for every page. `docs/index.md` lines 8 + 68 each open the bilingual blocks with `# Si-Chip`. `docs/architecture.md` lines 8 + 14 use `# Architecture` / `# 架构`. `docs/demo.md` lines 8 + 17 use `# Live Demo: …` / `# 实时演示：…`.
- **Description**: Three `<h1>` elements per rendered page — the layout's `page-title` plus an `<h1>` inside each of the EN and ZH `<div lang="…">` blocks. WCAG 2.4.6 (Headings and Labels) and the broader convention of one `<h1>` per page expect a single primary heading. With CSS hiding the off-language `<h1>`, only two are *visible*, but assistive tech still announces all three from the DOM (the CSS `display: none` on the off-language block does suppress AT, so visible AT-announced count is 2 — still wrong).
- **Evidence**:
  - `page_root.html` line 82 `<h1 class="page-title">Home</h1>`, line 87 `<h1 id="si-chip">Si-Chip</h1>` (EN), line 194 `<h1 id="si-chip-1">Si-Chip</h1>` (ZH).
  - `page_architecture.html` lines 82, 87, 93. `page_demo.html` lines 82, 87, 96.
  - Note: `/install/` and `/userguide/` are CLEAN (their bodies start with `<h2>`). Only the three pages above have the issue.
- **Impact**: A11y audits flag duplicate `<h1>` as a serious violation; SEO signal value of `<h1>` is diluted. Screen-reader users hear the page title twice (once from layout, once from the visible-language body) on three of five pages.
- **Fix**: Pick one of the two patterns and demote the other. Recommended: drop the body-level `# …` headings from `index.md`, `architecture.md`, `demo.md` (keep the layout's `page-title` as the canonical h1), and let the chapter sections start at `## 1. …`. Alternative: change the layout's `<h1 class="page-title">` to a `<p class="page-title">` *only* on pages where the body provides its own h1 — but this requires per-page front-matter (`hide_page_title: true`), more invasive.

### MAJOR

#### M-001: Hero-meta + footer.ver show `V0.1.0` before JS, `V0.1.1` after JS (FOWC version drift) — confirms L0 seed #2

- **Where**: `docs/_config.yml` line 3 (`version: 0.1.0`); `docs/_includes/header.html` line 7 (`V{{ site.version | default: '0.1.1' }}`); `docs/_includes/footer.html` line 6 (`[ VER: {{ site.version | default: '0.1.1' }} ]`); `docs/_layouts/default.html` lines 37 + 41 (JSON island has `V0.1.1` / `[ VER: 0.1.1 ]`).
- **Description**: `site.version` IS set in `_config.yml` to `0.1.0`, so the Liquid fallback `| default: '0.1.1'` never fires. The JSON i18n island hard-codes the post-JS replacement to `V0.1.1`. Result: every page renders `V0.1.0` server-side, then the JS swaps to `V0.1.1` after `applyLang()` runs.
- **Evidence**:
  - `page_root.html` line 21 `// YORHA AGENTS / SI-CHIP / V0.1.0` and line 307 `[ VER: 0.1.0 ]`.
  - `page_root.html` lines 330 + 334 i18n island `"hero.meta": "// YORHA AGENTS / SI-CHIP / V0.1.1"`, `"footer.ver": "[ VER: 0.1.1 ]"`.
  - All 5 snapshots show the same drift.
- **Impact**: Visible jitter on every page load; the "current version" indicator briefly lies. Users with slow JS execution see V0.1.0 indefinitely.
- **Fix**: Edit `docs/_config.yml` line 3 → `version: 0.1.1`. This is the single source of truth and matches the actual current release tag (`releases/tag/v0.1.1` returns 200). The Liquid `default` fallback then becomes belt-and-suspenders, and the JSON island continues to back the JS swap (now a no-op for version text).

#### M-002: `data-i18n="nav.spec(v0.1.0)"` key never resolves — confirms L0 seed #3

- **Where**: `docs/_includes/header.html` lines 13-18 (the Liquid loop builds key as `'nav.' | append: t` where `t = item.title | downcase | replace: ' ', ''`). For `Spec (v0.1.0)`, `t` becomes `spec(v0.1.0)`, so `data-i18n="nav.spec(v0.1.0)"`. The JSON island in `default.html` lines 35 + 54 has `"nav.spec"` only.
- **Description**: JS lookup `dict[lang][key]` with `key="nav.spec(v0.1.0)"` returns `undefined`; the conditional `if (dict[lang] && dict[lang][key])` falls through, leaving the original `▶ SPEC (V0.1.0)` text. When the user toggles to ZH, every nav link translates EXCEPT this one — visible inconsistency.
- **Evidence**: `page_root.html` line 65 `<a … data-i18n="nav.spec(v0.1.0)">▶ SPEC (V0.1.0)</a>`. Same on every page.
- **Impact**: User toggles to ZH and sees 6/7 nav links in Chinese plus one stubbornly English `▶ SPEC (V0.1.0)`. Looks like a regression bug.
- **Fix**: Two equally simple options. (a) In `header.html` add a Liquid sanitization step that strips parens before generating the key:

```liquid
{% assign t = item.title | downcase | replace: ' ', '' | replace: '(', '' | replace: ')', '' | replace: '.', '' %}
```

  with matching JSON keys `nav.specv010` (ugly but stable). Or (b) Rename the nav entry to `Spec` in `_config.yml` line 47 (drop the `(v0.1.0)` from the title; let the rendered text continue to read `SPEC (V0.1.0)` via i18n strings). Option (b) is simpler and keeps the JSON readable.

#### M-003: Day-mode `--fg-soft` on `--bg` fails WCAG AA contrast (2.93:1 vs 4.5:1)

- **Where**: `docs/assets/css/nier.css` lines 7 + 6 (token defs). Used by `.hero-meta` (line 85), `.page-meta` (line 170), `.page-divider` (line 188), `.hero-subtitle .cursor` (no — that's `--accent`), `.page-body h4` (line 213), `.page-body table td` border (line 271), `.page-body ol li::before` counter (line 243), `.page-body blockquote` body text (line 325), `.footer-divider` (line 399), `.footer-link a` (line 434), `.page-body pre::before` "// CODE" label (line 297), `.hero-title .bracket` (line 102).
- **Description**: Computed contrast `#7A745E` on `#D2CDB7` = **2.93:1**. WCAG AA requires 4.5:1 for normal text and 3:1 for large text or UI components. This pair fails BOTH thresholds.
- **Evidence**: numeric calculation in section "Color contrast measurements" below.
- **Impact**: Hero meta line, page chrome divider, blockquote body, footer source/release/license links, table cell borders, and ordered-list counters are all hard to read in day mode for users with low vision. Multiple text instances per page.
- **Fix**: Darken `--fg-soft` to at least `#615C49` (≈ 4.5:1) or `#5A553F` (≈ 5.4:1) so it clears AA-normal. Verify with the formula in §Methodology of the task brief. Night mode pair (`#8C8771` on `#14120F`) already passes at 5.18:1 — only the day token needs adjustment.

#### M-004: Day-mode `--rust` blockquote left-border fails 3:1 UI contrast (2.65:1)

- **Where**: `nier.css` line 9 token, line 322 `border-left: 4px solid var(--rust)`.
- **Description**: `#92765A` on `#D2CDB7` = **2.65:1**. Below WCAG AA non-text 3:1. The blockquote's defining visual marker is invisible to many users.
- **Evidence**: numeric calculation below.
- **Impact**: Blockquote cues (e.g. `Status (v0.1.0):` callout on `/`, the spec-warning callouts on `/demo/` and `/userguide/`) lose their visual border, blending into normal paragraphs.
- **Fix**: Either darken `--rust` toward `#74573D` (≈ 4.6:1) for day mode, OR keep the rust color but thicken the border to `6px`. Note night-mode `--rust-night #B89A78` passes at 7.06:1 — only the day token is the problem.

#### M-005: Toggle buttons missing `aria-pressed` state

- **Where**: `docs/_includes/header.html` lines 4-5 (`<button class="toggle" type="button" data-toggle-lang …>` and `… data-toggle-theme …>`). `docs/assets/js/nier.js` lines 26-33 + 35-60 (`applyTheme` / `applyLang`) update text content but never set `aria-pressed`.
- **Description**: WCAG 4.1.2 (Name, Role, Value) requires programmatic state for toggle controls. Screen readers announce these as plain buttons; users cannot tell whether DAY or NIGHT, EN or ZH is currently active without sighted feedback.
- **Evidence**: `page_root.html` lines 18-19 — only `aria-label` present.
- **Fix**: In `header.html` add `aria-pressed="false"` to both buttons; in `nier.js` `applyTheme()` add `t.setAttribute("aria-pressed", String(theme === "night"))` and similarly in `applyLang()` `t.setAttribute("aria-pressed", String(lang === "zh"))`. Choose ONE consistent direction (e.g. `pressed = night/zh`).

#### M-006: Pre-JS body `data-theme="day" data-lang="en"` causes flash for users with stored prefs (FOWC) — confirms L0 seed F3/F4

- **Where**: `docs/_layouts/default.html` line 13 hardcodes `<body class="nier" data-theme="day" data-lang="en">`. `docs/assets/js/nier.js` lines 26-32 + 35-60 then read `localStorage` and OS preference and re-apply.
- **Description**: A user whose `localStorage["si-chip-theme"]="night"` will see the day palette for 1 paint frame (≈40-200ms depending on connection / parser blocking) before JS runs the `init()` function. Same for `lang=zh` users. Visible flicker.
- **Evidence**: `nier.js` line 95-99 only binds via `DOMContentLoaded` / immediate; no inline pre-paint script.
- **Impact**: Visible flash on every navigation for returning users with non-default prefs. Worse on slower networks.
- **Fix**: Add a *synchronous* inline script in the `<head>` of `default.html` BEFORE the stylesheet link:

```html
<script>
  (function() {
    try {
      var t = localStorage.getItem("si-chip-theme");
      var l = localStorage.getItem("si-chip-lang");
      if (!t && window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) t = "night";
      if (!l && (navigator.language || "").toLowerCase().indexOf("zh") === 0) l = "zh";
      document.documentElement.setAttribute("data-theme", t || "day");
      document.documentElement.setAttribute("data-lang", l || "en");
    } catch (e) {}
  })();
</script>
```

  Then duplicate the `body[data-theme=…]` selectors in `nier.css` to also target `html[data-theme=…]` (or move attributes to `<html>`). This eliminates flash entirely.

#### M-007: Stale Liquid-loop whitespace in `<nav>` — confirms L0 seed #4

- **Where**: `docs/_includes/header.html` lines 11-20 (the `{% for %}{% assign %}{% if %}{% else %}{% endif %}{% endfor %}` block).
- **Description**: Each iteration emits five blank lines (the `{% for %}`, two `{% assign %}`, `{% if %}` open/close). Across 7 nav items that is ~50 blank lines added to every rendered page.
- **Evidence**: `page_root.html` lines 25-74 — the `<nav class="hero-nav">` body is mostly whitespace.
- **Impact**: ~1 KB of unnecessary HTML per page (5 pages × 5 KB/day at modest traffic = wasted bandwidth, slower TTFB on cold cache). Also makes "view source" debugging painful.
- **Fix**: Use Liquid whitespace-stripping syntax: replace `{%` with `{%-` and `%}` with `-%}`:

```liquid
<nav class="hero-nav" aria-label="Primary">
{%- for item in site.nav -%}
  {%- assign t = item.title | downcase | replace: ' ', '' -%}
  {%- assign i18n_key = 'nav.' | append: t -%}
  {%- if item.url contains '://' -%}
    <a class="nav-link" href="{{ item.url }}" data-i18n="{{ i18n_key }}">▶ {{ item.title | upcase }}</a>
  {%- else -%}
    <a class="nav-link" href="{{ item.url | relative_url }}" data-i18n="{{ i18n_key }}">▶ {{ item.title | upcase }}</a>
  {%- endif -%}
{%- endfor -%}
</nav>
```

#### M-008: Wrap-up blockquote outside lang-divs leaks English to ZH users

- **Where**: `docs/install.md` line 9 (the `> The canonical install guide also lives at the [repository root]` line); `docs/userguide.md` line 9 (matching `User Guide` text). Both render OUTSIDE every `<div lang="…">` block.
- **Description**: These trailing blockquotes are emitted as direct children of `.page-body`, with no `lang` attribute. The CSS hide rule (`body[data-lang="en"] [lang="zh"] {…}`) only targets elements that have `lang="zh"`; the bare blockquote does not, so it remains visible in BOTH languages, in English only.
- **Evidence**: `page_install.html` lines 643-645 (after the closing `</div>` of the zh block); `page_userguide.html` lines 1019-1021 same.
- **Impact**: ZH-mode users see one English sentence at the bottom of the install and userguide pages — looks like a translation oversight.
- **Fix**: In both `docs/install.md` and `docs/userguide.md`, wrap the trailing line in bilingual divs:

```markdown
<div lang="en" markdown="1">
> The canonical install guide also lives at the [repository root](https://github.com/YoRHa-Agents/Si-Chip/blob/main/INSTALL.md).
</div>
<div lang="zh" markdown="1">
> 标准安装指南同样存放在[仓库根目录](https://github.com/YoRHa-Agents/Si-Chip/blob/main/INSTALL.md)。
</div>
```

#### M-009: `// CHAPTER 0X //` markers leak across both languages (no zh equivalent, no `lang` attribute)

- **Where**: `docs/architecture.md` lines 18, 55, 89, 120, 153 — all five `// CHAPTER 0N //` lines appear OUTSIDE the lang divs and render as plain `<p>// CHAPTER 0X //</p>`. `docs/demo.md` lines 23, 53, 91, 139, 169, 218, 274 — seven `// CHAPTER` markers, same pattern.
- **Description**: These decorative section dividers are visible in both EN and ZH modes. They are not translated to anything ZH-specific (e.g. `// 章节 0X //`) but are also not even tagged with `lang="en"`. Mostly defensible (they're stylized engineering captions), but inconsistent with the rest of the bilingual treatment and easy to fix.
- **Evidence**: `page_architecture.html` lines 97, 133, 166, 196, 228; `page_demo.html` lines 102, 196, 308, 460, 540, 587, 641.
- **Impact**: ZH users see English mark-up text scattered through chapter breaks. Aesthetic inconsistency.
- **Fix**: Either accept and tag `lang="en"` to keep them visible only in EN mode (and add `lang="zh"` clones with translated chapter words), OR restyle them as a CSS-injected pseudo-element on the next h2 so the literal text is removed from the markdown.

#### M-010: All 5 pages share one `<meta name="description">`; no Open Graph / Twitter / canonical tags

- **Where**: `docs/_layouts/default.html` line 7 — only `<meta name="description" content="{{ site.description }}">`. No `og:`, `twitter:`, or `<link rel="canonical">`.
- **Description**: Every page has the same description "Persistent BasicAbility optimization factory - frozen spec v0.1.0". Pages like `/userguide/` and `/install/` deserve unique descriptions for search snippets. No social-sharing previews (no Open Graph image, title, description); no Twitter card; no canonical URL. SEO + share UX gap.
- **Evidence**: `page_root.html` line 7 vs `page_userguide.html` line 7 — identical.
- **Impact**: Search engines surface the same snippet for every page; LinkedIn / X / Slack previews fall back to a bare URL with no thumbnail.
- **Fix**: In `default.html` `<head>`, add per-page meta with front-matter overrides:

```html
<meta name="description" content="{{ page.description | default: site.description }}">
<link rel="canonical" href="{{ page.url | absolute_url }}">
<meta property="og:title" content="{% if page.title %}{{ page.title }} · {% endif %}{{ site.title }}">
<meta property="og:description" content="{{ page.description | default: site.description }}">
<meta property="og:url" content="{{ page.url | absolute_url }}">
<meta property="og:type" content="website">
<meta property="og:image" content="{{ '/assets/og-card.png' | absolute_url }}">
<meta name="twitter:card" content="summary_large_image">
```

  Add a `description:` field to each page's front-matter (5 pages). Generate a 1200×630 `og-card.png` honoring the NieR styling.

#### M-011: Hero subtitle CSS animation `fadein 200ms` ignores `prefers-reduced-motion`

- **Where**: `nier.css` lines 112-114.
- **Description**: `nier.js` correctly suppresses the cursor blink under reduced-motion, but `.hero-subtitle { opacity: 0; animation: fadein 200ms linear forwards; animation-delay: 60ms; }` runs unconditionally. Users who set the reduced-motion media query still get a fade.
- **Evidence**: `nier.js` line 80 reduced-motion check is for cursor only; CSS `@media (prefers-reduced-motion)` block absent.
- **Impact**: Minor motion sensitivity violation (200ms is short, low risk).
- **Fix**: In `nier.css` add at the bottom:

```css
@media (prefers-reduced-motion: reduce) {
  .hero-subtitle { opacity: 1; animation: none; }
}
```

### MINOR

#### m-001: `.btn-green` referenced in `index.md` but never defined in CSS

- **Where**: `docs/index.md` line 12 (EN) + line 72 (ZH) — `[▶ LIVE DEMO](./demo/){:.btn .btn-green}`. `nier.css` defines `.btn` (lines 363-378) but no `.btn-green`.
- **Description**: The "live demo" button is meant to look distinct (green) but inherits plain `.btn` styling, indistinguishable from its siblings.
- **Evidence**: `page_root.html` line 91 + 198 — the class string is rendered but no green appears in the CSS.
- **Fix**: Add to `nier.css`:

```css
.page-body a.btn.btn-green,
a.btn.btn-green { color: #2D5A3F; border-color: #2D5A3F; }
.page-body a.btn.btn-green:hover, a.btn.btn-green:hover { background: #2D5A3F; color: var(--bg); }
body[data-theme="night"] .page-body a.btn.btn-green { color: #8FB996; border-color: #8FB996; }
```

  (Verify contrast on both themes after picking the final shade.)

#### m-002: Missing favicon — `/favicon.ico` returns 404

- **Where**: `default.html` `<head>` has no `<link rel="icon">`.
- **Evidence**: `curl -o /dev/null -w "%{http_code}" https://yorha-agents.github.io/Si-Chip/favicon.ico` → **404**.
- **Impact**: Browser tab shows a generic globe icon; some browsers log a 404 to console on every page.
- **Fix**: Add a `docs/favicon.ico` (or SVG `docs/favicon.svg`) and inject `<link rel="icon" href="{{ '/favicon.svg' | relative_url }}" type="image/svg+xml">` into `<head>`. The NieR aesthetic favors a simple `[ ]` glyph in `--accent` color.

#### m-003: No `sitemap.xml` and no `robots.txt`

- **Evidence**: Both return 404 on the live site. `_config.yml` only loads `jekyll-relative-links`.
- **Impact**: Crawlers must rely on internal link discovery; no opportunity to publish `sitemap_index.xml` for Bing/Google. Mostly fine for a 5-page site but trivial to add.
- **Fix**: In `_config.yml` add `jekyll-sitemap` to plugins and create `docs/robots.txt`:

```text
User-agent: *
Allow: /
Sitemap: https://yorha-agents.github.io/Si-Chip/sitemap.xml
```

#### m-004: `<table>` headers lack `scope="col"` attribute

- **Where**: every `<table>` in every snapshot (Kramdown does not emit `scope` by default).
- **Evidence**: `page_install.html` lines 113-118 — `<th>Flag</th>` etc., no `scope`.
- **Impact**: Screen readers can usually infer column scope, but for tables wider than 3 columns explicit `scope="col"` reduces ambiguity (WCAG 1.3.1).
- **Fix**: Either post-process the HTML in a Jekyll plugin or pre-render tables as raw HTML with `<th scope="col">…</th>`. Lower-effort: add a small JS shim in `nier.js` that walks `.page-body table thead th` and adds `scope="col"`.

#### m-005: ZH font stack uses `Noto Sans JP`, not `Noto Sans SC`

- **Where**: `nier.css` line 14 `--font-body: 'Noto Sans JP', system-ui, …`. The Google Fonts URL in `default.html` line 10 loads only `Noto+Sans+JP`.
- **Description**: `Noto Sans JP` is the Japanese variant and contains the kanji subset, which renders Simplified Chinese characters with Japanese glyph forms (e.g. 直, 经, 设 differ between SC and JP). Native ZH readers will notice "off" character shapes.
- **Evidence**: `nier.css` line 14 + `default.html` line 10.
- **Fix**: Add `Noto Sans SC` to the Google Fonts query and to the `--font-body` stack ahead of JP:

```html
<link href="https://fonts.googleapis.com/css2?family=B612+Mono:wght@400;700&family=Noto+Sans+JP:wght@300;400&family=Noto+Sans+SC:wght@300;400&family=Saira+Stencil+One&display=swap" rel="stylesheet">
```

  And in CSS:

```css
:root { --font-body: 'Noto Sans SC', 'Noto Sans JP', system-ui, -apple-system, 'Segoe UI', sans-serif; }
:lang(zh) { font-family: 'Noto Sans SC', 'Noto Sans JP', system-ui, sans-serif; }
:lang(en) { font-family: 'Noto Sans JP', system-ui, sans-serif; }
```

#### m-006: ZH content uses `lang="zh"` instead of `lang="zh-Hans"` or `lang="zh-CN"`

- **Where**: every `<div lang="zh">` in every page; `nier.js` line 41 sets `document.documentElement.setAttribute("lang", "zh")`.
- **Description**: BCP-47 prefers a script subtag for Chinese (`zh-Hans` for Simplified, `zh-Hant` for Traditional). Some browsers' font matchers and screen readers use the subtag to pick the right glyph variant.
- **Fix**: change every `lang="zh"` to `lang="zh-Hans"` (5 markdown bodies, plus `nier.js` line 41 `setAttribute("lang", lang === "zh" ? "zh-Hans" : "en")`). Update CSS rule `body[data-lang="zh"] [lang="en"]` does not need changes since it targets the body attribute.

#### m-007: `::selection` not styled — night mode default may be unreadable

- **Where**: `nier.css` has no `::selection` rule.
- **Description**: Browsers default to a light-blue selection background with a contrasting (often white) text color. On a `#14120F` night background, default Firefox selection (#3297FD on #FFFFFF) inverted produces light blue background with dark text — usually OK, but inconsistent with the aesthetic.
- **Fix**: Add to `nier.css`:

```css
::selection { background: var(--accent); color: var(--bg); }
::-moz-selection { background: var(--accent); color: var(--bg); }
```

#### m-008: Code-block `pre::before` "// CODE" label leaks English into ZH mode

- **Where**: `nier.css` lines 290-300.
- **Description**: Every `<pre>` in every language block shows the literal string `// CODE` as a top-right label. ZH users see English. Same issue applies to Mermaid blocks (where the label is doubly wrong because the block is not "code").
- **Fix**: Remove the pseudo-element entirely, OR localize via CSS `:lang()`:

```css
.page-body pre::before { content: "// CODE"; }
:lang(zh) .page-body pre::before { content: "// 代码"; }
.page-body pre:has(code.language-mermaid)::before { content: "// DIAGRAM"; }
```

#### m-009: Code-block bash comments remain English in ZH bodies

- **Where**: e.g. `page_install.html` lines 387-401 (zh code block has `# Interactive (TTY): prompts for target and scope`); `page_demo.html` lines 619-637; `page_userguide.html` lines 920-924.
- **Description**: The bash code blocks were copy-pasted verbatim into the ZH `<div>`; their inline comments are still English.
- **Impact**: Low; many bilingual docs leave code in source language. Worth flagging.
- **Fix**: Either accept (cite as policy in CONTRIBUTING) or translate the `# …` comments inside the ZH code fences to Chinese.

#### m-010: External links lack `target="_blank"` + `rel="noopener noreferrer"`

- **Where**: `header.html` lines 16 + 18 (Spec, Source nav links); `footer.html` lines 13-15 (footer-link Source/Release/License).
- **Description**: Clicking any external link navigates the user away from the docs site; no target attribute means same-tab navigation. Most users expect external links to open in a new tab. When `target="_blank"` is added, `rel="noopener noreferrer"` is required to prevent reverse-tabnabbing and referrer leakage.
- **Fix**: In `header.html` line 16 (the `if url contains '://'` branch) add `target="_blank" rel="noopener noreferrer"`. Same for the three footer-link `<a>` tags in `footer.html`.

#### m-011: No "skip to main content" link for keyboard users

- **Where**: `default.html` body — no `<a class="skip-link" href="#main">…</a>` before the header.
- **Description**: Keyboard users currently tab through 9 hero-nav links + 2 toggle buttons before reaching page content. WCAG 2.4.1 (Bypass Blocks) recommends a visually-hidden skip link.
- **Fix**: Add as the first child of `<body>`:

```html
<a class="skip-link" href="#main">Skip to content</a>
```

  with CSS:

```css
.skip-link { position: absolute; left: -9999px; top: 0; }
.skip-link:focus { left: 0; padding: 0.6em 1em; background: var(--accent); color: var(--bg); z-index: 10000; }
```

  And add `id="main"` to the `<main class="content">` element.

### INFO

#### i-001: Scanlines invisible in night mode — `mix-blend-mode: screen` of black is identity

- **Where**: `nier.css` line 515-518 — `body[data-theme="night"] .scanlines { opacity: 0.03; mix-blend-mode: screen; }`.
- **Description**: The scanline gradient consists of black bars on transparent. Screen blending of black is the identity function (output = base), so the bars contribute nothing additional; only the 0.03 opacity moves the pixel. Effectively the scanline overlay is a no-op in night mode.
- **Impact**: Cosmetic. The "CRT" feel is missing in night mode.
- **Fix**: Either accept (the bars are imperceptible by design) or change night-mode scanlines to white at very low opacity:

```css
body[data-theme="night"] .scanlines {
  opacity: 0.06;
  mix-blend-mode: normal;
  background-image: repeating-linear-gradient(
    to bottom,
    rgba(255,255,255,0) 0,
    rgba(255,255,255,0) 1px,
    rgba(255,255,255,0.10) 1px,
    rgba(255,255,255,0.10) 2px
  );
}
```

#### i-002: `<html lang="en">` is hardcoded; SEO crawlers see EN regardless of user toggle

- **Where**: `default.html` line 2.
- **Description**: JS sets `document.documentElement.lang = "zh"` after toggle, but server-side render is always `en`. Search crawlers index the EN copy. Acceptable trade-off documented in L0 audit (B8); flagged here for completeness.
- **Fix (optional)**: Detect `Accept-Language: zh*` server-side. Not feasible on Pages; stay with current behavior. Could ship `/zh/` mirror pages with `lang="zh"` server-side later.

#### i-003: Pre-JS server-side render shows EN content even for ZH-stored users

- **Where**: i18n hide rules in `nier.css` lines 480-481 require `body[data-lang]` to be set. Initial `<body data-lang="en">` (line 13) means ZH-blocks are hidden until JS runs `applyLang("zh")`. With M-006 fix in place this is also resolved (the inline pre-paint script flips `data-lang` before first paint). Tracking here as a downstream INFO that closes once M-006 lands.

## Per-page audit matrix

Legend: `OK` = no finding / `n` = number of findings (at this severity or higher) / `—` = not applicable.

| Page             | a11y                              | SEO                            | i18n completeness                  | dark mode                | responsive | FOWC               | content                       |
|------------------|-----------------------------------|--------------------------------|------------------------------------|--------------------------|------------|--------------------|-------------------------------|
| `/`              | C-001 triple h1, M-005, m-004     | M-010, m-002, m-003            | M-002 spec key, m-005, m-006       | M-003, M-004             | OK         | M-001, M-006       | m-001 .btn-green missing      |
| `/install/`      | M-005, m-004, m-011               | M-010, m-002, m-003            | M-002, M-008 wrap-up leak, m-008-9 | M-003, M-004             | OK         | M-001, M-006       | OK                            |
| `/userguide/`    | M-005, m-004, m-011               | M-010, m-002, m-003            | M-002, M-008, m-008-9              | M-003, M-004, B-001 mermaid | OK      | M-001, M-006       | OK                            |
| `/architecture/` | C-001 triple h1, M-005, m-004     | M-010, m-002, m-003            | M-002, M-009 chapter leak          | M-003, M-004, **B-001 5 mermaid blocks** | OK | M-001, M-006 | B-001 broken diagrams         |
| `/demo/`         | C-001 triple h1, M-005, m-004     | M-010, m-002, m-003            | M-002, M-009, m-008-9              | M-003, M-004             | OK (table scroll OK) | M-001, M-006 | OK                |

## Color contrast measurements

Computed via the WCAG 2 relative-luminance formula in the task brief.

| Pair                                              | Ratio   | AA-text (≥4.5) | AA-large/UI (≥3.0) |
|---------------------------------------------------|---------|----------------|---------------------|
| day `--fg #3F3A2C` on `--bg #D2CDB7`              | 7.10:1  | PASS           | PASS                |
| day `--fg #3F3A2C` on `--bg-soft #C8C2A6`         | 6.33:1  | PASS           | PASS                |
| day `--fg-soft #7A745E` on `--bg`                 | **2.93:1** | **FAIL**    | **FAIL**            |
| day `--accent #171614` on `--bg`                  | 11.33:1 | PASS           | PASS                |
| day `--accent` on `--bg-soft`                     | 10.09:1 | PASS           | PASS                |
| day `--rust #92765A` on `--bg`                    | **2.65:1** | **FAIL**    | **FAIL**            |
| day `--blood #5A2A1F` on `--bg`                   | 7.37:1  | PASS           | PASS                |
| day `--bg` on `--accent` (link/btn hover)         | 11.33:1 | PASS           | PASS                |
| night `--fg #D2CDB7` on `--bg #14120F`            | 11.71:1 | PASS           | PASS                |
| night `--fg` on `--bg-soft #1F1C18`               | 10.63:1 | PASS           | PASS                |
| night `--fg-soft #8C8771` on `--bg`               | 5.18:1  | PASS           | PASS                |
| night `--accent #D2CDB7` on `--bg`                | 11.71:1 | PASS           | PASS                |
| night `--accent` on `--bg-soft`                   | 10.63:1 | PASS           | PASS                |
| night `--rust #B89A78` on `--bg`                  | 7.06:1  | PASS           | PASS                |
| night `--blood #A04438` on `--bg`                 | 3.01:1  | FAIL           | PASS                |
| night `--bg` on `--accent` (link/btn hover)       | 11.71:1 | PASS           | PASS                |

**Summary**: Day mode has 2 hard fails (`--fg-soft`, `--rust`) and night mode has 1 borderline (`--blood`, AA-text only — but `--blood` is reserved for "OUT OF SCOPE" badges that are not yet rendered anywhere in the v0.1.1 HTML, so this is a pre-emptive note).

## Live link & resource probes

| Resource                                                                                            | HTTP |
|-----------------------------------------------------------------------------------------------------|------|
| `https://yorha-agents.github.io/Si-Chip/sitemap.xml`                                                | 404  |
| `https://yorha-agents.github.io/Si-Chip/robots.txt`                                                 | 404  |
| `https://yorha-agents.github.io/Si-Chip/favicon.ico`                                                | 404  |
| `https://yorha-agents.github.io/Si-Chip/assets/css/nier.css`                                        | 200  |
| `https://github.com/YoRHa-Agents/Si-Chip/blob/main/.local/research/spec_v0.1.0.md` (Spec link)      | 200  |
| `https://github.com/YoRHa-Agents/Si-Chip` (Source link)                                             | 200  |
| `https://github.com/YoRHa-Agents/Si-Chip/releases/tag/v0.1.1` (Footer release link)                 | 200  |
| `https://fonts.googleapis.com/css2?family=B612+Mono…&family=Noto+Sans+JP…&family=Saira+Stencil+One` | 200  |

L0's hypothesis that the spec link 404s anonymously is **wrong** — the repo is public and the spec file resolves to 200. Spec link works.

## Cross-cutting confirmations of L0 seeds

1. **Duplicate `<h1>`** → CONFIRMED + amplified to *triple* `<h1>` on 3 of 5 pages (index, demo, architecture). Tracked as **C-001**. The other two pages (install, userguide) are clean.
2. **Version drift V0.1.0 vs V0.1.1** → CONFIRMED on all 5 pages, root cause identified as `_config.yml` `version: 0.1.0` (not the Liquid fallback). Tracked as **M-001**.
3. **`nav.spec(v0.1.0)` key mismatch** → CONFIRMED on all 5 pages. Tracked as **M-002**.
4. **Stale nav-loop whitespace** → CONFIRMED, ~1 KB per page. Tracked as **M-007**.

## Recommended fix order (top-3 must land in S2 FIX)

1. **B-001 mermaid runtime** — inject the mermaid.js bootstrap so `/architecture/` stops shipping raw DSL. (Highest user impact; the architecture page is the visual centerpiece.)
2. **M-001 + M-002** — bump `_config.yml version: 0.1.1` AND fix the spec-key sanitization. Two one-line edits, eliminates two visible bugs (FOWC version flicker + ZH nav inconsistency).
3. **M-003 + M-004** — darken `--fg-soft` and `--rust` for day mode to clear WCAG AA. Two token edits in `:root` of `nier.css`. Eliminates WCAG audit blockers and visibly improves readability.

After the top-3, group the next sprint as: **C-001** (drop body h1s on 3 pages) → **M-005** (toggle aria-pressed) → **M-006** (pre-paint script for FOWC) → **M-007** (Liquid whitespace) → **M-008** (wrap-up blockquote i18n) → **M-010** (per-page meta + OG/canonical). The MINOR / INFO items are quality-of-life follow-ups.

## Notes for L0

- BLOCKER count is 1 (mermaid). If the L0 gate considers the architecture page deferrable, B-001 may be re-classified to CRITICAL; a single-line CDN script fixes it.
- Color contrast failures are tightly scoped to two day-mode tokens — fixable in a 4-line CSS patch.
- No JS runtime errors detected in either snapshot; the i18n island is well-formed JSON; the IIFE wraps cleanly; localStorage and reduced-motion checks are guarded.
- No file in `docs/` was modified by this review (READ-ONLY).
