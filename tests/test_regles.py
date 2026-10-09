"""Règles de tri : chaque cas renvoie gardée, ou rejetée avec la bonne raison."""


def test_offre_gardee(trier):
    v = trier("Senior Platform Engineer", "Remote - Europe")
    assert v.gardee and v.raison is None


def test_titre_sans_mot_cible(trier):
    v = trier("Account Executive", "Paris, France")
    assert not v.gardee
    assert (v.categorie, v.raison) == ("titre", "titre : aucun mot-clé cible")


def test_titre_avec_mot_exclu(trier):
    v = trier("Engineering Manager, Platform", "Remote")
    assert v.categorie == "titre" and v.raison == "titre : mot exclu 'Manager'"


def test_lieu_bloque(trier):
    v = trier("Backend Engineer", "New York, NY")
    assert v.categorie == "lieu" and v.raison == "lieu : bloqué 'New York'"


def test_lieu_hors_liste(trier):
    v = trier("Backend Engineer", "Berlin")
    assert v.raison == "lieu : hors liste acceptée 'Berlin'"


def test_lieu_accepte_l_emporte_sur_bloque(trier):
    assert trier("Backend Engineer", "New York / Remote").gardee


def test_mot_entier_seulement(trier):
    # « ai » ne doit pas trouver « Email » ; « intern » ne doit pas exclure « Internal ».
    assert trier("Email Marketing Lead", "Remote").raison == "titre : aucun mot-clé cible"
    assert trier("Internal Tools Engineer", "Remote").gardee
    assert trier("AI Engineer", "France").gardee


def test_regles_du_depot_se_chargent():
    from pathlib import Path

    from app.regles import charger_regles, creer_tri

    regles = charger_regles(Path(__file__).resolve().parent.parent / "config" / "rules.json")
    assert creer_tri(regles)("Automation Engineer", "Remote - EMEA").gardee
