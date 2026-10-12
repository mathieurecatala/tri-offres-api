#!/usr/bin/env bash
# Le Tri d'offres sur un cluster Kubernetes LOCAL (kind dans Docker), monté par Terraform. Aucun compte cloud.
#
#   infra/k8s.sh monter        construit l'image, crée le cluster kind, installe le chart, lance le test de fumée
#   infra/k8s.sh fumee         test de fumée seul (HTTP depuis la machine, puis « helm test » dans le cluster)
#   infra/k8s.sh idempotence   « terraform plan » doit répondre « rien à changer » juste après monter (sinon échec)
#   infra/k8s.sh detruire      supprime tout (chart, cluster kind et ses volumes)
#
# Variables facultatives : PORT_LOCAL (8080 par défaut), NOM_CLUSTER (tri-offres par défaut).
# Il faut Docker, kind, kubectl, helm et terraform (infra/installer-outils.sh les installe dans ~/.local/bin).
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF="$RACINE/infra/terraform"
IMAGE=tri-offres-api
PORT="${PORT_LOCAL:-8080}"
CLUSTER="${NOM_CLUSTER:-tri-offres}"

verifier_outils() {
  local manque=0
  for outil in docker kind kubectl helm terraform; do
    command -v "$outil" >/dev/null || { echo "Outil manquant : $outil (voir infra/installer-outils.sh)" >&2; manque=1; }
  done
  [ "$manque" -eq 0 ]
}

# Étiquette = début de l'identifiant de l'image construite : si le code change, l'étiquette change et Kubernetes
# redéploie l'API ; si rien n'a changé, Terraform n'a rien à refaire.
etiquette() {
  docker image inspect --format '{{.Id}}' "$IMAGE:construite" | cut -d: -f2 | cut -c1-12
}

# Variables Terraform communes à apply, plan et destroy.
variables_tf() {
  echo "-var nom_cluster=$CLUSTER -var port_local=$PORT -var etiquette_api=$1"
}

monter() {
  verifier_outils
  echo "== 1/3 Image de l'API (cible prod du Dockerfile)"
  docker build --target prod -t "$IMAGE:construite" "$RACINE"
  local tag
  tag="$(etiquette)"
  docker tag "$IMAGE:construite" "$IMAGE:$tag"

  echo "== 2/3 Terraform : cluster kind + chargement de l'image + chart Helm"
  terraform -chdir="$TF" init -input=false
  # shellcheck disable=SC2046
  terraform -chdir="$TF" apply -input=false -auto-approve $(variables_tf "$tag")

  echo "== 3/3 Test de fumée"
  fumee
  echo
  echo "API : http://localhost:$PORT/docs"
  echo "kubectl : export KUBECONFIG=$TF/kubeconfig"
}

fumee() {
  verifier_outils
  "$RACINE/infra/fumee.sh" "http://localhost:$PORT"
  KUBECONFIG="$TF/kubeconfig" helm test tri-offres -n tri-offres --logs
}

idempotence() {
  verifier_outils
  local code=0
  # -detailed-exitcode : 0 = rien à changer, 2 = Terraform voudrait encore changer quelque chose, 1 = erreur.
  # shellcheck disable=SC2046
  terraform -chdir="$TF" plan -input=false -detailed-exitcode $(variables_tf "$(etiquette)") || code=$?
  case "$code" in
    0) echo "Idempotence : OK, une seconde exécution ne changerait rien." ;;
    2) echo "ÉCHEC : juste après « monter », Terraform voudrait encore changer quelque chose." >&2; exit 1 ;;
    *) echo "ÉCHEC : terraform plan a échoué (code $code)." >&2; exit 1 ;;
  esac
}

detruire() {
  verifier_outils
  terraform -chdir="$TF" init -input=false >/dev/null
  # L'étiquette de l'image n'a pas d'effet sur la destruction : une valeur fixe suffit.
  # shellcheck disable=SC2046
  terraform -chdir="$TF" destroy -input=false -auto-approve $(variables_tf detruire)
}

case "${1:-}" in
  monter) monter ;;
  fumee) fumee ;;
  idempotence) idempotence ;;
  detruire) detruire ;;
  *) echo "Usage : $0 monter | fumee | idempotence | detruire" >&2; exit 2 ;;
esac
