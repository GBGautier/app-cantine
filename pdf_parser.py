"""Lecture de bons de livraison / bons de commande / factures PDF de fournisseurs.

Principe : le PDF est lu page par page (OCR si la page est une image et que
`tesseract` est installé). On cherche d'abord un tableau avec en-têtes
(Réf. / Désignation / Qté / Prix / Montant), sinon on applique des profils de
lignes (regex) correspondant aux formats déjà rencontrés, puis une heuristique
générique. Chaque fournisseur peut aussi avoir sa regex (champ parser_regex)
avec les groupes nommés : code (référence), label, qty, unit, unit_price, total.
Le résultat est toujours présenté en prévisualisation avant import.
"""
import re
import shutil
import subprocess
import tempfile
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path



import pdfplumber

# ---------------------------------------------------------------- utilitaires


def to_float(s):
    if s is None:
        return None
    s = str(s).replace(" ", "").replace("\xa0", "").replace("\u202f", "")
    if "," in s:   # « 4.342,93 » : le point est un séparateur de milliers
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fnum(s):
    """Premier nombre trouvé dans une chaîne (virgule ou point décimal)."""
    m = re.search(r"(?<![\w.,])-?\d+(?:[.,]\d+)?", (s or "").replace(" ", "").replace("\xa0", ""))
    return to_float(m.group(0)) if m else None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def norm_ref(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


UNIT_MAP = {
    "k": "kg", "kg": "kg", "kilo": "kg", "p": "pièce", "pc": "pièce", "pce": "pièce", "c": "colis",
    "unité": "unité", "unités": "unité", "unite": "unité", "unites": "unité", "u": "unité",
    "pièce": "pièce", "pièces": "pièce", "piece": "pièce", "pieces": "pièce", "pu": "pièce", "sac": "sac", "col": "colis",
    "bidon": "bidon", "bidons": "bidon", "boite": "boite", "boites": "boite", "boîte": "boite", "boîtes": "boite",
}


def unit_norm(u):
    if not u:
        return None
    u = u.strip(". ").lower()
    return UNIT_MAP.get(u, u)


MONTHS = {m: i + 1 for i, m in enumerate(
    ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"])}

# ---------------------------------------------------------------- lecture du PDF


def ocr_page(page):
    """OCR d'une page-image. Renvoie '' si tesseract n'est pas installé."""
    if not shutil.which("tesseract"):
        return ""
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "page.png"
        page.to_image(resolution=250).save(str(png))
        for lang in ("fra+eng", "eng"):
            try:
                r = subprocess.run(["tesseract", str(png), "stdout", "-l", lang, "--psm", "6"],
                                   capture_output=True, text=True, timeout=120)
            except (subprocess.TimeoutExpired, OSError):
                return ""
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout
    return ""


HEAD_FIELDS = (
    ("label", ("designation", "produit", "libelle")),
    ("price", ("prix", "pu")),
    ("total", ("mont", "montant", "tt ht")),
    ("qty", ("qte", "quantite")),
    ("unit", ("unite",)),
    ("code", ("ref", "code")),
)


def classify_header(cell):
    n = norm(cell)
    if not n:
        return None
    for field, keys in HEAD_FIELDS:
        if any(n == k or n.startswith(k + " ") or (len(k) > 3 and n.startswith(k)) for k in keys):
            return field
    return "other"


def lines_from_tables(tables, carry=None):
    """Lignes d'articles à partir de tableaux avec en-têtes.
    `carry` mémorise les colonnes du dernier en-tête : un tableau qui continue sur la page suivante n'a pas d'en-tête."""
    out = []
    for table in tables:
        found = False
        for hi, row in enumerate(table):
            cols, extras, last = {}, {}, None
            for idx, c in enumerate(row):
                f = classify_header(c)
                if f in (None,):
                    if last:
                        extras.setdefault(last, []).append(idx)
                elif f == "other":
                    last = None
                elif f not in cols:
                    cols[f] = idx
                    last = f
                else:
                    last = None
            if not ("label" in cols and ("qty" in cols or "price" in cols) and ("total" in cols or "qty" in cols)):
                continue
            for r in table[hi + 1:]:
                out.extend(table_row_lines(r, cols, extras))
            found = True
            if carry is not None:
                carry.update(cols=cols, extras=extras, n=len(row))
            break
        if not found and carry and carry.get("n") == len(table[0]) and len(table[0]) >= 5:
            for r in table:
                out.extend(table_row_lines(r, carry["cols"], carry["extras"]))
    return out


def table_row_lines(r, cols, extras):
    def cell(f):
        i = cols.get(f)
        return (r[i] or "").strip() if i is not None and i < len(r) and r[i] else ""

    def extra(f):
        return " ".join((r[i] or "").strip() for i in extras.get(f, []) if i < len(r) and r[i])

    label_cell = cell("label")
    first = (r[0] or "").strip().lower() if r else ""
    if not label_cell or first.startswith(("total", "sous-total", "sous total")):
        return []
    label_lines = [l.strip() for l in label_cell.split("\n") if l.strip()]
    qty_lines = [l for l in cell("qty").split("\n") if l.strip()]
    tot_lines = [l for l in cell("total").split("\n") if l.strip()]
    ref_lines = [l.strip() for l in cell("code").split("\n") if l.strip()]
    # tableau « par colonnes » : une cellule contient toutes les lignes d'articles
    if len(label_lines) >= 2 and len(qty_lines) == len(label_lines) == len(tot_lines):
        pr = [l for l in cell("price").split("\n") if l.strip()]
        un = [l for l in cell("unit").split("\n") if l.strip()]
        res = []
        for i, lab in enumerate(label_lines):
            res.append({
                "ref": ref_lines[i] if len(ref_lines) == len(label_lines) else None,
                "label": lab, "qty": fnum(qty_lines[i]),
                "unit": unit_norm(un[i]) if i < len(un) else None,
                "unit_price": fnum(pr[i]) if i < len(pr) else None,
                "total_ht": fnum(tot_lines[i]),
            })
        return res
    total = fnum(cell("total"))
    qty = fnum(cell("qty"))
    price_cell = cell("price")
    price = fnum(price_cell)
    if total is None and qty is None:
        return []
    if total is None and price is None and "total" in cols and not cell("total") and "price" in cols:
        return []
    mu = re.search(r"€\s*/\s*([A-Za-zÀ-ÿ]+)", price_cell.replace("\n", " "))
    price_unit = unit_norm(mu.group(1)) if mu else None
    unit = unit_norm(cell("unit")) or price_unit
    mw = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|l)\b", extra("qty"), re.I)
    if mw and price_unit in ("kg", "g", "l"):  # prix au kilo : la quantité utile est le poids
        qty, unit = to_float(mw.group(1)), price_unit
    elif mw and price is None:                 # bon sans prix (« 2 | 20 kg | 2 Seau ») : on retient le poids
        qty, unit = to_float(mw.group(1)), unit_norm(mw.group(2))
    if total is None and qty is not None and price is not None:
        total = round(qty * price, 2)
    label = " ".join(label_lines + ([extra("label")] if extra("label") else []))
    label = re.sub(r"\s+", " ", label).strip(" .")
    ref = " ".join(ref_lines) or None
    return [{"ref": ref, "label": label, "qty": qty, "unit": unit, "unit_price": price, "total_ht": total}]


def read_pages(path):
    """Pages du PDF : liste de {text, table_lines, warnings}, et indicateur d'OCR."""
    pages, ocr_used, carry = [], False, {}
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            warns = []
            t = page.extract_text() or ""
            if not t.strip() and page.images:
                t = re.sub(r"[|\[\]()]", " ", ocr_page(page))
                if t:
                    ocr_used = True
                    warns.append(f"Page {i + 1} scannée : texte reconnu par OCR, à vérifier attentivement.")
                else:
                    warns.append(f"Page {i + 1} scannée (image) : OCR indisponible. Installez tesseract (avec la langue française) pour la lire.")
            try:
                tl = lines_from_tables(page.extract_tables(), carry)
            except Exception:
                tl = []
            pages.append({"text": t, "table_lines": tl, "warnings": warns})
    return pages, ocr_used


# Bandeau de page des bons : « Rest scolaire … - 28/08/2026 - BL_70618 »
PAGE_REF_RE = re.compile(r"-\s*\d{2}/\d{2}/\d{4}\s*-\s*((?:BL|BC)[_\- ]?\d+)\s*$", re.I)


def split_documents(pages):
    """Regroupe les pages par bon : un PDF peut contenir plusieurs bons (une référence BL_xxx différente en tête de page).
    Les pages sans référence rejoignent le bon précédent."""
    groups = []
    for pg in pages:
        first = next((l.strip() for l in pg["text"].splitlines() if l.strip()), "")
        m = PAGE_REF_RE.search(first)
        ref = norm_ref(m.group(1)) if m else None
        if groups and (ref is None or groups[-1]["key"] in (None, ref)):
            g = groups[-1]
            g["key"] = g["key"] or ref
        else:
            g = {"key": ref, "pages": []}
            groups.append(g)
        g["pages"].append(pg)
    return groups


# ---------------------------------------------------------------- profils de lignes (texte)

NUM = r"-?\d[\d\s]*(?:[.,]\d+)?"
N = r"-?\d+(?:[.,]\d+)?"

PROFILES = [
    # Biocoop / Manger Bio : MEBRJ5 Melon Charentais 15P L 600/780 France 2.08 € / Unité 30 62.40 5.5 2 Colis
    ("code_eur", re.compile(
        rf"^(?P<code>[A-Z0-9]{{4,}})\s+(?P<label>.+?)\s+(?P<unit_price>{N})\s*€\s*/\s*(?P<unit>[A-Za-zÀ-ÿ.]+)\s+"
        rf"(?P<qty>{N})\s+(?P<total>-?\d+[.,]\d{{2}})\b")),
    # CapMarée : 12LN559 FLT L.NOIR 150/+ V/CUT 10kg ANE - 632022 3C 30,000K 10,950 328,50 1
    ("capmaree", re.compile(
        r"^(?P<code>[0-9A-Z]{5,})\s+(?P<label>.+?)\s+(?P<qty>\d+[.,]\d{3})(?P<unit>[KPC])\s+"
        r"(?P<unit_price>\d+[.,]\d{2,3})\s+(?P<total>-?\d+[.,]\d{2})\s+\d\s*$")),
    # Viande (TEBA, souvent scannée) : 510180 CHEVEUX D'ANGE DE BOEUF BIO 120026254001 44,0 21,862 16.50 €/Kg 360,72 5.5%
    # Le montant est recalculé (poids × prix) : l'OCR lit mal les chiffres.
    ("teba", re.compile(
        r"^(?P<code>\d{4,})\s+(?P<label>.+?)\s+(?P<lot>\d{9,})\s+(?P<pieces>\S+)\s+(?P<weight>\d+[.,]\d+)\s+"
        r"(?P<unit_price>\d+[.,]\d+)\s*€?\s*/?\s*(?P<unit>[Kk]g|[Ll])\b")),
    # Grossiste (Passionfroid / Pomona) : 40/ 267328 Emmental rapé BIO 1KGx10 6,000COL 66,000SAC 9,360 F 1 617,76
    ("pomona", re.compile(
        r"^\d+/\s*(?P<code>\d{5,7})\s+(?P<label>.+?)\s+\d+[.,]\d{3}\s*[A-Z]{2,4}\s+(?P<qty>-?\d+[.,]\d{3})\s*(?P<unit>[A-Z]{1,4})\s+"
        r"(?P<unit_price>\d+[.,]\d{3})\s+[A-Z]\s+\d\s+(?P<total>-?\d+[.,]\d{2})\s*$")),
    # Graines de Bio : 1 FL017PB TOMATE ANCIENNE 15,00 7,49 10% 101,09 106,65 5,5   (n°, réf., libellé, qté[unité], PU, remise, HT, TTC, TVA)
    # Le prix est celui avant remise : on le remplace par le prix net (total ÷ quantité).
    ("graines", re.compile(
        r"^\d{1,3}\s+(?P<code>[A-Z0-9]{4,})\s+(?P<label>.+?)\s+(?P<qty>\d+[.,]\d{2})\s*(?P<unit>kg|g|l)?\s+"
        r"(?P<unit_price>\d+[.,]\d{2,3})\s+(?:(?P<rem>\d+(?:[.,]\d+)?)\s*%\s+)?"
        r"(?P<total>-?\d+[.,]\d{2})\s+-?\d+[.,]\d{2}\s+\d+(?:[.,]\d+)?\s*$", re.I)),
    # Producteur : 1 carottes kg 105,00 2,90 € 304,50 €
    ("unit_first", re.compile(
        rf"^\d{{1,3}}\s+(?P<label>.+?)\s+(?P<unit>kg|g|l|litres?|pi[eè]ces?|botte|barquette|unit[eé]s?)\s+"
        rf"(?P<qty>{N})\s+(?P<unit_price>{N})\s*€\s+(?P<total>-?\d+[.,]\d{{2}})\s*€", re.I)),
    # Factures de fermes : [Libellé] 420 unités 0,45 € 5,5 % 189,00 €
    ("platform", re.compile(
        rf"^(?:(?P<label>.+?)\s+)?(?P<qty>{N})\s+(?P<unit>unit[eé]s?|kg|g|l|litres?|pi[eè]ces?|u)\s+"
        rf"(?P<unit_price>{N})\s*€\s+(?P<tva>{N})\s*%\s+(?P<total>-?\d+[.,]\d{{2}})\s*€", re.I)),
    # Générique : libellé quantité unité PU total
    ("generic", re.compile(
        rf"^(?P<label>.*?[A-Za-zÀ-ÿ].*?)\s+(?P<qty>{NUM})\s*"
        rf"(?P<unit>kg|g|l|pc|pce|pièce|piece|u|col|colis|bt|bte|botte|barq|barquette|x)?\s+"
        rf"(?P<unit_price>\d+[.,]\d{{2,4}})\s*€?\s+(?P<total>-?\d+[.,]\d{{2}})\s*€?\s*$", re.I)),
]

SKIP_LINE = ("total", "sous-total", "sous total", "tva", "net à payer", "net a payer", "base ht")
DELIVERY_REF = re.compile(r"^(?:BL|BC)[-_ ]?[A-Z]?\d", re.I)


def parse_lines(text, custom_regex=None):
    profiles = []
    if custom_regex:
        try:
            profiles.append(("custom", re.compile(custom_regex, re.IGNORECASE)))
        except re.error:
            pass
    profiles += PROFILES
    src = [l.strip() for l in text.splitlines()]
    lines = []
    for i, raw in enumerate(src):
        if not raw or raw.lower().startswith(SKIP_LINE):
            continue
        for name, pat in profiles:
            m = pat.match(raw)
            if not m:
                continue
            g = m.groupdict()
            label = (g.get("label") or "").strip(" .-")
            if not label:  # libellé sur la ligne précédente (factures de fermes)
                for j in range(i - 1, max(i - 4, -1), -1):
                    prev = src[j]
                    if prev and not DELIVERY_REF.match(prev) and not prev.lower().startswith(SKIP_LINE):
                        label = re.sub(r"^PROFESSIONNELS\s+", "", prev, flags=re.I).strip(" .-")
                        break
            if name == "capmaree":
                label = re.sub(r"\s+[A-Z]{2,4}\s+-\s+.*$", "", label)
            label = label.lstrip("#").strip()
            qty = to_float(g.get("weight")) if g.get("weight") else to_float(g.get("qty"))
            pu = to_float(g.get("unit_price"))
            total = to_float(g.get("total"))
            if g.get("rem") and qty and total is not None:   # remise : prix net réellement payé
                pu = round(total / qty, 4)
            if (total is None or name == "teba") and qty is not None and pu is not None:
                total = round(qty * pu, 2)
            lines.append({"ref": (g.get("code") or None), "label": label, "qty": qty, "unit": unit_norm(g.get("unit")),
                          "unit_price": pu, "total_ht": total})
            break
    return lines


# ---------------------------------------------------------------- en-tête du document

DATE_RE = re.compile(r"(\d{2})[/.-](\d{2})[/.-](\d{4})")
LONG_DATE_RE = re.compile(
    r"(\d{1,2})\s*(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})",
    re.I)
DOC_TOKEN_RE = re.compile(r"\b((?:BL|BC|FA|FAC|FC)[_\- ]?\d{3,}(?:[\-/]\d+)*)\b")
INVOICE_TOKEN_RE = re.compile(r"\b((?:FA|FAC|FC)[_\- ]?\d{3,}(?:[\-/]\d+)*)\b")
FACT_NUM_RE = re.compile(r"facture\s*(?:n[°o]\s*)?[:#]?\s*([A-Z]*[\-_]?\d[\w\-/]*)", re.I)
HEADER_N_RE = re.compile(r"N°[^\n]*\n\s*\d{2}/\d{2}/\d{4}\s+(\d{3,})")
REF_RE = re.compile(
    r"(?:n[°o]|num[ée]ro|facture|commande|bon de livraison|bon)\b[ \t]*(?:n[°o]|:|#)?[ \t]*"
    r"([A-Z0-9\-/_.]*\d[A-Z0-9\-/_.]*)",
    re.IGNORECASE,
)
# bons de livraison cités sur une facture : « BL-K52438 (03/09/2026) », « BL N°7364 du … », « B.L No 333713 du … »
BL_CITED_RE = re.compile(r"\bB\.?\s?L\.?\s*(?:n[°o]\.?|:|#)?\s*[-_]?\s*([A-Z]{0,2}[-_]?\d{3,}[A-Z0-9\-_]*)", re.I)
AMOUNT = r"-?(?:\d{1,3}(?:[. \u00a0\u202f]\d{3})+|\d+)[.,]\d{2}"   # 4.342,93 · 4 342,93 · 143,01
TOTAL_RE = re.compile(rf"(?:total|montant)\s*(?:h\.?t\.?|hors taxes?)\s*:?\s*({AMOUNT})", re.IGNORECASE)
AVOIR_RE = re.compile(r"avoir\s*n[°o]\s*:?\s*([A-Z0-9][A-Z0-9\-/]*)", re.IGNORECASE)
TOTAL_NET_RE = re.compile(rf"total\s*net\s*ht\s*:?\s*({AMOUNT})", re.IGNORECASE)
TOTAL_ALT_RE = re.compile(rf"(?im)^\s*HT\s*:?\s*({AMOUNT})")

SKIP_WORDS = ("donneur", "avoir", "bon", "facture", "commande", "livraison", "date", "page", "n°", "client", "total", "tva", "siret", "émetteur", "emetteur")
HEADER_WORDS = ("qté", "qte", "quantité", "désignation", "designation", "prix", "montant", "origine", "code ")
COUNTRIES = ("france", "belgique", "espagne", "italie", "allemagne")
ADDRESS_WORDS = ("rue", "route", "avenue", "chemin", "boulevard", "bd", "place", "z.a", "za ", "zone", "impasse", "http", "www", "@")
URL_RE = re.compile(r"https?://(?:[a-z0-9\-]+\.)*?([a-z0-9\-]{4,})\.(?:fr|com|bzh|org|net|eu)", re.IGNORECASE)
GENERIC_MAIL = ("gmail", "orange", "free", "wanadoo", "hotmail", "outlook", "yahoo", "sfr", "laposte", "live", "icloud")
WWW_RE = re.compile(r"www\.([a-z0-9\-]{4,})\.(?:fr|com|bzh|org|net|eu)", re.IGNORECASE)
MAIL_RE = re.compile(r"@([a-z0-9\-]+)\.(?:fr|com|bzh|org|net|eu)", re.IGNORECASE)
ANCHOR_RE = re.compile(r"^(?:[ée]metteur|emetteur|fournisseur|vendeur|donneur d.ordre)\s*:?$", re.IGNORECASE)
TAIL_RE = re.compile(r"\s+(?:Facture|FACTURE|Date|N°|Numéro)\b.*$")


# Noms de fournisseurs mal orthographiés dans les PDF (clé : nom sans espaces ni accents, en minuscules)
SUPPLIER_ALIASES = {
    "capmaree": "Cap Marée",
}


# Fournisseurs reconnus à un mot de leur en-tête (nom proposé à la création) : (texte cherché sans espaces ni accents, nom)
KNOWN_SUPPLIERS = (
    ("episaveurs", "Episaveurs"),
    ("grainesdebio", "Graines de Bio"),
)
# Factures dont le texte du PDF est mélangé (numéro et date superposés à d'autres mots) : le nom du fichier
# « …FACTURW0000638917 20260917 8282885435.pdf » porte la date (AAAAMMJJ) et le numéro (10 chiffres).
FILENAME_REF_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})(\d{10})$")


def fix_supplier_name(name):
    return SUPPLIER_ALIASES.get(norm_ref(name), name) if name else name


def clean_company(name):
    name = name.split(",")[0].strip()
    name = re.sub(r"^(?:(?:SCIC|SAS|SARL|EURL|SA)\s+)+", "", name, flags=re.I).strip()
    return fix_supplier_name(name)


def strip_clients(line, client_names):
    """Retire de la ligne les noms du client (cantine) pour ne garder que le nom du fournisseur."""
    for c in sorted((c.strip() for c in client_names if c and c.strip()), key=len, reverse=True):
        line = re.sub(re.escape(c), " ", line, flags=re.I)
    line = re.sub(r"\bC\.?G\.?R\.?S\.?\b", " ", line, flags=re.I)
    return re.sub(r"\s+", " ", line).strip(" -:,.")


def guess_supplier_name(text, client_names=(), filename=None, ocr=False):
    """Nom de fournisseur probable ; le nom de la cantine (client) est ignoré."""
    clients = [norm(c) for c in client_names if c and c.strip()]
    is_client = lambda s: any(c and c in norm(s) for c in clients)
    lines = [l.strip() for l in text.splitlines()[:25]]  # noqa
    flat = norm_ref(" ".join(lines))
    for key, known in KNOWN_SUPPLIERS:        # 0) fournisseur connu d'avance
        if key in flat:
            return known
    for i, line in enumerate(lines):          # 1) « ÉMETTEUR » suivi du nom
        if ANCHOR_RE.match(line):
            for nxt in lines[i + 1:i + 3]:
                if not nxt:
                    continue
                if is_client(nxt):   # « BIOCOOP RESTAURATION C.G.R.S. SAFFRE » : fournisseur et client côte à côte
                    nxt = strip_clients(nxt, client_names)
                    if len(nxt) < 3:
                        continue
                    nxt = nxt.title() if nxt.isupper() else nxt
                return clean_company(nxt)
    for line in lines[:15]:                   # 2) site internet de commande en ligne
        m = URL_RE.search(line)
        if m and not is_client(line):
            return fix_supplier_name(m.group(1).capitalize())
    for line in lines:                        # 2b) domaine du mail ou du site, et la ligne qui porte ce nom (« Ferme Péard »)
        if is_client(line):
            continue
        m = MAIL_RE.search(line) or WWW_RE.search(line)
        if m and m.group(1).lower() not in GENERIC_MAIL and not ocr:
            dom = norm_ref(m.group(1))
            for cand in lines:
                if cand and len(cand) <= 40 and not is_client(cand) and not MAIL_RE.search(cand) and len(norm_ref(cand)) >= 5 \
                        and norm_ref(cand) == dom:
                    return clean_company(cand)
    if ocr:                                   # page scannée : le début du texte (logo, slogan) est peu fiable
        for line in lines:
            m = MAIL_RE.search(line)
            if m and m.group(1).lower() not in GENERIC_MAIL and not is_client(line):
                return fix_supplier_name(m.group(1).replace("-", " ").capitalize())
    for raw in lines[:14]:                    # 3) première ligne d'en-tête plausible
        line = TAIL_RE.sub("", re.split(r"\s+[A-Z]{2,4}\s*:", raw)[0])   # « PASSIONFROID OUEST ASC: certifié … »
        low = line.lower()
        if len(line) < 3 or len(line) > 70 or is_client(line) or low.strip() in COUNTRIES:
            continue
        if any(low.startswith(w) for w in SKIP_WORDS) or any(w in low for w in ADDRESS_WORDS + HEADER_WORDS):
            continue
        if sum(ch.isdigit() for ch in line) > 4 or not re.search(r"[A-Za-zÀ-ÿ]{3}", line):
            continue
        if sum(len(t) == 1 for t in line.split()) >= 2 or "(" in line:   # en-têtes de colonnes, codes…
            continue
        return clean_company(line)
    if filename:                              # 4) à défaut, le nom du fichier
        for tok in re.split(r"[-_ .]+", Path(filename).stem):
            if (len(tok) >= 4 and tok.isalpha() and not is_client(tok)
                    and tok.lower() not in ("facture", "fact", "bon", "commande", "livraison", "sept", "oct")):
                return fix_supplier_name(tok.capitalize())
    return None


def match_supplier(text, suppliers, filename=""):
    """Fournisseur reconnu par son nom ou l'un de ses mots-clés, dans le texte ou le nom du fichier.
    La comparaison est aussi faite sans espaces ni accents : « CAPMAREE » doit retrouver « Cap Marée »."""
    t = f" {norm(text)} {norm(Path(filename).stem) if filename else ''} "
    tr = norm_ref(t)
    best, score = None, 0
    for s in suppliers:
        terms = [s["name"]] + re.split(r"[;,\n]", s.get("keywords") or "")
        for term in terms:
            n, nr = norm(term), norm_ref(term)
            if (n and f" {n} " in t) or (len(nr) >= 5 and nr in tr):
                if len(nr) > score:
                    best, score = s, len(nr)
    return best


def match_product(label, products, supplier_id=None, ref=None):
    """Rattachement d'une ligne à un produit connu :
    - si la ligne a une référence : correspondance STRICTE de référence uniquement (casse/accents/espaces ignorés).
      Une référence qui ne correspond à aucun produit ne rattache jamais par libellé.
    - si la ligne n'a PAS de référence (certains bons/factures) : rapprochement par ressemblance du libellé."""
    if ref:
        r = norm_ref(ref)
        if not r:
            return None
        best = None
        for p in products:
            if not p.get("ref") or norm_ref(p["ref"]) != r:
                continue
            if supplier_id and p.get("supplier_id") == supplier_id:
                return p          # référence du même fournisseur : prioritaire
            if best is None:
                best = p          # référence trouvée chez un autre fournisseur : dernier recours
        return best
    # sans référence : rapprochement par libellé
    nl = norm(label)
    best, best_score = None, 0.0
    for p in products:
        score = SequenceMatcher(None, nl, norm(p["name"])).ratio()
        if supplier_id and p.get("supplier_id") == supplier_id:
            score += 0.05
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 0.6 else None


def doc_kind(low):
    """« facture » ou « livraison » (un bon de commande est provisoire, comme un bon de livraison)."""
    pos_f, pos_l = low.find("facture"), min([p for p in (low.find("bon de livraison"), low.find("bon de commande")) if p != -1] or [-1])
    if re.search(r"commande\s*/\s*livraison", low):
        return "livraison"
    if pos_f != -1 and (pos_l == -1 or pos_f < pos_l):
        return "facture"
    return "livraison"


def parse_pdf(path, suppliers, products, client_names=()):
    """Liste de documents lus (un par bon / facture contenu dans le PDF)."""
    pages, ocr_used = read_pages(path)
    docs = []
    for g in split_documents(pages):
        text = "\n".join(p["text"] for p in g["pages"])
        table_lines = [l for p in g["pages"] for l in p["table_lines"]]
        warnings = [w for p in g["pages"] for w in p["warnings"]]
        docs.append(parse_document(text, table_lines, warnings, ocr_used, Path(path).name, suppliers, products, client_names))
    useful = [d for d in docs if d["lines"] or not d["ignored"]]   # un « bon » qui ne contient que la cotisation interfel n'est pas une réception
    return useful or docs


def parse_document(text, table_lines, warnings, ocr_used, filename, suppliers, products, client_names=()):
    supplier = match_supplier(text, suppliers, filename)
    custom = supplier.get("parser_regex") if supplier else None
    lines = parse_lines(text, custom) if custom else (table_lines or parse_lines(text))
    if not lines and table_lines:
        lines = table_lines

    # règles de tri : pas de cotisation interfel, pas de ligne à quantité nulle
    kept, ignored = [], 0
    for l in lines:
        if "interfel" in norm(l["label"]) or "interfel" in norm(l.get("ref") or "") or (l["qty"] is not None and l["qty"] == 0):
            ignored += 1
            continue
        kept.append(l)
    lines = kept

    for l in lines:
        p = match_product(l["label"], products, supplier["id"] if supplier else None, l.get("ref"))
        l["product_id"] = p["id"] if p else None
        l["product_name"] = p["name"] if p else None
        l["product_price"] = p.get("unit_price") if p else None
        l["product_unit"] = p.get("unit") if p else None

    kind = doc_kind(text.lower())
    ref = None
    if kind == "facture":
        m = FACT_NUM_RE.search(text) or HEADER_N_RE.search(text) or INVOICE_TOKEN_RE.search(text) or REF_RE.search(text)
    else:
        m = DOC_TOKEN_RE.search(text) or HEADER_N_RE.search(text) or REF_RE.search(text)
    credit = bool(re.search(r"(?im)^\s*(?:page\s*\d+\s*/\s*\d+\s*)?avoir\s*n[°o]", text))
    if credit:                                  # avoir : note de crédit (quantités et montants négatifs), n'annule aucun bon
        am = AVOIR_RE.search(text)
        kind = "facture"
        m = None
        ref = "AV-" + am.group(1) if am else None
        warnings.append("Avoir (note de crédit) : les quantités et montants sont négatifs et viennent en déduction.")
    if m:
        ref = m.group(1).rstrip(".").replace(" ", "")
    fn_date = None
    if "episaveurs" in norm_ref(text):         # texte mélangé : numéro et date lus dans le nom du fichier
        fm = FILENAME_REF_RE.search(Path(filename).stem) if filename else None
        if fm and 1 <= int(fm.group(2)) <= 12 and 1 <= int(fm.group(3)) <= 31:
            ref = fm.group(4)
            fn_date = f"{fm.group(1)}-{fm.group(2)}-{fm.group(3)}"
            warnings.append("Numéro et date de la facture lus dans le nom du fichier (le texte du PDF est mélangé) : à vérifier.")
    date = None
    d = DATE_RE.search(text)
    if "date base" in text.lower():          # « Échéance | Date base » : la date de la facture est la date base (la plus ancienne des deux)
        m2 = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2})/(\d{2})/(\d{4})\b", text)
        if m2:
            a_, b_ = f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}", f"{m2.group(6)}-{m2.group(5)}-{m2.group(4)}"
            date = min(a_, b_)
            d = None
    if fn_date:
        date = fn_date
    elif date:
        pass
    elif d:
        date = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
    else:
        ld = LONG_DATE_RE.search(text)
        if ld:
            mon = MONTHS.get(norm(ld.group(2)))
            if mon:
                date = f"{ld.group(3)}-{mon:02d}-{int(ld.group(1)):02d}"
    total = None
    t = TOTAL_NET_RE.search(text) or TOTAL_RE.search(text) or TOTAL_ALT_RE.search(text)
    if t:
        total = to_float(t.group(1))
    sum_lines = round(sum(l["total_ht"] or 0 for l in lines), 2)
    priced = any(l["total_ht"] is not None for l in lines)
    if total is None and lines and priced:
        total = sum_lines
    elif lines and priced and total is not None and abs(sum_lines - total) > 0.05:
        warnings.append(f"La somme des lignes lues ({sum_lines:.2f} €) ne correspond pas au total HT du document ({total:.2f} €) : "
                        "une ligne manque ou un montant est faux, vérifiez avant d'enregistrer.")
    bad = 0
    for l in lines:
        if l["qty"] is not None and l["unit_price"] is not None and l["total_ht"] is not None:
            if abs(l["qty"] * l["unit_price"] - l["total_ht"]) > max(0.05, 0.01 * l["total_ht"]):
                bad += 1
    if bad:
        warnings.append(f"{bad} ligne(s) dont le montant ne correspond pas à quantité × prix unitaire : à vérifier.")

    # bons de livraison cités sur une facture (pour proposer de les remplacer)
    bl_refs = []
    if kind == "facture" and not credit:
        for m in BL_CITED_RE.finditer(text):
            r = m.group(1).rstrip("-_")
            if r and r not in bl_refs:
                bl_refs.append(r)

    guess = None if supplier else guess_supplier_name(text, client_names, filename, ocr_used)
    if not lines:
        warnings.append("Aucune ligne d'article reconnue : complétez à la main ou ajoutez une regex sur la fiche du fournisseur.")
    return {
        "supplier_id": supplier["id"] if supplier else None,
        "supplier_name": supplier["name"] if supplier else None,
        "supplier_guess": guess,
        "ref": ref,
        "date": date,
        "kind": kind,
        "total_ht": total,
        "lines": lines,
        "bl_refs": bl_refs,
        "ignored": ignored,
        "warnings": warnings,
        "text_preview": text[:1500],
    }