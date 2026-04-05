#!/usr/bin/env python3
"""Match exact ISRC via MusicBrainz.

Sorties par defaut:
- musicbrainz_matched.json (chansons retrouvees)
- musicbrainz_not_found.json (chansons non retrouvees)
"""

import os
import json
import time
import argparse
import random
from pathlib import Path
import requests
from dotenv import load_dotenv


load_dotenv()

MB_BASE = "https://musicbrainz.org/ws/2"


def get_user_agent():
    ua = os.getenv("MB_USER_AGENT")
    if ua:
        return ua
    return "DeezerMoodCluster/0.1 (contact: none)"


def mb_isrc_lookup(isrc):
    headers = {"User-Agent": get_user_agent(), "Accept": "application/json"}

    url_isrc = f"{MB_BASE}/isrc/{isrc}"
    params_isrc = {"fmt": "json"}
    r = requests.get(url_isrc, params=params_isrc, headers=headers, timeout=20)
    if r.status_code == 200:
        data = r.json()
        recs = data.get("recordings", [])
        if recs:
            return recs
    elif r.status_code not in (400, 404):
        r.raise_for_status()

    url_search = f"{MB_BASE}/recording"
    params_search = {"fmt": "json", "query": f"isrc:{isrc}"}
    r2 = requests.get(url_search, params=params_search, headers=headers, timeout=20)
    r2.raise_for_status()
    data2 = r2.json()
    recs2 = data2.get("recordings", [])
    return recs2


def mb_title_artist_search(title, artists):
    """Fallback search by title and artist when ISRC not found."""
    headers = {"User-Agent": get_user_agent(), "Accept": "application/json"}

    artist = artists[0] if artists else ""
    if not artist:
        return []

    query = f'recording:"{title}" AND artist:"{artist}"'
    url_search = f"{MB_BASE}/recording"
    params_search = {"fmt": "json", "query": query}

    r = requests.get(url_search, params=params_search, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("recordings", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="all_songs.json", help="Fichier d'entrée")
    parser.add_argument("--found", default="musicbrainz_matched.json", help="Sortie pour tracks retrouvés")
    parser.add_argument("--not-found", default="musicbrainz_not_found.json", help="Sortie pour tracks non retrouvés")
    parser.add_argument("--sleep", type=float, default=1.0, help="Pause entre requêtes MB")
    parser.add_argument("--sample", type=int, default=None, help="Nombre de tracks à échantillonner aléatoirement")
    parser.add_argument("--seed", type=int, default=42, help="Seed pour l'échantillonnage")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Fichier introuvable: {args.input}")
        return

    items = json.loads(Path(args.input).read_text())
    if args.sample:
        random.seed(args.seed)
        if args.sample < len(items):
            items = random.sample(items, args.sample)
    found = []
    not_found = []
    total = len(items)

    for idx, item in enumerate(items, start=1):
        isrc = item.get("isrc")
        if not isrc:
            not_found.append({**item, "reason": "missing_isrc"})
            if idx % 100 == 0:
                Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
                Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
                print(f"Progress: {idx}/{total} | Found: {len(found)} | Not found: {len(not_found)}")
            continue

        try:
            recs = mb_isrc_lookup(isrc)
        except Exception as e:
            not_found.append({**item, "reason": f"lookup_error: {e}"})
            time.sleep(args.sleep)
            if idx % 100 == 0:
                Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
                Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
                print(f"Progress: {idx}/{total} | Found: {len(found)} | Not found: {len(not_found)}")
            continue

        if not recs:
            try:
                time.sleep(args.sleep)
                recs = mb_title_artist_search(item.get("title", ""), item.get("artists", []))
            except Exception as e:
                not_found.append({**item, "reason": f"fallback_error: {e}"})
                time.sleep(args.sleep)
                if idx % 100 == 0:
                    Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
                    Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
                    print(f"Progress: {idx}/{total} | Found: {len(found)} | Not found: {len(not_found)}")
                continue

            if not recs:
                not_found.append({**item, "reason": "not_found_after_fallback"})
                time.sleep(args.sleep)
                if idx % 100 == 0:
                    Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
                    Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
                    print(f"Progress: {idx}/{total} | Found: {len(found)} | Not found: {len(not_found)}")
                continue

        mbids = [rec.get("id") for rec in recs if rec.get("id")]
        found.append({**item, "musicbrainz": {"mbids": mbids}})

        if idx % 100 == 0:
            Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
            Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
            print(f"Progress: {idx}/{total} | Found: {len(found)} | Not found: {len(not_found)}")

        time.sleep(args.sleep)

    Path(args.found).write_text(json.dumps(found, ensure_ascii=False, indent=2))
    Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))

    print(f"Found: {len(found)} | Not found: {len(not_found)}")
    print(f"Output: {args.found} / {args.not_found}")


if __name__ == "__main__":
    main()