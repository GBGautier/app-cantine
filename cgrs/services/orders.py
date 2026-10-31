"""Règles des réceptions (bons de livraison et factures) : références, totaux, doublons, prix, rapprochement."""

import re

from cgrs.parsers import pdf_parser
from cgrs.services.units import convert


def ref_key(s):
    """Référence ramenée à sa partie significative : sans ponctuation, majuscules, sans préfixe BL / BC / FAC / FA / FC."""
    k = re.sub(r"[^A-Z0-9]", "", (s or "").upper())
    return re.sub(r"^(?:BL|BC|FAC|FA|FC)", "", k)


def order_total(o):
    """Total HT d'une réception : celui saisi, à défaut la somme des lignes (montant, sinon quantité x prix unitaire)."""
    if o.total_ht is not None:
        return o.total_ht
    return round(
        sum((l.total_ht if l.total_ht is not None else (l.qty or 0) * (l.unit_price or 0)) for l in o.lines), 2
    )


def price_in_product_unit(unit_price, line_unit, product_unit):
    """Prix d'une ligne exprimé dans l'unité du produit ; None si les unités sont incompatibles (€/kg et €/pièce).

    Sans unité d'un côté ou de l'autre, le prix est repris tel quel.
    """
    if line_unit and product_unit and convert(1, line_unit, product_unit) is None:
        return None
    price = unit_price
    if line_unit and product_unit:
        factor = convert(1, line_unit, product_unit)  # prix par unité de la ligne -> prix par unité du produit
        if factor:
            price = round(price / factor, 4)
    return price


def price_differs(a, b):
    """Deux prix sont différents (tolérance de 1e-9 pour les erreurs d'arrondi)."""
    return abs(a - b) > 1e-9


def find_duplicate_in(rows, ref, kind, supplier_id=None, exclude_id=None):
    """Première réception de `rows` ayant la même référence et le même type, chez le même fournisseur s'il est connu."""
    key = pdf_parser.norm_ref(ref or "")
    if not key:
        return None
    for r in rows:
        if (
            r["id"] != exclude_id
            and pdf_parser.norm_ref(r["ref"]) == key
            and r["kind"] == kind
            and (not supplier_id or r["supplier_id"] in (supplier_id, None))
        ):
            return r
    return None


def rank_candidates(cands, refs, total_ht):
    """Bons de livraison qu'une facture peut remplacer : marque ceux cités sur la facture ou de même montant.

    Ajoute `match` et `reason` à chaque candidat (en place), place les correspondances en premier, garde 25 résultats.
    """
    keys = {ref_key(r) for r in refs if ref_key(r)}
    for c in cands:
        reasons = []
        if ref_key(c["ref"]) and ref_key(c["ref"]) in keys:
            reasons.append("cité sur la facture")
        if total_ht is not None and c["total_ht"] is not None and abs(c["total_ht"] - total_ht) < 0.01:
            reasons.append("même montant")
        c["match"] = bool(reasons)
        c["reason"] = ", ".join(reasons)
    cands.sort(key=lambda c: not c["match"])
    return cands[:25]


def invoice_price_day(kind, current_delivery_date, replaced_dates):
    """Date des relevés de prix : une facture qui remplace des bons de livraison garde leur (plus ancienne) date."""
    dd = [d for d in [current_delivery_date, *(replaced_dates or [])] if d] if kind == "facture" else []
    return min(dd) if dd else None
