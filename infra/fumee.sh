#!/usr/bin/env bash
# Test de fumée HTTP de l'API déployée : de vraies routes doivent répondre. Lecture seule (rien n'est écrit en base)
# et sans appel réseau vers les ATS : il prouve le câblage Service -> API -> Postgres, pas la collecte.
#   infra/fumee.sh http://localhost:8080
set -euo pipefail
URL="${1:?Usage : infra/fumee.sh <adresse de base, par exemple http://localhost:8080>}"
REP="$(mktemp -d)"
trap 'rm -rf "$REP"' EXIT

# lire <chemin> <fichier> : GET, réponse enregistrée dans un fichier (pas de tube qui pourrait se couper en route).
lire() {
  curl --fail --silent --show-error --retry 15 --retry-delay 2 --retry-all-errors -o "$REP/$2" "$URL$1"
  head -c 300 "$REP/$2"
  echo
}

# /health peut mettre quelques secondes à répondre juste après un déploiement (d'où les --retry).
lire /health health.json
grep -q '"statut":"ok"' "$REP/health.json" && grep -q '"base":"ok"' "$REP/health.json" \
  || { echo "ÉCHEC : /health ne dit pas que l'API et la base vont bien" >&2; exit 1; }

lire "/offres?limite=1" offres.json
grep -q '"total":' "$REP/offres.json" || { echo "ÉCHEC : /offres ne rend pas une page d'offres" >&2; exit 1; }

lire "/rejets?limite=1" rejets.json
grep -q '"par_categorie":' "$REP/rejets.json" || { echo "ÉCHEC : /rejets ne rend pas les rejets" >&2; exit 1; }

curl --fail --silent --show-error -o /dev/null "$URL/docs"
echo "Test de fumée HTTP : OK ($URL)"
