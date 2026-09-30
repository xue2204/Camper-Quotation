# Local Camper Quote System

Run from this directory (Python 3 required):

```sh
python3 -m http.server 4173 --bind 0.0.0.0
```

Open `http://127.0.0.1:4173/`.

The local `source-pages/` folder holds the publicly accessible model markup captured for 26 model routes. `index.html` implements the source selector tree and `builder.html` renders the local captured option catalog with live client-side price/weight updates. The source site’s video, tracking, CRM submission, financing widget, and external customer form are excluded.

## Project structure

- `app.js`: truck/bed branches, platforms, configurations, packages and selection state.
- `builder.js`: model rendering, accessory overrides, colors, totals and local summary.
- `source-pages/model-*.html`: local model catalogs.
- `assets/`: local images, styles and fonts.
- `config-overrides.json`: accessory edits saved by the separate management project.
- `tools/`: source capture, asset localization and catalog verification utilities.

The accessory manager remains a separate sibling project, `change-quota-message`; run `python3 server.py` from that directory on port 4175. It writes this project's `config-overrides.json`.

The initial commit named `第一版全相同系统` preserves the existing implementation before product removals. This version name does not imply verified parity with live external submission services.
