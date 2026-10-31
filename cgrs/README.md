# Package `cgrs`

Découpage de l'ancien `app.py` (1915 lignes) en modules. **Le code a été déplacé, pas réécrit** : chaque ligne de
l'ancien fichier se retrouve à l'identique ici (seuls changent les imports, `@app.get` → `@router.get`, et l'assemblage
dans `application.py`).

`uvicorn app:app` et `from app import app` (main.py, lancer.bat) continuent de fonctionner : `app.py` à la racine
se contente d'importer l'application assemblée ici.

| Module | Contenu |
|---|---|
| `application.py` | Création de l'application, en-têtes de sécurité, enregistrement des routes, amorçage des données par défaut, fichiers statiques |
| `config.py` | Chemins : dossier statique, dossier des fichiers envoyés (`paths.py` à la racine reste la source) |
| `constants.py` | Provenances, gammes, catégories, jours, profils |
| `security.py` | Mots de passe, sessions, profils et droits (`READ`, `EDIT`, `ADMIN`, `ANY`), limitation des tentatives |
| `utils.py` | Horodatage, journal d'actions, conversion d'unités, lecture/écriture SQL générique |
| `uploads.py` | Enregistrement des fichiers envoyés (PDF, fiches techniques) |
| `pricing.py` | Historique des prix des produits |
| `routes/auth.py`, `users.py` | Connexion, premier compte, mot de passe ; gestion des utilisateurs |
| `routes/suppliers.py`, `products.py` | Fournisseurs ; produits, fiches techniques, prix |
| `routes/orders.py` | Réceptions (bons de livraison, factures), import de PDF, rapprochement |
| `routes/recipes.py`, `meals.py` | Recettes ; repas, coûts matières, liste de courses, import de menus |
| `routes/stock.py`, `stats.py` | Stocks et inventaires ; statistiques |
| `routes/settings.py`, `convives.py`, `grammages.py`, `commitments.py`, `meta.py` | Paramètres, effectifs par défaut, grammages, engagements, métadonnées du frontend |
| `routes/backup.py`, `export.py`, `files.py`, `action_log.py` | Sauvegarde / restauration ; exports Dolibarr ; fichiers ; journal |

Ce qui reste à la racine, inchangé : `db.py`, `paths.py`, `pdf_parser.py`, `menu_parser.py`, `dolibarr.py`, `main.py`,
`static/`, `lancer.bat`, `requirements.txt` (déplacer ces fichiers pourrait casser un exécutable déjà construit).

Ajouts du durcissement : `errors.py` (erreurs de base de données → réponses claires, erreurs internes avec référence),
`journal.py` (journal fichier), `autobackup.py` (sauvegardes automatiques). Voir `docs/DEPLOIEMENT.md`.
