"""Préparation des tests : base Postgres dédiée (tri_offres_test), vidée avant chaque test.

La base de test est créée si elle n'existe pas. DATABASE_URL est remplacée AVANT d'importer l'application,
pour que les tests ne touchent jamais la base de travail.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

URL_TEST = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://tri:tri@localhost:5432/tri_offres_test")
os.environ["DATABASE_URL"] = URL_TEST


def _creer_base_de_test():
    url = make_url(URL_TEST)
    # On se connecte à la base « postgres » (toujours présente) pour créer la base de test.
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        existe = c.scalar(text("select 1 from pg_database where datname = :n"), {"n": url.database})
        if not existe:
            c.execute(text(f'create database "{url.database}"'))
    admin.dispose()


_creer_base_de_test()

from app.db import Session, creer_tables, engine  # noqa: E402  (après le choix de la base)
from app.regles import creer_tri  # noqa: E402

REGLES = {
    "title_must_match_any": ["engineer", "developer", "ai", "platform"],
    "title_exclude": ["intern", "manager", "staff"],
    "location_allow_any": ["remote", "france", "europe"],
    "location_block_any": ["usa", "new york"],
}


@pytest.fixture
def base():
    """Session sur une base vide."""
    creer_tables()
    with engine.begin() as c:
        c.execute(text("truncate offres restart identity"))
    with Session() as s:
        yield s


@pytest.fixture
def trier():
    return creer_tri(REGLES)
