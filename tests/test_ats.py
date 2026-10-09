"""Lecture des API publiques des ATS, avec des réponses simulées (aucun appel réseau)."""
import pytest

from app import ats


@pytest.fixture
def reponses(monkeypatch):
    """Remplace lire_json : chaque URL renvoie la réponse prévue dans le dictionnaire, sinon None."""
    prevues = {}
    monkeypatch.setattr(ats, "lire_json", lambda url, timeout=30: prevues.get(url))
    return prevues


def test_greenhouse(reponses):
    reponses["https://boards-api.greenhouse.io/v1/boards/acme/jobs"] = {"jobs": [
        {"title": " Data Engineer ", "location": {"name": "Paris,   France"}, "absolute_url": "https://x/1"},
    ]}
    assert ats.lister_offres("Acme", "greenhouse", "acme") == [{
        "entreprise": "Acme", "ats": "greenhouse", "titre": "Data Engineer",
        "lieu": "Paris, France", "url": "https://x/1", "salaire": "",
    }]


def test_greenhouse_instance_europeenne(reponses):
    reponses["https://boards-api.eu.greenhouse.io/v1/boards/acme/jobs"] = {"jobs": [
        {"title": "Engineer", "location": {"name": "Berlin"}, "absolute_url": "https://x/2"},
    ]}
    assert [o["url"] for o in ats.lister_offres("Acme", "greenhouse", "acme")] == ["https://x/2"]


def test_lever_salaire_et_lieux(reponses):
    reponses["https://api.lever.co/v0/postings/acme?mode=json"] = [{
        "text": "Platform Engineer", "hostedUrl": "https://jobs.lever.co/acme/1", "workplaceType": "remote",
        "categories": {"location": "Paris", "allLocations": ["Lyon"]},
        "salaryRange": {"min": 60000, "max": 75000, "currency": "EUR"},
    }]
    (o,) = ats.lister_offres("Acme", "lever", "acme")
    assert o["lieu"] == "Paris / Lyon remote"
    assert o["salaire"] == "60k-75k EUR"


def test_ashby_remote(reponses):
    reponses["https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true"] = {"jobs": [{
        "title": "AI Engineer", "location": "France", "secondaryLocations": [{"location": "Spain"}],
        "isRemote": True, "jobUrl": "https://jobs.ashbyhq.com/acme/1",
        "compensation": {"compensationTierSummary": "€70K – €90K"},
    }]}
    (o,) = ats.lister_offres("Acme", "ashby", "acme")
    assert o["lieu"] == "France / Spain remote"
    assert o["salaire"] == "€70K – €90K"


def test_tableau_injoignable(reponses):
    assert ats.lister_offres("Acme", "lever", "acme") is None


def test_ats_inconnu(reponses):
    with pytest.raises(ValueError):
        ats.lister_offres("Acme", "workday", "acme")
