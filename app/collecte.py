"""Collecte : ATS publics -> tri par règles -> Postgres.

Idempotent : relancer la collecte met à jour les offres déjà connues au lieu de les dupliquer.
"""
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app import ats
from app.db import Offre


def collecter(session, entreprises: list[dict], trier, lister=None) -> dict:
    """Collecte les offres de chaque entreprise, les trie et les enregistre.

    `lister` sert aux tests (fausse collecte) ; par défaut, les vraies API publiques.
    Renvoie un bilan : offres vues, gardées, entreprises injoignables.
    """
    lister = lister or ats.lister_offres
    # Les appels réseau sont lents : une entreprise par fil, 8 en même temps au plus.
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultats = list(pool.map(lambda e: (e, lister(e["company"], e["ats"], e["board"])), entreprises))

    bilan = {"offres_vues": 0, "gardees": 0, "nouvelles": 0, "fermees": 0, "injoignables": []}
    for entreprise, offres in resultats:
        if offres is None:
            # Tableau injoignable : on ne touche pas à ses offres connues.
            bilan["injoignables"].append(entreprise["company"])
            continue
        # Une même offre peut apparaître deux fois dans une réponse : on ne garde que la dernière.
        uniques = {(o["ats"], o["url"]): o for o in offres if o["url"]}
        for o in uniques.values():
            v = trier(o["titre"], o["lieu"])
            valeurs = {**o, "gardee": v.gardee, "categorie_rejet": v.categorie, "raison_rejet": v.raison}
            requete = insert(Offre).values(**valeurs, active=True).on_conflict_do_update(
                constraint="offre_unique",
                set_={**valeurs, "active": True, "vue_derniere_fois": func.now()},
            ).returning(Offre.vue_premiere_fois == Offre.vue_derniere_fois)
            # Vrai si la ligne vient d'être créée (les deux dates sont celles de cette transaction).
            if session.execute(requete).scalar():
                bilan["nouvelles"] += 1
            bilan["offres_vues"] += 1
            bilan["gardees"] += v.gardee
        # Les offres connues de cette entreprise qui n'apparaissent plus sont fermées.
        fermees = session.execute(
            update(Offre)
            .where(Offre.entreprise == entreprise["company"], Offre.ats == entreprise["ats"],
                   Offre.active.is_(True), Offre.url.not_in([u for _, u in uniques] or [""]))
            .values(active=False)
        )
        bilan["fermees"] += fermees.rowcount
    session.commit()
    return bilan


def retrier(session, trier) -> dict:
    """Réapplique les règles à toutes les offres stockées, sans appel réseau (après une modification de rules.json)."""
    changees = 0
    for offre in session.scalars(select(Offre)):
        v = trier(offre.titre, offre.lieu)
        if (offre.gardee, offre.raison_rejet) != (v.gardee, v.raison):
            offre.gardee, offre.categorie_rejet, offre.raison_rejet = v.gardee, v.categorie, v.raison
            changees += 1
    session.commit()
    return {"offres_changees": changees}
