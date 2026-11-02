"""Exports : CSV pour Dolibarr ; réceptions d'une période (CSV des lignes avec indicateurs, PDF en archive zip)."""

import re
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask

from cgrs import db
from cgrs.config import UPLOADS
from cgrs.parsers import dolibarr
from cgrs.security import READ
from cgrs.services.exports import KINDS, check_period, csv_text, line_row, zip_member_name


router = APIRouter()


# ---------- Export Dolibarr (CSV pour l'assistant d'import) ----------
@router.get("/api/export/dolibarr/suppliers")
def export_dolibarr_suppliers(user: dict = READ):
    return dolibarr.suppliers_csv(db)


@router.get("/api/export/dolibarr/products")
def export_dolibarr_products(user: dict = READ):
    return dolibarr.products_csv(db)


@router.get("/api/export/dolibarr/orders")
def export_dolibarr_orders(user: dict = READ):
    return dolibarr.orders_csv(db)


@router.get("/api/export/dolibarr/meals")
def export_dolibarr_meals(user: dict = READ):
    return dolibarr.meals_csv(db)


# ---------- Réceptions d'une période ----------
KINDS_FILE = {"facture": "factures", "livraison": "bons-de-livraison", "tous": "receptions"}


def _period(date_from, date_to, kind):
    try:
        return check_period(date_from, date_to, kind)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


def _kind_filter(kind):
    return ("", ()) if kind == "tous" else (" AND o.kind=?", (kind,))


@router.get("/api/export/receptions/lignes.csv")
def export_reception_lines(date_from: str, date_to: str, kind: str = "facture", user: dict = READ):
    """Une ligne par produit reçu sur la période, avec le produit et ses indicateurs (bio, Egalim, local, direct…)."""
    date_from, date_to, kind = _period(date_from, date_to, kind)
    extra, args = _kind_filter(kind)
    lines = db.rows(
        "SELECT o.date, o.kind, o.ref AS order_ref, o.source_file, s.name AS supplier_name, "
        "l.product_id, l.ref, l.label, l.qty, l.unit, l.unit_price, l.total_ht, "
        "p.ref AS product_ref, p.name AS product_name, p.category, p.gamme, p.label_egalim, p.label_detail, "
        "p.provenance, p.direct_producteur, p.commerce_equitable "
        "FROM order_lines l JOIN orders o ON o.id=l.order_id "
        "LEFT JOIN suppliers s ON s.id=o.supplier_id LEFT JOIN products p ON p.id=l.product_id "
        "WHERE o.date >= ? AND o.date <= ?" + extra + " ORDER BY o.date, o.id, l.id",
        (date_from, date_to, *args),
    )
    for l in lines:
        l["source_file_name"] = re.sub(r"^[0-9a-f]{12}_", "", l["source_file"]) if l["source_file"] else ""
    body = "\ufeff" + csv_text(line_row(l) for l in lines)  # BOM : Excel reconnaît l'UTF-8
    name = f"lignes_{KINDS_FILE[kind]}_{date_from}_{date_to}.csv"
    return Response(
        body, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@router.get("/api/export/receptions/pdf.zip")
def export_reception_pdfs(date_from: str, date_to: str, kind: str = "facture", user: dict = READ):
    """Les PDF d'origine des réceptions de la période, dans une archive zip (un fichier par document)."""
    date_from, date_to, kind = _period(date_from, date_to, kind)
    extra, args = _kind_filter(kind)
    orders = db.rows(
        "SELECT o.id, o.date, o.ref, o.source_file, s.name AS supplier_name FROM orders o "
        "LEFT JOIN suppliers s ON s.id=o.supplier_id WHERE o.date >= ? AND o.date <= ?"
        + extra
        + " ORDER BY o.date, o.id",
        (date_from, date_to, *args),
    )
    if not orders:
        raise HTTPException(404, f"Aucun document ({KINDS[kind]}) entre le {date_from} et le {date_to}")
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    used, seen, added, missing = set(), set(), 0, 0
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_STORED) as z:
        for o in orders:
            f = o["source_file"]
            path = UPLOADS / Path(f).name if f else None
            if not path or not path.is_file():
                missing += 1
                continue
            if f in seen:  # un même PDF peut contenir plusieurs bons : un seul exemplaire dans l'archive
                continue
            seen.add(f)
            z.write(path, zip_member_name(o, used))
            added += 1
    if not added:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(404, f"Aucun PDF conservé pour ces documents ({missing} sans fichier)")
    name = f"pdf_{KINDS_FILE[kind]}_{date_from}_{date_to}.zip"
    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=name,
        headers={"X-Documents-Sans-Fichier": str(missing)},
        background=BackgroundTask(lambda: Path(tmp.name).unlink(missing_ok=True)),
    )
