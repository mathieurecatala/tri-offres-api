variable "nom_cluster" {
  description = "Nom du cluster kind (le conteneur Docker du nœud s'appellera <nom>-control-plane)."
  type        = string
  default     = "tri-offres"
}

variable "image_noeud" {
  description = "Image du nœud kind, épinglée par empreinte : celle publiée pour kind 0.31.0 (la version embarquée par le provider)."
  type        = string
  default     = "kindest/node:v1.35.0@sha256:452d707d4862f52530247495d180205e029056831160e22870e37e3f6c1ac31f"
}

variable "image_api" {
  description = "Nom de l'image de l'API construite en local (cible prod du Dockerfile), sans l'étiquette."
  type        = string
  default     = "tri-offres-api"
}

variable "etiquette_api" {
  description = "Étiquette de l'image de l'API. infra/k8s.sh passe l'identifiant de l'image construite : une nouvelle image = un nouveau déploiement."
  type        = string
  default     = "local"
}

variable "port_local" {
  description = "Port de la machine (127.0.0.1 seulement) sur lequel l'API répond : http://localhost:<port>/docs."
  type        = number
  default     = 8080
}
