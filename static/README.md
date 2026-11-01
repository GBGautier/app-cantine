# Interface (navigateur)

Page unique, sans outil de construction : `index.html` charge des scripts classiques (pas de modules) qui partagent
la même portée globale, **dans l'ordre ci-dessous** (un fichier peut appeler ce que définissent les fichiers chargés
avant lui au moment de son chargement ; les fonctions ne s'appellent entre elles qu'une fois la page démarrée).

| Fichier | Contenu |
|---|---|
| `css/app.css` | Styles |
| `js/base.js` | Outils de base (`$`, `h()`, `api()`, état global) |
| `js/composants.js` | Fenêtres (`modal`), champs (`field`), sélecteurs, notifications |
| `js/identification.js` | Connexion / création du premier compte |
| `js/export-pdf-statistiques.js` | Export PDF des statistiques |
| `js/statistiques.js`, `fournisseurs.js`, `produits.js`, `receptions.js`, `repas.js`, `recettes.js`, `stocks.js`, `parametres.js` | Une page chacune (avec ses formulaires) |
| `js/grammages-donnees.js`, `grammages.js` | Table des grammages recommandés ; page Grammages |
| `js/navigation.js` | Menu, affichage de la page demandée |
| `js/demarrage.js` | `boot()` : doit rester **le dernier** des scripts de l'application |
| `js/visionneuse-pdf.js` | Visionneuse de PDF (chargée après la fenêtre qu'elle pilote) |
| `vendor/` | Bibliothèques tierces embarquées (jsPDF) : voir `vendor/README.md` |

Le logo (`img/logo.png`, `img/favicon.png` ; `img/logo-complet*.png` pour l'écran de connexion, variante claire et sombre) sert dans l'en-tête et comme icône de l'onglet ; `windows/cgrs.ico` est l'icône de l'exécutable.

Le navigateur revalide ces fichiers à chaque ouverture (`Cache-Control: no-cache`) : après une mise à jour, on ne
retrouve jamais un mélange d'anciens et de nouveaux fichiers.
