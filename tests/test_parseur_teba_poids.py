"""Facture de viande scannée (disposition « Poids / PU / Montant / TVA »), texte fictif."""

from cgrs.parsers import pdf_parser

L1 = "1234 SAUCISSES DE BOEUF BIO 120000000002 11,000 25,250 12,500 315,630 5.5%"
L2 = "1234 SAUCISSES DE BOEUF BIO 120000000001 4,000 6,736 12,500 84,200 5.5%"


def test_lignes_poids_pu_montant():
    a, b = pdf_parser.parse_lines("\n".join([L1, L2]))
    assert (a["ref"], a["label"], a["qty"], a["unit"], a["unit_price"], a["total_ht"]) == (
        "1234",
        "SAUCISSES DE BOEUF BIO",
        25.25,
        "kg",
        12.5,
        315.63,
    )
    assert (b["qty"], b["total_ht"]) == (6.736, 84.2)


def test_date_de_la_piece_et_non_de_la_commande(tmp_path):
    from tests.ui.pdf_factice import pdf_minimal

    f = tmp_path / "f.pdf"
    f.write_bytes(
        pdf_minimal(
            [
                "FACTURE N°42",
                "Commande N°7 du 01/01/2030",
                "Date de la Pièce : 15/02/2030",
                "BL N°9 du 10/02/2030",
                L1,
                L2,
                "HT 399,83",
            ]
        )
    )
    d = pdf_parser.parse_pdf(str(f), [], [])[0]
    assert d["date"] == "2030-02-15"
    assert len(d["lines"]) == 2
    assert not d["warnings"]
