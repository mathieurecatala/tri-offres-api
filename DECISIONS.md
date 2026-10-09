# Décisions

- 08/10/2026 : Un seul produit qui grossit (Docker + CI, puis Airflow + dbt, puis Kubernetes local) plutôt que
  plusieurs dépôts jetables.
- 08/10/2026 : Licence MIT.
- 08/10/2026 : FastAPI + SQLAlchemy 2 + psycopg 3 ; tables créées au démarrage, pas d'Alembic tant qu'il n'y a qu'une
  table et rien à migrer.
- 08/10/2026 : Une offre est identifiée par (ats, url) : clé d'unicité de la collecte idempotente (`ON CONFLICT`).
- 08/10/2026 : Offre absente de la dernière collecte réussie de son entreprise : marquée `active=false`, pas supprimée
  (utile au quotidien : savoir qu'une offre est fermée) ; une entreprise injoignable ne ferme rien.
- 08/10/2026 : `POST /tri` ajouté : réappliquer `rules.json` sans recollecter, `config/` monté dans le
  conteneur pour régler les règles sans reconstruire l'image.
- 08/10/2026 : Appels HTTP en `urllib` (bibliothèque standard) ; `httpx2` seulement pour le
  client de test (httpx est déprécié par Starlette 1.7).
- 08/10/2026 : Dockerfile : cibles `dev` (API + pytest + tests, utilisée par compose et la CI) et `prod` (API seule,
  cible par défaut) ; utilisateur `tri` uid 10001.
- 08/10/2026 : Tests sur un vrai Postgres (base `tri_offres_test` créée par `tests/conftest.py`, vidée à chaque test).
- 08/10/2026 : gitleaks en CI via l'image officielle `ghcr.io/gitleaks/gitleaks:v8.30.1` plutôt que l'action
  gitleaks-action (pas de clé de licence à gérer) ; en pre-commit, le hook officiel à la même version.
- 08/10/2026 : Raisons de rejet traduites en français (« titre : mot exclu 'manager' ») ; logique des règles inchangée.
