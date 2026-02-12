{{/*
Expand the name of the chart.
*/}}
{{- define "hyperliquid-bot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "hyperliquid-bot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "hyperliquid-bot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "hyperliquid-bot.labels" -}}
helm.sh/chart: {{ include "hyperliquid-bot.chart" . }}
{{ include "hyperliquid-bot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "hyperliquid-bot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hyperliquid-bot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "hyperliquid-bot.backend.labels" -}}
{{ include "hyperliquid-bot.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "hyperliquid-bot.backend.selectorLabels" -}}
{{ include "hyperliquid-bot.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "hyperliquid-bot.frontend.labels" -}}
{{ include "hyperliquid-bot.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "hyperliquid-bot.frontend.selectorLabels" -}}
{{ include "hyperliquid-bot.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Create the name of the backend service account to use
*/}}
{{- define "hyperliquid-bot.backend.serviceAccountName" -}}
{{- if .Values.backend.serviceAccount.create }}
{{- default (printf "%s-backend" (include "hyperliquid-bot.fullname" .)) .Values.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the frontend service account to use
*/}}
{{- define "hyperliquid-bot.frontend.serviceAccountName" -}}
{{- if .Values.frontend.serviceAccount.create }}
{{- default (printf "%s-frontend" (include "hyperliquid-bot.fullname" .)) .Values.frontend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.frontend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend image
*/}}
{{- define "hyperliquid-bot.backend.image" -}}
{{- $tag := default .Chart.AppVersion .Values.backend.image.tag }}
{{- printf "%s:%s" .Values.backend.image.repository $tag }}
{{- end }}

{{/*
Frontend image
*/}}
{{- define "hyperliquid-bot.frontend.image" -}}
{{- $tag := default .Chart.AppVersion .Values.frontend.image.tag }}
{{- printf "%s:%s" .Values.frontend.image.repository $tag }}
{{- end }}

{{/*
Namespace
*/}}
{{- define "hyperliquid-bot.namespace" -}}
{{- default .Release.Namespace .Values.namespaceOverride }}
{{- end }}

{{/*
Secret name
*/}}
{{- define "hyperliquid-bot.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "hyperliquid-bot.fullname" . }}
{{- end }}
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "hyperliquid-bot.configMapName" -}}
{{- include "hyperliquid-bot.fullname" . }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "hyperliquid-bot.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
PostgreSQL port
*/}}
{{- define "hyperliquid-bot.postgresql.port" -}}
{{- if .Values.postgresql.enabled }}
{{- "5432" }}
{{- else }}
{{- .Values.externalDatabase.port | default "5432" }}
{{- end }}
{{- end }}

{{/*
PostgreSQL database
*/}}
{{- define "hyperliquid-bot.postgresql.database" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
PostgreSQL username
*/}}
{{- define "hyperliquid-bot.postgresql.username" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.username }}
{{- else }}
{{- .Values.externalDatabase.username }}
{{- end }}
{{- end }}

{{/*
PostgreSQL secret name for password
*/}}
{{- define "hyperliquid-bot.postgresql.secretName" -}}
{{- if .Values.postgresql.enabled }}
{{- if .Values.postgresql.auth.existingSecret }}
{{- .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}
{{- else }}
{{- include "hyperliquid-bot.secretName" . }}
{{- end }}
{{- end }}

{{/*
PostgreSQL secret key for password
*/}}
{{- define "hyperliquid-bot.postgresql.secretKey" -}}
{{- if .Values.postgresql.enabled }}
{{- "password" }}
{{- else }}
{{- "database-password" }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "hyperliquid-bot.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" .Release.Name }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Redis port
*/}}
{{- define "hyperliquid-bot.redis.port" -}}
{{- if .Values.redis.enabled }}
{{- "6379" }}
{{- else }}
{{- .Values.externalRedis.port | default "6379" }}
{{- end }}
{{- end }}

{{/*
Redis secret name for password
*/}}
{{- define "hyperliquid-bot.redis.secretName" -}}
{{- if .Values.redis.enabled }}
{{- if .Values.redis.auth.existingSecret }}
{{- .Values.redis.auth.existingSecret }}
{{- else }}
{{- printf "%s-redis" .Release.Name }}
{{- end }}
{{- else }}
{{- include "hyperliquid-bot.secretName" . }}
{{- end }}
{{- end }}

{{/*
Redis secret key for password
*/}}
{{- define "hyperliquid-bot.redis.secretKey" -}}
{{- if .Values.redis.enabled }}
{{- "redis-password" }}
{{- else }}
{{- "redis-password" }}
{{- end }}
{{- end }}

{{/*
Database URL template
*/}}
{{- define "hyperliquid-bot.databaseUrl" -}}
postgresql+asyncpg://$(DATABASE_USER):$(DATABASE_PASSWORD)@{{ include "hyperliquid-bot.postgresql.host" . }}:{{ include "hyperliquid-bot.postgresql.port" . }}/{{ include "hyperliquid-bot.postgresql.database" . }}
{{- end }}

{{/*
Redis URL template
*/}}
{{- define "hyperliquid-bot.redisUrl" -}}
redis://:$(REDIS_PASSWORD)@{{ include "hyperliquid-bot.redis.host" . }}:{{ include "hyperliquid-bot.redis.port" . }}/0
{{- end }}

{{/*
Pod anti-affinity
*/}}
{{- define "hyperliquid-bot.podAntiAffinity" -}}
{{- if eq .type "hard" }}
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          {{- include .selectorLabels .context | nindent 10 }}
      topologyKey: kubernetes.io/hostname
{{- else }}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            {{- include .selectorLabels .context | nindent 12 }}
        topologyKey: kubernetes.io/hostname
{{- end }}
{{- end }}

{{/*
Render pod annotations with checksum for config/secrets
*/}}
{{- define "hyperliquid-bot.checksumAnnotations" -}}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
{{- if .Values.secrets.create }}
checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
{{- end }}
{{- end }}
