"""Dossier de données de l'exécutable : l'ancien dossier « CGRS » est repris sous le nouveau nom, sans perte."""

from cgrs.paths import migrate_legacy_dir


def test_ancien_dossier_renomme_avec_son_contenu(tmp_path):
    ancien, nouveau = tmp_path / "CGRS", tmp_path / "Cantine"
    (ancien / "uploads").mkdir(parents=True)
    (ancien / "cantine.db").write_bytes(b"donnees")
    (ancien / "uploads" / "bl.pdf").write_bytes(b"pdf")
    assert migrate_legacy_dir(nouveau, ancien) == nouveau
    assert not ancien.exists()
    assert (nouveau / "cantine.db").read_bytes() == b"donnees"
    assert (nouveau / "uploads" / "bl.pdf").read_bytes() == b"pdf"


def test_nouveau_dossier_deja_present_n_est_pas_ecrase(tmp_path):
    ancien, nouveau = tmp_path / "CGRS", tmp_path / "Cantine"
    ancien.mkdir()
    (ancien / "cantine.db").write_bytes(b"ancienne")
    nouveau.mkdir()
    (nouveau / "cantine.db").write_bytes(b"actuelle")
    assert migrate_legacy_dir(nouveau, ancien) == nouveau
    assert (nouveau / "cantine.db").read_bytes() == b"actuelle"
    assert (ancien / "cantine.db").read_bytes() == b"ancienne"  # rien n'est supprimé


def test_installation_neuve_sans_ancien_dossier(tmp_path):
    assert migrate_legacy_dir(tmp_path / "Cantine", tmp_path / "CGRS") == tmp_path / "Cantine"
    assert not (tmp_path / "CGRS").exists()


def test_renommage_impossible_on_garde_l_ancien_dossier(tmp_path, monkeypatch):
    ancien, nouveau = tmp_path / "CGRS", tmp_path / "Cantine"
    ancien.mkdir()
    (ancien / "cantine.db").write_bytes(b"donnees")

    def refuse(self, cible):
        raise PermissionError("fichier ouvert")

    monkeypatch.setattr(type(ancien), "rename", refuse)
    assert migrate_legacy_dir(nouveau, ancien) == ancien  # pas de démarrage sur une base vide
    assert (ancien / "cantine.db").exists()
