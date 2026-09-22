#!/usr/bin/env python3

from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image
import html
import json
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "assets" / "review"
REVIEW = ROOT / "notes" / "photo-review.html"
SOURCES = ROOT / "notes" / "photo-review-sources.md"

API = "https://api.openverse.org/v1/images/"
UA = "EditorialWeddingPortfolio/1.0"

GROUPS = [
    (
        "Hero",
        "hero",
        2,
        [
            "modern editorial wedding couple",
            "luxury wedding couple",
            "modern bride groom wedding",
        ],
    ),
    (
        "City Wedding",
        "city",
        6,
        [
            "modern city wedding couple",
            "urban wedding couple",
            "city bride groom",
            "hotel wedding couple",
        ],
    ),
    (
        "Estate Wedding",
        "estate",
        6,
        [
            "estate wedding couple",
            "manor wedding couple",
            "garden wedding bride groom",
            "country house wedding couple",
        ],
    ),
    (
        "Coastal Wedding",
        "coastal",
        6,
        [
            "coastal wedding couple",
            "beach wedding bride groom",
            "seaside wedding couple",
            "ocean wedding couple",
        ],
    ),
    (
        "Photographer Portrait",
        "portrait",
        1,
        [
            "photographer portrait camera",
            "professional photographer portrait",
        ],
    ),
]

ALLOWED = {"cc0", "by", "by-sa", "pdm"}

REJECT = (
    "painting",
    "drawing",
    "illustration",
    "engraving",
    "archive",
    "book",
    "poster",
    "historic",
    "historical",
    "manuscript",
)

def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)

def search(query):
    url = API + "?" + urlencode({
        "q": query,
        "page_size": 20,
    })
    return get_json(url).get("results", [])

def valid(item, portrait=False):
    license_code = str(item.get("license") or "").lower()
    if license_code not in ALLOWED:
        return False

    # Openverse frequently omits width/height metadata even when
    # the original image is large enough. Validate actual dimensions
    # after download instead of rejecting missing metadata here.

    text = " ".join([
        str(item.get("title") or ""),
        str(item.get("creator") or ""),
        str(item.get("source") or ""),
    ]).lower()

    if any(word in text for word in REJECT):
        return False

    url = str(item.get("url") or item.get("thumbnail") or "")
    return url.startswith(("http://", "https://"))

def download(url, destination):
    req = Request(url, headers={"User-Agent": UA})

    with urlopen(req, timeout=60) as response:
        destination.write_bytes(response.read())

    try:
        with Image.open(destination) as image:
            image.verify()

        with Image.open(destination) as image:
            if image.format != "JPEG":
                raise ValueError(f"not JPEG: {image.format}")
            short_side = min(image.width, image.height)
            long_side = max(image.width, image.height)

            if short_side < 600 or long_side < 900:
                raise ValueError(
                    f"image too small: {image.width}x{image.height}"
                )
    except Exception:
        destination.unlink(missing_ok=True)
        raise

def filename(folder, index):
    if folder == "portrait":
        return "photographer.jpg"
    return f"{folder}-{index:02d}.jpg"

def main():
    if STAGE.exists():
        shutil.rmtree(STAGE)

    STAGE.mkdir(parents=True)

    records = []
    globally_used = set()

    for group_name, folder_name, count, queries in GROUPS:
        portrait = folder_name == "portrait"
        candidates = []
        seen = set()

        for query in queries:
            print(f"Searching: {query}")

            try:
                results = search(query)
            except Exception as exc:
                print("  search error:", exc)
                continue

            for item in results:
                if not valid(item, portrait):
                    continue

                identity = (
                    item.get("foreign_landing_url")
                    or item.get("url")
                )

                if (
                    not identity
                    or identity in seen
                    or identity in globally_used
                ):
                    continue

                seen.add(identity)
                candidates.append(item)

            time.sleep(0.35)

        destination_dir = STAGE / folder_name
        destination_dir.mkdir(parents=True, exist_ok=True)

        chosen = []

        for item in candidates:
            if len(chosen) >= count:
                break

            local_name = filename(folder_name, len(chosen) + 1)
            destination = destination_dir / local_name

            try:
                print(f"Downloading {folder_name}/{local_name}")
                download(str(item.get("url") or item.get("thumbnail")), destination)
            except Exception as exc:
                print("  skipped:", exc)
                continue

            identity = (
                item.get("foreign_landing_url")
                or item.get("url")
            )
            globally_used.add(identity)

            chosen.append({
                "group": group_name,
                "folder": folder_name,
                "filename": local_name,
                "title": str(item.get("title") or "Untitled"),
                "creator": str(item.get("creator") or "Unknown"),
                "license": str(item.get("license") or "").upper(),
                "license_version": str(
                    item.get("license_version") or ""
                ),
                "source": str(item.get("source") or "Openverse"),
                "landing": str(
                    item.get("foreign_landing_url") or item.get("url")
                ),
            })

        if len(chosen) != count:
            raise RuntimeError(
                f"{group_name}: found {len(chosen)} usable images; "
                f"expected {count}"
            )

        records.extend(chosen)

    if len(records) != 21:
        raise RuntimeError(
            f"Expected 21 staged photographs, got {len(records)}"
        )

    md = [
        "# Staged Photo Sources",
        "",
        "These are review candidates and have not yet replaced the",
        "main project photographs.",
        "",
    ]

    cards = []

    for item in records:
        license_text = item["license"]
        if item["license_version"]:
            license_text += " " + item["license_version"]

        md.extend([
            f"## {item['group']} — `{item['filename']}`",
            "",
            f"- Title: {item['title']}",
            f"- Creator: {item['creator']}",
            f"- License: {license_text}",
            f"- Source: {item['source']}",
            f"- Original page: {item['landing']}",
            "",
        ])

        image_path = (
            f"../assets/review/{item['folder']}/{item['filename']}"
        )

        cards.append(f"""
<article>
  <img src="{html.escape(image_path)}"
       alt="{html.escape(item['title'])}">
  <div>
    <strong>{html.escape(item['group'])}</strong>
    <code>{html.escape(item['filename'])}</code>
    <span>{html.escape(item['title'])}</span>
    <span>{html.escape(item['creator'])}</span>
    <span>{html.escape(license_text)}</span>
    <a href="{html.escape(item['landing'])}"
       target="_blank"
       rel="noreferrer">Source</a>
  </div>
</article>
""")

    SOURCES.write_text("\n".join(md), encoding="utf-8")

    REVIEW.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Photo Review</title>
<style>
body {{
  margin: 0;
  padding: 32px;
  background: #111;
  color: #eee;
  font-family: Arial, sans-serif;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(300px,1fr));
  gap: 24px;
}}
article {{
  background: #1c1c1c;
  border: 1px solid #333;
}}
img {{
  display: block;
  width: 100%;
  height: 390px;
  object-fit: contain;
  background: #000;
}}
article div {{
  padding: 14px;
  display: grid;
  gap: 6px;
  font-size: 13px;
}}
code {{ color: #bbb; }}
a {{ color: white; }}
</style>
</head>
<body>
<h1>Editorial Wedding Portfolio — Photo Review</h1>
<p>21 staged candidates. The existing project assets are untouched.</p>
<div class="grid">
{''.join(cards)}
</div>
</body>
</html>
""",
        encoding="utf-8",
    )

    print()
    print("Staged images:", len(records))
    print("Review:", REVIEW)
    print("Metadata:", SOURCES)

if __name__ == "__main__":
    main()
