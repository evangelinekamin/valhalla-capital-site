# Valhalla Capital — memorial site

A static memorial for **Valhalla Capital**, an autonomous AI value-investing
experiment (agent "Valkyrie") that ran from 13 February to 16 June 2026, lost
9.77%, hit its −10% stop, and was retired. The page is a memorial landing, the
full post-mortem, and a clickthrough to a frozen snapshot of the live trading
dashboard.

The code and raw data live at
<https://github.com/evangelinekamin/valhalla-capital>.

## What this is

The main page is static HTML/CSS with no build step or framework. (Two caveats
to the old "no external requests, no JS" goal: the post-mortem's charts load
from an image host, and the `live-snapshot/` dashboard capture ships the
original dashboard's JavaScript in a frozen, inert state.) Drop onto GitHub
Pages as-is.

```
index.html              memorial landing + full post-mortem
styles.css              the stylesheet
.nojekyll               tells Pages to serve files verbatim (no Jekyll)
assets/
  favicon.svg           the wing mark (favicon)
  wing.svg              the wing mark (standalone, currentColor)
  equity-curve.svg      the equity curve as a standalone SVG
gen_chart.py            regenerates the inline equity SVG from the source CSV
live-snapshot/          frozen static capture of the live dashboard
  index.html            status board (plus valkyrie/decisions/trades.html)
  static/               the dashboard's own CSS/JS, served inert
```

The equity chart is embedded **inline** in `index.html` (so it inherits page
fonts and needs no extra request); an identical standalone copy lives in
`assets/equity-curve.svg`. Both are produced by `gen_chart.py` — see below.

## Deploy to GitHub Pages

1. Put these files at the **root** of a branch (e.g. `main`) in the target repo.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*.
4. Choose the branch and the **`/ (root)`** folder, then **Save**.
5. Pages publishes at `https://<user>.github.io/<repo>/` within a minute or two.

The `.nojekyll` file is what stops GitHub from running the content through
Jekyll, so files (including anything starting with `_` or `.`) are served as
written. Keep it.

To preview locally, any static server works, for example:

```sh
python3 -m http.server -d . 8000   # then open http://localhost:8000
```

## Regenerating the chart

`gen_chart.py` reads the archived daily-portfolio CSV and emits
`assets/equity-curve.svg`. If the data changes, regenerate and paste the new
SVG body into the `<!-- Inline SVG ... -->` block in `index.html`:

```sh
python3 gen_chart.py
```

The CSV path is hard-coded at the top of the script; edit `CSV_PATH` if the
source moves. The script has no third-party dependencies (standard library
only).

## Editing notes

- **Banner.** A styled banner at the top of `index.html` (search for
  `class="banner"`) carries the "no longer live" notice and links to the repo
  and the dashboard snapshot.
- **Design is a starting point.** The look is distilled from the fund's own
  monitoring terminal — a "VA-11 Hall-A terminal warmth meets Swiss typography"
  aesthetic: deep navy ground, warm cyan for life, soft pink for the retired,
  amber for the in-between. All the design tokens (colors, type scale, fonts)
  live as CSS custom properties in `:root` at the top of `styles.css`; tune
  them there. It is meant to be tweaked, not treated as final.
- **Fonts** are a system serif + grotesque + mono stack — nothing is fetched
  from a font CDN, so the page stays fully self-contained and offline-friendly.
- **Accessibility & privacy.** The page uses semantic HTML, a skip link, image
  `title`/`desc`, honors `prefers-reduced-motion`, and carries no analytics or
  trackers. (The post-mortem ends with a contact email, on purpose.) Keep it
  that way.
