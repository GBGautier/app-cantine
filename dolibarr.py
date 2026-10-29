"""Export CSV pour l'assistant d'import Dolibarr : fournisseurs, produits, commandes fournisseurs.

Séparateur « ; », encodage UTF-8 avec BOM (lisible par Excel et par l'assistant d'import Dolibarr).
Les correspondances avec les listes Dolibarr (options_*) sont définies ici : si les listes
changent côté Dolibarr, c'est ce fichier qu'il faut ajuster.
"""
import csv
import io

from fastapi import Response

# catégories CGRS → id de la liste Dolibarr « options_categorie »
DOL_CATS = {
    "Fruits: pommes, poires, kiwis": 1, "Fruits: autres": 2, "Légumes": 3, "Viande de porc": 4,
    "Viande de volaille": 5, "Viande de boeuf": 6, "Produits de la pêche": 7, "Produits laitiers": 8,
    "Ovoproduits": 9, "Épicerie: légumineuses": 10, "Épicerie: céréales": 11, "Épicerie: autre": 12,
    "Pain": 13,
}
# provenance CGRS → id de la liste Dolibarr « options_provenance »
DOL_PROV = {"cc_nozay": 1, "loire_atlantique": 2, "pays_loire": 3, "france": 4, "ue": 5, "international": 6}
# label EGalim → id de la liste Dolibarr « options_label_egalim »
DOL_LABELS = {"bio": 1, "autre": 2, "sans": 3}
TVA = "5.5"   # tous les produits à 5,5 %


def dol_unit(u):
    """Unité de prix Dolibarr : 1 au KG · 2 à la pièce · 3 au Litre."""
    if u in ("kg", "g"):
        return 1
    if u in ("l", "cl", "ml"):
        return 3
    return 2


def dfr(iso):
    """2026-10-28 → 28/10/2026 (format de date attendu par l'import Dolibarr)."""
    return "/".join(reversed((iso or "").split("-"))) if iso else ""


def _csv(filename, rows):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerows(rows)
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def products_csv(db):
    """Produits : ref, libellé, prix HT, TVA, à vendre/acheter, champs personnalisés."""
    rows = [["ref", "label", "price", "tva_tx", "status", "status_buy",
             "options_categorie", "options_gamme", "options_provenance", "options_label_egalim",
             "options_unite_de_prix", "options_commerce_equitable", "options_direct_producteur"]]
    for p in db.rows("SELECT ref, name, unit_price, category, gamme, provenance, label_egalim, unit, "
                     "commerce_equitable, direct_producteur FROM products ORDER BY name"):
        rows.append([p["ref"] or "", p["name"], p["unit_price"], TVA, "1", "1",
                    DOL_CATS.get(p["category"], ""), p["gamme"] or "", DOL_PROV.get(p["provenance"], ""),
                    DOL_LABELS.get(p["label_egalim"] or "sans", ""),
                    dol_unit(p["unit"]), 1 if p["commerce_equitable"] else 0, 1 if p["direct_producteur"] else 0])
    return _csv("produits_dolibarr.csv", rows)


def suppliers_csv(db):
    """Fournisseurs : nom, adresse (découpée adresse / CP / ville si « …, CP, Ville »), contact, SIRET."""
    rows = [["name", "address", "zip", "town", "phone", "email", "idprof1", "fournisseur", "tva_assuj", "url"]]
    for s in db.rows("SELECT name, address, phone, email, siret, order_url FROM suppliers ORDER BY name"):
        adr = [x.strip() for x in (s["address"] or "").split(",")]
        rows.append([s["name"], ", ".join(adr[:-2]) if len(adr) >= 3 else (s["address"] or ""),
                     adr[-2] if len(adr) >= 3 else "", adr[-1] if len(adr) >= 3 else "",
                     s["phone"] or "", s["email"] or "", s["siret"] or "", "1", "1", s["order_url"] or ""])
    return _csv("fournisseurs_dolibarr.csv", rows)


def orders_csv(db):
    """Réceptions exportées en commandes fournisseurs : une ligne par ligne de réception."""
    rows = [["ref", "ref_fournisseur", "date_commande", "produit_ref", "produit_label", "qty", "pu_ht", "tva_tx"]]
    lines = db.rows(
        "SELECT o.ref AS order_ref, s.name AS supplier_name, o.date, "
        "COALESCE(NULLIF(p.ref, ''), NULLIF(l.ref, ''), p.name, '') AS produit_ref, "
        "l.label, l.qty, l.unit_price "
        "FROM order_lines l "
        "JOIN orders o ON o.id = l.order_id "
        "LEFT JOIN suppliers s ON s.id = o.supplier_id "
        "LEFT JOIN products p ON p.id = l.product_id "
        "WHERE l.qty IS NOT NULL AND l.qty != 0 "
        "ORDER BY o.date, o.id, l.id")
    for l in lines:
        rows.append([l["order_ref"] or "", l["supplier_name"] or "", dfr(l["date"]),
                     l["produit_ref"], l["label"] or "", l["qty"], l["unit_price"], TVA])
    return _csv("commandes_fournisseurs_dolibarr.csv", rows)


def meals_csv(db):
    """Repas exportés en commandes clientes Dolibarr (module commande) :
    une ligne par produit sorti, groupées par la référence REP-<date> du repas.
    Champs personnalisés remplis : nombre total de repas / maternelles / élémentaires / adultes."""
    client = ""
    r = db.one("SELECT value FROM settings WHERE key='client_names'")
    if r and r["value"]:
        client = r["value"].split(";")[0].strip()
    rows = [["ref", "tiers", "date_commande",
             "options_nombre_total_repas", "options_nombre_maternelles",
             "options_nombre_elementaires", "options_nombre_adultes",
             "produit_ref", "produit_label", "qty", "pu_ht", "tva_tx"]]
    lines = db.rows(
        "SELECT m.date, m.guests, m.nb_maternelles, m.nb_elementaires, m.nb_adultes, "
        "COALESCE(NULLIF(p.ref, ''), p.name) AS produit_ref, p.name AS produit_label, mi.qty, "
        "CASE WHEN mi.prix_reel IS NOT NULL THEN mi.prix_reel ELSE p.unit_price END AS pu "
        "FROM meal_items mi "
        "JOIN meals m ON m.id = mi.meal_id "
        "LEFT JOIN products p ON p.id = mi.product_id "
        "WHERE mi.qty IS NOT NULL AND mi.qty != 0 "
        "ORDER BY m.date, m.id, mi.id")
    for l in lines:
        rows.append(["REP-" + (l["date"] or ""), client, dfr(l["date"]),
                     l["guests"], l["nb_maternelles"], l["nb_elementaires"], l["nb_adultes"],
                     l["produit_ref"], l["produit_label"] or "", l["qty"], l["pu"], TVA])
    return _csv("commandes_clients_repas_dolibarr.csv", rows)