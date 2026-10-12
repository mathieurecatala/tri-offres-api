# Tri d'offres

[![CI](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/ci.yml/badge.svg)](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/ci.yml)
[![Kubernetes](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/k8s.yml/badge.svg)](https://github.com/mathieurecatala/tri-offres-api/actions/workflows/k8s.yml)

## 1. Ce que c'est

**Projet personnel de Mathieu Recatala, octobre 2026, construit avec Claude Code.**

Je cherche des missions freelance en télétravail. Ce service collecte les offres d'emploi publiées par des entreprises
sur leurs pages carrières (API publiques de Greenhouse, Lever et Ashby : pas de clé, pas de connexion), les range dans
Postgres, les trie avec des règles écrites (titre, lieu, mots interdits) et **garde la raison de chaque rejet**. Le
résultat se lit par une API.

Sur les 4 entreprises suivies, il a collecté 128 offres et en a gardé 22 (mesure du 08/10/2026). Il me sert aussi à
apprendre l'infrastructure demandée dans les annonces, étape par étape : Docker et CI d'abord, puis Kubernetes en
local avec Helm et Terraform (section 6), ensuite Airflow et dbt.

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
.github/workflows/   CI : gitleaks, construction des images, tests dans le conteneur ; déploiement Kubernetes (k8s.yml)
infra/               Kubernetes local : chart Helm, Terraform (cluster kind), scripts (section 6)
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

## 6. Déploiement Kubernetes local

**Terraform sur un cluster kind local, sans cloud.** [kind](https://kind.sigs.k8s.io/) fait tourner un vrai
Kubernetes à l'intérieur d'un conteneur Docker, sur le poste. Rien n'est créé chez un fournisseur cloud : pas de compte,
pas de clé, 0 €. Ce n'est pas un déploiement de production, et ce projet ne tourne sur aucune infrastructure cloud.
Pour l'usage de tous les jours, `docker compose` (section 2) reste plus simple ; cette partie sert à déployer le même
produit sur Kubernetes et à le vérifier automatiquement.

Il faut Linux ou WSL avec Docker. Les outils (kind, kubectl, helm, terraform) s'installent sans droits administrateur,
aux versions épinglées et avec vérification de leur empreinte :

```bash
infra/installer-outils.sh    # kind, kubectl, helm, terraform dans ~/.local/bin
infra/k8s.sh monter          # image + cluster kind + chart, puis test de fumée ; API sur http://localhost:8080/docs
infra/k8s.sh detruire        # supprime le cluster et tout ce qu'il contient (offres comprises)
```

`infra/k8s.sh monter` enchaîne : construction de l'image `prod`, puis `terraform apply` (crée le cluster kind, y charge
l'image, crée l'espace de noms, installe le chart et attend que l'API et Postgres soient prêts), puis le test de fumée
(`infra/fumee.sh` sur `/health`, `/offres`, `/rejets`, `/docs`, et `helm test`). Ce test est en lecture seule et
n'appelle pas les ATS : il prouve que le Service, l'API et Postgres sont bien reliés, pas la collecte.
Relancé sans changement, Terraform ne refait rien (`infra/k8s.sh idempotence`, vérifié en CI). Après une
modification du code, la nouvelle image a une nouvelle étiquette et l'API est redéployée ; après une modification
d'un fichier du chart, son empreinte change et Terraform relance un `helm upgrade` (sans cela, le provider helm ne
voit pas un template modifié tant que la version du chart ne change pas : constaté le 13/10/2026).
Pour utiliser kubectl ou helm sur ce cluster : `export KUBECONFIG=infra/terraform/kubeconfig`.

Ce qu'il y a dans `infra/` :

| Fichier | Rôle |
|---|---|
| `helm/tri-offres/` | Le chart : l'API (Deployment + Service), Postgres (StatefulSet + volume de 1 Gi + Service), le Secret du mot de passe, la NetworkPolicy, et les tests `helm test`. |
| `terraform/` | Crée le cluster kind (un nœud, port 8080 de la machine relié à l'API), charge l'image, crée l'espace de noms, installe le chart. Providers épinglés : `tehcyx/kind` 0.11.0, `hashicorp/helm` 3.3.0, `hashicorp/kubernetes` 3.3.0, empreintes figées dans `.terraform.lock.hcl`. |
| `k8s.sh`, `fumee.sh` | Monter, tester, vérifier l'idempotence, détruire ; le test de fumée HTTP. |
| `installer-outils.sh` | Les quatre outils, versions et empreintes SHA-256 écrites dans le script. |

Choix et pourquoi :

- **Postgres écrit dans le chart** (StatefulSet avec l'image officielle `postgres:16-alpine`, même version majeure que
  `docker compose`, épinglée par empreinte) plutôt qu'un chart Postgres externe : une base, un pod, un volume ; le fichier se lit en entier et il
  n'y a pas de dépendance de plus à suivre.
- **Le mot de passe Postgres n'est écrit nulle part** : le chart le tire au hasard au premier déploiement (Secret
  Kubernetes) et le relit aux mises à jour.
- **Sondes** : Postgres est « prêt » quand `pg_isready` répond ; l'API est « prête » quand `/health` répond (donc la base
  aussi) et « vivante » tant que son port répond. Une panne de la base retire l'API du Service sans la redémarrer en
  boucle.
- **Ressources** : chaque conteneur a une réservation (`requests`) et un plafond (`limits`). Valeurs de départ fixées à
  partir d'une mesure faite dans kind le 12/10/2026 (environ 127 Mio pour l'API après une collecte réelle).
- **Sans droits** : tous les conteneurs tournent sans root, sans privilèges Linux, système de fichiers en lecture seule.
  L'espace de noms est au niveau de sécurité `restricted` de Kubernetes, qui refuserait un pod moins strict.
- **NetworkPolicy** : seule l'API peut ouvrir une connexion vers Postgres. Prouvé en CI : un pod autorisé joint la base,
  un pod identique sans l'étiquette est bloqué, et, contre-épreuve, ce même pod la joint dès qu'on retire la
  NetworkPolicy. kind l'applique avec son réseau par défaut (kindnetd).
- **kind 0.31.0 et Kubernetes 1.35** (et non les dernières versions) : c'est la version de kind embarquée par le
  provider Terraform ; l'image du nœud est épinglée par son empreinte, comme le recommande kind.

La CI `.github/workflows/k8s.yml` (à chaque modification du code ou de `infra/`) : `helm lint`, `terraform fmt -check`
et `validate` ; puis un cluster kind créé dans le runner GitHub (action officielle `helm/kind-action`), le chart
installé, le test de fumée HTTP sur le Service, `helm test` et la contre-épreuve de la NetworkPolicy ; enfin le même
chemin qu'en local (`infra/installer-outils.sh`, `infra/k8s.sh monter`, `idempotence`, puis `detruire`, donc
Terraform pour de vrai). Les clusters sont supprimés à la fin.

Ce qui manque pour aller en cloud : un registre d'images (l'image n'est publiée nulle part), un cluster géré et son
réseau, un état Terraform partagé (ici il reste sur le poste), un Ingress avec HTTPS, des sauvegardes de Postgres (ou
une base gérée), et des secrets gérés hors du cluster. Autre point : ici, les providers kubernetes et helm sont
configurés à partir du cluster créé dans le même code Terraform ; c'est acceptable pour un cluster local jetable, mais
en vrai le cluster et les applications seraient dans deux configurations Terraform séparées (deux états), ou
l'application serait déployée par la CI ou un outil GitOps. Rien de cela n'est fait ici.

Limites connues : Postgres n'est protégé qu'en entrée (pas de règle « tout refuser » par défaut ni de filtrage en
sortie) ; l'API crée ses tables au démarrage, donc plusieurs réplicas en même temps se gêneraient tant qu'il n'y a
pas de migrations.

## 7. Ce qui viendra ensuite

- **Airflow + dbt.** La collecte devient une tâche planifiée chaque jour par Airflow ; dbt construit à partir de
  la table brute des vues utiles (nouvelles offres du jour, offres gardées encore ouvertes, rejets par raison) et les
  teste.
- **Kubernetes en local : fait** (section 6). Reste possible ensuite : une tâche planifiée (CronJob) pour la collecte.

Hors périmètre pour l'instant : la lecture des offres par une IA.

## Licence

MIT, voir `LICENSE`.
