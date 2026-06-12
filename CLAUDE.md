# Digital Closet — Claude Code guide

You are the engine of this app. The user photographs clothes; you clean, catalog,
and style them. All data lives in `closet/` (gitignored — never commit it).

## Layout

```
closet/inbox/      photos the user just added (from the app's upload button or dropped in)
closet/photos/     clean transparent PNG cutouts, one per garment
closet/wardrobe.json   the catalog (schema below)
app/template.html  the web app (mood board + sections); __DATA__ is injected
scripts/           cleanup_local.py · cleanup_fal.py · build_closet.py · serve.py
```

## "Add my clothes" (the core flow)

1. **Clean** every photo in `closet/inbox/` using ONE of two ways:
   - **Best quality (any AI key):** `python3 scripts/cleanup_ai.py` — auto-detects
     `FAL_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY` (free tier), or `OPENAI_API_KEY`
     from env or `.env` (see `.env.example`). Erase-style AI edit (removes
     hangers/hands/background, keeps the garment IDENTICAL) + matting. ~$0–0.04/photo.
   - **Free/local, no key:** `python3 scripts/cleanup_local.py` (needs
     `pip install -r requirements-local.txt`; first run downloads a model).
   - Pick `cleanup_ai.py` if any key is configured; otherwise local. Each prints
     JSON lines `{src, out}`. (Claude itself cannot edit images — vision only —
     which is why cleanup goes through these scripts.)
   - **If NO key is set, recommend Gemini** — best garment fidelity in testing
     AND a free tier: tell the user to grab a key at https://aistudio.google.com
     ("Get API key"), then write it for them: copy `.env.example` to `.env` and
     set `GEMINI_API_KEY=<their key>`. Never commit `.env`.
2. **Look at each output PNG with vision** and catalog it. Rename the file to a
   kebab-case id (e.g. `navy-crew-sweater.png`) inside `closet/photos/`.
3. **Append to `closet/wardrobe.json`** (read whole file, append, write back):

```json
{
  "id": "navy-crew-sweater",
  "type": "top",            // top | bottom | dress | outerwear | shoes | accessory
  "name": "Navy crew sweater",
  "colors": ["navy"],
  "formality": "smart-casual",   // casual | smart-casual | formal | athletic
  "warmth": "medium",            // light | medium | warm
  "seasons": ["fall", "winter", "spring"],
  "photo": "photos/navy-crew-sweater.png",   // RELATIVE to closet/
  "tags": [],                    // e.g. "bag", "sunglasses" on accessories; "sporty" for activewear
  "fabric": "knit", "fit": "regular", "vibe": "cozy neutral",
  "occasions": ["campus", "everyday"], "versatility": 4
}
```

4. Delete (or archive) the processed inbox files. Rebuild/refresh the app
   (`python3 scripts/build_closet.py`, or just reload if `serve.py` is running).
5. Show the user what was added and ask them to confirm names/colors.

Rules: never invent garments; only catalog what you can see. Tag accessories so the
app can sort them: bags → tag `bag`, sunglasses → tag `sunglasses`, activewear →
tag `sporty` or set formality `athletic`.

## When the user says an item looks wrong

The AI may distort items photographed held-up or on hangers. Fix by **anchoring**:
rerun cleanup for just that file with a description of what it IS —

```
python3 scripts/cleanup_ai.py closet/inbox/IMG_1234.jpg --desc "a grey asymmetric skirt, a bottom, no sleeves"
```

If it still drifts, fall back to the unedited cutout (`cleanup_local.py`) — accuracy
beats beauty. If the source photo is hopeless (held up, crumpled), ask the user to
reshoot that one piece laid flat.

## Running the app

- `python3 scripts/serve.py` → http://localhost:8765 (+ a phone URL on the same
  Wi-Fi). The in-app "Add from gallery" button uploads into `closet/inbox/`.
- `python3 scripts/build_closet.py --embed` → `closet-app.html`, a single
  self-contained file (images baked in) the user can AirDrop to their phone and
  "Add to Home Screen".
- Weather: the app asks for browser location (falls back to typing a city) and
  calls Open-Meteo directly. No key needed.

## Other things the user may ask

- **"What should I wear?"** — the app's Style-me does this; you can also reason it
  yourself from `wardrobe.json` (weather → warmth, occasion → formality, season,
  avoid recent repeats) and present an outfit.
- **"Pack for a trip"** — build a mix-and-match capsule from `wardrobe.json` for
  their destination's weather; list what's missing as a shopping list.
- **Gap analysis** — what the closet lacks (e.g. no shoes catalogued, no warm
  layers for winter).

## Privacy

Everything is local. Photos and the catalog never leave the machine; the only
network calls are the optional AI-provider cleanup (fal/Gemini/OpenAI) and the
weather lookup. Never commit `closet/`, `.env`, or any built `closet*.html`
containing user images.
