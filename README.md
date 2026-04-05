# Deezer Playlist Pipeline

Pipeline Python pour transformer les likes Deezer en:

- dataset musical enrichi
- clusters de morceaux
- playlists mensuelles qui tournent dans le temps

Ce README est centré sur l'utilisation actuelle du projet.

## 1) Ce que fait le projet

Le pipeline enchaine ces etapes:

1. export des tracks likes depuis Deezer
2. enrichissement MusicBrainz (matching)
3. enrichissement AcousticBrainz (mood, danceability, genre, etc.)
4. analyse des previews audio (features de signal)
5. fusion en dataset final
6. vectorisation + clustering
7. generation de playlists mensuelles
8. publication des playlists dans Deezer
9. nettoyage des anciennes playlists du mois

## 2) Prerequis

- Python 3.10+
- ffmpeg installe (necessaire pour pydub)
- credentials Deezer app

## 3) Installation

Creer et activer un environnement virtuel:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Creer le fichier .env a la racine:

```env
application_id=YOUR_DEEZER_APP_ID
secret_key=YOUR_DEEZER_SECRET
application_domain=http://localhost:8080/callback
MB_USER_AGENT=DeezerMoodCluster/0.1 (contact: your@email.com)
```

## 4) Premiere execution (quick start)

Authentifier Deezer (une fois) et demander tous les scopes utiles:

```bash
python3 -m tools.deezer_latest_liked --force-auth
```

Le script affiche `Token recu (expires=...)`:

- `expires=0` => token long-terme (pas de reconnexion mensuelle en pratique)
- `expires=3600` => token court, reconnexion periodique possible

Construire dataset + clusters + playlists du mois:

```bash
python3 deezer_pipeline.py build-all --month 2026-04
```

Publier dans Deezer:

```bash
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
```

Supprimer les anciennes playlists du meme mois (garde seulement la serie courante):

```bash
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```

## 5) Commandes principales

Point d'entree unique:

```bash
python3 deezer_pipeline.py <commande>
```

Commandes utiles:

- build-dataset: reconstruit tout le dataset
- build-dataset --skip-export: reutilise all_songs.json existant
- update-dataset: met a jour final_dataset.json avec les nouveaux likes
- build-playlists --month YYYY-MM: recalcule vecteurs, clusters et playlists
- publish-playlists --input monthly_playlists.json: cree/met a jour les playlists Deezer
- cleanup-playlists --input monthly_playlists.json: supprime les anciennes playlists du mois
- build-all --month YYYY-MM: execute dataset puis playlists (generation locale)

Exemples:

```bash
python3 deezer_pipeline.py build-dataset
python3 deezer_pipeline.py update-dataset
python3 deezer_pipeline.py build-playlists --month 2026-04
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```

Defaults actuels:

- clustering: 12 clusters
- playlists: max 50 titres par playlist
- titres sans features audio: inseres aleatoirement dans les playlists generees

## 6) Fichiers produits

Sorties principales:

- all_songs.json
- musicbrainz_matched.json
- acousticbrainz_enriched.json
- preview_enriched.json
- final_dataset.json
- clustering_vectors.json
- clusters.json
- monthly_playlists.json
- monthly_playlists_history.json

Ces fichiers sont des artefacts locaux et sont ignores par .gitignore.

## 7) Structure du repo

```text
deezer/
├── deezer_pipeline.py          # interface utilisateur principale
├── core/                       # logique partagee
│   ├── audio_features.py
│   └── deezer_api.py
└── tools/                      # scripts operationnels
	├── deezer_latest_liked.py
	├── export_coup_de_coeur.py
	├── musicbrainz_enrich.py
	├── acousticbrainz_enrich.py
	├── full_preview_analysis.py
	├── merge_all_features.py
	├── update_dataset.py
	├── prepare_clustering_features.py
	├── cluster_tracks.py
	└── generate_monthly_playlists.py
```

Regle simple: utilise deezer_pipeline.py pour le quotidien.

## 8) Depannage rapide

Token Deezer manquant:

- relancer: python3 -m tools.deezer_latest_liked
- forcer une nouvelle auth (scopes complets): python3 -m tools.deezer_latest_liked --force-auth
- verifier application_domain dans .env

Permission insuffisante pour suppression de playlists:

- relancer l'auth avec --force-auth
- verifier que le script demande bien: basic_access, manage_library, delete_library, offline_access

Erreur pydub ou lecture MP3:

- verifier que ffmpeg est installe et accessible

Pas assez de tracks pour clustering:

- verifier que final_dataset.json contient des preview_features
- si besoin, relancer build-dataset puis build-playlists

## 9) Workflow mensuel (manuel)

Ce projet est volontairement opere manuellement chaque mois.

1. Update dataset:

```bash
python3 deezer_pipeline.py update-dataset
```

2. Regenerer playlists du mois:

```bash
python3 deezer_pipeline.py build-playlists --month YYYY-MM
```

3. Publier dans Deezer:

```bash
python3 deezer_pipeline.py publish-playlists --input monthly_playlists.json
```

4. Nettoyer les anciennes playlists du mois:

```bash
python3 deezer_pipeline.py cleanup-playlists --input monthly_playlists.json
```
