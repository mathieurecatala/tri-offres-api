#!/usr/bin/env bash
# Installe kind, kubectl, helm et terraform dans ~/.local/bin, sans sudo, aux versions épinglées ci-dessous.
# Chaque binaire est téléchargé depuis son site officiel et son empreinte SHA-256 est vérifiée avant installation.
# Linux x86_64 seulement (WSL Ubuntu, runner GitHub). Relancer le script ne retélécharge pas un outil déjà à jour.
set -euo pipefail

# Versions alignées entre elles (voir DECISIONS.md) :
#   - kind 0.31.0 : la version embarquée par le provider Terraform tehcyx/kind 0.11.0 ;
#   - kubectl 1.35 : même version mineure que le nœud kind (kindest/node v1.35.0) ;
#   - helm 3 : même version majeure que celle embarquée par le provider Terraform hashicorp/helm 3.3.0.
KIND_VERSION=0.31.0
KIND_SHA256=eb244cbafcc157dff60cf68693c14c9a75c4e6e6fedaf9cd71c58117cb93e3fa
KUBECTL_VERSION=1.35.9
KUBECTL_SHA256=3cfeaf80be482b435b0aa214aff6e0b2c312ee23c0ff20810c75517b6004c6eb
HELM_VERSION=3.22.0
HELM_SHA256=1e4ab49e429626cf6c6958d914248b78c9730803c2751b87627e171dc800e7bb
TERRAFORM_VERSION=1.16.5
TERRAFORM_SHA256=2bc2fcfff033265c9e02ca0351f01794eb122f62a9b2a49a3294b9e49eaab5e4

DEST="${HOME}/.local/bin"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$DEST"

[ "$(uname -sm)" = "Linux x86_64" ] || { echo "Ce script ne gère que Linux x86_64." >&2; exit 1; }

# telecharger <url> <fichier> <sha256> : télécharge et refuse un fichier dont l'empreinte ne correspond pas.
telecharger() {
  curl -fsSL --retry 3 -o "$TMP/$2" "$1"
  echo "$3  $TMP/$2" | sha256sum --check --quiet
}

# deja_installe <outil> <texte attendu dans sa sortie de version>
deja_installe() {
  local sortie
  [ -x "$DEST/$1" ] || return 1
  sortie="$("$DEST/$1" "${@:3}" 2>/dev/null)" || return 1
  [[ "$sortie" == *"$2"* ]]
}

if deja_installe kind "v${KIND_VERSION}" version; then
  echo "kind ${KIND_VERSION} déjà installé"
else
  telecharger "https://github.com/kubernetes-sigs/kind/releases/download/v${KIND_VERSION}/kind-linux-amd64" kind "$KIND_SHA256"
  install -m 0755 "$TMP/kind" "$DEST/kind"
  echo "kind ${KIND_VERSION} installé"
fi

if deja_installe kubectl "v${KUBECTL_VERSION}" version --client; then
  echo "kubectl ${KUBECTL_VERSION} déjà installé"
else
  telecharger "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl" kubectl "$KUBECTL_SHA256"
  install -m 0755 "$TMP/kubectl" "$DEST/kubectl"
  echo "kubectl ${KUBECTL_VERSION} installé"
fi

if deja_installe helm "v${HELM_VERSION}" version --short; then
  echo "helm ${HELM_VERSION} déjà installé"
else
  telecharger "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" helm.tar.gz "$HELM_SHA256"
  tar -xzf "$TMP/helm.tar.gz" -C "$TMP" linux-amd64/helm
  install -m 0755 "$TMP/linux-amd64/helm" "$DEST/helm"
  echo "helm ${HELM_VERSION} installé"
fi

if deja_installe terraform "v${TERRAFORM_VERSION}" version; then
  echo "terraform ${TERRAFORM_VERSION} déjà installé"
else
  telecharger "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    terraform.zip "$TERRAFORM_SHA256"
  # python3 plutôt que unzip : unzip n'est pas installé par défaut sur Ubuntu.
  python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extract('terraform', sys.argv[2])" "$TMP/terraform.zip" "$TMP"
  install -m 0755 "$TMP/terraform" "$DEST/terraform"
  echo "terraform ${TERRAFORM_VERSION} installé"
fi

case ":$PATH:" in
  *":$DEST:"*) ;;
  *) echo "Ajoute $DEST à ton PATH (par exemple dans ~/.bashrc)." ;;
esac
