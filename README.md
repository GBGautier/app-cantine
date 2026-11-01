# Gestion de cantine – réceptions & stocks

Application de gestion des réceptions (bons de livraison, factures), des stocks, des recettes et des repas de la
cantine : fournisseurs, produits et prix, import de PDF, coût des repas, statistiques (Egalim), exports.
Serveur FastAPI + base SQLite, interface web servie par l'application elle-même (aucun accès à Internet nécessaire).

## Lancer l'application

Python 3.12 ou 3.13 est nécessaire (sauf pour l'exécutable).

**Windows, sans rien taper** : double-cliquez sur `windows\lancer.bat`. Au premier lancement il crée l'environnement
Python et installe les dépendances (quelques minutes, une seule fois), puis ouvre l'application dans le navigateur.
Fermez la fenêtre noire pour arrêter l'application.

**En ligne de commande (tous systèmes)** :

```
pip install -r requirements.txt
python -m uvicorn app:app --port 8000
```

Puis ouvrez <http://localhost:8000>.

**Exécutable Windows (facultatif)** : `windows\construire_exe.bat` produit `dist\CGRS.exe` (fenêtre de bureau, sans Python
sur le poste). Il n'est pas signé : selon la configuration, Windows peut le bloquer (« l'éditeur ne peut pas être
vérifié », Smart App Control). Dans ce cas, utilisez `windows\lancer.bat`. Détails dans `docs/DEPLOIEMENT.md`.

## Première utilisation

Le premier écran demande de créer le compte administrateur. Ensuite, Paramètres > Utilisateurs permet d'ajouter :

- **Administrateur** : tous les droits ;
- **Lecture seule** : consulte tout, ne modifie rien ;
- **Statistiques** : uniquement la page Statistiques, sans aucun prix (les prix sont retirés côté serveur).

Si l'application est accessible depuis le réseau, créez le compte administrateur tout de suite.

## Personnaliser (nom, logo)

Paramètres > **Personnalisation** : nom et sous-titre de votre cantine, et logo (PNG, JPEG ou WebP, 512 Ko maximum).
Ils apparaissent dans l'en-tête, sur l'écran de connexion, dans l'onglet du navigateur, dans le titre de la fenêtre de
bureau et sur les PDF. Le nom est aussi pris en compte par l'import de PDF (jamais pris pour un fournisseur). Le logo est
enregistré dans la base : il suit les sauvegardes. Sans personnalisation, l'application s'appelle « Cantine ».

L'icône de `CGRS.exe` est fixée à la construction : remplacez `windows\cgrs.ico` avant `construire_exe.bat` pour
une autre icône. Les noms techniques (dossier `%LOCALAPPDATA%\CGRS`, `CGRS.exe`, variables `CGRS_*`) ne changent pas.

## Données et sauvegardes

| Quoi | Où |
|---|---|
| Base de données (SQLite) | `cantine.db` |
| PDF importés et fiches techniques | `uploads/` |
| Sauvegardes automatiques (une par jour, 14 conservées) | `sauvegardes-auto/` |
| Journal technique | `logs/cgrs.log` |

Avec l'exécutable, ces dossiers sont dans `%LOCALAPPDATA%\CGRS\` ; sinon à côté du code.

- Paramètres > Sauvegarde télécharge tout (base + PDF) dans une archive .zip ; la restauration se fait depuis la même page.
- **Copiez régulièrement `sauvegardes-auto/` et `uploads/` hors de l'ordinateur** (clé USB, disque réseau) : une sauvegarde
  sur le même disque ne protège pas d'une panne du disque.
- Ne publiez jamais de données réelles (base, PDF de fournisseurs) dans un dépôt public : `cantine.db`, `uploads/`, `logs/`
  et `sauvegardes-auto/` sont exclus par `.gitignore`, mais pas les PDF rangés ailleurs.

## Import de PDF

Les bons de livraison, bons de commande et factures PDF sont lus automatiquement, puis présentés pour vérification avant
enregistrement. Les PDF scannés sont lus par OCR si `tesseract` est installé (avec le français) :
`sudo apt install tesseract-ocr tesseract-ocr-fra` (Debian/Ubuntu) ou `brew install tesseract tesseract-lang` (macOS).
Les montants lus par OCR sont à vérifier ; l'application avertit si la somme des lignes ne correspond pas au total HT.
Fournisseur au format particulier : renseignez une expression régulière (groupes `code`, `label`, `qty`, `unit`,
`unit_price`, `total`) sur sa fiche.

## Pour les développeurs

```
pip install -r requirements.txt
pip install -r requirements/dev.txt     # séparément : requirements.txt impose les empreintes
pytest --ignore=tests/ui                # tests de l'API et des règles de calcul (rapides)
playwright install chromium && pytest tests/ui   # tests d'interface dans un vrai navigateur
ruff check . && ruff format --check .
```

| Dossier / fichier | Contenu |
|---|---|
| `app.py`, `main.py` | Point d'entrée du serveur (`uvicorn app:app`) ; application de bureau (fenêtre Windows) |
| `cgrs/` | Le code : routes, règles de calcul (`services/`), lecture des PDF (`parsers/`), base, sécurité. Voir `cgrs/README.md` |
| `static/` | Interface (HTML, CSS, JavaScript) ; bibliothèques embarquées dans `static/vendor/`. Voir `static/README.md` |
| `tests/` | Tests unitaires et d'API ; `tests/ui/` : tests d'interface (Playwright) |
| `windows/` | Lanceur, construction de l'exécutable, icône |
| `requirements/`, `requirements.txt` | Dépendances (versions et empreintes figées : ne pas modifier `requirements.txt` à la main) |
| `docs/DEPLOIEMENT.md` | Exploitation : hébergement sur Internet, options, sauvegarde, dépannage, mise à jour des dépendances |

L'intégration continue (GitHub Actions) lance ces contrôles sous Windows et Linux, avec Python 3.12 et 3.13.

## Licence

MIT, voir `LICENSE`.
