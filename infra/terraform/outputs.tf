output "url_api" {
  description = "Adresse de l'API sur cette machine."
  value       = "http://localhost:${var.port_local}"
}

output "kubeconfig" {
  description = "Pour utiliser kubectl ou helm sur ce cluster : export KUBECONFIG=<ce chemin>."
  value       = kind_cluster.local.kubeconfig_path
}
