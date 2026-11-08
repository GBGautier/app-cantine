"""Les factures établies au nom de « Chloé Simon » sont celles de la Ferme de la Morissais."""

from cgrs.parsers.pdf_parser import guess_supplier_name, match_supplier


def test_facture_au_nom_de_l_exploitante():
    texte = "Chloé SIMON\nLa Morissais\n44170 Nozay\nFacture n° 2026-044\nDate : 03/10/2026\n"
    assert guess_supplier_name(texte, client_names=["CGRS"]) == "Ferme de la Morissais"


def test_fournisseur_existant_reconnu_par_mot_cle():
    fournisseurs = [{"id": 3, "name": "Ferme de la Morissais", "keywords": "Chloé Simon"}]
    assert match_supplier("FACTURE\nChloé Simon\nNozay", fournisseurs)["id"] == 3
