#!/usr/bin/env python3
"""Capture builder pages that are reachable from currently published branches."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "source-pages"
MODELS = {
    18: "https://fourwheelcampers.com/model/hawk-model-pop-up-truck-camper-leader-full-size-trucks/hawk-base-model/build/",
    19: "https://fourwheelcampers.com/model/hawk-model-pop-up-truck-camper-leader-full-size-trucks/orvis-special-edition-hawk-model/build/",
    20: "https://fourwheelcampers.com/model/hawk-model-pop-up-truck-camper-leader-full-size-trucks/hawk-model-front-dinette/build/",
    21: "https://fourwheelcampers.com/model/grandby-model-pop-up-truck-camper-leader-full-size-trucks/grandby-base-model/build/",
    22: "https://fourwheelcampers.com/model/grandby-model-pop-up-truck-camper-leader-full-size-trucks/orvis-special-edition-grandby-model/build/",
    23: "https://fourwheelcampers.com/model/grandby-model-pop-up-truck-camper-leader-full-size-trucks/grandby-model-front-dinette/build/",
    24: "https://fourwheelcampers.com/model/swift-model-pop-up-truck-camper-leader-mid-size-trucks/swift-base-model/build/",
    25: "https://fourwheelcampers.com/model/fleet-model-pop-up-truck-camper-leader-mid-size-trucks/fleet-base-model/build/",
    26: "https://fourwheelcampers.com/model/fleet-model-pop-up-truck-camper-leader-mid-size-trucks/fleet-base-model-w-roll-over-couch/build/",
}


def capture(item):
    model, url = item
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (local selector archival)"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    destination = PAGES / f"model-{model}.html"
    destination.write_bytes(payload)
    return model, len(payload)


def main():
    PAGES.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(capture, item) for item in MODELS.items()]
        for future in as_completed(futures):
            model, size = future.result()
            print(f"captured model-{model}.html ({size} bytes)")


if __name__ == "__main__":
    main()
