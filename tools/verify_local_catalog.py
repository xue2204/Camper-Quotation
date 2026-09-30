#!/usr/bin/env python3
"""Verify branch coverage and locally served catalog assets."""
from pathlib import Path
from urllib.request import urlopen
import re

from localize_assets import ASSETS, CSS_REF_RE, CSS_URLS, LOCAL_RE, ROOT, decoded_copy, local_path

ROUTES = {
    "full:short", "full:standard", "full:long", "mid:short", "mid:long",
    "flatbed:mid-flat", "flatbed:regular-flat", "flatbed:long-flat",
}


def main():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    missing_routes = sorted(key for key in ROUTES if f'"{key}"' not in app)
    pages = sorted((ROOT / "source-pages").glob("model-*.html"))
    page_numbers = {int(re.search(r"(\d+)$", page.stem).group(1)) for page in pages}
    missing_pages = sorted(set(range(1, 27)) - page_numbers)

    refs = set()
    remote_images = []
    sources = pages + [ROOT / "index.html", ROOT / "builder.html", ROOT / "app.js", ROOT / "builder.js"]
    for source in sources:
        decoded = decoded_copy(source.read_text(encoding="utf-8", errors="ignore"))
        refs.update(LOCAL_RE.findall(decoded))
        remote_images.extend(re.findall(r"https?://[^\"'\s<>]+\.(?:png|jpe?g|webp|svg)", decoded, re.I))

    missing_assets = sorted(ref for ref in refs if not (ASSETS / ref).is_file())
    missing_css_assets = []
    for css_url in CSS_URLS:
        css_path = local_path(css_url)
        css_text = css_path.read_text(encoding="utf-8", errors="ignore")
        for ref in CSS_REF_RE.findall(css_text):
            if ref.startswith(("data:", "#", "http://", "https://")):
                continue
            relative = ref.split("?", 1)[0].split("#", 1)[0]
            expected = (css_path.parent / relative).resolve()
            if not expected.is_file():
                missing_css_assets.append(str(expected))

    http_failures = []
    for path in ["/", "/builder.html", *[f"/source-pages/model-{number}.html" for number in range(1, 27)]]:
        try:
            with urlopen("http://127.0.0.1:4173" + path, timeout=5) as response:
                if response.status != 200:
                    http_failures.append(f"{path}: HTTP {response.status}")
        except Exception as exc:
            http_failures.append(f"{path}: {exc}")

    failures = missing_routes or missing_pages or missing_assets or missing_css_assets or remote_images or http_failures
    print(f"routes={len(ROUTES) - len(missing_routes)}/{len(ROUTES)}")
    print(f"model_pages={len(page_numbers)}/26")
    print(f"local_image_refs={len(refs)} missing={len(missing_assets)} remote={len(remote_images)}")
    print(f"css_dependencies_missing={len(missing_css_assets)}")
    print(f"http_pages={28 - len(http_failures)}/28")
    if failures:
        for label, items in (
            ("missing route", missing_routes), ("missing page", missing_pages),
            ("missing asset", missing_assets), ("missing CSS asset", missing_css_assets),
            ("remote image", remote_images), ("HTTP failure", http_failures),
        ):
            for item in items:
                print(f"{label}: {item}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
