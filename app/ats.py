"""Lecture des offres publiques des ATS (Greenhouse, Lever, Ashby).

Uniquement des API publiques et documentées : pas de clé, pas de connexion, pas de pages privées.
Repris d'une première version en ligne de commande ; la lecture du texte complet n'est pas utile ici.
Dans les tests, `lire_json` est remplacée par une fausse fonction : aucun appel réseau.
"""
import json
import re
import urllib.request

AGENT = "tri-offres/0.1 (projet personnel)"


def lire_json(url: str, timeout: int = 30):
    """Renvoie le JSON de l'URL, ou None si la page ne répond pas."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _offre(entreprise, ats, titre, lieu, url, salaire=""):
    return {
        "entreprise": entreprise,
        "ats": ats,
        "titre": (titre or "").strip(),
        "lieu": re.sub(r"\s+", " ", lieu or "").strip(),
        "url": url or "",
        "salaire": salaire or "",
    }


def lister_offres(entreprise: str, ats: str, board: str):
    """Toutes les offres ouvertes d'une entreprise, ou None si son tableau d'offres est injoignable."""
    offres = []
    if ats == "greenhouse":
        d = lire_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
        if not (isinstance(d, dict) and d.get("jobs")):
            # Certaines entreprises sont hébergées sur l'instance européenne.
            d = lire_json(f"https://boards-api.eu.greenhouse.io/v1/boards/{board}/jobs")
        if not isinstance(d, dict):
            return None
        for j in d.get("jobs", []):
            offres.append(_offre(entreprise, ats, j.get("title"),
                                 (j.get("location") or {}).get("name"), j.get("absolute_url")))
    elif ats == "lever":
        d = lire_json(f"https://api.lever.co/v0/postings/{board}?mode=json")
        if not (isinstance(d, list) and d):
            d = lire_json(f"https://api.eu.lever.co/v0/postings/{board}?mode=json")
        if not isinstance(d, list):
            return None
        for j in d:
            cat = j.get("categories") or {}
            lieux = " / ".join([cat.get("location") or ""] + (cat.get("allLocations") or []))
            sr = j.get("salaryRange") or {}
            salaire = (f"{sr['min'] // 1000}k-{sr['max'] // 1000}k {sr.get('currency', '')}".strip()
                       if sr.get("min") and sr.get("max") else "")
            offres.append(_offre(entreprise, ats, j.get("text"),
                                 f"{lieux} {j.get('workplaceType', '')}", j.get("hostedUrl"), salaire))
    elif ats == "ashby":
        d = lire_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true")
        if not (isinstance(d, dict) and "jobs" in d):
            return None
        for j in d["jobs"]:
            lieu = j.get("location") or ""
            autres = [s.get("location", "") for s in (j.get("secondaryLocations") or [])]
            if autres:
                lieu += " / " + " / ".join(autres)
            if j.get("isRemote"):
                lieu += " remote"
            salaire = (j.get("compensation") or {}).get("compensationTierSummary") or ""
            offres.append(_offre(entreprise, ats, j.get("title"), lieu, j.get("jobUrl"), salaire))
    else:
        raise ValueError(f"ATS non pris en charge : {ats}")
    return offres
