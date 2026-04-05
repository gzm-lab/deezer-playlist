# Deezer Playlist Pipeline

> 🧒 **In plain English:** You press a button, and the app looks at all the songs you liked on Deezer, groups them by vibe (chill, energetic, happy...), and automatically creates new playlists for you every month!

Python pipeline that turns Deezer likes into:

- an enriched music dataset
- track clusters
- rotating monthly playlists

This README reflects the current workflow and commands.

## 1) What the project does

The pipeline runs these steps:

1. export liked tracks from Deezer
2. enrich with MusicBrainz matches
3. enrich with AcousticBrainz features (mood, danceability, genre, etc.)
4. analyze audio previews (signal-level features)
5. merge all data into a final dataset
6. vectorize and cluster tracks
7. generate monthly playlists
8. publish playlists to Deezer
9. clean up obsolete playlists for the month

## 2) Prerequisites

- Python 3.10+
- ffmpeg installed (required by pydub)
- Deezer app credentials

## 3) Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file at the repository root:

```env
application_id=YOUR_DEEZER_APP_ID
secret_key=YOUR_DEEZER_SECRET
application_domain=http://localhost:8080/callback
MB_USER_AGENT=DeezerMoodCluster/0.1 (contact: your@email.com)
```

## 4) First run (quick start)

Authenticate Deezer once and request all required scopes:

```bash
python3 -m tools.deezer_latest_liked --force-auth
```

The script prints `Token recu (expires=...)`:

- `expires=0` => long-lived token (typically no monthly re-login)
- `expires=3600` => short-lived token (periodic re-login may still be needed)

Build dataset + clusters + monthly playlists:

```bash
python3 deezer_pipeline.py build-all --month 2026-04
```

Publish to Deezer:

```bash
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
```

Delete obsolete playlists for the same month (keeps only the current set):

```bash
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```

## 5) Main commands

Single entry point:

```bash
python3 deezer_pipeline.py <command>
```

Useful commands:

- `build-dataset`: rebuild the full dataset
- `build-dataset --skip-export`: reuse existing `all_songs.json`
- `update-dataset`: incrementally update `final_dataset.json` with Deezer changes
- `build-playlists --month YYYY-MM`: recompute vectors, clusters, and monthly playlists
- `publish-playlists --input monthly_playlists.json`: create/update Deezer playlists
- `cleanup-playlists --input monthly_playlists.json`: delete obsolete playlists for that month
- `build-all --month YYYY-MM`: run dataset build, then playlist generation (local artifacts)

Examples:

```bash
python3 deezer_pipeline.py build-dataset
python3 deezer_pipeline.py update-dataset
python3 deezer_pipeline.py build-playlists --month 2026-04
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```

Current defaults:

- clustering: 12 clusters
- playlists: max 50 tracks per playlist
- tracks without audio features: randomly injected into generated playlists

## 6) Output files

Main artifacts:

- `all_songs.json`
- `musicbrainz_matched.json`
- `acousticbrainz_enriched.json`
- `preview_enriched.json`
- `final_dataset.json`
- `clustering_vectors.json`
- `clusters.json`
- `monthly_playlists.json`
- `monthly_playlists_history.json`

These files are local artifacts and are ignored by `.gitignore`.

## 7) Repository structure

```text
deezer/
├── deezer_pipeline.py          # main user entry point
├── core/                       # shared logic
│   ├── audio_features.py
│   └── deezer_api.py
└── tools/                      # operational scripts
	├── deezer_latest_liked.py
	├── export_coup_de_coeur.py
	├── musicbrainz_enrich.py
	├── acousticbrainz_enrich.py
	├── full_preview_analysis.py
	├── merge_all_features.py
	├── update_dataset.py
	├── prepare_clustering_features.py
	├── cluster_tracks.py
	├── generate_monthly_playlists.py
	├── publish_monthly_playlists.py
	└── cleanup_month_playlists.py
```

Simple rule: use `deezer_pipeline.py` for day-to-day operations.

## 8) Troubleshooting

Missing Deezer token:

- run: `python3 -m tools.deezer_latest_liked`
- force full re-auth (all scopes): `python3 -m tools.deezer_latest_liked --force-auth`
- verify `application_domain` in `.env`

Insufficient permission when deleting playlists:

- re-auth with `--force-auth`
- verify scopes include: `basic_access,manage_library,delete_library,offline_access`

Pydub/MP3 decoding issues:

- make sure `ffmpeg` is installed and available in PATH

Not enough tracks for clustering:

- check that `final_dataset.json` contains `preview_features`
- if needed, rerun `build-dataset` then `build-playlists`

## 9) Monthly manual workflow

This project is intentionally run manually every month.

1. Update dataset:

```bash
python3 deezer_pipeline.py update-dataset
```

2. Regenerate playlists for the month:

```bash
python3 deezer_pipeline.py build-playlists --month YYYY-MM
```

3. Publish to Deezer:

```bash
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
```

4. Clean up obsolete playlists for that month:

```bash
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```
