# Guide de l'application — suivi des achats et des repas de la cantine

> **Dernière mise à jour : 14 novembre 2026.**
> Version texte du guide. La présentation en diapositives avec captures d'écran est
> [`guide-application.pdf`](guide-application.pdf) : elle est régénérée automatiquement par
> `python docs/generer_guide.py` (l'application est lancée sur des données de démonstration puis photographiée).
> Les changements survenus depuis la première présentation (22 octobre 2026) sont listés en fin de document.
> Règle de maintenance : toute modification visible par l'utilisateur met à jour ce fichier dans le même commit
> (voir `CLAUDE.md` ; un test vérifie que chaque page, chaque carte de Paramètres et chaque outil de l'assistant y figurent).

## À quoi sert l'application ?

**Centraliser le quotidien de la cantine** : fournisseurs (contacts, livraisons, catégories), produits et prix
(catalogue, labels, historique), réceptions (bons de livraison et factures), repas et recettes (menus, convives, coûts),
stocks et statistiques (soldes, achats, engagements).

**Et automatiser** : lecture des bons de livraison PDF (y compris pages scannées par OCR), suivi des prix, calcul du
coût matières par repas et par convive, bilan des indicateurs du marché, export vers Dolibarr (4 fichiers CSV), assistant IA.

## Les pages

| Page | Contenu |
|---|---|
| **Statistiques** | Achats, indicateurs du marché (bilan CRT), coût par repas |
| **Réceptions** | Bons de livraison et factures : import PDF ou saisie |
| **Fournisseurs** | Contacts, jours de livraison, catégories vendues |
| **Produits** | Catalogue complet : prix, labels, fiches techniques |
| **Stocks** | Entrées, sorties, solde par produit |
| **Recettes** | Ingrédients et grammages GEMRCN |
| **Repas** | Menu, estimation des coûts, liste de courses et bilan |
| **Grammages** | Grammages de la cantine pour calculer les quantités |
| **Paramètres** | Utilisateurs, réglages, assistant, sauvegarde, exports |

Un bouton **💬 Assistant** (en bas à droite de toutes les pages) ouvre le chat de l'assistant IA.

## Connexion et profils

Paramètres > Utilisateurs. Quatre profils :

- **Administrateur** : tous les droits, gère les utilisateurs et les paramètres ;
- **Lecture et écriture** : mêmes droits, sauf la modification des paramètres ;
- **Lecture seule** : consulte tout sans rien modifier ;
- **Statistiques** : accès aux seules pages Statistiques et Grammages, sans aucun prix (retirés côté serveur).

## Fournisseurs

- **Liste** : nom, contact, jours de livraison, franco, prise de commande (internet avec lien direct, téléphone, e-mail),
  catégories vendues, nombre de produits et de réceptions.
- **Fiche** : contact (nom, téléphone, e-mail, SIRET, adresse), livraison (jours, franco = montant minimum),
  prise de commande, catalogue (catégories vendues, provenance par défaut de ses produits, direct producteur).
- **Avancé** : mots-clés de reconnaissance dans les PDF (séparés par « ; », ex. `capmaree; cap maree`) et expression
  régulière de lecture propre au fournisseur. Un fournisseur bien renseigné = des bons de livraison lus plus fiablement.
- Les factures établies au nom d'une personne sont reconnues par un mot-clé de l'en-tête (ex. « Chloé Simon » est
  rattachée à la Ferme de la Morissais).

## Produits

- **Fiche** : référence, nom, fournisseur ; catégorie (fruits, légumes, viandes, pêche…) et gamme (1 frais et brut à
  6 déshydratés) ; label EGalim (bio, autre label, sans) et détail du label (AOP, Label Rouge, MSC…) ; provenance
  (de CC Nozay à l'international) ; direct producteur ; commerce équitable ; unité de prix et prix unitaire HT ;
  favori ★ ou à éviter (orange) ; fiche technique (PDF, image) ; notes.
- Toute fiche s'ouvre en consultation : « Modifier » la déverrouille.
- **Historique des prix** : graphique et tableau (date, prix HT, réception d'origine). Le prix de la fiche est mis à
  jour à l'enregistrement d'une réception : jamais saisi deux fois.
- **Fiche technique** : liée à chaque produit, consultable dans une visionneuse, repérée par une icône dans la liste.
- **Liste** : recherche (nom, référence, fournisseur), filtres (catégorie dont « À compléter », fournisseur, favoris),
  tri par colonne, favori en un clic (étoile).

## Réceptions

- **Importer des PDF** : un ou plusieurs à la fois. Lecture automatique (tableaux, profils de fournisseurs connus, OCR
  pour une page scannée) ; rattachement des lignes aux produits par référence (sinon création en un clic) ; vérification
  puis enregistrement, avec avertissements en couleur. Un PDF peut contenir plusieurs bons : ils sont présentés l'un
  après l'autre.
- **Bon de livraison** : provisoire, les quantités sont comptées. **Facture** : définitive, elle remplace les bons
  correspondants (même référence, même total, période proche ; « Bon de livraison concerné : n° … » est repris).
- **Aucun double comptage** : une facture déjà enregistrée n'est pas importée deux fois.
- Chaque réception garde son **PDF d'origine**, consultable en un clic ; les libellés lus n'incluent pas la ligne
  « Origine : … » des factures de fermes.
- **Saisie manuelle** : bon sans PDF, ligne par ligne (référence, produit rattaché, nom, quantité, unité, prix HT,
  total). Le prix du produit est actualisé à l'enregistrement. Une réception saisie par erreur peut être supprimée.
- **Exporter…** : une période en CSV ou Excel (une ligne par produit reçu, avec les indicateurs) et l'archive des PDF.

## Recettes

Catégorie (de l'entrée au dessert) et convives de référence ; ingrédient principal (intitulé grammage GEMRCN) ;
quantités à servir et à commander calculées, coût estimé ; dates de service ; liées aux repas (menu, liste de courses).

## Repas

- **Suivi** : date, statut (prévu, en cours, passé), convives (maternelles, élémentaires, adultes), coût matières total
  et par convive, % local et % bio par repas. Un repas modifié est surligné en orange. **Liste de courses PDF**.
- **Importer le menu depuis un PDF** (bouton « Importer PDF menu ») : repas détectés (date, entrée, plat,
  accompagnement, laitage, dessert) à cocher ; les repas existants sont grisés ; on importe en général mois par mois.
- **Du menu à la commande** : 1) *Menu* (chaque poste relié à une recette) ; 2) *Estimation des coûts* avant le repas
  (quantités calculées depuis les grammages, liste de courses) ; 3) *Bilan* après le repas (quantités réellement
  sorties, coût réel, case « Finalisé », observations).

## Grammages GEMRCN

Grammages adaptés à la cantine, affichés à côté des recommandations GEMRCN (tolérance ± 10 %) ; servent à calculer les
quantités à servir et à commander. Convives (maternelles, élémentaires, adultes), coefficient cru/cuit ; quatre onglets :
entrées, plats + accompagnements, fromages, desserts + laitages.

## Stocks

Aucune saisie : le stock se calcule à partir des réceptions (entrées) et des repas (sorties). Solde par produit avec
sa valeur ; filtre « Masquer les stocks à zéro ». **Inventaire** : on saisit la quantité réellement présente, l'écart
est enregistré en ajustement (motif facultatif).

## Statistiques

La période Du / Au s'applique à toute la page.

- **Chiffres clés** : achats HT, prix par repas (coûts matières ÷ convives), repas et convives, % bio, % EGalim,
  % local, % direct producteur.
- **Bilan des indicateurs du marché (CRT)**, calculé sur la période choisie (sans cumul) et comparé aux engagements
  du CRT, fixés dans l'application (non paramétrables) avec un badge **Respecté / Non respecté** :
  synthèse de la période ; labels ; bio et EGalim par famille ; origine des approvisionnements (France, local, zones) ;
  origine par famille et par zone (avec l'objectif du CRT sous chaque valeur) ; qualité par catégorie (origine France,
  MSC pour le poisson) ; approvisionnement direct de producteurs (engagements au 1er septembre 2025 puis 2026) ;
  produits frais par catégorie ; répartition par gamme ; évolution mois par mois.
- **Répartitions** par label, provenance, gamme, catégorie et fournisseur ; **coût matières par repas** (graphique et
  tableau).
- **Exporter en PDF** : la page complète, prête à distribuer (mairie, C.G.R.S.), bilan CRT compris.
- Valeurs d'engagement (CRT) : bio 85 % toutes denrées, 100 % hors produits de la mer, par famille 95/100/90/80/75/60/100 ;
  EGalim 90 %, par famille 95/100/100/90/100/70/100 ; local 80 % ; direct 75 % (55 % avant le 1er septembre 2026) ;
  frais 82 % ; 1re gamme 90 % hors épicerie. Un changement de marché se fait dans `cgrs/services/bilan_periode.py`.
- Le profil « Statistiques » voit tous les pourcentages mais aucun montant.

## Assistant IA

Chat en langage naturel (💬 Assistant), qui consulte les données et peut en créer ou en modifier. **Toute écriture demande
la validation de l'utilisateur** dans le chat, et l'assistant n'a jamais plus de droits que lui.

**Outils de consultation**

| Outil | Rôle |
|---|---|
| `rechercher_produits` | Produits par nom, référence ou fournisseur, avec filtres catégorie, provenance (« sans origine » inclus), label, gamme, direct |
| `lister_fournisseurs` | Fournisseurs et leurs fiches |
| `consulter_stock` | Stock par produit |
| `lister_recettes`, `voir_recette` | Recettes |
| `lister_repas`, `voir_repas` | Repas |
| `lister_receptions`, `voir_reception` | Réceptions |
| `statistiques` | Chiffres clés d'une période |
| `comparer_fournisseurs`, `achats_par_fournisseur`, `achats_par_produit` | Répartition des achats (par produit avec les mêmes filtres) |
| `historique_prix` | Évolution du prix d'un produit |
| `engagements_egalim` | Engagements du marché |
| `prevoir_besoins` | Besoins d'achat prévisionnels |
| `bilan_mensuel` | Bilan d'un mois avec cumul depuis le 1er septembre (rubriques labels, origine, zones, gammes…) |
| `produits_en_defaut` | Pour chaque indicateur non respecté, les produits qui pèsent le plus dans l'écart |
| `simuler_remplacement` | Effet, sur les indicateurs, du remplacement de produits (par un autre produit réel, au prix réel et à un autre volume) |
| `reperer_anomalies` | Incohérences dans les données |
| `journal_actions` | Historique des actions |

**Outils d'écriture** (avec validation) : `creer_fournisseur`, `modifier_fournisseur`, `creer_produit`, `modifier_produit`,
`creer_recette`, `modifier_recette`, `creer_repas`, `modifier_repas`, `saisir_sorties_repas`, `creer_reception`,
`modifier_reception`, `ajuster_stock`.

**Branchement** (Paramètres > Assistant IA, administrateur) : Google Gemini, Mistral, Groq (clé API gratuite) ou Ollama
(modèle local, sans clé, hors ligne). Recherche des modèles disponibles, mode « Automatique ». Les mêmes outils sont
proposés à un client MCP externe (`/mcp`) avec un jeton en lecture seule ou en lecture et écriture.

Exemples : « quels sont les fruits sans origine ? », « répartition en valeur d'achat des légumes d'origine UE »,
« quels produits nous mettent en défaut sur le direct en octobre ? », « et si on remplaçait les frites par 100 kg de
pommes de terre à la place de 80 kg ? ».

## Paramètres

- **Personnalisation** : nom, sous-titre et logo de la cantine (en-tête, connexion, PDF).
- **Utilisateurs** : comptes et profils.
- **Convives par défaut** : maternelles, élémentaires, adultes, proposés pour les nouveaux repas, recettes et la page
  Grammages.
- **Noms de la cantine sur les documents** : plusieurs noms séparés par « ; » ; l'import PDF ne les prend jamais pour
  un fournisseur.
- **Tarif de vente d'un repas** : sert au déficit du bilan.
- **Direct producteur** : case « Compter les produits locaux de Manger Bio comme du direct producteur » (provenance
  locale, fournisseur dont le nom contient « Manger Bio » ; s'applique aux statistiques, au bilan et à l'assistant sans
  modifier les fiches produits).
- **Export Dolibarr** : 4 fichiers CSV (séparateur « ; », UTF-8) à importer dans l'ordre : fournisseurs, produits,
  réceptions (commandes fournisseurs), repas (commandes clients).
- **Sauvegarde** : tout sauvegarder (base, PDF importés, fiches techniques) ou restaurer ; l'archive contient des
  mots de passe chiffrés, à conserver en lieu sûr. **À faire régulièrement : c'est la seule protection contre la perte
  de données** (une sauvegarde automatique quotidienne est aussi conservée sur le serveur).
- **Assistant IA** (dernière carte) : fournisseur, clé, modèle, jetons MCP.

L'historique des actions n'est plus affiché : il est enregistré dans le journal technique `logs/cgrs.log` (et reste
consultable par l'assistant, outil `journal_actions`).

## Bon à savoir

- Tout est centralisé : fournisseurs, produits, réceptions, repas, stocks et statistiques au même endroit.
- Les prix, stocks et coûts se calculent tout seuls ; le prix n'est saisi qu'une fois (réception).
- Toute fiche s'ouvre en lecture : « Modifier » pour déverrouiller.
- Chaque réception garde son document source.

## Évolutions depuis la présentation (22 octobre 2026)

- **Statistiques** : le bloc « Engagements du marché » (paramétrable) est remplacé par le bilan des indicateurs du CRT sur
  la période, avec badges Respecté / Non respecté ; le PDF d'export reprend ce bilan. Le paramétrage des engagements a
  disparu de Paramètres (valeurs fixées d'après le CRT).
- **Paramètres** : ajout du tarif de vente d'un repas et de la case Manger Bio direct producteur ; l'historique des
  actions passe dans `logs/cgrs.log` ; l'Assistant IA est la dernière carte.
- **Assistant IA** (nouveau) : chat, outils de consultation et d'écriture, bilan mensuel, produits en défaut,
  simulation de remplacement, Gemini / Mistral / Groq / Ollama, serveur MCP.
- **Import PDF** : factures de ferme (libellés sans la ligne « Origine », bon de livraison concerné), fournisseur
  « Chloé Simon » = Ferme de la Morissais.
