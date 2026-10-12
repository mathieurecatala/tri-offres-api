{{/* Noms et étiquettes communs à tous les objets du chart. */}}

{{- define "tri-offres.nom" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 50 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 50 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "tri-offres.etiquettes" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Sélecteurs : ne changent jamais après l'installation (un Deployment refuse qu'on modifie son sélecteur). */}}
{{- define "tri-offres.selecteur.api" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: api
{{- end -}}

{{- define "tri-offres.selecteur.postgres" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: postgres
{{- end -}}

{{/* Réglages de sécurité communs à tous les conteneurs (exigés par le niveau « restricted » de Kubernetes). */}}
{{- define "tri-offres.securite.conteneur" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}

{{/* Réglages de sécurité des pods qui tournent avec l'image Postgres (utilisateur postgres de l'image alpine). */}}
{{- define "tri-offres.securite.pod.postgres" -}}
runAsNonRoot: true
runAsUser: 70
runAsGroup: 70
seccompProfile:
  type: RuntimeDefault
{{- end -}}
