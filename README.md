# CGRS – réceptions & stocks

Lancement (Python 3.12 ou 3.13) :

    pip install -r requirements.txt
    python -m uvicorn app:app --port 8000

Puis ouvrir http://localhost:8000

## Première utilisation
Le premier écran demande de créer le compte administrateur. Ensuite, Paramètres > Utilisateurs permet d'ajouter :
- **Administrateur** : tous les droits ;
- **Lecture seule** : consulte tout, ne modifie rien ;
- **Statistiques** : uniquement la page Statistiques, sans aucun prix (les prix sont retirés côté serveur).

Si l'application est accessible depuis le réseau, créez le compte administrateur tout de suite.

## Données
- `cantine.db` (SQLite) : toutes les données ; `uploads/` : PDF importés et fiches techniques.
- Paramètres > Sauvegarde télécharge tout dans une archive .zip (restauration : remplacer `cantine.db` et `uploads/`).

## Import de PDF
Les PDF scannés sont lus par OCR si `tesseract` est installé (avec le français) :
`sudo apt install tesseract-ocr tesseract-ocr-fra` (Debian/Ubuntu) ou `brew install tesseract tesseract-lang` (macOS).
Les montants lus par OCR sont à vérifier ; l'app avertit si la somme des lignes ne correspond pas au total HT.
Fournisseur au format particulier : renseigner une regex (groupes `code`, `label`, `qty`, `unit`, `unit_price`, `total`) sur sa fiche.


wXetK8tTvaSRgnS