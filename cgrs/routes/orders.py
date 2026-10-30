"""Réceptions : bons de livraison et factures, import de PDF."""

import re
from datetime import date as date_cls
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

import db
import pdf_parser
from cgrs.config import UPLOADS
from cgrs.pricing import add_history, refresh_product_price
from cgrs.routes.settings import get_client_names
from cgrs.security import READ, WRITE
from cgrs.uploads import save_upload
from cgrs.utils import convert, insert, update


router = APIRouter()


class Line(BaseModel):
    create_product: bool = False   # créer le produit à partir du libellé s'il n'existe pas
    product_id: Optional[int] = None
    ref: Optional[str] = None
    label: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_ht: Optional[float] = None


class Order(BaseModel):
    supplier_id: Optional[int] = None
    ref: Optional[str] = None
    kind: str = "livraison"
    date: Optional[str] = None
    total_ht: Optional[float] = None
    source_file: Optional[str] = None
    notes: Optional[str] = None
    new_supplier_name: Optional[str] = None   # créer le fournisseur s'il n'existe pas
    new_supplier_direct: bool = False         # … et le marquer « direct producteur » (ses produits le seront aussi)
    replaces: list[int] = []                  # bons de livraison remplacés par cette facture
    lines: list[Line] = []


def ref_key(s):
    k = re.sub(r"[^A-Z0-9]", "", (s or "").upper())
    return re.sub(r"^(?:BL|BC|FAC|FA|FC)", "", k)


@router.get("/api/orders")
def orders(user: dict = READ):
    return db.rows(
        "SELECT o.*, s.name AS supplier_name, "
        "(SELECT COUNT(*) FROM order_lines l WHERE l.order_id=o.id) AS nb_lines "
        "FROM orders o LEFT JOIN suppliers s ON s.id=o.supplier_id ORDER BY o.date DESC, o.id DESC")


@router.get("/api/orders/{id}")
def get_order(id: int, user: dict = READ):
    o = db.one("SELECT * FROM orders WHERE id=?", (id,))
    if not o:
        raise HTTPException(404)
    o["lines"] = db.rows(
        "SELECT l.*, p.name AS product_name FROM order_lines l "
        "LEFT JOIN products p ON p.id=l.product_id WHERE l.order_id=? ORDER BY l.id", (id,))
    return o


def save_lines(order_id, lines):
    for l in lines:
        total = l.total_ht
        if total is None and l.qty is not None and l.unit_price is not None:
            total = round(l.qty * l.unit_price, 2)
        db.execute(
            "INSERT INTO order_lines (order_id, product_id, ref, label, qty, unit, unit_price, total_ht) VALUES (?,?,?,?,?,?,?,?)",
            (order_id, l.product_id, l.ref, l.label, l.qty, l.unit, l.unit_price, total))


def order_total(o: Order):
    if o.total_ht is not None:
        return o.total_ht
    return round(sum((l.total_ht if l.total_ht is not None else (l.qty or 0) * (l.unit_price or 0)) for l in o.lines), 2)


def resolve_creations(o: Order):
    """Crée (ou retrouve) le fournisseur et les produits demandés ; rattache les lignes par référence connue."""
    created = {"supplier": None, "products": []}
    if o.supplier_id is None and (o.new_supplier_name or "").strip():
        name = o.new_supplier_name.strip()
        found = db.one("SELECT id FROM suppliers WHERE LOWER(name)=LOWER(?)", (name,))
        if found:
            o.supplier_id = found["id"]
        else:
            o.supplier_id = db.execute("INSERT INTO suppliers (name, direct_producteur) VALUES (?,?)", (name, 1 if o.new_supplier_direct else 0))
            created["supplier"] = name
    sup = db.one("SELECT * FROM suppliers WHERE id=?", (o.supplier_id,)) if o.supplier_id else None
    for l in o.lines:
        if l.product_id is not None:
            continue
        if l.ref:   # référence déjà connue : on rattache au produit existant
            q = "SELECT id FROM products WHERE LOWER(ref)=LOWER(?)" + (" AND supplier_id=?" if o.supplier_id else "")
            found = db.one(q, (l.ref, o.supplier_id) if o.supplier_id else (l.ref,))
            if found:
                l.product_id = found["id"]
                continue
        if not l.create_product:
            continue
        name = (l.label or "").strip()
        if not name:
            continue
        found = db.one("SELECT id FROM products WHERE LOWER(name)=LOWER(?) AND COALESCE(supplier_id,0)=COALESCE(?,0)",
                       (name, o.supplier_id))
        if found:
            l.product_id = found["id"]
            continue
        l.product_id = db.execute(
            "INSERT INTO products (ref, name, supplier_id, label_egalim, provenance, direct_producteur, unit) VALUES (?,?,?,?,?,?,?)",
            (l.ref, name, o.supplier_id, "bio", sup["local_default"] if sup else None,
             sup["direct_producteur"] if sup else 0, l.unit or "kg"))
        created["products"].append(name)
    return created


def update_prices(order_id, o: Order, day=None):
    """Met à jour le prix des produits quand il change et alimente l'historique ; apprend les références.

    `day` : date des relevés. Une facture qui remplace des bons de livraison garde la date de livraison
    (c'est à partir de ce jour-là que le prix s'applique, pas à partir de la date de la facture).
    """
    changes = []
    day = day or o.date or date_cls.today().isoformat()
    for l in o.lines:
        if l.product_id is None:
            continue
        p = db.one("SELECT * FROM products WHERE id=?", (l.product_id,))
        if not p:
            continue
        if l.ref and not (p["ref"] or "").strip():
            db.execute("UPDATE products SET ref=? WHERE id=?", (l.ref, p["id"]))
        if l.unit_price is None:
            continue
        # le prix n'est comparé que si les unités sont compatibles (€/kg avec €/kg, pas avec €/pièce)
        if l.unit and p["unit"] and convert(1, l.unit, p["unit"]) is None:
            continue
        price = l.unit_price
        if l.unit and p["unit"]:
            factor = convert(1, l.unit, p["unit"])   # prix par unité de la ligne -> prix par unité du produit
            if factor:
                price = round(price / factor, 4)
        last = db.one("SELECT price, date FROM price_history WHERE product_id=? ORDER BY date DESC, id DESC LIMIT 1", (p["id"],))
        if last is None or abs(last["price"] - price) > 1e-9:
            add_history(p["id"], day, price, p["unit"], order_id, "reception")
            if last is None or (last["date"] or "") <= day:
                if p["unit_price"] is None or abs(p["unit_price"] - price) > 1e-9:
                    changes.append({"name": p["name"], "old": p["unit_price"], "new": price, "unit": p["unit"]})
                db.execute("UPDATE products SET unit_price=? WHERE id=?", (price, p["id"]))
    return changes


def remove_order(order_id):
    pids = [r["product_id"] for r in db.rows("SELECT DISTINCT product_id FROM price_history WHERE order_id=?", (order_id,))]
    db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    for pid in pids:
        refresh_product_price(pid)


def price_day(order_id, o: Order, rdates):
    """Date des relevés de prix : une facture qui remplace des bons de livraison garde leur date de livraison."""
    cur = db.one("SELECT delivery_date FROM orders WHERE id=?", (order_id,))
    dd = [d for d in [cur and cur["delivery_date"], *(rdates or [])] if d] if o.kind == "facture" else []
    day = min(dd) if dd else None
    db.execute("UPDATE orders SET delivery_date=? WHERE id=?", (day, order_id))
    return day


def delete_replaced(ids, new_id, supplier_id):
    """Supprime les bons de livraison remplacés par la facture ; renvoie leur description."""
    done, dates = [], []
    for rid in ids:
        r = db.one("SELECT * FROM orders WHERE id=?", (rid,))
        if not r or r["kind"] != "livraison" or rid == new_id:
            continue
        if supplier_id and r["supplier_id"] and r["supplier_id"] != supplier_id:
            continue
        done.append(f"{r['ref'] or 'BL'} du {r['date'] or '?'}")
        if r["date"]:
            dates.append(r["date"])
        remove_order(rid)
    return done, dates


def normalize_order(o: Order):
    o.kind = "facture" if o.kind == "facture" else "livraison"
    if o.kind != "facture":
        o.replaces = []


def find_duplicate(ref, kind, supplier_id=None, exclude_id=None):
    """Réception déjà enregistrée avec la même référence (et le même type, chez le même fournisseur s'il est connu)."""
    key = pdf_parser.norm_ref(ref or "")
    if not key:
        return None
    for r in db.rows("SELECT o.id, o.ref, o.kind, o.date, o.supplier_id, s.name AS supplier_name FROM orders o "
                     "LEFT JOIN suppliers s ON s.id=o.supplier_id WHERE o.ref IS NOT NULL AND o.ref != ''"):
        if (r["id"] != exclude_id and pdf_parser.norm_ref(r["ref"]) == key and r["kind"] == kind
                and (not supplier_id or r["supplier_id"] in (supplier_id, None))):
            return r
    return None


@router.post("/api/orders")
def create_order(o: Order, user: dict = WRITE):
    normalize_order(o)
    dup = find_duplicate(o.ref, o.kind, o.supplier_id)
    if dup:
        raise HTTPException(409, f"{'La facture' if dup['kind'] == 'facture' else 'Le bon de livraison'} {dup['ref']} est déjà enregistré"
                                 f"{' (' + dup['supplier_name'] + ')' if dup['supplier_name'] else ''} : import refusé.")
    created = resolve_creations(o)
    o.total_ht = order_total(o)
    oid = insert("orders", o, exclude=("lines", "new_supplier_name", "new_supplier_direct", "replaces"))
    save_lines(oid, o.lines)
    replaced, rdates = delete_replaced(o.replaces, oid, o.supplier_id)   # d'abord : l'historique de prix des bons remplacés disparaît avec eux
    price_updates = update_prices(oid, o, price_day(oid, o, rdates))
    if replaced:
        note = "Remplace : " + " ; ".join(replaced)
        db.execute("UPDATE orders SET notes=? WHERE id=?", ((o.notes + "\n" if o.notes else "") + note, oid))
    return {"id": oid, "created": created, "price_updates": price_updates, "replaced": replaced}


@router.put("/api/orders/{id}")
def edit_order(id: int, o: Order, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM orders WHERE id=?", (id,)):
        raise HTTPException(404)
    normalize_order(o)
    dup = find_duplicate(o.ref, o.kind, o.supplier_id, exclude_id=id)
    if dup:
        raise HTTPException(409, f"Un autre enregistrement porte déjà la référence {dup['ref']} : modification refusée.")
    created = resolve_creations(o)
    o.total_ht = order_total(o)
    old_pids = [r["product_id"] for r in db.rows("SELECT DISTINCT product_id FROM price_history WHERE order_id=?", (id,))]
    db.execute("DELETE FROM price_history WHERE order_id=?", (id,))
    update("orders", id, o, exclude=("lines", "new_supplier_name", "new_supplier_direct", "replaces"))
    db.execute("DELETE FROM order_lines WHERE order_id=?", (id,))
    save_lines(id, o.lines)
    replaced, rdates = delete_replaced(o.replaces, id, o.supplier_id)
    price_updates = update_prices(id, o, price_day(id, o, rdates))
    for pid in old_pids:
        refresh_product_price(pid)
    if replaced:
        note = "Remplace : " + " ; ".join(replaced)
        db.execute("UPDATE orders SET notes=? WHERE id=?", ((o.notes + "\n" if o.notes else "") + note, id))
    return {"ok": True, "created": created, "price_updates": price_updates, "replaced": replaced}


@router.delete("/api/orders/{id}")
def delete_order(id: int, user: dict = WRITE):
    remove_order(id)
    return {"ok": True}


class CandidateQuery(BaseModel):
    supplier_id: Optional[int] = None
    kind: str = "facture"
    total_ht: Optional[float] = None
    refs: list[str] = []
    exclude_id: Optional[int] = None


@router.post("/api/orders/candidates")
def replacement_candidates(q: CandidateQuery, user: dict = WRITE):
    """Bons de livraison du fournisseur qu'une facture peut remplacer (cités sur la facture ou de même montant)."""
    if q.kind != "facture" or not q.supplier_id:
        return []
    cands = db.rows(
        "SELECT id, ref, date, total_ht FROM orders WHERE supplier_id=? AND kind='livraison' AND id != ? "
        "ORDER BY date DESC, id DESC LIMIT 60", (q.supplier_id, q.exclude_id or -1))
    keys = {ref_key(r) for r in q.refs if ref_key(r)}
    for c in cands:
        reasons = []
        if ref_key(c["ref"]) and ref_key(c["ref"]) in keys:
            reasons.append("cité sur la facture")
        if q.total_ht is not None and c["total_ht"] is not None and abs(c["total_ht"] - q.total_ht) < 0.01:
            reasons.append("même montant")
        c["match"] = bool(reasons)
        c["reason"] = ", ".join(reasons)
    cands.sort(key=lambda c: not c["match"])
    return cands[:25]


@router.post("/api/orders/parse-pdf")
async def parse_pdf(file: UploadFile = File(...), user: dict = WRITE):
    """Lit un PDF et renvoie une prévisualisation (rien n'est enregistré, le fichier est conservé)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    name = await save_upload(file, allowed={".pdf"})
    try:
        docs = pdf_parser.parse_pdf(
            str(UPLOADS / name), db.rows("SELECT * FROM suppliers"), db.rows("SELECT * FROM products"),
            client_names=get_client_names())
    except Exception as e:  # PDF illisible
        (UPLOADS / name).unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}")
    for d in docs:
        d["source_file"] = name
        dup = find_duplicate(d.get("ref"), d.get("kind"), d.get("supplier_id"))
        d["duplicate"] = ({"ref": dup["ref"], "date": dup["date"], "supplier_name": dup["supplier_name"]} if dup else None)
        d.pop("text_preview", None)   # contient parfois des coordonnées bancaires : inutile côté navigateur
    if docs and all(d["duplicate"] for d in docs):
        (UPLOADS / name).unlink(missing_ok=True)   # rien de nouveau : on ne garde pas le fichier en double
    return {"documents": docs, "source_file": name, "source_label": Path(file.filename).name}


@router.post("/api/orders/{id}/upload-pdf")
async def upload_order_pdf(id: int, file: UploadFile = File(...), user: dict = WRITE):
    """Attache un PDF (BL ou facture) à une réception existante."""
    if not db.one("SELECT 1 AS x FROM orders WHERE id=?", (id,)):
        raise HTTPException(404)
    name = await save_upload(file, allowed={".pdf"})
    # Suppression de l'ancien fichier s'il existait
    old = db.one("SELECT source_file FROM orders WHERE id=?", (id,))
    if old and old["source_file"]:
        (UPLOADS / Path(old["source_file"]).name).unlink(missing_ok=True)
    db.execute("UPDATE orders SET source_file=? WHERE id=?", (name, id))
    return {"source_file": name}


@router.delete("/api/orders/{id}/upload-pdf")
def delete_order_pdf(id: int, user: dict = WRITE):
    """Supprime le PDF attaché à une réception."""
    r = db.one("SELECT source_file FROM orders WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    if r["source_file"]:
        (UPLOADS / Path(r["source_file"]).name).unlink(missing_ok=True)
    db.execute("UPDATE orders SET source_file=NULL WHERE id=?", (id,))
    return {"ok": True}
