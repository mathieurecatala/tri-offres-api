"""Collecte vers Postgres : enregistrement, idempotence, offres fermées, nouveau tri."""
from sqlalchemy import func, select

from app.collecte import collecter, retrier
from app.db import Offre
from app.regles import creer_tri
from tests.conftest import REGLES

ENTREPRISES = [{"company": "Acme", "ats": "lever", "board": "acme"},
               {"company": "Globex", "ats": "ashby", "board": "globex"}]


def offre(entreprise, ats, titre, lieu, n):
    return {"entreprise": entreprise, "ats": ats, "titre": titre, "lieu": lieu,
            "url": f"https://jobs/{entreprise}/{n}", "salaire": ""}


def fausse_collecte(par_entreprise):
    """Fausse fonction de collecte : renvoie la liste prévue pour chaque entreprise (None = injoignable)."""
    return lambda entreprise, ats, board: par_entreprise.get(entreprise)


ACME = [offre("Acme", "lever", "Platform Engineer", "Remote", 1),
        offre("Acme", "lever", "Sales Manager", "Paris, France", 2)]
GLOBEX = [offre("Globex", "ashby", "AI Engineer", "New York", 1)]


def test_collecte_enregistre_et_trie(base, trier):
    bilan = collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME, "Globex": GLOBEX}))
    assert bilan == {"offres_vues": 3, "gardees": 1, "nouvelles": 3, "fermees": 0, "injoignables": []}
    rejet = base.scalar(select(Offre).where(Offre.titre == "AI Engineer"))
    assert (rejet.gardee, rejet.raison_rejet) == (False, "lieu : bloqué 'New York'")


def test_collecte_idempotente(base, trier):
    lister = fausse_collecte({"Acme": ACME, "Globex": GLOBEX})
    collecter(base, ENTREPRISES, trier, lister)
    bilan = collecter(base, ENTREPRISES, trier, lister)
    assert bilan["nouvelles"] == 0 and bilan["offres_vues"] == 3
    assert base.scalar(select(func.count()).select_from(Offre)) == 3


def test_doublon_dans_une_meme_reponse(base, trier):
    bilan = collecter(base, ENTREPRISES[:1], trier, fausse_collecte({"Acme": ACME + ACME[:1]}))
    assert bilan["offres_vues"] == 2


def test_offre_disparue_marquee_fermee(base, trier):
    collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME, "Globex": GLOBEX}))
    bilan = collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME[:1], "Globex": GLOBEX}))
    assert bilan["fermees"] == 1
    assert base.scalar(select(Offre.active).where(Offre.titre == "Sales Manager")) is False
    # Elle revient : elle est rouverte, sans doublon.
    collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME, "Globex": GLOBEX}))
    base.expire_all()
    assert base.scalar(select(Offre.active).where(Offre.titre == "Sales Manager")) is True


def test_entreprise_injoignable_ne_ferme_rien(base, trier):
    collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME, "Globex": GLOBEX}))
    bilan = collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME}))
    assert bilan["injoignables"] == ["Globex"] and bilan["fermees"] == 0
    assert base.scalar(select(func.count()).select_from(Offre).where(Offre.active.is_(True))) == 3


def test_nouveau_tri_apres_changement_de_regles(base, trier):
    collecter(base, ENTREPRISES, trier, fausse_collecte({"Acme": ACME, "Globex": GLOBEX}))
    plus_larges = {**REGLES, "location_allow_any": REGLES["location_allow_any"] + ["new york"]}
    assert retrier(base, creer_tri(plus_larges)) == {"offres_changees": 1}
    assert base.scalar(select(Offre.gardee).where(Offre.titre == "AI Engineer")) is True
