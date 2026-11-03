"""Classeur Excel (.xlsx) minimal, écrit avec la bibliothèque standard (aucune dépendance à ajouter).

Une seule feuille : en-tête en gras et figé, filtre automatique, colonnes ajustées, nombres et dates typés.
"""

import io
import re
import zipfile
from datetime import date
from xml.sax.saxutils import escape

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")  # caractères interdits en XML 1.0
_EPOCH = date(1899, 12, 30)  # origine des numéros de série d'Excel

# styles : 0 normal, 1 en-tête (gras), 2 date jj/mm/aaaa, 3 nombre à 2 décimales ou plus
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="2"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/>'
    '<numFmt numFmtId="165" formatCode="#,##0.00##"/></numFmts>'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="4">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    "</cellXfs></styleSheet>"
)


def _col(n):
    """Lettre(s) de la colonne n (0 = A)."""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, value, kind):
    if value is None or value == "":
        return ""
    if kind == "date":
        try:
            return f'<c r="{ref}" s="2"><v>{(date.fromisoformat(value) - _EPOCH).days}</v></c>'
        except ValueError:
            pass  # date illisible : gardée telle quelle, en texte
    elif kind == "number":
        try:
            return f'<c r="{ref}" s="3"><v>{float(str(value).replace(",", "."))!r}</v></c>'
        except ValueError:
            pass
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(_CTRL.sub("", str(value)))}</t></is></c>'


def xlsx_bytes(header, rows, date_cols=(), number_cols=(), sheet_name="Export"):
    """Classeur .xlsx (octets). `date_cols` : dates AAAA-MM-JJ ; `number_cols` : nombres (virgule ou point décimal)."""
    rows = [list(r) for r in rows]
    kinds = ["date" if h in date_cols else "number" if h in number_cols else "text" for h in header]
    out = []
    head = "".join(
        f'<c r="{_col(i)}1" s="1" t="inlineStr"><is><t>{escape(h)}</t></is></c>' for i, h in enumerate(header)
    )
    out.append(f'<row r="1">{head}</row>')
    widths = [min(max(len(h) + 2, 10), 40) for h in header]
    for n, row in enumerate(rows, start=2):
        cells = "".join(_cell(f"{_col(i)}{n}", v, kinds[i]) for i, v in enumerate(row))
        out.append(f'<row r="{n}">{cells}</row>')
        for i, v in enumerate(row):
            if kinds[i] == "text":
                widths[i] = min(max(widths[i], len(str(v)) + 2), 60)
    cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths))
    last = f"{_col(len(header) - 1)}{len(rows) + 1}"
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        f"<cols>{cols}</cols><sheetData>{''.join(out)}</sheetData>"
        f'<autoFilter ref="A1:{last}"/></worksheet>'
    )
    name = escape(re.sub(r"[\[\]:*?/\\]", "", sheet_name)[:31] or "Export", {'"': "&quot;"})
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{name}" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>"
        ),
        "xl/styles.xml": _STYLES,
        "xl/worksheets/sheet1.xml": sheet,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, xml in parts.items():
            z.writestr(path, xml)
    return buf.getvalue()
