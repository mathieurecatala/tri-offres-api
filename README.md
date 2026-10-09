# Tri d'offres

[![CI](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/ci.yml/badge.svg)](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/ci.yml)

## 1. Ce que c'est

**Projet personnel de Mathieu Recatala, octobre 2026, construit avec Claude Code.**

Je cherche des missions freelance en télétravail. Ce service collecte les offres d'emploi publiées par des entreprises
sur leurs pages carrières (API publiques de Greenhouse, Lever et Ashby : pas de clé, pas de connexion), les range dans
Postgres, les trie avec des règles écrites (titre, lieu, mots interdits) et **garde la raison de chaque rejet**. Le
résultat se lit par une API.

Sur les 4 entreprises suivies aujourd'hui, il collecte 128 offres et en garde 22. Il me sert aussi à apprendre
l'infrastructure demandée dans les annonces, étape par étape : Docker et CI d'abord (cette version), puis Airflow et
dbt, puis Kubernetes.

Projet voisin : [open-webui-docker](https://github.com/mathieurecatala/open-webui-docker), un assistant IA
auto-hébergé dont un outil interroge cette API.

## 2. Démarrer en 3 commandes

Il faut Docker (avec Compose v2).

```bash
git clone https://github.com/mathieurecatala/tri-offres-api.git && cd tri-offres-api
docker compose up -d --build                 # Postgres + API sur http://localhost:8000
curl -X POST http://localhost:8000/collecte  # collecte et tri des offres des entreprises suivies
```

Puis :

- http://localhost:8000/docs : documentation interactive (OpenAPI), chaque route s'essaie depuis le navigateur ;
- http://localhost:8000/offres?gardee=true : les offres gardées par les règles ;
- http://localhost:8000/rejets : les rejets et leur raison.

Tests (dans le conteneur, sur une base de test séparée) : `docker compose run --rm api pytest`.

Aucun fichier `.env` n'est nécessaire : les valeurs de développement sont dans `docker-compose.yml`. Pour les changer,
copier `.env.example` en `.env`.

## 3. Ce que fait l'API

| Route | Rôle |
|---|---|
| `GET /health` | L'API tourne et la base répond. |
| `POST /collecte` | Lit `config/companies.json`, collecte les offres de chaque entreprise, les trie avec `config/rules.json`, les enregistre. Rend un bilan : offres vues, gardées, nouvelles, fermées, entreprises injoignables. |
| `POST /tri` | Réapplique les règles à toutes les offres stockées, sans réseau (après avoir modifié `rules.json`). |
| `GET /offres` | Liste filtrée et paginée : `entreprise`, `gardee` (true/false), `texte` (dans le titre ou le lieu), `active` (true par défaut), `limite`, `decalage`. |
| `GET /offres/{id}` | Une offre. |
| `GET /rejets` | Offres rejetées avec leur raison (« titre : mot exclu 'manager' », « lieu : bloqué 'usa' »…) et le décompte par catégorie. |

Deux règles qui comptent pour un usage quotidien :

- **La collecte est idempotente.** Une offre est reconnue par son ATS et son lien : relancer la collecte met à jour les
  offres connues, n'ajoute que les nouvelles (le bilan dit combien), et marque *fermées* (`active=false`) celles qui ont
  disparu de la page de l'entreprise. Une entreprise injoignable ne ferme rien.
- **Les règles et la liste d'entreprises se modifient sans reconstruire l'image** : le dossier `config/` est monté dans
  le conteneur. Modifier `rules.json`, puis `POST /tri`.

## 4. Architecture

```
  API publiques sans clé : Greenhouse · Lever · Ashby
                │ HTTPS
                ▼
  ┌──────────────── docker compose ────────────────────────────────┐
  │                                                                │
  │  api : FastAPI, Python 3.12, utilisateur non root              │
  │    ats.py       lit les offres de chaque entreprise            │
  │    regles.py    gardée, ou rejetée avec sa raison              │
  │    collecte.py  ATS -> règles -> base (idempotent)             │
  │    main.py      routes HTTP et /docs                           │
  │    db.py        table « offres »                               │
  │        │   ▲                                                   │
  │        │   └── config/ (rules.json, companies.json), monté     │
  │        │ SQL                                                   │
  │        ▼                                                       │
  │  db : Postgres 16, volume « donnees » (survit au redémarrage)  │
  │       bases tri_offres (travail) et tri_offres_test (pytest)   │
  └────────────────────────────────────────────────────────────────┘
```

Fichiers :

```
app/                 code de l'API (5 fichiers, commentés en français)
config/              rules.json (règles de tri), companies.json (entreprises suivies)
tests/               pytest : règles, lecture des ATS, collecte en base, routes de l'API
Dockerfile           image en plusieurs étapes (dev avec les tests, prod sans)
docker-compose.yml   les deux services, la base de test, le volume
.github/workflows/   CI : gitleaks, construction des images, tests dans le conteneur
```

## 5. Choix techniques et pourquoi

- **FastAPI** : la documentation OpenAPI (`/docs`) est produite à partir du code, sans rien écrire à côté ; les
  paramètres sont validés automatiquement (une `limite` de 0 renvoie une erreur 422 claire).
- **Postgres plutôt que SQLite** : c'est ce que les étapes suivantes utiliseront (dbt, Airflow), et la collecte
  idempotente s'écrit en une requête (`INSERT … ON CONFLICT DO UPDATE`).
- **SQLAlchemy 2 + psycopg 3**, tables créées au démarrage, **pas encore de migrations** (Alembic) : une seule table,
  rien à migrer pour l'instant. À ajouter dès que le schéma devra évoluer avec des données à garder.
- **Bibliothèque standard pour les appels HTTP** (`urllib`) : repris d'une première version en ligne de commande ;
  une dépendance de moins dans l'image de production.
- **Dockerfile en plusieurs étapes** : les bibliothèques sont installées dans une étape à part puis copiées ;
  l'image `prod` ne contient ni pytest ni les tests, l'image `dev` (utilisée par `docker compose`) les contient pour
  que les tests tournent dans exactement le même environnement que l'API. Les deux tournent avec un utilisateur sans
  droits (`tri`, uid 10001).
- **Tests sur un vrai Postgres** (base `tri_offres_test`, créée automatiquement et vidée avant chaque test) plutôt
  que sur SQLite : `ON CONFLICT` et les types se comportent comme en vrai. **La collecte réseau est simulée** dans les
  tests : ils ne dépendent pas de la disponibilité des sites des entreprises.
- **CI GitHub Actions** : à chaque push et pull request, gitleaks parcourt tout l'historique git ; en parallèle, la CI
  construit l'image `prod`, construit l'image `dev`, lance `pytest` dans le conteneur et vérifie que
  `docker compose up` répond sur `/health`.
- **gitleaks** en pre-commit (`pip install pre-commit && pre-commit install`) et en CI. Il n'y a aucun secret dans ce
  projet ; le mot de passe Postgres `tri` est une valeur de développement, la base n'étant pas exposée hors de
  docker compose.

## 6. Ce qui viendra ensuite

- **Airflow + dbt.** La collecte devient une tâche planifiée chaque jour par Airflow ; dbt construit à partir de
  la table brute des vues utiles (nouvelles offres du jour, offres gardées encore ouvertes, rejets par raison) et les
  teste.
- **Kubernetes en local.** Les mêmes images déployées sur un cluster local (kind ou k3d), avec les manifestes
  expliqués.

Hors périmètre pour l'instant : la lecture des offres par une IA.

## Licence

MIT, voir `LICENSE`.
