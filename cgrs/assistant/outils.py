"""Catalogue des outils de l'assistant : une seule liste, utilisée par le chat intégré et par le serveur MCP.

Chaque outil s'appuie sur les routes existantes (mêmes contrôles, même journal d'actions) ; il agit avec les droits
de la personne ou du jeton qui l'appelle. Les outils d'écriture sont repérés (`ecriture=True`) : le chat demande une
validation avant de les exécuter, et un jeton « lecture » ne peut pas les appeler.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from cgrs import db
from cgrs.constants import CATEGORIES, GAMMES, PROVENANCES
from cgrs.routes import meals as r_meals
from cgrs.routes import orders as r_orders
from cgrs.routes import products as r_products
from cgrs.routes import recipes as r_recipes
from cgrs.routes import stats as r_stats
from cgrs.routes import stock as r_stock
from cgrs.routes import suppliers as r_suppliers
from cgrs.services.stats import breakdown, fill_spend
from cgrs.utils import log_action

MAX_RESULTAT = (
    4000  # caractères renvoyés au modèle par outil (le reste est coupé) : les quotas gratuits comptent les jetons
)
CATEGORIES_RECETTE = ["entree", "plat", "accompagnement", "laitage", "dessert"]
STATUTS_REPAS = ["prevu", "en_cours", "passe"]


class ErreurOutil(Exception):
    """Erreur lisible, renvoyée au modèle (qui peut corriger sa demande) ou à l'utilisateur."""


@dataclass
class Outil:
    nom: str
    titre: str
    description: str
    schema: dict
    fonction: Callable
    ecriture: bool = False
    resume: Optional[Callable] = None  # (arguments) -> phrase de validation


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _lim(valeur, defaut, maxi):
    try:
        return max(1, min(int(valeur), maxi))
    except (TypeError, ValueError):
        return defaut


def _date(valeur, nom):
    if valeur in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valeur)).isoformat()
    except ValueError:
        raise ErreurOutil(f"{nom} : date attendue au format AAAA-MM-JJ") from None


def _appel(fn, *args):
    """Appelle une route : les erreurs HTTP / de validation deviennent des messages lisibles."""
    try:
        return fn(*args)
    except HTTPException as e:
        raise ErreurOutil(str(e.detail)) from e
    except ValidationError as e:
        raise ErreurOutil("; ".join(f"{'.'.join(map(str, x['loc']))} : {x['msg']}" for x in e.errors())) from e


def _produits():
    return db.rows(
        "SELECT p.id, p.ref, p.name, p.unit, p.unit_price, p.category, p.gamme, p.label_egalim, p.provenance, p.direct_producteur, "
        "p.supplier_id, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.name"
    )


def trouver_produit(nom):
    """Produit désigné par son nom (insensible aux accents et à la casse). Rend (produit ou None, candidats)."""
    cible, tous = _norm(nom), _produits()
    if not cible:
        return None, []
    exacts = [p for p in tous if _norm(p["name"]) == cible]
    if len(exacts) == 1:
        return exacts[0], []
    contient = [p for p in tous if cible in _norm(p["name"]) or (_norm(p["name"]) and _norm(p["name"]) in cible)]
    if len(contient) == 1 and not exacts:
        return contient[0], []
    return None, (exacts or contient)[:5]


# ------------------------------------------------------------------ lecture


def _cle_provenance(valeur):
    """« UE », « union européenne », « loire-atlantique »… -> clé de provenance (ou None si inconnue)."""
    v = _norm(valeur).replace("-", " ")
    if not v:
        return None
    if v in ("ue", "europe", "union europeenne", "europeen"):
        return "ue"
    for cle, nom in PROVENANCES.items():
        if v in (_norm(cle).replace("_", " "), _norm(nom).replace("-", " ")):
            return cle
    return next((cle for cle, nom in PROVENANCES.items() if v in _norm(nom).replace("-", " ")), None)


def _rechercher_produits(user, a):
    q = _norm(a.get("requete"))
    cat, label, gamme = _norm(a.get("categorie")), _norm(a.get("label_egalim")), str(a.get("gamme") or "")[:1]
    prov = None
    if a.get("provenance"):
        prov = _cle_provenance(a["provenance"])
        if prov is None:
            raise ErreurOutil("provenance : " + ", ".join(PROVENANCES) + " (ou « UE »).")
    direct = a.get("direct_producteur")

    def garde(p):
        return (
            (not q or all(m in " ".join(_norm(p[k]) for k in ("name", "ref", "supplier_name")) for m in q.split()))
            and (not cat or cat in _norm(p["category"]))
            and (not prov or p["provenance"] == prov)
            and (not label or label == _norm(p["label_egalim"]))
            and (not gamme or gamme == str(p["gamme"] or ""))
            and (direct is None or bool(p["direct_producteur"]) == bool(direct))
        )

    out = [
        {
            "id": p["id"],
            "nom": p["name"],
            "reference": p["ref"],
            "fournisseur": p["supplier_name"],
            "unite": p["unit"],
            "prix_unitaire_ht": p["unit_price"],
            "categorie": p["category"],
            "gamme": p["gamme"],
            "label_egalim": p["label_egalim"],
            "provenance": p["provenance"],
            "direct_producteur": bool(p["direct_producteur"]),
        }
        for p in _produits()
        if garde(p)
    ]
    return {"nombre": len(out), "produits": out[: _lim(a.get("limite"), 20, 50)]}


def _lister_fournisseurs(user, a):
    return [{"id": s["id"], "nom": s["name"]} for s in db.rows("SELECT id, name FROM suppliers ORDER BY name")]


def _consulter_stock(user, a):
    q = _norm(a.get("requete"))
    rows = [
        {
            "produit_id": r["product_id"],
            "produit": r["name"],
            "stock": r["stock"],
            "unite": r["unit"],
            "recu": r["received"],
            "sorti": r["used"],
        }
        for r in r_stock.compute_stock()
        if not q or q in _norm(r["name"])
    ]
    return {"nombre": len(rows), "stock": rows[:80]}


def _lister_recettes(user, a):
    q, cat = _norm(a.get("requete")), a.get("categorie")
    return [
        {"id": r["id"], "nom": r["name"], "categorie": r["categorie"]}
        for r in db.rows("SELECT id, name, categorie FROM recipes ORDER BY name")
        if (not q or q in _norm(r["name"])) and (not cat or r["categorie"] == cat)
    ][:80]


def _voir_recette(user, a):
    r = _appel(r_recipes.get_recipe, _entier(a, "id"), user)
    return {
        "id": r["id"],
        "nom": r["name"],
        "categorie": r["categorie"],
        "description": r["description"],
        "ingredients": [
            {
                "produit": i.get("product_name") or i.get("label"),
                "produit_id": i["product_id"],
                "g_par_enfant_maternelle": i["qty_maternelle"],
                "g_par_enfant_elementaire": i["qty_elementaire"],
                "g_par_adulte": i["qty_adulte"],
                "principal": bool(i["principal"]),
            }
            for i in r["items"]
        ],
        "servie_le": [s["date"] for s in r["served"]][:10],
    }


def _lister_repas(user, a):
    d1, d2 = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")
    out = [
        {
            "id": m["id"],
            "date": m["date"],
            "statut": m["statut"],
            "entree": m["entree"],
            "plat": m["plat"],
            "accompagnement": m["accompagnement"],
            "laitage": m["laitage"],
            "dessert": m["dessert"],
            "convives": m["guests"],
            "cout_matieres": m["cost"],
            "produits_sortis": m["nb_items"],
        }
        for m in r_meals.meals_metrics(d1, d2)
    ]
    return {"nombre": len(out), "repas": out[: _lim(a.get("limite"), 40, 100)]}


def _lister_receptions(user, a):
    d1, d2, kind = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin"), a.get("type")
    out = [
        {
            "id": o["id"],
            "date": o["date"],
            "type": o["kind"],
            "reference": o["ref"],
            "fournisseur": o["supplier_name"],
            "total_ht": o["total_ht"],
            "lignes": o["nb_lines"],
        }
        for o in _appel(r_orders.orders, user)
        if (not d1 or (o["date"] or "") >= d1)
        and (not d2 or (o["date"] or "") <= d2)
        and (not kind or o["kind"] == kind)
    ]
    return {"nombre": len(out), "receptions": out[: _lim(a.get("limite"), 40, 100)]}


def _statistiques(user, a):
    s = _appel(r_stats.stats, _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin"), user)
    cles = (
        "total_ht",
        "meals",
        "guests",
        "cost_total",
        "price_per_meal",
        "pct_bio",
        "pct_egalim",
        "pct_local",
        "pct_direct",
    )
    out = {k: s.get(k) for k in cles}
    out["engagements"] = [
        {"nom": c["label"], "cible": c["target"], "realise": c["actual"], "statut": c["status"]}
        for c in s["commitments"]
    ]
    return out


def _comparer_fournisseurs(user, a):
    """Achats par fournisseur sur deux périodes, du plus en baisse au plus en hausse."""
    p1 = (_date(a.get("date_debut_a"), "date_debut_a"), _date(a.get("date_fin_a"), "date_fin_a"))
    p2 = (_date(a.get("date_debut_b"), "date_debut_b"), _date(a.get("date_fin_b"), "date_fin_b"))
    if not all(p1) or not all(p2):
        raise ErreurOutil("Les deux périodes (date_debut_a, date_fin_a, date_debut_b, date_fin_b) sont obligatoires.")
    directs = {r["name"] for r in db.rows("SELECT name FROM suppliers WHERE direct_producteur=1")}
    seulement = bool(a.get("direct_producteur_seulement"))
    cle = "amount"
    stats = [_appel(r_stats.stats, d1, d2, user) for d1, d2 in (p1, p2)]
    if stats[0].get("prices_hidden"):
        cle = "pct"  # profil sans accès aux prix : parts des achats seulement
    val = [{r["key"]: r.get(cle, 0) for r in s["by_supplier"]} for s in stats]
    noms = set(val[0]) | set(val[1])
    if seulement:
        noms &= directs
    lignes = [
        {
            "fournisseur": n,
            "direct_producteur": n in directs,
            "periode_a": val[0].get(n, 0),
            "periode_b": val[1].get(n, 0),
            "ecart": round(val[1].get(n, 0) - val[0].get(n, 0), 2),
        }
        for n in noms
    ]
    lignes.sort(key=lambda x: (x["ecart"], x["fournisseur"]))
    return {
        "unite": "€ HT" if cle == "amount" else "% des achats",
        "periode_a": {"du": p1[0], "au": p1[1]},
        "periode_b": {"du": p2[0], "au": p2[1]},
        "fournisseurs": lignes[: _lim(a.get("limite"), 30, 100)],
        "note": "ecart = periode_b - periode_a : négatif = on a moins acheté en période B.",
    }


def _achats_par_fournisseur(user, a):
    """Dépenses de la période par fournisseur (mêmes règles que les statistiques), éventuellement limitées au direct producteur."""
    if user.get("role") == "stats":
        raise ErreurOutil("Les montants d'achat ne sont pas accessibles avec ce profil.")
    d1, d2 = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")
    where, args = ["1=1"], []
    if d1:
        where.append("o.date >= ?")
        args.append(d1)
    if d2:
        where.append("o.date <= ?")
        args.append(d2)
    lignes = db.rows(
        "SELECT l.order_id, o.total_ht AS order_total, l.qty, COALESCE(l.total_ht, l.qty*l.unit_price) AS spend, "
        "p.direct_producteur, s.name AS supplier, s.direct_producteur AS supplier_direct "
        "FROM order_lines l JOIN orders o ON o.id=l.order_id "
        "LEFT JOIN products p ON p.id=l.product_id LEFT JOIN suppliers s ON s.id=o.supplier_id "
        f"WHERE {' AND '.join(where)}",
        args,
    )
    fill_spend(lignes)
    direct = bool(a.get("direct_producteur_seulement"))
    if direct:
        lignes = [r for r in lignes if r["direct_producteur"] or r["supplier_direct"]]
    total = round(sum(r["spend"] for r in lignes), 2)
    parts = breakdown(lignes, "supplier")
    return {
        "periode": [d1, d2],
        "direct_producteur_seulement": direct,
        "total_ht": total,
        "fournisseurs": [
            {"fournisseur": x["label"], "montant_ht": x["amount"], "part_pct": x["pct"]} for x in parts[:30]
        ],
    }


# ------------------------------------------------------------------ écriture

CHAMPS_PRODUIT = tuple(r_products.Product.model_fields)


def _entier(a, cle):
    try:
        return int(a[cle])
    except (KeyError, TypeError, ValueError):
        raise ErreurOutil(f"{cle} : nombre entier attendu") from None


def _creer_fournisseur(user, a):
    nom = (a.get("nom") or "").strip()
    if not nom:
        raise ErreurOutil("nom : obligatoire")
    ex = db.one("SELECT id FROM suppliers WHERE lower(name)=lower(?)", (nom,))
    if ex:
        raise ErreurOutil(f"Le fournisseur « {nom} » existe déjà (id {ex['id']}).")
    s = r_suppliers.Supplier(
        name=nom,
        contact=a.get("contact"),
        email=a.get("email"),
        phone=a.get("telephone"),
        address=a.get("adresse"),
        direct_producteur=1 if a.get("direct_producteur") else 0,
    )
    return {"id": _appel(r_suppliers.create_supplier, s, user)["id"], "nom": nom}


def _creer_produit(user, a):
    nom = (a.get("nom") or "").strip()
    if not nom:
        raise ErreurOutil("nom : obligatoire")
    fid = a.get("fournisseur_id")
    if fid is not None and not db.one("SELECT 1 AS x FROM suppliers WHERE id=?", (fid,)):
        raise ErreurOutil(f"Fournisseur {fid} introuvable (voir lister_fournisseurs).")
    if db.one("SELECT 1 AS x FROM products WHERE lower(name)=lower(?) AND supplier_id IS ?", (nom, fid)):
        raise ErreurOutil(f"Le produit « {nom} » existe déjà pour ce fournisseur.")
    p = r_products.Product(
        name=nom,
        supplier_id=fid,
        unit=a.get("unite") or "kg",
        unit_price=a.get("prix_unitaire_ht"),
        category=a.get("categorie"),
        gamme=a.get("gamme"),
        label_egalim=a.get("label_egalim") or "sans",
        provenance=a.get("provenance"),
    )
    return {"id": _appel(r_products.create_product, p, user)["id"], "nom": nom}


def _modifier_produit(user, a):
    pid = a.get("produit_id")
    p = db.one("SELECT * FROM products WHERE id=?", (pid,)) if isinstance(pid, int) else None
    if not p:
        raise ErreurOutil(f"Produit {pid} introuvable (voir rechercher_produits).")
    champs = {"reference": "ref", "nom": "name", "categorie": "category", "gamme": "gamme", "label_egalim": "label_egalim",
              "provenance": "provenance"}  # fmt: skip
    donnees = {k: p[k] for k in CHAMPS_PRODUIT}
    modifs = []
    for arg, col in champs.items():
        if arg in a and a[arg] is not None:
            v = str(a[arg]).strip()
            if col == "name" and not v:
                raise ErreurOutil("nom : ne peut pas être vide")
            if v != (p[col] or ""):
                donnees[col] = v or None
                modifs.append(f"{arg} : « {p[col] or ''} » → « {v} »")
    if not modifs:
        raise ErreurOutil("Aucune modification : les valeurs demandées sont déjà celles du produit.")
    _appel(r_products.edit_product, pid, r_products.Product(**donnees), user)
    log_action(user, "update", "product", pid, "Produit modifié par l'assistant : " + " ; ".join(modifs))
    return {"id": pid, "nom": donnees["name"], "modifications": modifs}


def construire_ingredient(ing, nb_m, nb_e, nb_a):
    """Ingrédient de recette décrit par le modèle -> (RecipeItem, produit relié ou None, texte, ambiguïté ou None)."""
    g = ing.get("grammes_par_convive")
    if not isinstance(g, (int, float)) or g <= 0:
        raise ErreurOutil("ingredients : grammes_par_convive (nombre > 0) obligatoire pour chaque ingrédient")
    pid, libelle = ing.get("produit_id"), (ing.get("libelle") or "").strip()
    texte = (ing.get("produit") or libelle).strip()
    prod, ambigu = None, None
    if pid is not None:
        prod = next((p for p in _produits() if p["id"] == pid), None)
        if not prod:
            raise ErreurOutil(f"produit_id {pid} introuvable (voir rechercher_produits).")
    elif texte:
        prod, cands = trouver_produit(texte)
        if not prod and cands:
            ambigu = {"ingredient": texte, "candidats": [c["name"] for c in cands]}
    if not prod and not texte:
        raise ErreurOutil("ingredients : chaque ingrédient doit avoir un produit ou un libellé")
    total = round((g * nb_m + g * nb_e + g * nb_a) / 1000, 3)  # quantité totale à servir, en kg (g × convives)
    unite = "l" if prod and prod["unit"] == "l" else "kg"
    item = r_recipes.RecipeItem(
        product_id=prod["id"] if prod else None,
        label=libelle or (prod["name"] if prod else texte),  # libellé général ; l'éditeur n'affiche que lui
        qty_maternelle=g,
        qty_elementaire=g,
        qty_adulte=g,
        qty_servi=total or None,
        qty_commander=total or None,
        unit=unite,
        principal=bool(ing.get("principal")),
    )
    return item, prod, texte, ambigu


def _creer_recette(user, a):
    nom = (a.get("nom") or "").strip()
    if not nom:
        raise ErreurOutil("nom : obligatoire")
    if db.one("SELECT id FROM recipes WHERE lower(name)=lower(?)", (nom,)):
        raise ErreurOutil(f"Une recette « {nom} » existe déjà : choisissez un autre nom.")
    cv = a.get("convives") or {}
    nb_m, nb_e, nb_a = (int(cv.get(k) or 0) for k in ("maternelles", "elementaires", "adultes"))
    items, reliés, non_reliés, ambigus = [], [], [], []
    for ing in a.get("ingredients") or []:
        item, prod, texte, ambigu = construire_ingredient(ing, nb_m, nb_e, nb_a)
        if ambigu:
            ambigus.append(ambigu)
        items.append(item)
        (reliés if prod else non_reliés).append(prod["name"] if prod else texte)
    rec = r_recipes.Recipe(
        name=nom,
        categorie=a.get("categorie"),
        description=a.get("description"),
        nb_maternelles=nb_m,
        nb_elementaires=nb_e,
        nb_adultes=nb_a,
        items=items,
    )
    rid = _appel(r_recipes.create_recipe, rec, user)["id"]
    out = {"id": rid, "nom": nom, "ingredients_relies_a_un_produit": reliés, "ingredients_sans_produit": non_reliés}
    if ambigus:
        out["a_verifier"] = ambigus
    if non_reliés:
        out["conseil"] = (
            "Ces ingrédients n'ont pas de produit : ils n'entrent pas dans le coût. Proposer de créer les produits."
        )
    return out


def _creer_repas(user, a):
    jour = _date(a.get("date"), "date")
    if not jour:
        raise ErreurOutil("date : obligatoire (AAAA-MM-JJ)")
    ex = db.one("SELECT id FROM meals WHERE date=?", (jour,))
    if ex:
        raise ErreurOutil(
            f"Un repas existe déjà le {jour} (id {ex['id']}) : utilisez saisir_sorties_repas pour le compléter."
        )
    cv = a.get("convives") or {}
    for cle in ("entree", "plat", "accompagnement", "laitage", "dessert"):
        rid = a.get("recette_" + cle + "_id")
        if rid is not None and not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (rid,)):
            raise ErreurOutil(f"recette_{cle}_id {rid} introuvable (voir lister_recettes).")
    m = r_meals.Meal(
        date=jour,
        nb_maternelles=int(cv.get("maternelles") or 0),
        nb_elementaires=int(cv.get("elementaires") or 0),
        nb_adultes=int(cv.get("adultes") or 0),
        statut=a.get("statut") or "prevu",
        **{c: a.get(c) for c in ("entree", "plat", "accompagnement", "laitage", "dessert")},
        **{f"recipe_{c}": a.get(f"recette_{c}_id") for c in ("entree", "plat", "accompagnement", "laitage", "dessert")},
    )
    return {"id": _appel(r_meals.create_meal, m, user)["id"], "date": jour}


@db.atomic
def _sorties(user, a):
    mid = _entier(a, "repas_id")
    if not db.one("SELECT 1 AS x FROM meals WHERE id=?", (mid,)):
        raise ErreurOutil(f"Repas {mid} introuvable (voir lister_repas).")
    ajoutes = []
    for s in a.get("sorties") or []:
        p = db.one("SELECT id, name, unit FROM products WHERE id=?", (s.get("produit_id"),))
        q = s.get("quantite")
        if not p:
            raise ErreurOutil(f"produit_id {s.get('produit_id')} introuvable (voir rechercher_produits).")
        if not isinstance(q, (int, float)) or q <= 0:
            raise ErreurOutil("sorties : quantite (nombre > 0) obligatoire")
        unite = s.get("unite") or p["unit"]
        db.execute("INSERT INTO meal_items (meal_id, product_id, qty, unit) VALUES (?,?,?,?)", (mid, p["id"], q, unite))
        ajoutes.append(f"{q} {unite or ''} {p['name']}".replace("  ", " "))
    if not ajoutes:
        raise ErreurOutil("sorties : au moins un produit est nécessaire")
    log_action(user, "update", "meal", mid, "Sorties ajoutées par l'assistant : " + ", ".join(ajoutes))
    return {"repas_id": mid, "sorties_ajoutees": ajoutes}


def _creer_reception(user, a):
    kind = a.get("type") or "livraison"
    lignes = []
    for l in a.get("lignes") or []:
        lignes.append(
            r_orders.Line(
                product_id=l.get("produit_id"),
                label=l.get("libelle"),
                qty=l.get("quantite"),
                unit=l.get("unite"),
                unit_price=l.get("prix_unitaire_ht"),
                total_ht=l.get("total_ht"),
            )
        )
    if not lignes:
        raise ErreurOutil("lignes : au moins une ligne est nécessaire")
    o = r_orders.Order(
        supplier_id=a.get("fournisseur_id"),
        new_supplier_name=(a.get("nouveau_fournisseur") or None),
        ref=a.get("reference"),
        kind=kind,
        date=_date(a.get("date"), "date") or date.today().isoformat(),
        total_ht=a.get("total_ht"),
        lines=lignes,
    )
    res = _appel(r_orders.create_order, o, user)
    return {"id": res["id"], "type": kind, "lignes": len(lignes)}


# ------------------------------------------------------------------ catalogue

_STR, _NUM, _INT = {"type": "string"}, {"type": "number"}, {"type": "integer"}
_DATE = {"type": "string", "description": "Date AAAA-MM-JJ"}
_CONVIVES = {
    "type": "object",
    "description": "Nombre de convives par catégorie",
    "properties": {"maternelles": _INT, "elementaires": _INT, "adultes": _INT},
}


def _obj(props, requis=()):
    return {"type": "object", "properties": props, "required": list(requis)}


def _n(n, mot):
    return f"{n} {mot}{'s' if n > 1 else ''}"


def _liste(items):
    return ", ".join(items)


OUTILS = [
    Outil(
        "rechercher_produits",
        "Rechercher des produits",
        "Cherche des produits de la cantine par nom, référence ou fournisseur (ex. « carotte »), et/ou filtre par categorie "
        "(ex. Légumes), provenance (ex. ue, france, loire_atlantique), label_egalim (bio, autre, sans), gamme (1 à 6) ou "
        "direct_producteur. Pour « les légumes d'origine UE » : categorie=Légumes, provenance=ue, sans requete. "
        "Rend id, unité, prix, label, provenance.",
        _obj(
            {
                "requete": _STR,
                "categorie": _STR,
                "provenance": _STR,
                "label_egalim": _STR,
                "gamme": _STR,
                "direct_producteur": {"type": "boolean"},
                "limite": _INT,
            }
        ),
        _rechercher_produits,
    ),
    Outil(
        "lister_fournisseurs",
        "Lister les fournisseurs",
        "Liste des fournisseurs (id et nom).",
        _obj({}),
        _lister_fournisseurs,
    ),
    Outil(
        "consulter_stock",
        "Consulter le stock",
        "Stock actuel (reçu − sorti ± inventaire) par produit ; filtre facultatif par nom.",
        _obj({"requete": _STR}),
        _consulter_stock,
    ),
    Outil(
        "lister_recettes",
        "Lister les recettes",
        "Liste des recettes (id, nom, catégorie), filtrable par nom ou catégorie : " + _liste(CATEGORIES_RECETTE) + ".",
        _obj({"requete": _STR, "categorie": {"type": "string", "enum": CATEGORIES_RECETTE}}),
        _lister_recettes,
    ),
    Outil(
        "voir_recette",
        "Voir une recette",
        "Détail d'une recette : ingrédients et grammages.",
        _obj({"id": _INT}, ["id"]),
        _voir_recette,
    ),
    Outil(
        "lister_repas",
        "Lister les repas",
        "Repas d'une période : menu, statut, convives, coût matières, nombre de produits sortis.",
        _obj({"date_debut": _DATE, "date_fin": _DATE, "limite": _INT}),
        _lister_repas,
    ),
    Outil(
        "lister_receptions",
        "Lister les réceptions",
        "Bons de livraison et factures d'une période (type : livraison ou facture).",
        _obj(
            {
                "date_debut": _DATE,
                "date_fin": _DATE,
                "type": {"type": "string", "enum": ["livraison", "facture"]},
                "limite": _INT,
            }
        ),
        _lister_receptions,
    ),
    Outil(
        "statistiques",
        "Statistiques",
        "Indicateurs d'une période (un mois : premier et dernier jour) : achats, repas valorisés, prix par repas, "
        "% bio (pct_bio), Egalim (pct_egalim), local (pct_local), direct producteur (pct_direct), engagements.",
        _obj({"date_debut": _DATE, "date_fin": _DATE}),
        _statistiques,
    ),
    Outil(
        "comparer_fournisseurs",
        "Comparer les fournisseurs",
        "Compare les achats par fournisseur entre deux périodes (période A puis B) : montants, écart, et indique les fournisseurs "
        "en direct producteur. Sert à savoir chez qui on a moins ou plus commandé (direct_producteur_seulement pour les directs).",
        _obj(
            {
                "date_debut_a": _DATE,
                "date_fin_a": _DATE,
                "date_debut_b": _DATE,
                "date_fin_b": _DATE,
                "direct_producteur_seulement": {"type": "boolean"},
                "limite": _INT,
            },
            ["date_debut_a", "date_fin_a", "date_debut_b", "date_fin_b"],
        ),
        _comparer_fournisseurs,
    ),
    Outil(
        "achats_par_fournisseur",
        "Achats par fournisseur",
        "Montant acheté (HT) à chaque fournisseur sur une période, du plus gros au plus petit ; direct_producteur_seulement "
        "limite aux achats en direct producteur. Pour comparer deux périodes (« chez qui a-t-on moins commandé ? »), "
        "appelez-le une fois par période puis comparez les montants.",
        _obj({"date_debut": _DATE, "date_fin": _DATE, "direct_producteur_seulement": {"type": "boolean"}}),
        _achats_par_fournisseur,
    ),
    Outil(
        "creer_fournisseur",
        "Créer un fournisseur",
        "Crée un fournisseur (refuse un nom déjà existant).",
        _obj(
            {
                "nom": _STR,
                "contact": _STR,
                "email": _STR,
                "telephone": _STR,
                "adresse": _STR,
                "direct_producteur": {"type": "boolean"},
            },
            ["nom"],
        ),
        _creer_fournisseur,
        True,
        lambda a: f"Créer le fournisseur « {a.get('nom')} »",
    ),
    Outil(
        "creer_produit",
        "Créer un produit",
        "Crée un produit du catalogue (refuse un doublon chez le même fournisseur).",
        _obj(
            {
                "nom": _STR,
                "fournisseur_id": _INT,
                "unite": {"type": "string", "description": "kg, l, unité, pièce, botte…"},
                "prix_unitaire_ht": _NUM,
                "categorie": {"type": "string", "enum": CATEGORIES},
                "gamme": {"type": "string", "enum": list(GAMMES)},
                "label_egalim": {"type": "string", "enum": ["bio", "autre", "sans"]},
                "provenance": {"type": "string", "enum": list(PROVENANCES)},
            },
            ["nom"],
        ),
        _creer_produit,
        True,
        lambda a: (
            f"Créer le produit « {a.get('nom')} »"
            + (f" à {a['prix_unitaire_ht']} €/{a.get('unite') or 'kg'}" if a.get("prix_unitaire_ht") else "")
        ),
    ),
    Outil(
        "modifier_produit",
        "Modifier un produit",
        "Corrige la fiche d'un produit existant : référence fournisseur, nom, catégorie, gamme, label Egalim, provenance. "
        "Les autres champs et tout l'historique (achats, prix, recettes, stock) sont conservés. Pour corriger plusieurs "
        "produits, appelez l'outil une fois par produit. Cherchez d'abord les produits avec rechercher_produits "
        "(la recherche accepte une référence).",
        _obj(
            {
                "produit_id": _INT,
                "reference": {"type": "string", "description": "Nouvelle référence fournisseur"},
                "nom": _STR,
                "categorie": _STR,
                "gamme": _STR,
                "label_egalim": _STR,
                "provenance": _STR,
            },
            ["produit_id"],
        ),
        _modifier_produit,
        True,
        lambda a: (
            "Modifier le produit "
            + str(a.get("produit_id"))
            + " : "
            + ", ".join(f"{k} = « {v} »" for k, v in a.items() if k != "produit_id" and v is not None)
        ),
    ),
    Outil(
        "creer_recette",
        "Créer une recette",
        "Crée une recette avec ses ingrédients. Chaque ingrédient est relié à un produit existant (produit_id, ou nom du produit "
        "retrouvé automatiquement) avec son grammage en g par convive ; sans produit il reste en libellé libre et n'entre pas dans "
        "le coût. Donnez toujours à chaque ingrédient un libellé général (« Courgettes », pas « COURGETTE FRANCE PAYS DE LOIRE »). Cherchez d'abord les produits avec rechercher_produits.",
        _obj(
            {
                "nom": _STR,
                "categorie": {"type": "string", "enum": CATEGORIES_RECETTE},
                "description": {"type": "string", "description": "Préparation, étapes"},
                "convives": _CONVIVES,
                "ingredients": {
                    "type": "array",
                    "items": _obj(
                        {
                            "produit_id": _INT,
                            "produit": {"type": "string", "description": "Nom du produit du catalogue"},
                            "libelle": {
                                "type": "string",
                                "description": "Libellé GÉNÉRAL de l'ingrédient, sans marque ni origine ni label "
                                "(ex. « Courgettes », « Emmental râpé », « Crème fraîche »), jamais le nom commercial du produit",
                            },
                            "grammes_par_convive": _NUM,
                            "principal": {"type": "boolean"},
                        },
                        ["grammes_par_convive"],
                    ),
                },
            },
            ["nom", "categorie", "ingredients"],
        ),
        _creer_recette,
        True,
        lambda a: f"Créer la recette « {a.get('nom')} » ({_n(len(a.get('ingredients') or []), 'ingrédient')})",
    ),
    Outil(
        "creer_repas",
        "Créer un repas",
        "Crée un repas à une date (un seul repas par date), avec son menu, des recettes liées et le nombre de convives.",
        _obj(
            {
                "date": _DATE,
                "entree": _STR,
                "plat": _STR,
                "accompagnement": _STR,
                "laitage": _STR,
                "dessert": _STR,
                **{f"recette_{c}_id": _INT for c in ("entree", "plat", "accompagnement", "laitage", "dessert")},
                "convives": _CONVIVES,
                "statut": {"type": "string", "enum": STATUTS_REPAS},
            },
            ["date"],
        ),
        _creer_repas,
        True,
        lambda a: f"Créer le repas du {a.get('date')} ({a.get('plat') or 'menu à compléter'})",
    ),
    Outil(
        "saisir_sorties_repas",
        "Saisir des sorties de produits",
        "Ajoute des produits sortis pour un repas existant (diminue le stock).",
        _obj(
            {
                "repas_id": _INT,
                "sorties": {
                    "type": "array",
                    "items": _obj({"produit_id": _INT, "quantite": _NUM, "unite": _STR}, ["produit_id", "quantite"]),
                },
            },
            ["repas_id", "sorties"],
        ),
        _sorties,
        True,
        lambda a: f"Sortir {_n(len(a.get('sorties') or []), 'produit')} pour le repas n° {a.get('repas_id')}",
    ),
    Outil(
        "creer_reception",
        "Créer une réception",
        "Enregistre un bon de livraison ou une facture avec ses lignes (fournisseur existant ou à créer).",
        _obj(
            {
                "type": {"type": "string", "enum": ["livraison", "facture"]},
                "date": _DATE,
                "reference": _STR,
                "fournisseur_id": _INT,
                "nouveau_fournisseur": _STR,
                "total_ht": _NUM,
                "lignes": {
                    "type": "array",
                    "items": _obj(
                        {
                            "produit_id": _INT,
                            "libelle": _STR,
                            "quantite": _NUM,
                            "unite": _STR,
                            "prix_unitaire_ht": _NUM,
                            "total_ht": _NUM,
                        }
                    ),
                },
            },
            ["lignes"],
        ),
        _creer_reception,
        True,
        lambda a: (
            f"Enregistrer {'la facture' if a.get('type') == 'facture' else 'le bon de livraison'} {a.get('reference') or ''} ({len(a.get('lignes') or [])} lignes)".replace(
                "  ", " "
            )
        ),
    ),
]
from cgrs.assistant.outils_gestion import OUTILS_GESTION  # noqa: E402  (importe ce module : défini plus bas)

OUTILS.extend(OUTILS_GESTION)
PAR_NOM = {o.nom: o for o in OUTILS}


def outils_permis(role):
    """Outils utilisables avec ce profil : lecture seule ou lecture + écriture."""
    return [o for o in OUTILS if not o.ecriture or role in ("admin", "editor")]


def executer(user, nom, arguments):
    """Exécute un outil et rend un dictionnaire (ou liste) sérialisable ; lève ErreurOutil si la demande est refusée."""
    outil = PAR_NOM.get(nom)
    if not outil:
        raise ErreurOutil(f"Outil inconnu : {nom}")
    if outil.ecriture and user["role"] not in ("admin", "editor"):
        raise ErreurOutil("Droits insuffisants : cet accès est en lecture seule.")
    if not isinstance(arguments, dict):
        raise ErreurOutil("Les arguments doivent être un objet JSON")
    return outil.fonction(user, arguments)


def en_texte(resultat):
    """Résultat d'un outil en JSON compact, coupé s'il est trop long."""
    t = json.dumps(resultat, ensure_ascii=False, default=str)
    return t if len(t) <= MAX_RESULTAT else t[:MAX_RESULTAT] + " …(résultat tronqué : affinez la recherche)"
