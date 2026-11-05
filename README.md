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

**Exécutable Windows (facultatif)** : `windows\construire_exe.bat` produit `dist\Cantine.exe` (fenêtre de bureau, sans Python
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

L'icône de `Cantine.exe` est fixée à la construction : remplacez `windows\cgrs.ico` avant `construire_exe.bat` pour
une autre icône. Les noms techniques (dossier `%LOCALAPPDATA%\Cantine`, `Cantine.exe`, variables `CGRS_*`) ne changent pas.

## Données et sauvegardes

| Quoi | Où |
|---|---|
| Base de données (SQLite) | `cantine.db` |
| PDF importés et fiches techniques | `uploads/` |
| Sauvegardes automatiques (une par jour, 14 conservées) | `sauvegardes-auto/` |
| Journal technique | `logs/cgrs.log` |

Avec l'exécutable, ces dossiers sont dans `%LOCALAPPDATA%\Cantine\` ; sinon à côté du code.

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

## Assistant IA

Le bouton **💬 Assistant** (en bas à droite) ouvre un chat qui comprend vos demandes : « crée une recette de gratin de
courgettes pour 120 convives », « quel est le stock de carottes ? », « quel est le prix par repas ce mois-ci ? ». Il
consulte les produits, fournisseurs, stocks, recettes, repas, réceptions et statistiques, et peut créer des recettes, des
repas, des sorties de produits, des produits, des fournisseurs et des réceptions. **Chaque création demande votre
validation** dans le chat, et l'assistant n'a jamais plus de droits que vous (un profil « lecture seule » ne peut rien créer).

**Branchement (administrateur)** : Paramètres > **Assistant IA** : choisissez Google Gemini, Mistral ou Groq, collez une
clé API gratuite (le lien est dans la page) et enregistrez. Les quotas gratuits sont limités : l'assistant l'indique s'ils
sont dépassés. La page cherche les modèles disponibles avec votre clé (bouton « ↻ Chercher ») et propose le plus adapté ; en mode « Automatique », l'assistant prend le recommandé, et un fournisseur qui retire un modèle ne le casse donc pas. La clé est enregistrée sur le serveur
(donc dans les sauvegardes : ne publiez jamais une sauvegarde) et n'est jamais affichée ni journalisée. Les données
envoyées au fournisseur sont celles que l'assistant consulte pour répondre.

**Modèle local avec Ollama (gratuit, sans clé, hors ligne)** : installez [Ollama](https://ollama.com/download) sur la machine
qui fait tourner l'application, puis téléchargez un modèle qui sait appeler des outils, par exemple
`ollama pull qwen2.5:7b` (ou `llama3.1`). Dans Paramètres > Assistant IA, choisissez **Ollama (local)** : aucune clé à saisir,
le bouton « ↻ Chercher » liste vos modèles. Les données ne quittent pas la machine. Un modèle local est plus lent et moins
fiable que les modèles en ligne (prévoir 8 Go de mémoire ou plus ; sans carte graphique, une réponse peut prendre
une minute). Si Ollama tourne sur une autre machine, indiquez son adresse au lancement de l'application :
`CGRS_ASSISTANT_URL=http://adresse:11434/v1/chat/completions`. Attention : « local » est vu depuis le serveur de l'application, pas
depuis votre navigateur.

**Serveur MCP** : les mêmes outils sont proposés à un client MCP externe (par exemple Claude Desktop) à l'adresse
`http://localhost:8000/mcp` (Streamable HTTP). Créez un jeton dans Paramètres > Assistant IA (lecture seule, ou lecture et
écriture) : il n'est affiché qu'une fois, avec un exemple de configuration. Le jeton est une clé d'accès : un jeton « lecture
et écriture » donne le droit de créer des données. Un connecteur qui n'accepte que OAuth n'est pas pris en charge.

## Export d'une période

Réceptions > **Exporter…** : choisissez les dates (par défaut le mois précédent) et le type (factures, bons de livraison
ou les deux), puis téléchargez :

- **le fichier des lignes**, au format **CSV** ou **Excel (.xlsx)** au choix : une ligne par produit reçu, avec la réception (date, type, référence, fournisseur), le produit
  (catégorie, gamme), la quantité, le prix et le montant HT, et les indicateurs : label Egalim, provenance, et
  oui/non pour bio, Egalim, local, direct producteur, commerce équitable (mêmes définitions que les statistiques). CSV : séparateur
  « ; », virgule décimale, il s'ouvre directement dans Excel. Excel : vraies dates et vrais nombres, en-tête figé avec filtres ;
- **l'archive des PDF** : les PDF d'origine, un fichier par document, nommés `date_fournisseur_référence.pdf`.

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
