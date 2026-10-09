"""Routes de l'API, sur la base de test, avec une collecte simulée."""
import json

import pytest
from fastapi.testclient import TestClient

from app import ats, main
from tests.conftest import REGLES

FAUSSES_OFFRES = {
    "Acme": [
        {"entreprise": "Acme", "ats": "lever", "titre": "Platform Engineer", "lieu": "Remote",
         "url": "https://jobs/acme/1", "salaire": "60k-70k EUR"},
        {"entreprise": "Acme", "ats": "lever", "titre": "Sales Manager", "lieu": "Paris",
         "url": "https://jobs/acme/2", "salaire": ""},
    ],
    "Globex": [
        {"entreprise": "Globex", "ats": "ashby", "titre": "AI Engineer", "lieu": "New York",
         "url": "https://jobs/globex/1", "salaire": ""},
    ],
}


@pytest.fixture
def client(base, tmp_path, monkeypatch):
    """Client HTTP sur l'API, avec une configuration et une collecte de test."""
    (tmp_path / "rules.json").write_text(json.dumps(REGLES))
    (tmp_path / "companies.json").write_text(json.dumps([
        {"company": "Acme", "ats": "lever", "board": "acme"},
        {"company": "Globex", "ats": "ashby", "board": "globex"},
        {"company": "Initech", "ats": "greenhouse", "board": "initech"},  # injoignable
    ]))
    monkeypatch.setattr(main, "CONFIG", tmp_path)
    monkeypatch.setattr(ats, "lister_offres", lambda e, a, b: FAUSSES_OFFRES.get(e))
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def client_rempli(client):
    assert client.post("/collecte").status_code == 200
    return client


def test_health(client):
    assert client.get("/health").json() == {"statut": "ok", "base": "ok"}


def test_documentation_openapi(client):
    chemins = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/collecte", "/offres", "/offres/{offre_id}", "/rejets", "/tri"} <= set(chemins)


def test_collecte(client):
    bilan = client.post("/collecte").json()
    assert bilan == {"offres_vues": 3, "gardees": 1, "nouvelles": 3, "fermees": 0, "injoignables": ["Initech"]}
    assert client.post("/collecte").json()["nouvelles"] == 0


def test_offres_filtres(client_rempli):
    c = client_rempli
    assert c.get("/offres").json()["total"] == 3
    gardees = c.get("/offres", params={"gardee": True}).json()
    assert [o["titre"] for o in gardees["offres"]] == ["Platform Engineer"]
    assert c.get("/offres", params={"entreprise": "Globex"}).json()["total"] == 1
    assert c.get("/offres", params={"texte": "engineer"}).json()["total"] == 2
    assert c.get("/offres", params={"texte": "PARIS"}).json()["total"] == 1


def test_offres_pagination(client_rempli):
    p1 = client_rempli.get("/offres", params={"limite": 2}).json()
    p2 = client_rempli.get("/offres", params={"limite": 2, "decalage": 2}).json()
    assert (p1["total"], len(p1["offres"]), len(p2["offres"])) == (3, 2, 1)
    assert not {o["id"] for o in p1["offres"]} & {o["id"] for o in p2["offres"]}
    assert client_rempli.get("/offres", params={"limite": 0}).status_code == 422


def test_offre_par_id(client_rempli):
    premiere = client_rempli.get("/offres").json()["offres"][0]
    assert client_rempli.get(f"/offres/{premiere['id']}").json() == premiere
    assert client_rempli.get("/offres/999999").status_code == 404


def test_rejets(client_rempli):
    r = client_rempli.get("/rejets").json()
    assert r["total"] == 2
    assert r["par_categorie"] == {"titre": 1, "lieu": 1}
    raisons = {x["titre"]: x["raison_rejet"] for x in r["rejets"]}
    assert raisons == {"Sales Manager": "titre : aucun mot-clé cible", "AI Engineer": "lieu : bloqué 'New York'"}
    assert client_rempli.get("/rejets", params={"categorie": "lieu"}).json()["total"] == 1


def test_tri_apres_changement_de_regles(client_rempli, tmp_path):
    (tmp_path / "rules.json").write_text(json.dumps({**REGLES, "location_allow_any": ["new york", "remote"]}))
    assert client_rempli.post("/tri").json() == {"offres_changees": 1}
    assert client_rempli.get("/offres", params={"gardee": True}).json()["total"] == 2
