#!/usr/bin/env python3
"""Download public source images used by the locally captured builder pages.

It preserves each original WordPress path under assets/ and rewrites the local
HTML files to use /assets/... so model images no longer depend on the source
website at render time.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen
import json
import re

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "source-pages"
ASSETS = ROOT / "assets"
URL_RE = re.compile(r"https://fourwheelcampers\.com/[^\"'\s<>]+?\.(?:png|jpe?g|webp|svg)", re.I)
ESCAPED_URL_RE = re.compile(r"https:\\/\\/fourwheelcampers\.com(?:\\/[^\"'\s<>]+?)+?\.(?:png|jpe?g|webp|svg)", re.I)
LOCAL_RE = re.compile(r"/assets/(wp-content/[^\"'\s<>]+?\.(?:png|jpe?g|webp|svg))", re.I)
CSS_REF_RE = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)
CSS_URLS = {
    "https://fourwheelcampers.com/wp-content/themes/fourwh/assets/css/screen.css",
    "https://fourwheelcampers.com/wp-content/themes/fourwh/assets/css/model.css",
}
SEED_URLS = {
    "https://fourwheelcampers.com/wp-content/uploads/2025/10/Full-Sized-Trucks_@2x.png",
    "https://fourwheelcampers.com/wp-content/uploads/2025/10/Mid-Sized-Trucks_@2x.png",
    "https://fourwheelcampers.com/wp-content/uploads/2025/10/Flatbed-Truck_@2x.png",
    "https://fourwheelcampers.com/wp-content/uploads/2018/12/truck_3.png",
    "https://fourwheelcampers.com/wp-content/uploads/2018/12/truck_1.png",
    "https://fourwheelcampers.com/wp-content/uploads/2018/12/truck_2.png",
    "https://fourwheelcampers.com/wp-content/uploads/2025/10/Short-Bed_@2x-440x183.png",
    "https://fourwheelcampers.com/wp-content/uploads/2025/10/Long-Bed_@2x-440x182.png",
    "https://fourwheelcampers.com/wp-content/uploads/2019/03/FLEET-FLAT-BED-web.jpg",
    "https://fourwheelcampers.com/wp-content/uploads/2019/03/HAWK-FLAT-BED-web.jpg",
    "https://fourwheelcampers.com/wp-content/uploads/2019/03/GRANDBY-FLAT-BED-web-1-440x197.jpg",
    "https://fourwheelcampers.com/wp-content/uploads/2024/05/Model-M-Tacoma-model-selector_scaled-grey-440x293.jpg",
    "https://fourwheelcampers.com/wp-content/uploads/2025/01/campout-model-thumbnail-copy-440x293.jpg",
    "https://fourwheelcampers.com/wp-content/uploads/2025/01/admin-ajax-slide-in-copy-440x293.jpg",
}

def decoded_copy(text: str) -> str:
    """Decode the forms used inside HTML attributes and embedded JSON."""
    text = unescape(text).replace("\\/", "/")
    for _ in range(2):
        text = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda match: chr(int(match.group(1), 16)),
            text,
        )
    return text


def canonical_url(url: str) -> str:
    return unquote(decoded_copy(url)).split("?", 1)[0]


def local_path(url: str) -> Path:
    return ASSETS / unquote(urlparse(canonical_url(url)).path).lstrip("/")

def download(url: str) -> tuple[str, str]:
    dest = local_path(url)
    if dest.exists() and dest.stat().st_size:
        return url, "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        request_url = quote(canonical_url(url), safe=":/%?=&#+,;@()[]!'$")
        req = Request(request_url, headers={"User-Agent": "Mozilla/5.0 (local asset archival)"})
        with urlopen(req, timeout=30) as response:
            payload = response.read()
        if not payload:
            return url, "empty"
        dest.write_bytes(payload)
        return url, "downloaded"
    except Exception as exc:
        if dest.exists():
            dest.unlink()
        return url, f"failed: {exc}"

def main() -> None:
    sources = sorted(PAGES.glob("model-*.html"))
    sources += [path for path in (ROOT / "index.html", ROOT / "builder.html", ROOT / "app.js", ROOT / "builder.js") if path.exists()]
    page_text = {page: page.read_text(encoding="utf-8", errors="ignore") for page in sources}
    urls = set(SEED_URLS) | set(CSS_URLS)
    for text in page_text.values():
        decoded = decoded_copy(text)
        urls.update(canonical_url(url) for url in URL_RE.findall(decoded))
        urls.update(canonical_url(url) for url in ESCAPED_URL_RE.findall(text))
        urls.update(
            "https://fourwheelcampers.com/" + canonical_url(path).lstrip("/")
            for path in LOCAL_RE.findall(decoded)
        )

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(download, url) for url in sorted(urls)]
        for future in as_completed(futures):
            url, result = future.result()
            results[url] = result

    css_dependencies = set()
    for css_url in CSS_URLS:
        css_file = local_path(css_url)
        if not css_file.exists():
            continue
        css_text = css_file.read_text(encoding="utf-8", errors="ignore")
        for reference in CSS_REF_RE.findall(css_text):
            if reference.startswith(("data:", "#")):
                continue
            css_dependencies.add(canonical_url(urljoin(css_url, reference)))
    new_urls = css_dependencies - urls
    if new_urls:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(download, url) for url in sorted(new_urls)]
            for future in as_completed(futures):
                url, result = future.result()
                results[url] = result
        urls.update(new_urls)

    for page, text in page_text.items():
        for url in urls:
            local = "/assets/" + urlparse(url).path.lstrip("/")
            variants = {
                url,
                url.replace("/", "\\/"),
                json.dumps(url, ensure_ascii=True)[1:-1],
                json.dumps(url, ensure_ascii=True)[1:-1].replace("/", "\\/"),
            }
            for variant in variants:
                text = text.replace(variant, local)
        page.write_text(text, encoding="utf-8")

    ok = sum(not status.startswith("failed") and status != "empty" for status in results.values())
    failed = [(url, status) for url, status in results.items() if status.startswith("failed") or status == "empty"]
    missing = [url for url in sorted(urls) if not local_path(url).is_file() or not local_path(url).stat().st_size]
    print(f"localized {ok}/{len(urls)} source images; missing locally: {len(missing)}")
    for url, status in failed:
        print(f"{status} :: {url}")
    if missing:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
