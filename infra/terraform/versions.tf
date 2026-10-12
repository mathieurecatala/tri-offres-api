# Versions épinglées (vérifiées sur registry.terraform.io le 12/10/2026). Le fichier .terraform.lock.hcl fige en plus
# les empreintes des providers téléchargés : deux postes obtiennent exactement les mêmes binaires.
terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    # Crée et détruit des clusters kind (Kubernetes dans des conteneurs Docker). Embarque kind 0.31.0.
    kind = {
      source  = "tehcyx/kind"
      version = "= 0.11.0"
    }
    # Installe le chart Helm du dépôt dans le cluster.
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
    # Objets Kubernetes simples gérés hors du chart (ici l'espace de noms et son niveau de sécurité).
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "= 3.3.0"
    }
  }
}
