"""Facture de commerce avec colonnes HT et TTC (texte fictif, sans donnée réelle)."""

from cgrs.parsers import pdf_parser

LIGNE = "1234567890123A PAIN DE MIE NATURE (BL N°1234 du 01/01/26 ) 2,000 1,80 1,90 0,00 5.50 3,60 3,80"


def test_ligne_ht_ttc():
    (l,) = pdf_parser.parse_lines(LIGNE)
    assert l["ref"] == "1234567890123A"
    assert l["label"] == "PAIN DE MIE NATURE"
    assert (l["qty"], l["unit_price"], l["total_ht"]) == (2.0, 1.8, 3.6)


def test_sous_total_et_en_tete_ignores():
    texte = "\n".join(
        [
            "CODE Référence Qté Prix HT Prix TTC Rem(%) TVA Tot HT Tot TTC",
            LIGNE,
            "Sous-Total BL 1234 du 01/01/2026 3,60 3,80",
        ]
    )
    assert len(pdf_parser.parse_lines(texte)) == 1


def test_pdf_complet(tmp_path):
    from tests.ui.pdf_factice import pdf_minimal

    f = tmp_path / "f.pdf"
    f.write_bytes(
        pdf_minimal(
            [
                "Facture n° 000000000000001",
                "Date : 29/09/2026",
                "CODE Référence Qté Prix HT Prix TTC Rem(%) TVA Tot HT Tot TTC",
                LIGNE,
                "Total HT 3,60",
            ]
        )
    )
    d = pdf_parser.parse_pdf(str(f), [], [])[0]
    assert [(x["ref"], x["qty"], x["total_ht"]) for x in d["lines"]] == [("1234567890123A", 2.0, 3.6)]
    assert not d["warnings"]
