# Digital Closet

Your real wardrobe, digitized — clean cutouts of your actual clothes, organized
into sections, with a Pinterest-style **outfit-of-the-day mood board** that reads
today's real weather. Private by design: photos never leave your machine.

Built to be driven by [Claude Code](https://claude.com/claude-code): you photograph
clothes, Claude cleans + catalogs them and styles you.

## What it does

- **Mood board generator** — pick the occasion (or let weather auto-set), hit
  *Style me*, get a flat-lay board composed from your own pieces (main piece,
  layer, shoes, bag, sunglasses, jewelry).
- **Live weather** — asks for your location (or a city) and dresses you for
  today via Open-Meteo; warns about rain/snow. No API key.
- **Sections** — Dresses · Tops · Bottoms · Jackets & coats · Activewear ·
  Shoes · Bags · Accessories.
- **Add from gallery** — a button in the app uploads photos straight into the
  intake folder (works from your phone on the same Wi-Fi).
- **AI cleanup** — every photo becomes a clean, hanger-free cutout of the
  *real* garment (no AI-invented clothes).

## Quick start

```bash
git clone <this repo> && cd digital-closet
pip install -r requirements.txt          # just Pillow
python3 scripts/serve.py                 # → http://localhost:8765 (+ phone URL)
```

Open it, tap **Add from gallery**, pick photos of your clothes (one garment per
photo, laid flat works best). Then clean + catalog them:

### Easiest: let Claude Code do it
Open this folder in Claude Code and say **"add my clothes"** — it runs the
cleanup, looks at each piece, and writes the catalog for you. `CLAUDE.md`
teaches it everything.

### Manual: two cleanup ways

| | Way 1 — local (free) | Way 2 — fal.ai (best quality) |
|---|---|---|
| Setup | `pip install -r requirements-local.txt` | `export FAL_KEY=...` ([fal.ai](https://fal.ai) key) |
| Run | `python3 scripts/cleanup_local.py` | `python3 scripts/cleanup_fal.py` |
| How | rembg matting on your machine | AI erase (hangers/hands removed, garment kept identical) + matting |
| Cost | free | ~$0.04 / photo |

Both write clean PNGs to `closet/photos/` — then add each item to
`closet/wardrobe.json` (schema in `CLAUDE.md`; or let Claude do it).

## Take it with you

```bash
python3 scripts/build_closet.py --embed   # → closet-app.html (images baked in)
```

AirDrop `closet-app.html` to your phone → open in Safari → Share →
**Add to Home Screen**. Offline closet app.

## Photo tips

- One garment per photo, laid flat on a plain contrasting surface.
- No hangers, no hands in frame (the AI can erase them, but flat is cleaner).
- If a cutout comes out wrong, redo it with an anchor:
  `python3 scripts/cleanup_fal.py <photo> --desc "a grey wrap skirt, no sleeves"`

## Privacy

- Photos and catalog live only in `closet/` (gitignored).
- Network calls: Open-Meteo weather (anonymous) and — only if you opt into
  Way 2 — fal.ai for cleanup. That's it.
- The local server binds to your machine/LAN; nothing is published.

## License

MIT
