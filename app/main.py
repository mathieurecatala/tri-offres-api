"""API du Tri d'offres (FastAPI). Documentation interactive : http://localhost:8000/docs"""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select, text

from app import collecte as collecte_mod
from app.db import Offre, Session, creer_tables
from app.regles import charger_regles, creer_tri

# Les fichiers de règles et d'entreprises sont relus à chaque appel : on les modifie sans redémarrer.
CONFIG = Path(os.environ.get("CONFIG_DIR", Path(__file__).resolve().parent.parent / "config"))


@asynccontextmanager
async def demarrage(app):
    creer_tables()
    yield


app = FastAPI(
    title="Tri d'offres",
    description="Collecte des offres publiques (Greenhouse, Lever, Ashby), tri par règles écrites, "
                "raison gardée pour chaque rejet.",
    version="0.1.0",
    lifespan=demarrage,
)


def session():
    with Session() as s:
        yield s


def trieur():
    return creer_tri(charger_regles(CONFIG / "rules.json"))


# --- Formats de réponse (ils apparaissent aussi dans /docs) ---

class OffreSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entreprise: str
    ats: str
    titre: str
    lieu: str
    url: str
    salaire: str
    gardee: bool
    raison_rejet: str | None
    active: bool
    vue_premiere_fois: datetime
    vue_derniere_fois: datetime


class PageOffres(BaseModel):
    total: int
    limite: int
    decalage: int
    offres: list[OffreSortie]


class Rejet(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entreprise: str
    titre: str
    lieu: str
    categorie_rejet: str
    raison_rejet: str


class PageRejets(BaseModel):
    total: int
    par_categorie: dict[str, int]
    limite: int
    decalage: int
    rejets: list[Rejet]


class BilanCollecte(BaseModel):
    offres_vues: int
    gardees: int
    nouvelles: int
    fermees: int
    injoignables: list[str]


# --- Routes ---

@app.get("/health", tags=["service"])
def health(s=Depends(session)):
    """Répond si l'API tourne et que la base répond."""
    s.execute(text("select 1"))
    return {"statut": "ok", "base": "ok"}


@app.post("/collecte", response_model=BilanCollecte, tags=["collecte"])
def lancer_collecte(s=Depends(session)):
    """Collecte les offres des entreprises de config/companies.json, les trie et les enregistre.

    Idempotent : relancer met à jour les offres connues, ferme celles qui ont disparu, n'ajoute que les nouvelles.
    """
    entreprises = json.loads((CONFIG / "companies.json").read_text(encoding="utf-8"))
    return collecte_mod.collecter(s, entreprises, trieur())


@app.post("/tri", tags=["collecte"])
def relancer_tri(s=Depends(session)):
    """Réapplique config/rules.json à toutes les offres stockées, sans appel réseau."""
    return collecte_mod.retrier(s, trieur())


@app.get("/offres", response_model=PageOffres, tags=["offres"])
def lister_offres(
    entreprise: str | None = Query(None, description="Nom exact de l'entreprise"),
    gardee: bool | None = Query(None, description="true : gardées par les règles ; false : rejetées"),
    texte: str | None = Query(None, description="Cherché dans le titre et le lieu (sans tenir compte de la casse)"),
    active: bool | None = Query(True, description="true par défaut : seulement les offres encore ouvertes"),
    limite: int = Query(50, ge=1, le=500),
    decalage: int = Query(0, ge=0),
    s=Depends(session),
):
    """Liste les offres, filtrées et paginées, les plus récemment vues d'abord."""
    filtres = []
    if entreprise is not None:
        filtres.append(Offre.entreprise == entreprise)
    if gardee is not None:
        filtres.append(Offre.gardee.is_(gardee))
    if active is not None:
        filtres.append(Offre.active.is_(active))
    if texte:
        motif = f"%{texte}%"
        filtres.append(or_(Offre.titre.ilike(motif), Offre.lieu.ilike(motif)))
    total = s.scalar(select(func.count()).select_from(Offre).where(*filtres))
    offres = s.scalars(
        select(Offre).where(*filtres)
        .order_by(Offre.vue_premiere_fois.desc(), Offre.id.desc()).limit(limite).offset(decalage)
    ).all()
    return {"total": total, "limite": limite, "decalage": decalage, "offres": offres}


@app.get("/offres/{offre_id}", response_model=OffreSortie, tags=["offres"])
def lire_offre(offre_id: int, s=Depends(session)):
    offre = s.get(Offre, offre_id)
    if offre is None:
        raise HTTPException(404, "Offre introuvable")
    return offre


@app.get("/rejets", response_model=PageRejets, tags=["offres"])
def lister_rejets(
    categorie: str | None = Query(None, description="titre ou lieu"),
    limite: int = Query(50, ge=1, le=500),
    decalage: int = Query(0, ge=0),
    s=Depends(session),
):
    """Offres rejetées avec la raison de chaque rejet, et le décompte par catégorie (offres ouvertes seulement)."""
    filtres = [Offre.gardee.is_(False), Offre.active.is_(True)]
    par_categorie = dict(
        s.execute(select(Offre.categorie_rejet, func.count()).where(*filtres).group_by(Offre.categorie_rejet)).all()
    )
    if categorie:
        filtres.append(Offre.categorie_rejet == categorie)
    total = s.scalar(select(func.count()).select_from(Offre).where(*filtres))
    rejets = s.scalars(
        select(Offre).where(*filtres).order_by(Offre.entreprise, Offre.id).limit(limite).offset(decalage)
    ).all()
    return {"total": total, "par_categorie": par_categorie, "limite": limite, "decalage": decalage, "rejets": rejets}
