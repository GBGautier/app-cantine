"""Export des réceptions sur une période : contrôle de la période, lignes du CSV avec indicateurs, noms des fichiers du zip.

Sans base ni serveur : les fonctions reçoivent des lignes déjà lues.
"""

import csv
import io
import re
import unicodedata
from datetime import date

from cgrs.constants import LOCAL, PROVENANCES
from cgrs.services.orders import line_total
from cgrs.services.xlsx import xlsx_bytes

KINDS = {"facture": "factures", "livraison": "bons de livraison", "tous": "factures et bons de livraison"}

CSV_HEADER = [
    "date",
    "type",
    "reference_reception",
    "fournisseur",
    "reference_produit",
    "produit",
    "categorie",
    "gamme",
    "quantite",
    "unite",
    "prix_unitaire_ht",
    "montant_ht",
    "label_egalim",
    "detail_label",
    "provenance",
    "bio",
    "egalim",
    "local",
    "direct_producteur",
    "commerce_equitable",
    "fichier_pdf",
]


def check_period(date_from, date_to, kind):
    """Période et type demandés : rend (date_from, date_to, kind) ou lève ValueError avec un message lisible."""
    if kind not in KINDS:
        raise ValueError("Type inconnu : facture, livraison ou tous")
    try:
        d1, d2 = date.fromisoformat(date_from or ""), date.fromisoformat(date_to or "")
    except ValueError:
        raise ValueError("Dates attendues au format AAAA-MM-JJ") from None
    if d1 > d2:
        raise ValueError("La date de début est après la date de fin")
    return d1.isoformat(), d2.isoformat(), kind


def _num(value):
    """Nombre au format français (virgule), vide s'il est inconnu : le CSV s'ouvre directement dans Excel."""
    if value is None:
        return ""
    text = f"{round(float(value), 4):.4f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _yes(flag):
    return "oui" if flag else "non"


def line_row(line):
    """Une ligne du CSV : la ligne de réception, son produit et les indicateurs (mêmes définitions que les statistiques).

    Une ligne sans produit rattaché garde ses informations et laisse les indicateurs vides.
    """
    known = line.get("product_id") is not None
    label, provenance = line.get("label_egalim"), line.get("provenance")
    return [
        line.get("date") or "",
        "facture" if line.get("kind") == "facture" else "bon de livraison",
        line.get("order_ref") or "",
        line.get("supplier_name") or "",
        line.get("product_ref") or line.get("ref") or "",
        line.get("product_name") or line.get("label") or "",
        line.get("category") or "",
        line.get("gamme") or "",
        _num(line.get("qty")),
        line.get("unit") or "",
        _num(line.get("unit_price")),
        _num(line_total(line.get("qty"), line.get("unit_price"), line.get("total_ht"))),
        (label or "") if known else "",
        line.get("label_detail") or "",
        PROVENANCES.get(provenance, provenance or "") if known else "",
        _yes(label == "bio") if known else "",
        _yes(label in ("bio", "autre")) if known else "",
        _yes(provenance in LOCAL) if known else "",
        _yes(line.get("direct_producteur")) if known else "",
        _yes(line.get("commerce_equitable")) if known else "",
        line.get("source_file_name") or "",
    ]


def csv_text(rows):
    """Texte CSV (séparateur « ; », fins de ligne Windows) avec l'en-tête ; l'appelant ajoute le BOM pour Excel."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(CSV_HEADER)
    w.writerows(rows)
    return buf.getvalue()


# colonnes du classeur Excel : vraies dates et vrais nombres (le CSV, lui, écrit des textes avec virgule décimale)
DATE_COLUMNS = ("date",)
NUMBER_COLUMNS = ("quantite", "prix_unitaire_ht", "montant_ht")


def xlsx_lines(rows):
    """Classeur Excel (octets) des mêmes lignes que le CSV."""
    return xlsx_bytes(CSV_HEADER, rows, DATE_COLUMNS, NUMBER_COLUMNS, "Lignes de réception")


def safe_name(text, limit=40):
    """Morceau de nom de fichier : lettres, chiffres, tirets ; sans accents ni caractères interdits sous Windows."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-")[:limit]


def zip_member_name(order, used):
    """Nom d'un PDF dans le zip : AAAA-MM-JJ_fournisseur_reference.ext, rendu unique dans `used` (ensemble modifié)."""
    stem = "_".join(
        p
        for p in (order.get("date") or "sans-date", safe_name(order.get("supplier_name")), safe_name(order.get("ref")))
        if p
    )
    ext = ("." + order["source_file"].rsplit(".", 1)[-1].lower()) if "." in (order.get("source_file") or "") else ".pdf"
    name, n = stem + ext, 2
    while name in used:
        name = f"{stem}-{n}{ext}"
        n += 1
    used.add(name)
    return name
