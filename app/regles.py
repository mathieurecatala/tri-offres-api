"""Tri par règles écrites : chaque offre est gardée ou rejetée, avec la raison du rejet.

Les règles sont dans config/rules.json (mots du titre, lieux acceptés ou bloqués).
Logique reprise d'une première version en ligne de commande, raisons traduites en français.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Verdict:
    gardee: bool
    categorie: str | None = None  # "titre" ou "lieu" quand l'offre est rejetée
    raison: str | None = None     # phrase lisible, ex. "titre : mot exclu 'manager'"


def _mots(liste):
    """Expression régulière qui trouve un des mots de la liste, en mot entier, sans tenir compte de la casse.

    Le « mot entier » compte : « ai » ne doit pas trouver « Email » ni « Maintenance ».
    """
    return re.compile(r"\b(" + "|".join(re.escape(m) for m in liste) + r")\b", re.I)


def charger_regles(chemin: Path) -> dict:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def creer_tri(regles: dict):
    """Prépare les expressions une seule fois et renvoie la fonction de tri."""
    cible = _mots(regles["title_must_match_any"])
    exclu = _mots(regles["title_exclude"])
    lieu_ok = _mots(regles["location_allow_any"])
    lieu_bloque = _mots(regles["location_block_any"])

    def trier(titre: str, lieu: str) -> Verdict:
        if not cible.search(titre):
            return Verdict(False, "titre", "titre : aucun mot-clé cible")
        m = exclu.search(titre)
        if m:
            return Verdict(False, "titre", f"titre : mot exclu '{m.group(0)}'")
        # Un lieu accepté l'emporte : « Remote / New York » reste gardé.
        if not lieu_ok.search(lieu):
            m = lieu_bloque.search(lieu)
            if m:
                return Verdict(False, "lieu", f"lieu : bloqué '{m.group(0)}'")
            return Verdict(False, "lieu", f"lieu : hors liste acceptée '{lieu[:60]}'")
        return Verdict(True)

    return trier
