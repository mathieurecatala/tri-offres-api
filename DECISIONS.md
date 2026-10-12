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
- 12/10/2026 : Kubernetes local : les annonces visées demandent Terraform, CI/CD et Kubernetes ; tout reste local
  (kind dans Docker), sans compte cloud, 0 €.
- 12/10/2026 : Postgres écrit dans le chart (StatefulSet, image officielle `postgres`, version majeure 16 comme
  compose, épinglée par empreinte) plutôt qu'un chart externe : un pod, un volume, lisible en entier, aucune
  dépendance de plus.
- 12/10/2026 : Mot de passe Postgres tiré au hasard par le chart (`randAlphaNum`), relu par `lookup` aux mises à jour,
  Secret gardé à la désinstallation (`resource-policy: keep`) comme le volume : rien dans git, rien dans l'état Terraform.
- 12/10/2026 : kind 0.31.0 + `kindest/node:v1.35.0@sha256:452d…` partout (poste, CI, Terraform) : c'est la version
  embarquée par le provider `tehcyx/kind` 0.11.0 ; les images de nœud de kind 0.32+ exigent un kind récent pour
  `kind load` et passent kubeadm en v1beta4 (notes de version de kind 0.32.0). kubectl 1.35.9 (même version mineure
  que le nœud), Helm 3.22.0 (même version majeure que celle embarquée par `hashicorp/helm` 3.3.0).
- 12/10/2026 : Image chargée dans le nœud par `kind load docker-image` (provisioner `local-exec` de `terraform_data`) :
  pas de registre. Étiquette = début de l'identifiant de l'image, pour qu'un nouveau code redéploie l'API.
- 12/10/2026 : Espace de noms au niveau Pod Security `restricted` : prouve que les securityContext sont complets.
- 12/10/2026 : NetworkPolicy gardée parce que prouvée : kindnetd applique les NetworkPolicy depuis kind 0.24
  (kube-network-policies) ; `helm test` montre un pod autorisé accepté et un pod identique sans étiquette bloqué, et
  la CI refait le test sans la NetworkPolicy (la connexion doit alors passer).
- 12/10/2026 : Liveness de l'API sur le port TCP, readiness sur `/health` (qui interroge la base) : une base en panne
  sort l'API du Service sans la redémarrer en boucle.
- 13/10/2026 : Empreinte des fichiers du chart passée dans les valeurs (`empreinteChart`) : avec un chart local, le
  provider helm ne voyait pas un template modifié sans changement de version (`terraform plan` = « No changes ») ;
  avec l'empreinte, le plan montre la mise à jour. Préféré à `experiments.manifest`, qui doit lire le cluster au
  moment du plan alors qu'il n'existe pas encore.
- 13/10/2026 : Idempotence vérifiée en CI : `infra/k8s.sh idempotence` (`terraform plan -detailed-exitcode`, échec si
  Terraform veut encore changer quelque chose juste après l'apply).
- 13/10/2026 : Tests de fumée en lecture seule (`/health`, `/offres`, `/rejets`, `/docs`) : un test ne doit pas
  modifier les données d'une base remplie.
