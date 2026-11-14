"""Les factures établies au nom de « Chloé Simon » sont celles de la Ferme de la Morissais."""

from cgrs.parsers.pdf_parser import guess_supplier_name, match_supplier


def test_facture_au_nom_de_l_exploitante():
    texte = "Chloé SIMON\nLa Morissais\n44170 Nozay\nFacture n° 2026-044\nDate : 03/10/2026\n"
    assert guess_supplier_name(texte, client_names=["CGRS"]) == "Ferme de la Morissais"


def test_fournisseur_existant_reconnu_par_mot_cle():
    fournisseurs = [{"id": 3, "name": "Ferme de la Morissais", "keywords": "Chloé Simon"}]
    assert match_supplier("FACTURE\nChloé Simon\nNozay", fournisseurs)["id"] == 3


def test_ligne_de_facture_sans_la_ligne_origine():
    from cgrs.parsers.pdf_parser import table_row_lines

    cols = {"code": 0, "label": 1, "price": 3, "qty": 4, "total": 6}
    ligne = [
        "55TIDCBN",
        "Chou blanc lisse\nOrigine : Fay de Bretagne",
        "Oui",
        "2.50 € / kg",
        "8 8 kg",
        "",
        "20.00",
        "5.5",
    ]
    [res] = table_row_lines(ligne, cols, {})
    assert res["label"] == "Chou blanc lisse" and res["ref"] == "55TIDCBN" and res["total_ht"] == 20.0


def test_bon_de_livraison_concerne_par_la_facture():
    from cgrs.parsers.pdf_parser import BL_CONCERNE_RE

    assert (
        BL_CONCERNE_RE.search("Date : 08/11/2026\nBon de livraison concerné : n° 31\nLivraison du 13/10").group(1)
        == "31"
    )


def test_plusieurs_bons_de_livraison_concernes():
    from cgrs.parsers.pdf_parser import BL_CONCERNE_RE

    m = BL_CONCERNE_RE.search("Bons de livraison concernés : n° 44057, 44126\nLivraison : Restaurant scolaire")
    assert m.group(1) == "44057, 44126"
    assert BL_CONCERNE_RE.search("Bon de livraison concerné : n° 31\nLivraison du 13/10").group(1) == "31"
