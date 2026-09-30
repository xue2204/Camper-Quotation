#!/usr/bin/env python3
"""Enumerate the public truck-selector branches for regression checks."""
from html import unescape
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import json
import re

AJAX_URL = "https://fourwheelcampers.com/wp-admin/admin-ajax.php"
FITMENTS = [
    (0, "Full Sized Trucks", 0, "Short Bed", "full:short"),
    (0, "Full Sized Trucks", 1, "Standard Bed", "full:standard"),
    (0, "Full Sized Trucks", 2, "Long Bed", "full:long"),
    (1, "Mid Sized Trucks", 0, "Short Bed", "mid:short"),
    (1, "Mid Sized Trucks", 1, "Long Bed", "mid:long"),
    (2, "Flatbed Trucks", 0, "Mid-Sized Truck Flatbed", "flatbed:mid-flat"),
    (2, "Flatbed Trucks", 1, "Full Sized Truck w/ Regular Flatbed", "flatbed:regular-flat"),
    (2, "Flatbed Trucks", 2, "Full Sized Truck w/ Long Flatbed", "flatbed:long-flat"),
]


def cookie_header(values):
    pairs = []
    for name, value in values.items():
        raw = json.dumps(value, separators=(",", ":")) if isinstance(value, dict) else str(value)
        pairs.append(f"{name}={quote(raw, safe='')}")
    return "; ".join(pairs)


def post(data, cookies):
    request = Request(
        AJAX_URL,
        data=urlencode(data).encode(),
        headers={"User-Agent": "Mozilla/5.0 (selector branch audit)", "Cookie": cookie_header(cookies)},
    )
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def cards(markup):
    openings = list(re.finditer(r'<li class="([^"]*\boption-box\b[^"]*)"[^>]*data-index="([^"]+)"([^>]*)>', markup))
    headings = list(re.finditer(r'<h3 class="title">(.*?)</h3>', markup, re.S))
    result = []
    for number, opening in enumerate(openings):
        next_start = openings[number + 1].start() if number + 1 < len(openings) else len(markup)
        heading = next((item for item in headings if opening.end() <= item.start() < next_start), None)
        attrs = opening.group(3)
        url_match = re.search(r'data-url="([^"]+)"', attrs)
        result.append({
            "index": opening.group(2),
            "title": re.sub(r"<[^>]+>", "", unescape(heading.group(1))).strip() if heading else "",
            "url": unescape(url_match.group(1)) if url_match else "",
            "classes": opening.group(1).split(),
        })
    return result


def main():
    output = {}
    for truck_index, truck, bed_index, bed, key in FITMENTS:
        cookies = {
            "fwc_truckSize": {"index": truck_index, "title": truck},
            "fwc_bedLength": {"index": bed_index, "title": bed},
            "fwc_ts_steps": "1",
        }
        markup = post({"action": "load_truck_selector"}, cookies)
        heading = re.search(r'<h2 class="title">(.*?)</h2>', markup, re.S)
        branch = {
            "stage": re.sub(r"<[^>]+>", "", unescape(heading.group(1))).strip() if heading else "",
            "cards": cards(markup),
        }
        for platform in branch["cards"]:
            platform_cookies = dict(cookies)
            platform_cookies["fwc_platform"] = {"index": platform["index"], "title": platform["title"]}
            if "next-configuration" in platform["classes"]:
                config_markup = post(
                    {"action": "load_configurations", "index": platform["index"], "prev_section": "section-platform"},
                    platform_cookies,
                )
                platform["configurations"] = cards(config_markup)
                for config in platform["configurations"]:
                    if "next-option-packages" not in config["classes"]:
                        continue
                    package_cookies = dict(platform_cookies)
                    package_cookies["fwc_platform-configuration"] = {
                        "index": config["index"], "title": config["title"]
                    }
                    package_cookies["fwc_ts_steps"] = "1,2"
                    config["packages"] = cards(post({"action": "load_truck_selector"}, package_cookies))
            elif "next-option-packages" in platform["classes"]:
                platform_cookies["fwc_ts_steps"] = "1,2"
                platform["packages"] = cards(post({"action": "load_truck_selector"}, platform_cookies))
        output[key] = branch
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
