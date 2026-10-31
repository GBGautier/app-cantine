# Déploiement et exploitation

## Où sont les données ?

| Quoi | Où |
|---|---|
| Base de données | `cantine.db` |
| PDF et fiches techniques | `uploads/` |
| Sauvegardes automatiques | `sauvegardes-auto/` (`auto-AAAAMMJJ-HHMMSS.db`) |
| Journal technique | `logs/cgrs.log` (5 fichiers de 1 Mo maximum) |

Avec l'exécutable Windows, ces dossiers sont dans `%LOCALAPPDATA%\CGRS\` ; sinon à côté du code.

## Application de bureau Windows

**Exécutable (recommandé)** : double-cliquez sur `construire_exe.bat` (Python 3.12 ou 3.13 requis, une seule fois, sur
un poste de construction). Il produit `dist\CGRS.exe`, un fichier unique à copier sur n'importe quel poste Windows,
sans installer Python. Au lancement, une fenêtre s'ouvre sur l'application. Le poste doit avoir Microsoft Edge WebView2
(déjà présent sur Windows 10/11 à jour).

Les données de l'exécutable sont dans `%LOCALAPPDATA%\CGRS\` (base, `uploads\`, `sauvegardes-auto\`, `logs\`) :
mettre à jour l'exécutable ne touche pas aux données. Si l'exécutable ne démarre pas, lisez `logs\cgrs.log`.

**Sans exécutable** : `lancer.bat` crée un environnement Python au premier lancement, puis ouvre l'application dans le
navigateur (données à côté du code).

Dans les deux cas, les sauvegardes automatiques tournent dès le lancement (une copie par jour, 14 conservées).
**Copiez régulièrement `sauvegardes-auto\` et `uploads\` hors de l'ordinateur** (clé USB, disque réseau) : une
sauvegarde sur le même disque ne protège pas d'une panne du disque.

## Serveur accessible depuis Internet

L'application n'a pas de HTTPS propre : placez-la **derrière un proxy HTTPS** (Caddy, nginx, IIS/ARR…) et ne
l'exposez jamais directement.

```
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
```

- `--proxy-headers --forwarded-allow-ips=<IP du proxy>` : indispensable pour que la limitation des tentatives de
  connexion voie l'adresse du visiteur (et non celle du proxy) et que le cookie de session soit « Secure ».
- Exemple Caddy (HTTPS automatique) : `cantine.exemple.fr { reverse_proxy 127.0.0.1:8000 }`

Variables d'environnement (toutes facultatives ; sans elles, comportement d'origine) :

| Variable | Défaut | Effet |
|---|---|---|
| `CGRS_DOCS` | `1` | `0` masque `/docs`, `/redoc`, `/openapi.json` (recommandé sur Internet) |
| `CGRS_HSTS` | `0` | `1` ajoute `Strict-Transport-Security` (HTTPS uniquement) |
| `CGRS_SECURE_COOKIES` | `0` | `1` force le cookie de session « Secure » |
| `CGRS_BACKUP_INTERVAL_HOURS` | `24` | Intervalle des sauvegardes automatiques ; `0` les désactive |
| `CGRS_BACKUP_KEEP` | `14` | Nombre de sauvegardes automatiques conservées |

Recommandation Internet : `CGRS_DOCS=0 CGRS_HSTS=1 CGRS_SECURE_COOKIES=1`, mot de passe administrateur long,
un seul processus uvicorn (base SQLite).

## Sauvegarde et restauration

- Automatique : base seule (cohérente, à chaud). Les PDF ne changent jamais une fois enregistrés : copiez `uploads/`.
- Complète : bouton « Sauvegarder toutes les données » (base + PDF, archive .zip).
- Restauration : bouton de l'interface (une copie `avant-restauration-…` de l'état actuel est conservée),
  ou manuellement : arrêter l'application, remplacer `cantine.db` par une copie `auto-….db`, relancer.

## En cas de problème

Un message « Erreur interne du serveur. Référence à communiquer : xxxxxxxx » : cherchez cette référence dans
`logs/cgrs.log`, la trace complète s'y trouve. Les connexions refusées y sont aussi notées (identifiant et adresse).

## Tests

```
pip install -r requirements.txt -r requirements-dev.txt
pytest
ruff check .
```

La configuration de `pytest` et de `ruff` est dans `pyproject.toml`.
