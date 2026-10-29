"""Lecture de menus scolaires en PDF.

Le PDF est structuré en tableau avec les colonnes = jours de la semaine et
les lignes = catégories (Entrée, Plat, Accompagnement, Laitage, Dessert).
On renvoie une liste de dict :
  { date, entree, plat, accompagnement, laitage, dessert }
"""
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import pdfplumber

MONTHS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

DAYS_FR = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4,
    "samedi": 5, "dimanche": 6,
}

CAT_MAP = {
    "entree": "entree", "entrée": "entree",
    "plat": "plat",
    "accompagnement": "accompagnement", "acompagnement": "accompagnement",
    "laitage": "laitage",
    "dessert": "dessert",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def clean_value(val, cat=None):
    """Nettoie une valeur de cellule :
    - supprime tous les '*'
    - supprime les mots isolés 'n' / 'nt' (reliquats de 'Accompagnement' tronqué)
      pour la catégorie accompagnement."""
    val = (val or "").replace("*", " ")
    if cat == "accompagnement":
        toks = [t for t in val.split() if t.lower() not in ("n", "nt", "t")]
        val = " ".join(toks)
    return " ".join(val.split()).strip()


CANON_CATS = ["entree", "plat", "accompagnement", "laitage", "dessert"]


def classify_cat(cell):
    """Reconnaît une catégorie même tronquée ou mal orthographiée
    (Acompagnement, Acompagnemen, Accompagneme, "Accompagneme nt"...)."""
    n = norm(cell).replace(" ", "")
    if not n:
        return None
    # exact / avec fautes connues
    for k, v in CAT_MAP.items():
        if n == norm(k).replace(" ", ""):
            return v
    # texte tronqué : préfixe d'au moins 3 lettres d'une catégorie
    if len(n) >= 3:
        for c in CANON_CATS:
            if c.startswith(n):
                return c
    # début de cellule = catégorie complète (ex. "Plat principal")
    for k, v in CAT_MAP.items():
        kk = norm(k).replace(" ", "")
        if n.startswith(kk):
            return v
    # fautes de frappe : similarité
    if len(n) >= 4:
        import difflib
        close = difflib.get_close_matches(n, CANON_CATS, n=1, cutoff=0.78)
        if close:
            return close[0]
    return None


NUMERIC_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})(?!\d)")


def resolve_year(day_name, day_num, month_num, year, doc_year):
    """Année d'une date d'en-tête. Les menus suivent l'année scolaire (septembre à août) : septembre-décembre
    tombent l'année de départ, janvier-août l'année suivante. Si l'en-tête donne le nom du jour, l'année
    retenue est celle où ce jour de la semaine tombe bien ce jour-là ; une année mal tapée dans le PDF
    (« 05/10/2027 » pour un lundi 5 octobre 2026) est ainsi corrigée."""
    base = doc_year or datetime.today().year
    school = base if month_num >= 8 else base + 1
    cands = []
    for y in (year, school, base, base + 1, base - 1):
        if y and y not in cands:
            cands.append(y)
    wd = DAYS_FR.get(day_name) if day_name else None
    if wd is not None:
        for y in cands:
            try:
                if datetime(y, month_num, day_num).weekday() == wd:
                    return y
            except ValueError:
                continue
        return year or school
    # pas de nom de jour : on garde l'année écrite si elle est dans l'année scolaire, sinon on la corrige
    if year and (base if month_num >= 8 else base + 1) == year:
        return year
    return school


def parse_date_header(text):
    """Extrait (jour_semaine, jour_num, mois_num, annee) d'une cellule d'en-tête."""
    text_l = text.lower().strip()
    # Ex: "lundi 30 novembre" ou "lundi 30 novembre 2026"
    m = re.search(
        r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+(\d{1,2})\s+"
        r"(janvier|f[\u00e9e]vrier|mars|avril|mai|juin|juillet|ao[u\u00fb]t|septembre|octobre|novembre|d[\u00e9e]cembre)"
        r"(?:\s+(\d{4}))?",
        text_l,
    )
    if m:
        day_name = m.group(1)
        day_num = int(m.group(2))
        month_str = unicodedata.normalize("NFKD", m.group(3)).encode("ascii", "ignore").decode().lower()
        month_num = MONTHS_FR.get(month_str)
        year = int(m.group(4)) if m.group(4) else None
        return day_name, day_num, month_num, year
    # Ex: "05/10/2026 (rouge)" ou "16/10/2026 (Halloween)" : date numérique, sans nom de jour
    m = NUMERIC_DATE_RE.search(text_l)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(1)) <= 31:
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return None, int(m.group(1)), int(m.group(2)), year
    return None


def infer_year(day_num, month_num, context_year=None):
    """Déduit l'année à partir du contexte (année scolaire courante)."""
    if context_year:
        return context_year
    today = datetime.today()
    # Essaie l'année en cours, puis +1, puis -1
    for y in [today.year, today.year + 1, today.year - 1]:
        try:
            datetime(y, month_num, day_num)
            return y
        except ValueError:
            continue
    return today.year


def build_date(day_num, month_num, year):
    try:
        return datetime(year, month_num, day_num).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _empty_meal(date):
    return {"date": date, "entree": None, "plat": None,
            "accompagnement": None, "laitage": None, "dessert": None}


def _header_col_dates(row, doc_year):
    """Mapping colonne -> date ISO pour une ligne d'en-tête, {} si pas de dates."""
    cols = {}
    for col_idx, cell in enumerate(row):
        if not cell:
            continue
        parsed = parse_date_header(str(cell))
        if not parsed:
            continue
        day_name, day_num, month_num, year = parsed
        if month_num is None:
            continue
        year = resolve_year(day_name, day_num, month_num, year, doc_year)
        date_str = build_date(day_num, month_num, year)
        if date_str:
            cols[col_idx] = date_str
    return cols


def parse_menu_tables(tables, doc_year=None, ctx=None):
    """Extrait les menus depuis les tableaux pdfplumber.

    Gère plusieurs semaines dans un même tableau (une ligne d'en-tête de dates
    démarre un nouveau bloc) et les tableaux de suite de page sans en-tête
    (on réutilise les colonnes du dernier en-tête, via ctx).
    """
    if ctx is None:
        ctx = {}
    results = []
    for table in tables:
        if not table:
            continue
        col_dates = ctx.get("col_dates")  # reprise d'un bloc commencé sur la page précédente
        meals = ctx.get("meals") if col_dates else None

        def flush():
            nonlocal meals
            if meals:
                results.extend(meals.values())
            meals = None

        for row in table:
            if not row:
                continue
            new_cols = _header_col_dates(row, doc_year)
            if new_cols:
                # nouvelle semaine : on termine la précédente
                flush()
                col_dates = new_cols
                meals = {d: _empty_meal(d) for d in col_dates.values()}
                continue
            if not col_dates or meals is None:
                continue

            # La cellule de catégorie est à gauche de la première colonne de date
            first_date_col = min(col_dates)
            cat_cells = row[:max(1, first_date_col)]
            cat = None
            for cell in cat_cells:
                if cell:
                    cat = classify_cat(str(cell))
                    if cat:
                        break
            if not cat:
                continue

            for col_idx, date_str in col_dates.items():
                if col_idx < len(row) and row[col_idx]:
                    val = clean_value(str(row[col_idx]), cat)
                    if val and val not in ("-", "\u2014"):
                        prev = meals[date_str][cat]
                        # une même catégorie sur plusieurs lignes : on concatène
                        meals[date_str][cat] = (prev + " " + val) if prev else val

        # fin de tableau : le bloc reste ouvert pour une éventuelle suite sur la page
        # suivante (mêmes dicts, complétés en place ; doublons fusionnés ensuite)
        ctx["col_dates"] = col_dates
        ctx["meals"] = meals
        if meals:
            results.extend(meals.values())
    return results


def parse_menu_pdf(path):
    """Lit un PDF de menus et retourne une liste de repas."""
    results = []
    doc_year = None

    with pdfplumber.open(path) as pdf:
        full_text = ""
        for page in pdf.pages:
            t = page.extract_text() or ""
            full_text += t + "\n"

        # Détecte l'année globale
        year_match = re.search(r"\b(20\d{2})\b", full_text)
        doc_year = int(year_match.group(1)) if year_match else None

        ctx = {}
        for page in pdf.pages:
            tables = page.extract_tables()
            page_results = parse_menu_tables(tables, doc_year, ctx) if tables else []
            if page_results:
                results.extend(page_results)
            else:
                # Fallback: parse texte brut
                t = page.extract_text() or ""
                if t:
                    # Tente de parser le texte en cherchant les patterns de date
                    text_results = parse_menu_from_raw_text(t, doc_year)
                    results.extend(text_results)

    # Déduplique par date
    # (fusion : on complète les catégories vides au lieu d'ignorer les doublons)
    seen = {}
    for r in results:
        d = r.get("date")
        if not d:
            continue
        if d not in seen:
            seen[d] = dict(r)
        else:
            for k, v in r.items():
                if v and not seen[d].get(k):
                    seen[d][k] = v
    return sorted(seen.values(), key=lambda x: x["date"])


def parse_menu_from_raw_text(text, doc_year=None):
    """Parse le texte brut d'une page de menu (fallback sans tableau)."""
    results = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    date_pattern = re.compile(
        r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+(\d{1,2})\s+"
        r"(janvier|f[\u00e9e]vrier|mars|avril|mai|juin|juillet|ao[u\u00fb]t|septembre|octobre|novembre|d[\u00e9e]cembre)"
        r"(?:\s+(\d{4}))?",
        re.IGNORECASE,
    )

    # Cherche les lignes qui semblent être des en-têtes de semaine
    header_lines = []
    for i, line in enumerate(lines):
        dates_in_line = list(date_pattern.finditer(line))
        if len(dates_in_line) >= 2:
            header_lines.append((i, dates_in_line))

    for header_idx, (line_idx, date_matches) in enumerate(header_lines):
        # Détermine la plage de lignes pour cette semaine
        end_idx = header_lines[header_idx + 1][0] if header_idx + 1 < len(header_lines) else len(lines)
        week_lines = lines[line_idx + 1:end_idx]

        # Construit les colonnes de dates
        ordered_dates = []
        for m in date_matches:
            day_num = int(m.group(2))
            month_str = unicodedata.normalize("NFKD", m.group(3)).encode("ascii", "ignore").decode().lower()
            month_num = MONTHS_FR.get(month_str)
            year = resolve_year(m.group(1).lower(), day_num, month_num, int(m.group(4)) if m.group(4) else None, doc_year)
            date_str = build_date(day_num, month_num, year)
            if date_str:
                ordered_dates.append(date_str)

        if not ordered_dates:
            continue

        meals = {d: {"date": d, "entree": None, "plat": None,
                     "accompagnement": None, "laitage": None, "dessert": None}
                 for d in ordered_dates}

        # Cherche les lignes de catégories dans les lignes suivantes
        # Format typique: "EntreeValeur1Valeur2Valeur3Valeur4" ou "Entree Valeur1 Valeur2..."
        for wline in week_lines:
            cat = None
            rest = wline
            first = re.match(r"^\s*(\S+)\s*", wline)
            if first:
                c = classify_cat(first.group(1))
                if c:
                    cat = c
                    rest = wline[first.end():].strip()

            if not cat:
                continue

            # Essaie de séparer les valeurs par tab ou par pattern de majuscule
            parts = re.split(r"\t+", rest)
            if len(parts) < 2:
                # Tente de séparer par *
                parts = [p.strip() for p in rest.split("*") if p.strip()]

            for i, d in enumerate(ordered_dates):
                if i < len(parts):
                    cleaned = clean_value(parts[i], cat)
                    if cleaned:
                        meals[d][cat] = cleaned

        results.extend(meals.values())

    return results
