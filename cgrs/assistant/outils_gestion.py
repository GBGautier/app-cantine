"""Outils de l'assistant pour le suivi et la correction des données : détails, historiques, modifications, contrôles.

Ce module complète le catalogue de outils.py (il est chargé par lui, en fin de fichier). Chaque outil d'écriture passe par les
fonctions des routes existantes : mêmes validations, mêmes calculs de prix, même journal des actions.
"""

import json

from cgrs import db
from cgrs.assistant.outils import (
    _DATE,
    _INT,
    _NUM,
    _STR,
    ErreurOutil,
    Outil,
    STATUTS_REPAS,
    _appel,
    _cle_provenance,
    _date,
    _entier,
    _lim,
    _norm,
    _obj,
    _produits,
    construire_ingredient,
    produits_nommes,
    trouver_produit,
)
from cgrs.routes import meals as r_meals
from cgrs.routes import orders as r_orders
from cgrs.routes import products as r_products
from cgrs.routes import recipes as r_recipes
from cgrs.routes import stats as r_stats
from cgrs.routes import stock as r_stock
from cgrs.routes import suppliers as r_suppliers
from cgrs.constants import GAMMES
from cgrs.services import bilan as svc_bilan
from cgrs.services import bilan_periode as svc_periode
from cgrs.services.stats import load_lines
from cgrs.services.units import convert
from cgrs.utils import log_action

CONVIVES = ("maternelles", "elementaires", "adultes")
REPAS_PLATS = ("entree", "plat", "accompagnement", "laitage", "dessert")


def _montants_interdits(user):
    if user.get("role") == "stats":
        raise ErreurOutil("Les montants et les prix ne sont pas accessibles avec ce profil.")


def _produit(a, cle="produit_id"):
    """Produit désigné par son identifiant (cle) ou, à défaut, par son nom (« produit »)."""
    pid = a.get(cle)
    if isinstance(pid, int):
        p = next((x for x in _produits() if x["id"] == pid), None)
        if not p:
            raise ErreurOutil(f"Produit {pid} introuvable (voir rechercher_produits).")
        return p
    nom = a.get("produit")
    if not nom:
        raise ErreurOutil(f"{cle} ou produit : obligatoire (voir rechercher_produits).")
    p, candidats = trouver_produit(nom)
    if p:
        return p
    if candidats:
        raise ErreurOutil(
            "Produit ambigu, précisez produit_id parmi : " + ", ".join(f"{c['name']} ({c['id']})" for c in candidats)
        )
    raise ErreurOutil(f"Produit « {nom} » introuvable (voir rechercher_produits).")


def _fournisseur_nom(sid):
    r = db.one("SELECT name FROM suppliers WHERE id=?", (sid,)) if sid else None
    return r["name"] if r else None


# ------------------------------------------------------------------ lecture


def _voir_reception(user, a):
    o = _appel(r_orders.get_order, _entier(a, "id"), user)
    return {
        "id": o["id"],
        "type": o["kind"],
        "date": o["date"],
        "reference": o["ref"],
        "fournisseur": _fournisseur_nom(o["supplier_id"]),
        "total_ht": o["total_ht"],
        "pdf_joint": bool(o.get("source_file")),
        "notes": o["notes"],
        "lignes": [
            {
                "ligne_id": l["id"],
                "produit_id": l["product_id"],
                "produit": l["product_name"] or l["label"],
                "reference": l["ref"],
                "quantite": l["qty"],
                "unite": l["unit"],
                "prix_unitaire_ht": l["unit_price"],
                "total_ht": l["total_ht"],
            }
            for l in o["lines"]
        ],
    }


def _voir_repas(user, a):
    m = _appel(r_meals.get_meal, _entier(a, "id"), user)
    return {
        "id": m["id"],
        "date": m["date"],
        "statut": m["statut"],
        "convives": {
            "maternelles": m["nb_maternelles"],
            "elementaires": m["nb_elementaires"],
            "adultes": m["nb_adultes"],
        },
        "menu": {c: m[c] for c in REPAS_PLATS if m.get(c)},
        "recettes_liees": {c: m.get("recipe_" + c) for c in REPAS_PLATS if m.get("recipe_" + c)},
        "notes": m["notes"],
        "commentaire_apres_repas": m["commentaire_post"],
        "sorties": [
            {
                "sortie_id": i["id"],
                "produit_id": i["product_id"],
                "produit": i["product_name"],
                "quantite": i["qty"],
                "unite": i["unit"],
                "prix_reel": i["prix_reel"],
            }
            for i in m["items"]
        ],
        "lignes_estimation": len(m.get("estimation") or []),
    }


def _historique_prix(user, a):
    _montants_interdits(user)
    p = _produit(a)
    d1 = _date(a.get("date_debut"), "date_debut")
    hist = [h for h in _appel(r_products.product_prices, p["id"], user) if not d1 or (h["date"] or "") >= d1]
    if not hist:
        return {
            "produit": p["name"],
            "produit_id": p["id"],
            "unite": p["unit"],
            "prix_actuel": p["unit_price"],
            "historique": [],
        }
    chrono = sorted(hist, key=lambda h: (h["date"] or "", h["id"]))
    premier, dernier = chrono[0]["price"], chrono[-1]["price"]
    prix = [h["price"] for h in hist]
    return {
        "produit": p["name"],
        "produit_id": p["id"],
        "unite": p["unit"],
        "prix_actuel": p["unit_price"],
        "nombre_de_prix": len(hist),
        "premier_prix": {"date": chrono[0]["date"], "prix": premier},
        "dernier_prix": {"date": chrono[-1]["date"], "prix": dernier},
        "variation_pct": round(100 * (dernier - premier) / premier, 1) if premier else None,
        "minimum": min(prix),
        "maximum": max(prix),
        "historique": [
            {
                "date": h["date"],
                "prix": h["price"],
                "unite": h["unit"],
                "source": h["source"],
                "reception": h["order_ref"],
            }
            for h in hist[: _lim(a.get("limite"), 12, 40)]
        ],
    }


def _engagements(user, a):
    s = _appel(r_stats.stats, _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin"), user)
    total = s.get("total_ht")
    out = []
    for c in s["commitments"]:
        ligne = {
            "nom": c["label"],
            "indicateur": c.get("metric_label"),
            "objectif": c["target"],
            "sens": "maximum" if c["mode"] == "max" else "minimum",
            "realise": c["actual"],
            "statut": c["status"],
        }
        if c["status"] == "ko" and c["actual"] is not None:
            ligne["ecart_points"] = round(abs(c["target"] - c["actual"]), 1)
            if total and "price_per_meal" not in c["metrics"] and c["mode"] != "max":
                # part des achats à réorienter vers des produits conformes (à budget d'achats constant)
                ligne["a_reorienter_ht"] = round((c["target"] - c["actual"]) / 100 * total, 2)
        out.append(ligne)
    atteints = sum(1 for c in out if c["statut"] == "ok")
    return {
        "periode": [_date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")],
        "atteints": f"{atteints}/{len(out)}",
        "engagements": out,
    }


def _besoins(user, a):
    """Produits à commander pour les repas prévus de la période, comparés au stock actuel, par fournisseur."""
    _montants_interdits(user)
    d1, d2 = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")
    if not d1 or not d2:
        raise ErreurOutil("date_debut et date_fin : obligatoires")
    repas = db.rows(
        "SELECT id, date, estimation FROM meals WHERE date>=? AND date<=? AND statut IN ('prevu','en_cours')", (d1, d2)
    )
    produits = {p["id"]: p for p in _produits()}
    besoin = {}

    deja_sorti = {}  # sorties déjà saisies pour ces repas : elles ont déjà baissé le stock

    def ajouter(pid, qty, unit, saisi=False):
        p = produits.get(pid)
        if not p or not isinstance(qty, (int, float)) or qty <= 0:
            return
        pu = p["unit"] or "kg"
        q = convert(qty, unit or pu, pu)
        besoin[pid] = besoin.get(pid, 0.0) + (q if q is not None else 0.0)
        if saisi:
            deja_sorti[pid] = deja_sorti.get(pid, 0.0) + (q if q is not None else 0.0)

    for m in repas:
        sorties = db.rows("SELECT product_id, qty, unit FROM meal_items WHERE meal_id=?", (m["id"],))
        if sorties:
            for i in sorties:
                ajouter(i["product_id"], i["qty"], i["unit"], saisi=True)
            continue
        try:  # repas sans sorties saisies : on prend les lignes de l'estimation des coûts
            lignes = json.loads(m["estimation"]) if m["estimation"] else []
        except ValueError:
            lignes = []
        for l in lignes:
            if isinstance(l, dict) and isinstance(l.get("product_id"), int):
                ajouter(l["product_id"], l.get("qty"), l.get("unit"))
    en_stock = {}
    for r in r_stock.compute_stock():
        if r["unit"] == (produits.get(r["product_id"], {}).get("unit") or "kg"):
            en_stock[r["product_id"]] = r["stock"]
    par_fournisseur = {}
    for pid, b in besoin.items():
        p = produits[pid]
        avant = en_stock.get(pid, 0.0) + deja_sorti.get(pid, 0.0)  # stock avant les sorties de ces repas
        reste = round(max(0.0, b - max(0.0, avant)), 3)
        if reste <= 0:
            continue
        cout = round(reste * p["unit_price"], 2) if p["unit_price"] is not None else None
        f = par_fournisseur.setdefault(p["supplier_id"], [])
        f.append(
            {
                "produit_id": pid,
                "produit": p["name"],
                "besoin": round(b, 3),
                "stock": round(max(0.0, avant), 3),
                "a_commander": reste,
                "unite": p["unit"] or "kg",
                "cout_estime_ht": cout,
            }
        )
    fournisseurs = []
    for sid, lignes in par_fournisseur.items():
        s = (
            db.one("SELECT name, franco, delivery_days, order_method FROM suppliers WHERE id=?", (sid,))
            if sid
            else None
        )
        total = round(sum(l["cout_estime_ht"] or 0 for l in lignes), 2)
        try:
            jours = json.loads(s["delivery_days"]) if s and s["delivery_days"] else []
        except ValueError:
            jours = []
        f = {
            "fournisseur": s["name"] if s else "sans fournisseur",
            "total_estime_ht": total,
            "produits": sorted(lignes, key=lambda l: l["produit"]),
        }
        if s and s["franco"]:
            f["franco"] = s["franco"]
            f["franco_atteint"] = total >= s["franco"]
        if jours:
            f["jours_livraison"] = jours
        fournisseurs.append(f)
    fournisseurs.sort(key=lambda f: f["fournisseur"])
    return {
        "periode": [d1, d2],
        "repas_prevus": len(repas),
        "a_commander": fournisseurs,
        "remarque": "Besoins tirés des produits sortis ou estimés dans les repas prévus ; stock = stock actuel du produit.",
    }


def _arr(v, d=1):
    return None if v is None else round(v, d)


def _bilan_mensuel(user, a):
    """Bilan d'un mois comparé au cumul depuis septembre, par rubrique (résultat court : une rubrique à la fois)."""
    mois = a.get("mois") or svc_bilan.mois_par_defaut()
    try:
        b = svc_bilan.bilan(mois, masquer_prix=user.get("role") == "stats")
    except svc_bilan.MoisInvalide as e:
        raise ErreurOutil(str(e)) from None
    rubrique = (a.get("rubrique") or "resume").lower()

    def lignes(rows, total=False):
        out = []
        for r in rows:
            x = {"nom": r["nom"], "engagement": r.get("engagement"), "mois": _arr(r["mois"]), "cumul": _arr(r["cumul"])}
            if total and r.get("total_ht") is not None:
                x["total_ht"] = round(r["total_ht"])
            out.append(x)
        return out

    base = {"mois": b["libelle"], "cumul": b["libelle_cumul"]}
    pm, pc = b["prix"]["mois"], b["prix"]["cumul"]
    if rubrique == "resume":
        prix = {"mois": pm, "cumul": pc, "tarif_repas": b["tarif_repas"]} if not b["prix_masques"] else None
        for k in ("mois", "cumul"):
            if prix:
                prix[k] = {
                    c: prix[k][c]
                    for c in ("repas", "prix_par_repas", "deficit_par_repas", "deficit_total", "achats_ht")
                    if c in prix[k]
                }
        ko = [e["nom"] for e in b["engagements"] if e["mois"]["statut"] == "ko"]
        return {
            **base,
            "synthese": b["synthese"],
            "prix": prix,
            "tendance_mois_vs_cumul": [
                {
                    "indicateur": t["indicateur"],
                    "mois": _arr(t["mois"]),
                    "cumul": _arr(t["cumul"]),
                    "ecart_pts": t["ecart_points"],
                }
                for t in b["tendance"]
            ],
            "engagements_non_atteints_ce_mois": ko,
            "autres_rubriques": [
                "labels",
                "bio_familles",
                "egalim_familles",
                "origine",
                "zones",
                "categories",
                "direct",
                "frais",
                "gammes",
                "engagements",
                "evolution",
            ],
        }
    if rubrique == "labels":
        return {
            **base,
            "labels": {
                k: {"engagement": v["engagement"], "mois": _arr(v["mois"]), "cumul": _arr(v["cumul"])}
                for k, v in b["labels"].items()
            },
        }
    if rubrique == "origine":
        o = b["origine"]
        return {
            **base,
            "origine": {
                k: {"engagement": o[k]["engagement"], "mois": _arr(o[k]["mois"]), "cumul": _arr(o[k]["cumul"])}
                for k in ("france", "local", "hors_france")
            },
            "repartition": lignes(o["repartition"]),
        }
    if rubrique == "categories":
        return {**base, "origine_france_par_categorie": lignes(b["categories_france"])}
    if rubrique == "direct":
        return {**base, "direct_producteur_par_famille": lignes(b["direct"], total=True)}
    if rubrique == "frais":
        return {**base, "produits_frais_par_categorie": lignes(b["frais"], total=True)}
    if rubrique == "bio_familles":
        return {**base, "bio_par_famille": lignes(b["bio_familles"], total=True)}
    if rubrique == "egalim_familles":
        return {**base, "egalim_par_famille": lignes(b["egalim_familles"], total=True)}
    if rubrique == "zones":
        return {
            **base,
            "origine_par_famille": [
                {
                    "nom": r["nom"],
                    "zones": {z["nom"]: {"mois": _arr(z["mois"]), "cumul": _arr(z["cumul"])} for z in r["zones"]},
                }
                for r in b["zones"]
            ],
        }
    if rubrique == "gammes":
        return {
            **base,
            "gammes": [
                {
                    "nom": g["nom"],
                    "mois": _arr(g["mois"]),
                    "cumul": _arr(g["cumul"]),
                    "hors_epicerie": {
                        "mois": _arr(g["hors_epicerie"]["mois"]),
                        "cumul": _arr(g["hors_epicerie"]["cumul"]),
                    },
                }
                for g in b["gammes"]
            ],
        }
    if rubrique == "engagements":
        return {
            **base,
            "engagements": [
                {"nom": e["nom"], "objectif": e["objectif"], "sens": e["sens"], "mois": e["mois"], "cumul": e["cumul"]}
                for e in b["engagements"]
            ],
        }
    if rubrique == "evolution":
        return {
            **base,
            "evolution": [
                {k: _arr(v) if isinstance(v, float) else v for k, v in e.items() if k != "libelle"}
                for e in b["evolution"]
            ],
        }
    raise ErreurOutil(
        "rubrique : resume | labels | bio_familles | egalim_familles | origine | zones | categories | direct | frais | gammes | engagements | evolution"
    )


def _anomalies(user, a):
    """Contrôles de cohérence : ce qu'il faudrait compléter ou corriger dans les données."""
    produits = _produits()
    sans_prix = [p for p in produits if not p["unit_price"]]
    par_ref, par_nom = {}, {}
    for p in produits:
        if p["ref"] and p["ref"].strip():
            par_ref.setdefault((p["supplier_id"], p["ref"].strip().lower()), []).append(p)
        par_nom.setdefault((p["supplier_id"], _norm(p["name"])), []).append(p)

    def groupes(d):
        return [[f"{p['name']} (#{p['id']})" for p in g] for g in d.values() if len(g) > 1][:10]

    doublons = groupes(par_ref) + groupes(par_nom)
    sans_pdf = db.rows(
        "SELECT o.id, o.date, o.ref, o.kind, s.name AS fournisseur FROM orders o LEFT JOIN suppliers s ON s.id=o.supplier_id "
        "WHERE o.source_file IS NULL OR o.source_file='' ORDER BY o.date DESC, o.id DESC"
    )
    sans_produit = db.rows(
        "SELECT l.order_id, COUNT(*) AS n FROM order_lines l WHERE l.product_id IS NULL GROUP BY l.order_id ORDER BY l.order_id DESC"
    )
    vides = db.rows(
        "SELECT o.id, o.date, o.ref FROM orders o WHERE (o.total_ht IS NULL OR o.total_ht=0) "
        "OR NOT EXISTS (SELECT 1 FROM order_lines l WHERE l.order_id=o.id) ORDER BY o.date DESC LIMIT 10"
    )
    passes_sans_sorties = db.rows(
        "SELECT m.id, m.date, m.guests FROM meals m WHERE m.statut='passe' AND m.guests>0 "
        "AND NOT EXISTS (SELECT 1 FROM meal_items i WHERE i.meal_id=m.id) ORDER BY m.date DESC"
    )

    def bloc(liste, formate):
        return {"nombre": len(liste), "exemples": [formate(x) for x in liste[:10]]}

    return {
        "produits_sans_prix": bloc(sans_prix, lambda p: f"{p['name']} (#{p['id']})"),
        "doublons_probables_de_produits": {"nombre": len(doublons), "groupes": doublons},
        "receptions_sans_pdf": bloc(
            sans_pdf, lambda o: f"#{o['id']} {o['date']} {o['kind']} {o['ref'] or ''} {o['fournisseur'] or ''}".strip()
        ),
        "receptions_avec_lignes_sans_produit": bloc(
            sans_produit, lambda r: f"réception #{r['order_id']} : {r['n']} ligne(s)"
        ),
        "receptions_vides_ou_sans_total": bloc(vides, lambda o: f"#{o['id']} {o['date']} {o['ref'] or ''}".strip()),
        "repas_passes_sans_sorties": bloc(
            passes_sans_sorties, lambda m: f"#{m['id']} {m['date']} ({m['guests']} convives)"
        ),
    }


def _journal(user, a):
    if user.get("role") != "admin":
        raise ErreurOutil("Le journal des actions est réservé aux administrateurs.")
    where, args = ["1=1"], []
    for cle, col in (("entite", "entity"), ("utilisateur", "username"), ("action", "action")):
        if a.get(cle):
            where.append(f"{col}=?")
            args.append(str(a[cle]))
    if a.get("date_debut"):
        where.append("ts >= ?")
        args.append(_date(a["date_debut"], "date_debut"))
    rows = db.rows(
        "SELECT ts, username, action, entity, entity_id, description FROM action_log WHERE "
        + " AND ".join(where)
        + " ORDER BY ts DESC, id DESC LIMIT ?",
        (*args, _lim(a.get("limite"), 25, 80)),
    )
    return {
        "nombre": len(rows),
        "actions": [
            {
                "quand": r["ts"],
                "qui": r["username"],
                "action": r["action"],
                "objet": f"{r['entity']} #{r['entity_id']}",
                "detail": (r["description"] or "")[:160],
            }
            for r in rows
        ],
    }


# ------------------------------------------------------------------ écriture


def _trouver_ingredient(items, ref):
    """Ligne de recette désignée par un identifiant de produit (entier) ou par un libellé / nom de produit."""
    if isinstance(ref, int):
        trouves = [i for i in items if i["product_id"] == ref]
    else:
        cible = _norm(ref)
        exacts = [i for i in items if cible in (_norm(i.get("label")), _norm(i.get("product_name")))]
        trouves = exacts or [
            i for i in items if cible and (cible in _norm(i.get("label")) or cible in _norm(i.get("product_name")))
        ]
    if not trouves:
        raise ErreurOutil(f"Ingrédient « {ref} » introuvable dans la recette (voir voir_recette).")
    if len(trouves) > 1:
        raise ErreurOutil(
            f"Ingrédient « {ref} » ambigu : " + ", ".join(str(i.get("label") or i.get("product_name")) for i in trouves)
        )
    return trouves[0]


def _modifier_recette(user, a):
    rid = _entier(a, "id")
    r = _appel(r_recipes.get_recipe, rid, user)
    cv = a.get("convives") or {}
    nb = {k: int(cv[k]) if cv.get(k) is not None else r.get("nb_" + k) or 0 for k in CONVIVES}
    convives_changes = any(cv.get(k) is not None and int(cv[k]) != (r.get("nb_" + k) or 0) for k in CONVIVES)
    nom = (a.get("nom") or r["name"]).strip()
    if not nom:
        raise ErreurOutil("nom : ne peut pas être vide")
    if nom != r["name"] and db.one("SELECT 1 AS x FROM recipes WHERE lower(name)=lower(?) AND id<>?", (nom, rid)):
        raise ErreurOutil(f"Une recette « {nom} » existe déjà.")
    items = [dict(i) for i in r["items"]]
    modifs = []
    retires = []
    for ref in a.get("retirer") or []:
        i = _trouver_ingredient(items, ref)
        items.remove(i)
        retires.append(str(i.get("label") or i.get("product_name")))
    if retires:
        modifs.append("retiré : " + ", ".join(retires))
    for m in a.get("modifier") or []:
        i = _trouver_ingredient(items, m.get("ingredient"))
        g = m.get("grammes_par_convive")
        if g is not None:
            if not isinstance(g, (int, float)) or g <= 0:
                raise ErreurOutil("modifier : grammes_par_convive doit être un nombre > 0")
            i["qty_maternelle"] = i["qty_elementaire"] = i["qty_adulte"] = g
            i["_recalcul"] = True
        if m.get("principal") is not None:
            i["principal"] = bool(m["principal"])
        modifs.append(f"modifié : {i.get('label') or i.get('product_name')}")
    for ing in a.get("ajouter") or []:
        item, prod, texte, _ = construire_ingredient(ing, nb["maternelles"], nb["elementaires"], nb["adultes"])
        d = item.model_dump()
        d["product_name"] = prod["name"] if prod else None
        items.append(d)
        modifs.append("ajouté : " + (item.label or texte))
    if convives_changes:
        modifs.append("convives : " + ", ".join(f"{k} {nb[k]}" for k in CONVIVES))
    for champ, cle in (("nom", "name"), ("categorie", "categorie"), ("description", "description")):
        if a.get(champ) is not None and str(a[champ]).strip() != (r[cle] or ""):
            modifs.append(f"{champ} modifié")
    if not modifs:
        raise ErreurOutil("Aucune modification demandée.")
    liste = []
    for i in items:
        if i.get("_recalcul") or convives_changes:
            # quantité totale à servir = grammes × convives ; la marge de commande existante est conservée
            tot = (
                (i.get("qty_maternelle") or 0) * nb["maternelles"]
                + (i.get("qty_elementaire") or 0) * nb["elementaires"]
                + (i.get("qty_adulte") or 0) * nb["adultes"]
            ) / 1000
            if tot > 0 and i.get("qty_servi"):
                marge = (i.get("qty_commander") or i["qty_servi"]) / i["qty_servi"]
                i["qty_servi"], i["qty_commander"] = round(tot, 3), round(tot * marge, 3)
            elif tot > 0:
                i["qty_servi"] = i["qty_commander"] = round(tot, 3)
        liste.append(
            r_recipes.RecipeItem(
                **{k: i.get(k) for k in r_recipes.RecipeItem.model_fields if k in i and k != "principal"},
                principal=bool(i.get("principal")),
            )
        )
    rec = r_recipes.Recipe(
        name=nom,
        categorie=a.get("categorie") or r["categorie"],
        description=a.get("description") if a.get("description") is not None else r["description"],
        nb_maternelles=nb["maternelles"],
        nb_elementaires=nb["elementaires"],
        nb_adultes=nb["adultes"],
        items=liste,
    )
    _appel(r_recipes.edit_recipe, rid, rec, user)
    return {"id": rid, "nom": nom, "modifications": modifs}


def _modifier_repas(user, a):
    mid = _entier(a, "id")
    m = _appel(r_meals.get_meal, mid, user)
    donnees = {
        k: m[k]
        for k in (
            "date",
            "nb_maternelles",
            "nb_elementaires",
            "nb_adultes",
            "notes",
            "commentaire_post",
            "modif_prevu",
            "statut",
            *REPAS_PLATS,
        )
    }
    for c in REPAS_PLATS:
        v = m.get("recipe_" + c)
        donnees["recipe_" + c] = int(v) if v not in (None, "") else None
    modifs = []

    def changer(cle, valeur, nom):
        if valeur is not None and valeur != donnees[cle]:
            modifs.append(f"{nom} : « {donnees[cle] or ''} » → « {valeur} »")
            donnees[cle] = valeur

    changer("date", _date(a.get("date"), "date"), "date")
    if donnees["date"] != m["date"] and db.one("SELECT id FROM meals WHERE date=? AND id<>?", (donnees["date"], mid)):
        raise ErreurOutil(f"Un repas existe déjà le {donnees['date']}.")
    cv = a.get("convives") or {}
    for k, col in zip(CONVIVES, ("nb_maternelles", "nb_elementaires", "nb_adultes")):
        if cv.get(k) is not None:
            if int(cv[k]) < 0:
                raise ErreurOutil("convives : nombre positif attendu")
            changer(col, int(cv[k]), f"convives {k}")
    if a.get("statut") is not None and a["statut"] not in STATUTS_REPAS:
        raise ErreurOutil("statut : " + " | ".join(STATUTS_REPAS))
    changer("statut", a.get("statut"), "statut")
    for c in REPAS_PLATS:
        changer(c, a.get(c), c)
        rid = a.get(f"recette_{c}_id")
        if rid is not None:
            if not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (rid,)):
                raise ErreurOutil(f"recette_{c}_id {rid} introuvable (voir lister_recettes).")
            changer("recipe_" + c, rid, f"recette {c}")
    changer("notes", a.get("notes"), "notes")
    changer("commentaire_post", a.get("commentaire_apres_repas"), "commentaire")
    if not modifs:
        raise ErreurOutil("Aucune modification : les valeurs demandées sont déjà celles du repas.")
    meal = r_meals.Meal(
        **donnees,
        estimation=m.get("estimation") or None,
        items=[
            r_meals.MealItem(product_id=i["product_id"], qty=i["qty"], unit=i["unit"], prix_reel=i["prix_reel"])
            for i in m["items"]
        ],
    )
    _appel(r_meals.edit_meal, mid, meal, user)
    log_action(user, "update", "meal", mid, "Repas modifié par l'assistant : " + " ; ".join(modifs))
    return {"id": mid, "modifications": modifs}


def _modifier_reception(user, a):
    oid = _entier(a, "id")
    o = _appel(r_orders.get_order, oid, user)
    modifs = []
    entete = {
        "supplier_id": o["supplier_id"],
        "ref": o["ref"],
        "kind": o["kind"],
        "date": o["date"],
        "notes": o["notes"],
    }
    for arg, col in (
        ("fournisseur_id", "supplier_id"),
        ("reference", "ref"),
        ("type", "kind"),
        ("date", "date"),
        ("notes", "notes"),
    ):
        v = a.get(arg)
        if v is None:
            continue
        v = _date(v, "date") if arg == "date" else v
        if arg == "fournisseur_id" and not db.one("SELECT 1 AS x FROM suppliers WHERE id=?", (v,)):
            raise ErreurOutil(f"Fournisseur {v} introuvable (voir lister_fournisseurs).")
        if v != entete[col]:
            modifs.append(f"{arg} : « {entete[col] or ''} » → « {v} »")
            entete[col] = v
    lignes = {l["id"]: dict(l) for l in o["lines"]}
    changement_lignes = False
    for m in a.get("lignes") or []:
        lid = m.get("ligne_id")
        if lid not in lignes:
            raise ErreurOutil(
                f"ligne_id {lid} : cette ligne n'appartient pas à la réception {oid} (voir voir_reception)."
            )
        l = lignes[lid]
        if m.get("supprimer"):
            del lignes[lid]
            modifs.append(f"ligne supprimée : {l['product_name'] or l['label']}")
            changement_lignes = True
            continue
        avant = (l["qty"], l["unit"], l["unit_price"], l["product_id"])
        if m.get("quantite") is not None:
            l["qty"] = m["quantite"]
        if m.get("unite") is not None:
            l["unit"] = m["unite"]
        if m.get("prix_unitaire_ht") is not None:
            l["unit_price"] = m["prix_unitaire_ht"]
        if m.get("produit_id") is not None:
            if not db.one("SELECT 1 AS x FROM products WHERE id=?", (m["produit_id"],)):
                raise ErreurOutil(f"produit_id {m['produit_id']} introuvable (voir rechercher_produits).")
            l["product_id"] = m["produit_id"]
        if avant != (l["qty"], l["unit"], l["unit_price"], l["product_id"]):
            if (
                avant[:3] != (l["qty"], l["unit"], l["unit_price"])
                and l["qty"] is not None
                and l["unit_price"] is not None
            ):
                l["total_ht"] = round(l["qty"] * l["unit_price"], 2)
            modifs.append(f"ligne {lid} modifiée : {l['product_name'] or l['label']}")
            changement_lignes = True
    if not modifs:
        raise ErreurOutil("Aucune modification demandée.")
    if not lignes:
        raise ErreurOutil("Une réception doit garder au moins une ligne (supprimez la réception depuis l'application).")
    ordre = r_orders.Order(
        **entete,
        total_ht=None if changement_lignes else o["total_ht"],  # recalculé depuis les lignes si elles changent
        source_file=o.get("source_file"),
        lines=[
            r_orders.Line(
                product_id=l["product_id"],
                ref=l["ref"],
                label=l["label"],
                qty=l["qty"],
                unit=l["unit"],
                unit_price=l["unit_price"],
                total_ht=l["total_ht"],
            )
            for l in lignes.values()
        ],
    )
    _appel(r_orders.edit_order, oid, ordre, user)
    log_action(user, "update", "order", oid, "Réception modifiée par l'assistant : " + " ; ".join(modifs))
    return {"id": oid, "modifications": modifs}


def _ajuster_stock(user, a):
    p = _produit(a)
    q = a.get("quantite_reelle")
    if not isinstance(q, (int, float)) or q < 0:
        raise ErreurOutil("quantite_reelle : nombre ≥ 0 attendu (quantité réellement présente)")
    unite = a.get("unite") or p["unit"] or "kg"
    avant = next(
        (r["stock"] for r in r_stock.compute_stock() if r["product_id"] == p["id"] and r["unit"] == unite), 0.0
    )
    res = _appel(
        r_stock.stock_adjust,
        r_stock.StockAdjust(product_id=p["id"], unit=unite, target_qty=q, reason=a.get("motif")),
        user,
    )
    if res["delta"]:
        log_action(user, "adjust", "stock", p["id"], f"Inventaire par l'assistant : {p['name']} {avant} → {q} {unite}")
    return {"produit": p["name"], "unite": unite, "stock_avant": avant, "stock_apres": q, "ecart": res["delta"]}


def _modifier_fournisseur(user, a):
    sid = _entier(a, "id")
    s = db.one("SELECT * FROM suppliers WHERE id=?", (sid,))
    if not s:
        raise ErreurOutil(f"Fournisseur {sid} introuvable (voir lister_fournisseurs).")
    s = r_suppliers.supplier_out(dict(s))
    donnees = {k: s.get(k) for k in r_suppliers.Supplier.model_fields}
    modifs = []
    for arg, col in (
        ("nom", "name"),
        ("contact", "contact"),
        ("email", "email"),
        ("telephone", "phone"),
        ("adresse", "address"),
        ("franco", "franco"),
        ("mode_commande", "order_method"),
        ("lien_commande", "order_url"),
        ("jours_livraison", "delivery_days"),
        ("direct_producteur", "direct_producteur"),
        ("notes", "notes"),
    ):
        v = a.get(arg)
        if v is None:
            continue
        if col == "direct_producteur":
            v = 1 if v else 0
        if col == "name":
            v = str(v).strip()
            if not v:
                raise ErreurOutil("nom : ne peut pas être vide")
            if db.one("SELECT 1 AS x FROM suppliers WHERE lower(name)=lower(?) AND id<>?", (v, sid)):
                raise ErreurOutil(f"Un fournisseur « {v} » existe déjà.")
        if v != donnees[col]:
            modifs.append(f"{arg} : « {donnees[col] if donnees[col] not in (None, []) else ''} » → « {v} »")
            donnees[col] = v
    if not modifs:
        raise ErreurOutil("Aucune modification : les valeurs demandées sont déjà celles du fournisseur.")
    _appel(r_suppliers.edit_supplier, sid, r_suppliers.Supplier(**donnees), user)
    log_action(user, "update", "supplier", sid, "Fournisseur modifié par l'assistant : " + " ; ".join(modifs))
    return {"id": sid, "nom": donnees["name"], "modifications": modifs}


# ------------------------------------------------------------------ catalogue

_ING = _obj(
    {
        "produit_id": _INT,
        "produit": {"type": "string", "description": "Nom du produit si l'identifiant n'est pas connu"},
        "libelle": {"type": "string", "description": "Libellé GÉNÉRAL (« Courgettes »), jamais le nom commercial"},
        "grammes_par_convive": _NUM,
        "principal": {"type": "boolean"},
    },
    ["grammes_par_convive"],
)
_CV = {
    "type": "object",
    "description": "Nombre de convives par catégorie",
    "properties": {"maternelles": _INT, "elementaires": _INT, "adultes": _INT},
}


def _resume_modif(nom, cle="id"):
    return lambda a: (
        f"{nom} {a.get(cle)} : " + ", ".join(f"{k} = {v}" for k, v in a.items() if k != cle and v is not None)
    )


def _produits_en_defaut(user, a):
    d1, d2 = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")
    res = svc_periode.produits_en_defaut(d1, d2, a.get("indicateur"), _lim(a.get("limite_indicateurs"), 5, 10))
    if user.get("role") == "stats":
        for r in res:
            for p in r["produits"]:
                p.pop("montant_ht", None)
    return (
        {"periode": [d1, d2], "indicateurs_non_respectes": res}
        if res
        else {"periode": [d1, d2], "message": "Aucun indicateur à engagement n'est en défaut sur cette période."}
    )


def _selection_produits(a):
    """Lignes d'achat visées : un produit (nom ou id) ou un ensemble défini par des filtres."""
    if a.get("produit_id"):
        pid = _entier(a, "produit_id")
        return (lambda r: r["product_id"] == pid), f"produit {pid}"
    if a.get("produit"):
        ids = {p["id"] for p in produits_nommes(a["produit"])}
        if not ids:
            raise ErreurOutil(f"Aucun produit ne correspond à « {a['produit']} » (nom, mot du nom ou référence).")
        if len(ids) > 12:
            raise ErreurOutil(
                f"{len(ids)} produits correspondent à « {a['produit']} » : précisez (mot de plus, référence ou fournisseur)."
            )
        return (lambda r: r["product_id"] in ids), f"{len(ids)} produit(s)"
    cat, label, gamme = _norm(a.get("categorie")), _norm(a.get("label_egalim")), str(a.get("gamme") or "")[:1]
    prov = _cle_provenance(a["provenance"]) if a.get("provenance") else None
    if a.get("provenance") and prov is None:
        raise ErreurOutil("provenance non reconnue (ue, france, loire_atlantique, pays_loire, cc_nozay, international)")
    direct, four = a.get("direct_producteur"), _norm(a.get("fournisseur"))
    if not any([cat, label, gamme, prov, four, direct is not None]):
        raise ErreurOutil(
            "Indiquez un produit (nom ou produit_id) ou au moins un filtre (categorie, provenance, gamme, fournisseur…)."
        )
    return (
        lambda r: (
            (not cat or cat in _norm(r["category"]))
            and (not prov or r["provenance"] == prov)
            and (not label or label == _norm(r["label_egalim"]))
            and (not gamme or gamme == str(r["gamme"] or ""))
            and (direct is None or bool(r["direct_producteur"]) == bool(direct))
            and (not four or four in _norm(r["supplier"]))
        )
    ), "filtres"


def _ids_selection(a):
    if a.get("produit_id"):
        return {int(a["produit_id"])}
    return {p["id"] for p in produits_nommes(a["produit"])} if a.get("produit") else set()


def _simuler_remplacement(user, a):
    d1, d2 = _date(a.get("date_debut"), "date_debut"), _date(a.get("date_fin"), "date_fin")
    selection, _ = _selection_produits(a)
    visees = sorted({r["produit"] for r in load_lines(d1, d2) if selection(r) and r["produit"]})
    changements, substitut, ratio, avertissements = {}, None, 1.0, []
    if a.get("remplacer_par"):
        sub = _produit(
            {"produit_id": a.get("remplacer_par_id")} if a.get("remplacer_par_id") else {"produit": a["remplacer_par"]}
        )
        fiche = db.one("SELECT * FROM products WHERE id=?", (sub["id"],))
        if not fiche["unit_price"]:
            raise ErreurOutil(f"« {fiche['name']} » n'a pas de prix : impossible de valoriser le remplacement.")
        substitut = {
            "prix": fiche["unit_price"],
            "caracteristiques": {
                k: fiche[k]
                for k in ("provenance", "gamme", "label_egalim", "label_detail", "direct_producteur", "category")
            },
        }
        try:
            if a.get("quantite_remplacee") and a.get("quantite_remplacante"):
                ratio = float(a["quantite_remplacante"]) / float(a["quantite_remplacee"])
            else:
                ratio = float(a.get("ratio_quantite") or 1)
        except (TypeError, ValueError, ZeroDivisionError):
            raise ErreurOutil(
                "quantités : nombres attendus (ex. quantite_remplacee=80, quantite_remplacante=100)"
            ) from None
        if ratio <= 0:
            raise ErreurOutil("Le rapport de quantités doit être positif.")
        changements = {"remplacé par": fiche["name"]}
        unites = {p["unit"] for p in _produits() if p["id"] in _ids_selection(a)} - {fiche["unit"]}
        if unites:
            avertissements.append(
                f"Unités différentes ({', '.join(sorted(map(str, unites)))} remplacées par {fiche['unit']}) : les quantités sont comparées telles quelles."
            )
    if a.get("nouvelle_provenance"):
        cle = _cle_provenance(a["nouvelle_provenance"])
        if cle is None:
            raise ErreurOutil(
                "nouvelle_provenance non reconnue (ue, france, loire_atlantique, pays_loire, cc_nozay, international)"
            )
        changements["provenance"] = cle
    if a.get("nouvelle_gamme"):
        g = str(a["nouvelle_gamme"])[:1]
        if g not in GAMMES:
            raise ErreurOutil(
                "nouvelle_gamme : 1 frais et brut, 2 conserves, 3 surgelés, 4 cru prêt à l'emploi, 5 cuit sous vide, 6 déshydratés"
            )
        changements["gamme"] = g
    if a.get("nouveau_label_egalim"):
        changements["label_egalim"] = str(a["nouveau_label_egalim"]).strip().lower()
    if a.get("nouveau_direct_producteur") is not None:
        changements["direct_producteur"] = 1 if a["nouveau_direct_producteur"] else 0
    try:
        prix = float(a.get("variation_prix_pct") or 0)
    except (TypeError, ValueError):
        raise ErreurOutil("variation_prix_pct : nombre attendu") from None
    if not changements and not prix and not substitut:
        raise ErreurOutil(
            "Indiquez ce qui change : nouvelle_provenance, nouvelle_gamme, nouveau_label_egalim, nouveau_direct_producteur ou variation_prix_pct."
        )
    res = svc_periode.simuler(
        d1, d2, selection, {k: v for k, v in changements.items() if k != "remplacé par"}, prix, substitut, ratio
    )
    if not res["lignes_concernees"]:
        raise ErreurOutil("Aucun achat ne correspond à cette sélection sur la période.")
    if user.get("role") == "stats":
        res.pop("montant_ht_remplace", None)
        res.pop("montant_ht_apres", None)
    return {
        "periode": [d1, d2],
        "produits_concernes": visees[:12],
        "hypothese": changements
        | ({"variation_prix_pct": prix} if prix else {})
        | ({"quantite_remplacante_par_unite_remplacee": round(ratio, 3)} if substitut else {}),
        **({"avertissements": avertissements} if avertissements else {}),
        **res,
    }


OUTILS_GESTION = [
    Outil(
        "voir_reception",
        "Voir une réception",
        "Détail d'une réception (facture ou livraison) : fournisseur, date, référence, total, PDF joint et chaque ligne avec "
        "son ligne_id (à utiliser pour la modifier). Trouvez l'id avec lister_receptions.",
        _obj({"id": _INT}, ["id"]),
        _voir_reception,
    ),
    Outil(
        "voir_repas",
        "Voir un repas",
        "Détail d'un repas : date, statut, convives, menu, recettes liées, produits sortis (quantités, prix réels). Trouvez l'id avec lister_repas.",
        _obj({"id": _INT}, ["id"]),
        _voir_repas,
    ),
    Outil(
        "historique_prix",
        "Évolution du prix d'un produit",
        "Historique des prix d'un produit (produit_id ou nom) : premier et dernier prix, variation en %, minimum, maximum, "
        "derniers relevés avec leur réception. date_debut limite la période.",
        _obj({"produit_id": _INT, "produit": _STR, "date_debut": _DATE, "limite": _INT}),
        _historique_prix,
    ),
    Outil(
        "engagements_egalim",
        "Engagements Egalim",
        "État des engagements (bio, local, Egalim, prix par repas…) sur une période : objectif, réalisé, atteint ou non, "
        "écart en points et montant d'achats à réorienter pour atteindre l'objectif. Sans dates : toute la période.",
        _obj({"date_debut": _DATE, "date_fin": _DATE}),
        _engagements,
    ),
    Outil(
        "prevoir_besoins",
        "Prévoir les besoins d'achat",
        "Produits à commander pour les repas prévus (non passés) d'une période, déduction faite du stock actuel, groupés par "
        "fournisseur avec coût estimé, franco et jours de livraison.",
        _obj({"date_debut": _DATE, "date_fin": _DATE}, ["date_debut", "date_fin"]),
        _besoins,
    ),
    Outil(
        "bilan_mensuel",
        "Bilan mensuel",
        "Le point d'un mois (AAAA-MM, par défaut le dernier mois) comparé au cumul depuis septembre : synthèse, prix par repas "
        "et déficit, tendance. Rubrique « resume » par défaut ; demandez ensuite une rubrique pour le détail : labels, bio_familles, egalim_familles, origine, zones (origine par famille), "
        "categories, direct (par famille), frais (par catégorie), gammes, engagements, evolution (mois par mois).",
        _obj({"mois": {"type": "string", "description": "Mois AAAA-MM"}, "rubrique": _STR}),
        _bilan_mensuel,
    ),
    Outil(
        "produits_en_defaut",
        "Produits en défaut",
        "Pour chaque indicateur du bilan qui n'atteint pas son engagement (bio, EGalim, local, direct, frais, gammes…), les produits "
        "qui pèsent le plus dans l'écart, avec le nombre de points d'indicateur en jeu pour chacun. Période optionnelle ; "
        "indicateur = filtre sur le nom (ex. « direct », « bio »).",
        _obj({"date_debut": _DATE, "date_fin": _DATE, "indicateur": _STR, "limite_indicateurs": _INT}),
        _produits_en_defaut,
    ),
    Outil(
        "simuler_remplacement",
        "Simuler un remplacement",
        "Simule, sur une période, l'effet d'un changement d'approvisionnement sur les indicateurs à engagement (sans rien modifier) : "
        "les achats d'un ou plusieurs produits (produit = nom, mot du nom comme « frites » ou référence ; ou produit_id) ou d'un ensemble (categorie, provenance, gamme, label_egalim, "
        "direct_producteur, fournisseur) prennent une nouvelle provenance, gamme (3 = surgelés, 1 = frais), label, statut direct "
        "producteur et/ou une variation de prix. Ex. « et si ce produit UE surgelé devenait un produit frais France ? » : "
        "produit=…, nouvelle_provenance=france, nouvelle_gamme=1. Pour un remplacement par un PRODUIT RÉEL du catalogue, avec son vrai prix "
        "et un autre volume (« 80 kg de frites par 100 kg de pommes de terre ») : remplacer_par=pommes de terre (nom, référence ou "
        "remplacer_par_id), quantite_remplacee=80, quantite_remplacante=100 (ou ratio_quantite=1.25) ; le montant d'achat est alors "
        "recalculé au prix du nouveau produit. Rend les indicateurs qui changent (avant, après, points), les quantités et les montants.",
        _obj(
            {
                "produit": _STR,
                "produit_id": _INT,
                "categorie": _STR,
                "provenance": _STR,
                "gamme": _STR,
                "label_egalim": _STR,
                "direct_producteur": {"type": "boolean"},
                "fournisseur": _STR,
                "remplacer_par": _STR,
                "remplacer_par_id": _INT,
                "ratio_quantite": _NUM,
                "quantite_remplacee": _NUM,
                "quantite_remplacante": _NUM,
                "nouvelle_provenance": _STR,
                "nouvelle_gamme": _STR,
                "nouveau_label_egalim": _STR,
                "nouveau_direct_producteur": {"type": "boolean"},
                "variation_prix_pct": _NUM,
                "date_debut": _DATE,
                "date_fin": _DATE,
            }
        ),
        _simuler_remplacement,
    ),
    Outil(
        "reperer_anomalies",
        "Repérer les anomalies",
        "Contrôle les données : produits sans prix, doublons probables de produits, réceptions sans PDF / sans total / avec lignes "
        "non reliées à un produit, repas passés sans sorties (stock faussé).",
        _obj({}),
        _anomalies,
    ),
    Outil(
        "journal_actions",
        "Journal des actions",
        "Dernières actions enregistrées (qui a modifié quoi et quand). Réservé aux administrateurs. Filtres : utilisateur, "
        "entite (product, order, meal, recipe, supplier, stock…), action, date_debut.",
        _obj({"utilisateur": _STR, "entite": _STR, "action": _STR, "date_debut": _DATE, "limite": _INT}),
        _journal,
    ),
    Outil(
        "modifier_recette",
        "Modifier une recette",
        "Modifie une recette existante : nom, catégorie, description, convives (les quantités sont alors recalculées), "
        "ingrédients à retirer (produit_id ou libellé), à modifier ({ingredient, grammes_par_convive, principal}) ou à ajouter "
        "(comme pour creer_recette). Voir voir_recette pour l'état actuel.",
        _obj(
            {
                "id": _INT,
                "nom": _STR,
                "categorie": _STR,
                "description": _STR,
                "convives": _CV,
                "retirer": {"type": "array", "items": {"type": "string"}},
                "modifier": {
                    "type": "array",
                    "items": _obj(
                        {
                            "ingredient": {"type": "string"},
                            "grammes_par_convive": _NUM,
                            "principal": {"type": "boolean"},
                        },
                        ["ingredient"],
                    ),
                },
                "ajouter": {"type": "array", "items": _ING},
            },
            ["id"],
        ),
        _modifier_recette,
        True,
        _resume_modif("Modifier la recette"),
    ),
    Outil(
        "modifier_repas",
        "Modifier un repas",
        "Modifie un repas existant : date, convives, statut (prevu | en_cours | passe), menu (entree, plat, accompagnement, laitage, "
        "dessert), recettes liées (recette_<plat>_id), notes, commentaire_apres_repas. Les sorties de produits sont conservées ; "
        "pour en ajouter, utilisez saisir_sorties_repas.",
        _obj(
            {
                "id": _INT,
                "date": _DATE,
                "convives": _CV,
                "statut": _STR,
                "entree": _STR,
                "plat": _STR,
                "accompagnement": _STR,
                "laitage": _STR,
                "dessert": _STR,
                "recette_plat_id": _INT,
                "recette_entree_id": _INT,
                "recette_accompagnement_id": _INT,
                "recette_laitage_id": _INT,
                "recette_dessert_id": _INT,
                "notes": _STR,
                "commentaire_apres_repas": _STR,
            },
            ["id"],
        ),
        _modifier_repas,
        True,
        _resume_modif("Modifier le repas"),
    ),
    Outil(
        "modifier_reception",
        "Modifier une réception",
        "Corrige une réception : date, référence, type, fournisseur_id, notes, et ses lignes (par ligne_id, voir voir_reception) : "
        "quantite, unite, prix_unitaire_ht, produit_id, ou supprimer. Les prix et le total sont recalculés.",
        _obj(
            {
                "id": _INT,
                "date": _DATE,
                "reference": _STR,
                "type": {"type": "string", "description": "livraison | facture"},
                "fournisseur_id": _INT,
                "notes": _STR,
                "lignes": {
                    "type": "array",
                    "items": _obj(
                        {
                            "ligne_id": _INT,
                            "quantite": _NUM,
                            "unite": _STR,
                            "prix_unitaire_ht": _NUM,
                            "produit_id": _INT,
                            "supprimer": {"type": "boolean"},
                        },
                        ["ligne_id"],
                    ),
                },
            },
            ["id"],
        ),
        _modifier_reception,
        True,
        _resume_modif("Modifier la réception"),
    ),
    Outil(
        "ajuster_stock",
        "Ajuster le stock",
        "Inventaire : fixe la quantité réellement présente d'un produit (produit_id ou nom) ; l'écart avec le stock calculé est "
        "enregistré comme ajustement (perte, casse, erreur…). motif facultatif.",
        _obj(
            {"produit_id": _INT, "produit": _STR, "quantite_reelle": _NUM, "unite": _STR, "motif": _STR},
            ["quantite_reelle"],
        ),
        _ajuster_stock,
        True,
        lambda a: (
            f"Ajuster le stock de {a.get('produit') or 'produit ' + str(a.get('produit_id'))} à {a.get('quantite_reelle')} {a.get('unite') or ''}".strip()
        ),
    ),
    Outil(
        "modifier_fournisseur",
        "Modifier un fournisseur",
        "Modifie la fiche d'un fournisseur : nom, contact, email, telephone, adresse, franco, mode_commande, lien_commande, "
        "jours_livraison (lun, mar, mer, jeu, ven…), direct_producteur (ses produits le deviennent), notes.",
        _obj(
            {
                "id": _INT,
                "nom": _STR,
                "contact": _STR,
                "email": _STR,
                "telephone": _STR,
                "adresse": _STR,
                "franco": _NUM,
                "mode_commande": _STR,
                "lien_commande": _STR,
                "jours_livraison": {"type": "array", "items": {"type": "string"}},
                "direct_producteur": {"type": "boolean"},
                "notes": _STR,
            },
            ["id"],
        ),
        _modifier_fournisseur,
        True,
        _resume_modif("Modifier le fournisseur"),
    ),
]
