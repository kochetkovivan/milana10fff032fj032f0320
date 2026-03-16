import json
import os
import re
import urllib.request
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "valid.txt"
OUTPUT_FILE = "data.json"
AVATARS_DIR = "avatars"


def parse_line(line):
    """Parse a pipe-delimited line from valid.txt."""
    parts = line.strip().split("|")
    if len(parts) < 5:
        return None

    username = parts[0]  # e.g. @elena_psixology
    login = username.lstrip("@")
    name = parts[1]
    description = parts[2]

    # Extract image URL from =IMAGE("url"; ...)
    image_part = parts[4]
    match = re.search(r'=IMAGE\("([^"]+)"', image_part)
    avatar_url = match.group(1) if match else None

    return {
        "username": username,
        "login": login,
        "name": name,
        "description": description,
        "avatar_url": avatar_url,
        "avatar": f"{AVATARS_DIR}/{login}.jpg",
    }


def download_avatar(entry):
    """Download avatar image, return (login, success)."""
    if not entry["avatar_url"]:
        return entry["login"], False

    path = entry["avatar"]
    if os.path.exists(path):
        return entry["login"], True

    try:
        req = urllib.request.Request(
            entry["avatar_url"],
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())
        return entry["login"], True
    except Exception as e:
        print(f"  Failed {entry['login']}: {e}")
        return entry["login"], False


def main():
    os.makedirs(AVATARS_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]

    entries = []
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            entries.append(parsed)

    print(f"Parsed {len(entries)} entries from {INPUT_FILE}")

    # Download avatars in parallel
    print("Downloading avatars...")
    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(download_avatar, e): e for e in entries}
        for i, future in enumerate(as_completed(futures), 1):
            login, success = future.result()
            if success:
                ok += 1
            else:
                fail += 1
            if i % 50 == 0 or i == len(entries):
                print(f"  Progress: {i}/{len(entries)}")

    print(f"Downloaded: {ok} ok, {fail} failed")

    # Build output JSON (same format as data.json)
    result = []
    for e in entries:
        result.append({
            "username": e["username"],
            "login": e["login"],
            "name": e["name"],
            "description": e["description"],
            "avatar": e["avatar"],
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(result)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
