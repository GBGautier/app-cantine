"""Bon de livraison de fruits : colonnes « Description », « Nbre colis », « Qté », « P.U. HT » et « Total HT Net »."""

from cgrs.parsers.pdf_parser import TOTAL_NET_RE, lines_from_tables

TABLE = [
    ["Description", "Origine", "N° lot", "Nbre colis", "Qté", "Unité", "P.U. HT", "Montant\nHT", "TVA"],
    [
        "Pomme bio dalinette 95+ cat.2\nKiwi Hayward bio cat.2 vrac\nTransport PLACIER",
        "FRANCE\nFRANCE",
        "PLA 26103 K12\nPLA 26252 K06",
        "3,00\n3,00\n0,00",
        "42,000\n30,000\n1,0",
        "Kg\nKg",
        "1,50\n5,05\n35,00",
        "63,00\n151,50\n35,00",
        "5,50\n5,50\n20,00",
    ],
]


def test_quantite_en_kg_et_non_nombre_de_colis():
    lignes = lines_from_tables([TABLE])
    assert [(l["label"], l["qty"], l["unit"], l["unit_price"], l["total_ht"]) for l in lignes] == [
        ("Pomme bio dalinette 95+ cat.2", 42.0, "kg", 1.5, 63.0),
        ("Kiwi Hayward bio cat.2 vrac", 30.0, "kg", 5.05, 151.5),
        ("Transport PLACIER", 1.0, None, 35.0, 35.0),
    ]


def test_total_ht_net():
    assert TOTAL_NET_RE.search("Total HT Net 278,13").group(1) == "278,13"
    assert TOTAL_NET_RE.search("Total net HT : 12,50").group(1) == "12,50"
