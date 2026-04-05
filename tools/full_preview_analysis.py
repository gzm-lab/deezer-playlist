#!/usr/bin/env python3
"""Download all preview files and analyze them."""

import json
import requests
from pathlib import Path
import time
from core.audio_features import analyze_audio
from core.deezer_api import get_track_preview


def main():
    songs = json.loads(Path("all_songs.json").read_text())
    previews_dir = Path("previews")
    previews_dir.mkdir(exist_ok=True)

    enriched = []
    no_preview = []
    analysis_failed = []

    total = len(songs)

    print(f"Processing {total} tracks...\n")

    for idx, song in enumerate(songs, 1):
        track_id = song.get("id")
        preview_url = get_track_preview(track_id)

        if not preview_url:
            no_preview.append({**song, "reason": "no_preview_url"})
            if idx % 100 == 0:
                Path("preview_enriched.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
                Path("preview_no_preview.json").write_text(json.dumps(no_preview, ensure_ascii=False, indent=2))
                Path("preview_failed.json").write_text(json.dumps(analysis_failed, ensure_ascii=False, indent=2))
                print(f"Progress: {idx}/{total} | Enriched: {len(enriched)} | No preview: {len(no_preview)} | Failed: {len(analysis_failed)}")
            time.sleep(0.03)
            continue

        preview_path = previews_dir / f"{track_id}.mp3"

        if not preview_path.exists():
            try:
                r = requests.get(preview_url, timeout=30)
                r.raise_for_status()
                preview_path.write_bytes(r.content)
            except Exception as e:
                no_preview.append({**song, "reason": f"download_error: {e}"})
                if idx % 100 == 0:
                    Path("preview_enriched.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
                    Path("preview_no_preview.json").write_text(json.dumps(no_preview, ensure_ascii=False, indent=2))
                    Path("preview_failed.json").write_text(json.dumps(analysis_failed, ensure_ascii=False, indent=2))
                    print(f"Progress: {idx}/{total} | Enriched: {len(enriched)} | No preview: {len(no_preview)} | Failed: {len(analysis_failed)}")
                time.sleep(0.03)
                continue

        features = analyze_audio(preview_path)

        if features:
            enriched.append({**song, "preview_features": features})
        else:
            analysis_failed.append({**song, "reason": "analysis_error", "preview_path": str(preview_path)})

        if idx % 100 == 0:
            Path("preview_enriched.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
            Path("preview_no_preview.json").write_text(json.dumps(no_preview, ensure_ascii=False, indent=2))
            Path("preview_failed.json").write_text(json.dumps(analysis_failed, ensure_ascii=False, indent=2))
            print(f"Progress: {idx}/{total} | Enriched: {len(enriched)} | No preview: {len(no_preview)} | Failed: {len(analysis_failed)}")

        time.sleep(0.03)

    Path("preview_enriched.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    Path("preview_no_preview.json").write_text(json.dumps(no_preview, ensure_ascii=False, indent=2))
    Path("preview_failed.json").write_text(json.dumps(analysis_failed, ensure_ascii=False, indent=2))

    print("\n✅ Complete!")
    print(f"Enriched: {len(enriched)} tracks ({len(enriched)/total*100:.1f}%)")
    print(f"No preview: {len(no_preview)} tracks ({len(no_preview)/total*100:.1f}%)")
    print(f"Analysis failed: {len(analysis_failed)} tracks ({len(analysis_failed)/total*100:.1f}%)")
    print("\nOutput files:")
    print("  - preview_enriched.json")
    print("  - preview_no_preview.json")
    print("  - preview_failed.json")


if __name__ == "__main__":
    main()