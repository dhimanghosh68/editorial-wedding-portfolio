#!/usr/bin/env python3

from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import html
import json
import re
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "assets" / "images"
NOTES = ROOT / "notes" / "image-sources.md"

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "EditorialWeddingPortfolio/1.0 (portfolio asset acquisition)"

GROUPS = [
    {
        "name": "Hero",
        "folder": "hero",
        "count": 2,
        "queries": [
            "wedding couple photography",
            "bride groom wedding",
        ],
        "names": ["hero-01.jpg", "hero-02.jpg"],
    },
    {
        "name": "City Wedding",
        "folder": "city",
        "count": 6,
        "queries": [
            "city wedding bride groom",
            "urban wedding couple",
            "wedding city photography",
        ],
        "names": [f"city-{i:02d}.jpg" for i in range(1, 7)],
    },
    {
        "name": "Estate Wedding",
        "folder": "estate",
        "count": 6,
        "queries": [
            "estate wedding bride groom",
            "manor wedding couple",
            "garden wedding bride groom",
            "luxury wedding venue couple",
        ],
        "names": [f"estate-{i:02d}.jpg" for i in range(1, 7)],
    },
    {
        "name": "Coastal Wedding",
        "folder": "coastal",
        "count": 6,
        "queries": [
            "beach wedding bride groom",
            "coastal wedding couple",
            "seaside wedding bride groom",
            "destination wedding beach",
        ],
        "names": [f"coastal-{i:02d}.jpg" for i in range(1, 7)],
    },
    {
        "name": "Photographer Portrait",
        "folder": "portrait",
        "count": 1,
        "queries": [
            "photographer portrait camera",
            "professional photographer portrait",
        ],
        "names": ["photographer.jpg"],
        "prefer_portrait": True,
    },
]

def clean_html(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()

def api_request(search):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search,
        "gsrnamespace": 6,
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": 1800,
        "format": "json",
        "formatversion": 2,
    }

    req = Request(
        API + "?" + urlencode(params),
        headers={"User-Agent": USER_AGENT},
    )

    with urlopen(req, timeout=30) as response:
        return json.load(response)

def candidates_for(search):
    data = api_request(search)
    pages = data.get("query", {}).get("pages", [])

    out = []

    for page in pages:
        infos = page.get("imageinfo") or []
        if not infos:
            continue

        info = infos[0]

        if info.get("mime") != "image/jpeg":
            continue

        width = int(info.get("width") or 0)
        height = int(info.get("height") or 0)

        if width < 1200 or height < 700:
            continue

        download_url = info.get("thumburl") or info.get("url")
        if not download_url:
            continue

        metadata = info.get("extmetadata") or {}

        source_page = (
            info.get("descriptionurl")
            or "https://commons.wikimedia.org/wiki/"
            + quote(page["title"].replace(" ", "_"), safe=":/")
        )

        out.append({
            "title": page.get("title", ""),
            "download_url": download_url,
            "source_page": source_page,
            "artist": clean_html(
                (metadata.get("Artist") or {}).get("value", "")
            ),
            "license": clean_html(
                (metadata.get("LicenseShortName") or {}).get("value", "")
            ),
            "license_url": clean_html(
                (metadata.get("LicenseUrl") or {}).get("value", "")
            ),
            "width": width,
            "height": height,
        })

    return out

def download(url, destination):
    req = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(req, timeout=60) as response:
        destination.write_bytes(response.read())

    with Image.open(destination) as image:
        image.verify()

    with Image.open(destination) as image:
        if image.format != "JPEG":
            raise RuntimeError(
                f"{destination}: expected JPEG, got {image.format}"
            )

def collect_group(group, used):
    pool = []

    for query in group["queries"]:
        print(f"Searching Commons: {query}")

        try:
            found = candidates_for(query)
        except Exception as exc:
            print(f"  search failed: {exc}")
            continue

        for item in found:
            key = item["source_page"]

            if key in used:
                continue

            if group.get("prefer_portrait"):
                if item["height"] <= item["width"]:
                    continue

            pool.append(item)

        time.sleep(0.5)

    unique = []
    seen_local = set()

    for item in pool:
        key = item["source_page"]

        if key in seen_local or key in used:
            continue

        seen_local.add(key)
        unique.append(item)

    if len(unique) < group["count"]:
        raise RuntimeError(
            f'{group["name"]}: only found {len(unique)} suitable images; '
            f'need {group["count"]}'
        )

    chosen = unique[:group["count"]]

    destination_dir = IMAGE_ROOT / group["folder"]
    destination_dir.mkdir(parents=True, exist_ok=True)

    records = []

    for filename, item in zip(group["names"], chosen):
        destination = destination_dir / filename

        print(f"Downloading {filename}")
        download(item["download_url"], destination)

        used.add(item["source_page"])

        records.append({
            "filename": filename,
            **item,
        })

    return records

def write_sources(records):
    lines = [
        "# Image Sources",
        "",
        "Photography in this portfolio sample was acquired from",
        "Wikimedia Commons using its public MediaWiki API.",
        "",
        "Images are stored locally in the project.",
        "",
        "No image filters, tinting, recoloring, black-and-white conversion,",
        "or intentional cropping were applied by this project.",
        "",
        "License and attribution information below is taken from the",
        "metadata returned by Wikimedia Commons at acquisition time.",
        "",
    ]

    for group_name, items in records:
        lines.extend([
            f"## {group_name}",
            "",
            "| Local file | Photographer / creator | License | Source |",
            "|---|---|---|---|",
        ])

        for item in items:
            creator = item["artist"] or "See source page"
            license_name = item["license"] or "See source page"

            creator = creator.replace("|", "\\|")
            license_name = license_name.replace("|", "\\|")

            lines.append(
                f'| `{item["filename"]}` | '
                f'{creator} | '
                f'{license_name} | '
                f'[Wikimedia Commons]({item["source_page"]}) |'
            )

        lines.append("")

    NOTES.write_text("\n".join(lines), encoding="utf-8")

def main():
    used = set()
    all_records = []

    for group in GROUPS:
        records = collect_group(group, used)
        all_records.append((group["name"], records))

    total = sum(len(items) for _, items in all_records)

    if total != 21:
        raise RuntimeError(f"Expected 21 images, acquired {total}")

    write_sources(all_records)

    print()
    print(f"Acquired {total} photographs.")
    print(f"Source ledger: {NOTES}")

if __name__ == "__main__":
    main()
