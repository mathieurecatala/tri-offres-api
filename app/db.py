"""Connexion à Postgres et table des offres (SQLAlchemy 2)."""
import os
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Fourni par docker-compose.yml ; les tests le remplacent par l'adresse de la base de test.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://tri:tri@localhost:5432/tri_offres")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Offre(Base):
    __tablename__ = "offres"
    # Une offre est reconnue par son ATS et son lien : recollecter ne crée pas de doublon.
    __table_args__ = (UniqueConstraint("ats", "url", name="offre_unique"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entreprise: Mapped[str] = mapped_column(String(200), index=True)
    ats: Mapped[str] = mapped_column(String(20))
    titre: Mapped[str] = mapped_column(Text)
    lieu: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    salaire: Mapped[str] = mapped_column(Text, default="")
    # Résultat du tri par règles
    gardee: Mapped[bool] = mapped_column(Boolean, index=True)
    categorie_rejet: Mapped[str | None] = mapped_column(String(20))
    raison_rejet: Mapped[str | None] = mapped_column(Text)
    # Une offre absente de la dernière collecte de son entreprise est fermée : on la garde, marquée inactive.
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    vue_premiere_fois: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vue_derniere_fois: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def creer_tables():
    """Crée les tables si elles n'existent pas (pas de migrations à ce stade, voir DECISIONS.md)."""
    Base.metadata.create_all(engine)
