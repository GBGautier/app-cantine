"""Constantes métier : provenances, gammes, catégories, jours, profils."""


PROVENANCES = {
    "cc_nozay": "CC Nozay",
    "loire_atlantique": "Loire-Atlantique",
    "pays_loire": "Pays de la Loire et limitrophes",
    "france": "France",
    "ue": "Union européenne",
    "international": "International",
}
LOCAL = ("cc_nozay", "loire_atlantique", "pays_loire")
GAMMES = {
    "1": "1 - frais et brut",
    "2": "2 - conserves",
    "3": "3 - surgelés",
    "4": "4 - cru prêt à l'emploi",
    "5": "5 - cuit sous vide",
    "6": "6 - déshydratés ou lyophilisés",
}
CATEGORIES = [
    "Fruits: pommes, poires, kiwis", "Fruits: autres", "Légumes", "Viande de porc", "Viande de volaille", "Viande de boeuf",
    "Produits de la pêche", "Produits laitiers", "Ovoproduits", "Épicerie: légumineuses", "Épicerie: céréales", "Épicerie: autre", "Pain", "Autre",
]
DAYS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
ORDER_METHODS = {"internet": "Internet", "telephone": "Téléphone", "email": "E-mail", "autre": "Autre"}
ROLES = {
    "admin": "Administrateur (tous les droits)",
    "editor": "Lecture et modification",
    "reader": "Lecture seule",
    "stats": "Statistiques uniquement",
}
KINDS = ("livraison", "facture")
