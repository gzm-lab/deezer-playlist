# Deezer Music Analysis Pipeline

Repo pour :

- construire un dataset enrichi à partir de Deezer
- préparer des vecteurs de clustering
- générer des playlists mensuelles cohérentes et rotatives

## Ce qu'il faut lancer

Tu n'as pas besoin de choisir parmi 10 scripts.
Le point d'entrée normal du repo est :

```bash
python3 deezer_pipeline.py <commande>
```

### Commandes utiles

Reconstruire le dataset complet :

```bash
python3 deezer_pipeline.py build-dataset
```

Reconstruire le dataset sans réexporter Deezer :

```bash
python3 deezer_pipeline.py build-dataset --skip-export
```

Mettre à jour le dataset après de nouveaux likes :

```bash
python3 deezer_pipeline.py update-dataset
```

Construire les clusters et playlists du mois :

```bash
python3 deezer_pipeline.py build-playlists --month 2026-04
```

Tout faire d'un coup :

```bash
python3 deezer_pipeline.py build-all --month 2026-04
```

## Installation

Créer un fichier `.env` :

```bash
application_id=YOUR_DEEZER_APP_ID
secret_key=YOUR_DEEZER_SECRET
application_domain=http://localhost:8080/callback
MB_USER_AGENT=DeezerMoodCluster/0.1 (contact: your@email.com)
```

Installer les dépendances :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`pydub` nécessite `ffmpeg` installé sur la machine.

## Workflow interne

Les scripts bas niveau restent dans le repo, mais ils ne sont plus l'interface principale :

- `tools/export_coup_de_coeur.py`
- `tools/musicbrainz_enrich.py`
- `tools/acousticbrainz_enrich.py`
- `tools/full_preview_analysis.py`
- `tools/merge_all_features.py`
- `tools/update_dataset.py`
- `tools/prepare_clustering_features.py`
- `tools/cluster_tracks.py`
- `tools/generate_monthly_playlists.py`

Leur rôle est simple : ils sont orchestrés par `deezer_pipeline.py`.

## Structure

```text
deezer/
├── deezer_pipeline.py
├── core/
│   ├── audio_features.py
│   └── deezer_api.py
└── tools/
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

La racine est volontairement minimale : un point d'entrée utilisateur, un package `core` pour la logique partagée, et un package `tools` pour les scripts opérationnels.

## Fichiers générés localement

Le repo produit localement des fichiers comme :

- `all_songs.json`
- `final_dataset.json`
- `clustering_vectors.json`
- `clusters.json`
- `monthly_playlists.json`
- `monthly_playlists_history.json`
- `previews/`
- `old/`

Ils sont ignorés par `.gitignore` pour que le repo reste propre à pousser.
