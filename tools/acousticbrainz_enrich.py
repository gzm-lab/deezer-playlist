#!/usr/bin/env python3
"""Enrich MusicBrainz matched tracks with AcousticBrainz high-level features.

Input: musicbrainz_matched.json (tracks with mbids)
Output: acousticbrainz_enriched.json (tracks with AB features)
"""

import json
import time
import argparse
from pathlib import Path
import requests


AB_BASE = "https://acousticbrainz.org/api/v1"


def get_acousticbrainz_features(mbid):
    """Fetch high-level features from AcousticBrainz for a given MBID.

    Returns dict with features or None if not found.
    """
    url = f"{AB_BASE}/{mbid}/high-level"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            data = r.json()
            highlevel = data.get("highlevel", {})

            features = {}

            for mood in ["acoustic", "aggressive", "electronic", "happy", "party", "relaxed", "sad"]:
                if f"mood_{mood}" in highlevel:
                    features[f"mood_{mood}"] = highlevel[f"mood_{mood}"].get("value")
                    features[f"mood_{mood}_probability"] = highlevel[f"mood_{mood}"].get("probability", 0)

            if "danceability" in highlevel:
                features["danceability"] = highlevel["danceability"].get("value")
                features["danceability_probability"] = highlevel["danceability"].get("probability", 0)

            if "genre_rosamerica" in highlevel:
                features["genre"] = highlevel["genre_rosamerica"].get("value")
                features["genre_probability"] = highlevel["genre_rosamerica"].get("probability", 0)

            if "tonal_atonal" in highlevel:
                features["tonal_atonal"] = highlevel["tonal_atonal"].get("value")

            if "voice_instrumental" in highlevel:
                features["voice_instrumental"] = highlevel["voice_instrumental"].get("value")
                features["voice_instrumental_probability"] = highlevel["voice_instrumental"].get("probability", 0)

            return features if features else None
        if r.status_code == 404:
            return None
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching AB for {mbid}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="musicbrainz_matched.json", help="Input file with MBIDs")
    parser.add_argument("--output", "-o", default="acousticbrainz_enriched.json", help="Output file with AB features")
    parser.add_argument("--not-found", default="ab_not_found.json", help="Output for tracks without AB data")
    parser.add_argument("--sleep", type=float, default=0.5, help="Pause between requests")
    parser.add_argument("--sample", type=int, default=None, help="Test on N tracks")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Input file not found: {args.input}")
        return

    items = json.loads(Path(args.input).read_text())
    if args.sample:
        items = items[:args.sample]

    enriched = []
    not_found = []
    total = len(items)

    for idx, item in enumerate(items, start=1):
        mbids = item.get("musicbrainz", {}).get("mbids", [])

        if not mbids:
            not_found.append({**item, "ab_reason": "no_mbid"})
            if idx % 100 == 0:
                Path(args.output).write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
                Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
                print(f"Progress: {idx}/{total} | Enriched: {len(enriched)} | Not found: {len(not_found)}")
            continue

        mbid = mbids[0]
        features = get_acousticbrainz_features(mbid)

        if features:
            enriched.append({**item, "acousticbrainz": features})
        else:
            not_found.append({**item, "ab_reason": "not_in_acousticbrainz"})

        if idx % 100 == 0:
            Path(args.output).write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
            Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))
            print(f"Progress: {idx}/{total} | Enriched: {len(enriched)} | Not found: {len(not_found)}")

        time.sleep(args.sleep)

    Path(args.output).write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    Path(args.not_found).write_text(json.dumps(not_found, ensure_ascii=False, indent=2))

    print("\n✅ Complete!")
    print(f"Enriched: {len(enriched)} tracks ({len(enriched)/total*100:.1f}%)")
    print(f"Not found in AB: {len(not_found)} tracks ({len(not_found)/total*100:.1f}%)")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()