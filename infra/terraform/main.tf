# Tri d'offres sur un cluster Kubernetes LOCAL (kind), sans compte cloud : tout tourne dans Docker sur ce poste.
# Ordre de création : cluster kind -> image de l'API chargée dans le nœud -> espace de noms -> chart Helm.
# « terraform destroy » défait tout dans l'ordre inverse (le cluster en dernier, ce qui efface aussi ses volumes).

locals {
  espace_de_noms = "tri-offres"
  # Port du nœud kind sur lequel le Service de l'API est exposé (plage NodePort 30000-32767).
  node_port = 30080
  chart     = "${path.module}/../helm/tri-offres"
  # Empreinte de tous les fichiers du chart. Pour un chart local, le provider helm ne compare que la version du chart
  # et les valeurs : une sonde modifiée dans un template, sans changer Chart.yaml, donnait « No changes » (vérifié le
  # 13/10/2026). Passer cette empreinte dans les valeurs force un « helm upgrade » dès qu'un fichier du chart change.
  empreinte_chart = sha1(join("", [for f in sort(fileset(local.chart, "**")) : filesha1("${local.chart}/${f}")]))
}

resource "kind_cluster" "local" {
  name            = var.nom_cluster
  node_image      = var.image_noeud
  wait_for_ready  = true
  kubeconfig_path = abspath("${path.module}/kubeconfig") # à part : ne touche pas ~/.kube/config

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      # Le port 30080 du nœud (NodePort de l'API) est publié sur 127.0.0.1:<port_local> de la machine.
      extra_port_mappings {
        container_port = local.node_port
        host_port      = var.port_local
        listen_address = "127.0.0.1"
      }
    }
  }
}

# L'image de l'API n'est publiée dans aucun registre : on la copie de Docker vers le nœud kind.
# Refait si le cluster est recréé ou si l'étiquette de l'image change.
resource "terraform_data" "image_api" {
  triggers_replace = [kind_cluster.local.id, var.etiquette_api]

  provisioner "local-exec" {
    command = "kind load docker-image '${var.image_api}:${var.etiquette_api}' --name '${kind_cluster.local.name}'"
  }
}

provider "kubernetes" {
  host                   = kind_cluster.local.endpoint
  client_certificate     = kind_cluster.local.client_certificate
  client_key             = kind_cluster.local.client_key
  cluster_ca_certificate = kind_cluster.local.cluster_ca_certificate
}

provider "helm" {
  kubernetes = {
    host                   = kind_cluster.local.endpoint
    client_certificate     = kind_cluster.local.client_certificate
    client_key             = kind_cluster.local.client_key
    cluster_ca_certificate = kind_cluster.local.cluster_ca_certificate
  }
}

# Espace de noms au niveau de sécurité « restricted » : Kubernetes refuse tout pod qui tournerait en root,
# garderait des droits Linux ou pourrait élever ses privilèges. Le chart doit donc être propre pour s'installer.
resource "kubernetes_namespace_v1" "tri_offres" {
  metadata {
    name = local.espace_de_noms
    labels = {
      "pod-security.kubernetes.io/enforce" = "restricted"
    }
  }
}

resource "helm_release" "tri_offres" {
  name      = "tri-offres"
  namespace = kubernetes_namespace_v1.tri_offres.metadata[0].name
  chart     = local.chart

  # Terraform attend que l'API et Postgres soient prêts (sondes readiness) avant de déclarer le déploiement réussi.
  wait    = true
  timeout = 300

  values = [yamlencode({
    api = {
      image = {
        repository = var.image_api
        tag        = var.etiquette_api
      }
      service = {
        type      = "NodePort"
        nodePort  = local.node_port
        portLocal = var.port_local
      }
    }
    empreinteChart = local.empreinte_chart
  })]

  depends_on = [terraform_data.image_api]
}
