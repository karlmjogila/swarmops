---
name: devops-infra
description: >
  Design and operate production infrastructure on AWS using Terraform/Terragrunt for
  IaC, Kubernetes/EKS for container orchestration, Helm for packaging, and ArgoCD for
  GitOps delivery. Covers the full lifecycle: infrastructure provisioning, container
  builds, CI/CD pipelines (GitHub Actions), deployment strategies (blue-green, canary,
  rolling), and observability via the Grafana LGTM stack (Loki, Grafana, Tempo, Mimir).
  Enforces strict build/release/run separation, treats every environment as disposable
  and reproducible from code, and scales horizontally through the process model. Logs
  are event streams routed to Loki, metrics remote-written to Mimir, traces flow through
  OpenTelemetry to Tempo, dashboards managed as code. Every Helm chart ships with
  helm-unittest tests. Infrastructure changes are validated with Terratest. Dev/prod
  parity is non-negotiable.
triggers:
  - docker
  - dockerfile
  - compose
  - ci
  - cd
  - pipeline
  - deploy
  - deployment
  - infrastructure
  - production
  - staging
  - terraform
  - terragrunt
  - kubernetes
  - k8s
  - eks
  - helm
  - helm-unittest
  - gitops
  - argocd
  - observability
  - loki
  - tempo
  - mimir
  - grafana
  - lgtm
  - iac
  - lambda
  - s3
---

# DevOps & Infrastructure

Infrastructure is code. Version it, review it, test it first, automate everything. Manual steps are bugs waiting to happen. Every environment must be rebuildable from `git clone` and `terragrunt apply`.

## Core Principles

1. **Reproducibility** — Every environment is destroyed and recreated from code alone. No snowflakes, no hand-tuned servers. If the AWS account vanished, you rebuild from version control.
2. **Immutability** — Never patch running infrastructure. Build a new image, deploy it, verify, tear down the old. Containers do not get `exec`'d into in production.
3. **Observability** — If you cannot see it, you cannot fix it. Every service emits structured logs (Loki), exposes metrics (Mimir), propagates traces (Tempo), and surfaces health probes. Dashboards are committed as JSON, not clicked together.

## Infrastructure as Code (Terraform / Terragrunt)

### Module Structure

ALWAYS separate reusable Terraform modules from environment config. Modules live in a versioned repo; Terragrunt wires them into environments.

```
infra/
  modules/                     # Separate repo, versioned via Git tags
    eks-cluster/
      main.tf / variables.tf / outputs.tf
      tests/eks_cluster_test.go
    rds-postgres/
    ecr-repo/
  live/                        # Terragrunt environment config
    terragrunt.hcl             # Root: remote state + provider
    _envcommon/
      eks.hcl
    dev/
      env.hcl
      us-east-1/region.hcl
        eks/terragrunt.hcl
    staging/
      env.hcl
      us-east-1/eks/terragrunt.hcl
    prod/
      env.hcl
      us-east-1/eks/terragrunt.hcl
```

### Root Terragrunt Config (State in S3 + DynamoDB Locking)

NEVER use local state for anything beyond throwaway experiments.

```hcl
# live/terragrunt.hcl
remote_state {
  backend = "s3"
  generate = { path = "backend.tf", if_exists = "overwrite_terragrunt" }
  config = {
    bucket         = "myorg-terraform-state-${get_aws_account_id()}"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
provider "aws" {
  region = "${local.region}"
  default_tags {
    tags = { Environment = "${local.environment}", ManagedBy = "terraform" }
  }
}
EOF
}

locals {
  region_vars = read_terragrunt_config(find_in_parent_folders("region.hcl"))
  env_vars    = read_terragrunt_config(find_in_parent_folders("env.hcl"))
  region      = local.region_vars.locals.region
  environment = local.env_vars.locals.environment
}
```

### Environment-Specific Config

```hcl
# live/prod/us-east-1/eks/terragrunt.hcl
terraform {
  source = "git::git@github.com:myorg/infra-modules.git//eks-cluster?ref=v2.4.1"
}
include "root" { path = find_in_parent_folders() }
include "envcommon" {
  path   = "${dirname(find_in_parent_folders())}/_envcommon/eks.hcl"
  expose = true
}
inputs = {
  cluster_name        = "myapp-prod"
  cluster_version     = "1.31"
  node_instance_types = ["m6i.xlarge"]
  node_min_size       = 3
  node_max_size       = 10
}
```

**Module versioning rules:** ALWAYS pin to a Git tag (`?ref=v2.4.1`), NEVER a branch. Promote through environments: dev gets RC tags, staging/prod get stable tags. NEVER `?ref=main` in staging or prod.

### TDD for Infrastructure (Terratest)

Write the test before the module.

```go
// modules/eks-cluster/tests/eks_cluster_test.go
package test

import (
	"testing"
	"time"
	"github.com/gruntwork-io/terratest/modules/k8s"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestEksClusterCreation(t *testing.T) {
	t.Parallel()
	opts := &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"cluster_name": "test-cluster", "cluster_version": "1.31",
			"node_instance_types": []string{"t3.medium"},
			"node_min_size": 1, "node_max_size": 2, "environment": "test",
		},
	}
	defer terraform.Destroy(t, opts)
	terraform.InitAndApply(t, opts)

	endpoint := terraform.Output(t, opts, "cluster_endpoint")
	require.NotEmpty(t, endpoint)

	kubeOpts := k8s.NewKubectlOptions("", terraform.Output(t, opts, "kubeconfig_path"), "default")
	k8s.WaitUntilNumNodesReady(t, kubeOpts, 1, 12, 10*time.Second)
	assert.GreaterOrEqual(t, len(k8s.GetNodes(t, kubeOpts)), 1)
}
```

## Kubernetes / EKS

### Deployment Manifest

Every deployment specifies resource requests/limits, all three health probes, and graceful shutdown. Containers start fast and stop cleanly -- this is the disposability contract. Scale by adding pods, not bigger pods.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels: { app.kubernetes.io/name: myapp }
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels: { app.kubernetes.io/name: myapp }
  template:
    metadata:
      labels: { app.kubernetes.io/name: myapp }
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      serviceAccountName: myapp
      terminationGracePeriodSeconds: 30
      securityContext: { runAsNonRoot: true, runAsUser: 1001, fsGroup: 1001 }
      containers:
        - name: myapp
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.2.3
          ports:
            - { name: http, containerPort: 3000 }
            - { name: metrics, containerPort: 9090 }
          envFrom:
            - configMapRef: { name: myapp-config }
            - secretRef: { name: myapp-secrets }
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { cpu: "1", memory: 512Mi }
          startupProbe:
            httpGet: { path: /api/health, port: http }
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 12
          readinessProbe:
            httpGet: { path: /api/health, port: http }
            periodSeconds: 10
          livenessProbe:
            httpGet: { path: /api/health, port: http }
            periodSeconds: 30
          lifecycle:
            preStop:
              exec: { command: ["sh", "-c", "sleep 5"] }
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels: { app.kubernetes.io/name: myapp }
```

### Service & Ingress (ALB)

```yaml
apiVersion: v1
kind: Service
metadata: { name: myapp }
spec:
  type: ClusterIP
  ports: [{ name: http, port: 80, targetPort: http }]
  selector: { app.kubernetes.io/name: myapp }
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/healthcheck-path: /api/health
spec:
  ingressClassName: alb
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: myapp, port: { name: http } }
```

### Secrets via External Secrets Operator

NEVER put secret values in YAML committed to Git. ALWAYS use ESO backed by AWS Secrets Manager.

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata: { name: myapp-secrets }
spec:
  refreshInterval: 1h
  secretStoreRef: { name: aws-secrets-manager, kind: ClusterSecretStore }
  target: { name: myapp-secrets, creationPolicy: Owner }
  data:
    - secretKey: DATABASE_URL
      remoteRef: { key: myapp/prod/database, property: url }
```

### HPA & IRSA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: myapp }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: myapp }
  minReplicas: 3
  maxReplicas: 20
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

NEVER use node-level IAM roles. ALWAYS use IRSA for pod-level AWS access:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/myapp-prod-role
```

## Helm Charts

### Chart Structure -- Tests Are Mandatory

```
charts/myapp/
  Chart.yaml
  values.yaml              # Safe defaults for dev
  values-prod.yaml         # Production overrides
  templates/
    _helpers.tpl
    deployment.yaml
    service.yaml
    ingress.yaml
    hpa.yaml
    serviceaccount.yaml
  tests/                   # helm-unittest -- NEVER ship without this
    deployment_test.yaml
    ingress_test.yaml
    hpa_test.yaml
```

### Values Pattern

Keep defaults safe for dev. Override per environment. Same chart, different values -- this is how you enforce dev/prod parity.

```yaml
# values.yaml (dev defaults)
replicaCount: 1
image:
  repository: 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp
  tag: "latest"
resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits: { cpu: 500m, memory: 256Mi }
autoscaling: { enabled: false, minReplicas: 1, maxReplicas: 5 }
ingress: { enabled: false, className: alb }
probes:
  startup: { path: /api/health, initialDelaySeconds: 5, failureThreshold: 12 }
  readiness: { path: /api/health, periodSeconds: 10 }
  liveness: { path: /api/health, periodSeconds: 30 }
externalSecret: { enabled: false }
```

```yaml
# values-prod.yaml
replicaCount: 3
image: { tag: "v2.1.0", pullPolicy: Always }
resources:
  requests: { cpu: 250m, memory: 256Mi }
  limits: { cpu: "1", memory: 512Mi }
autoscaling: { enabled: true, minReplicas: 3, maxReplicas: 20 }
ingress:
  enabled: true
  host: myapp.example.com
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/myapp-prod-role
externalSecret:
  enabled: true
  data:
    - secretKey: DATABASE_URL
      remoteRef: { key: myapp/prod/database, property: url }
```

### Helm Unit Tests (helm-unittest)

Install: `helm plugin install https://github.com/helm-unittest/helm-unittest`. Run: `helm unittest charts/myapp --color`.

```yaml
# charts/myapp/tests/deployment_test.yaml
suite: deployment tests
templates: [deployment.yaml]
tests:
  - it: should set replica count from values
    set: { replicaCount: 5 }
    asserts:
      - equal: { path: spec.replicas, value: 5 }

  - it: should run as non-root
    asserts:
      - equal: { path: spec.template.spec.securityContext.runAsNonRoot, value: true }

  - it: should set resource limits
    set:
      resources:
        limits: { cpu: "1", memory: 512Mi }
    asserts:
      - equal: { path: spec.template.spec.containers[0].resources.limits.memory, value: 512Mi }

  - it: should configure all three probes
    asserts:
      - isNotNull: { path: spec.template.spec.containers[0].startupProbe }
      - isNotNull: { path: spec.template.spec.containers[0].readinessProbe }
      - isNotNull: { path: spec.template.spec.containers[0].livenessProbe }

  - it: should set image from values
    set: { image: { repository: my-ecr/myapp, tag: "v3.0.0" } }
    asserts:
      - equal: { path: spec.template.spec.containers[0].image, value: "my-ecr/myapp:v3.0.0" }

  - it: should include preStop hook for graceful shutdown
    asserts:
      - isNotNull: { path: spec.template.spec.containers[0].lifecycle.preStop }
```

```yaml
# charts/myapp/tests/ingress_test.yaml
suite: ingress tests
templates: [ingress.yaml]
tests:
  - it: should not render when disabled
    set: { ingress.enabled: false }
    asserts:
      - hasDocuments: { count: 0 }
  - it: should set host when enabled
    set: { ingress: { enabled: true, className: alb, host: myapp.example.com } }
    asserts:
      - equal: { path: spec.ingressClassName, value: alb }
      - equal: { path: spec.rules[0].host, value: myapp.example.com }
```

```yaml
# charts/myapp/tests/hpa_test.yaml
suite: hpa tests
templates: [hpa.yaml]
tests:
  - it: should not render when autoscaling is disabled
    set: { autoscaling.enabled: false }
    asserts:
      - hasDocuments: { count: 0 }
  - it: should set min and max replicas
    set: { autoscaling: { enabled: true, minReplicas: 3, maxReplicas: 20 } }
    asserts:
      - equal: { path: spec.minReplicas, value: 3 }
      - equal: { path: spec.maxReplicas, value: 20 }
```

## GitOps (ArgoCD)

Separate the app code repo from the GitOps config repo. ArgoCD watches the config repo. Build/release/run are strictly separated.

### ArgoCD Application Manifest

```yaml
# gitops-config/apps/myapp-prod.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-prod
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-failed.slack: platform-alerts
spec:
  project: production
  source:
    repoURL: git@github.com:myorg/app-charts.git
    targetRevision: v1.3.0
    path: charts/myapp
    helm:
      valueFiles: [values.yaml, values-prod.yaml]
      parameters:
        - { name: image.tag, value: "v2.1.0" }
  destination: { server: "https://kubernetes.default.svc", namespace: myapp-prod }
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [CreateNamespace=true, ServerSideApply=true]
    retry: { limit: 3, backoff: { duration: 5s, factor: 2, maxDuration: 3m } }
```

### Promotion Workflow

1. **Build** -- CI builds the container image, tags it `v2.1.0`, pushes to ECR.
2. **Release** -- CI opens a PR updating `image.tag` in `values-staging.yaml`. Merge triggers ArgoCD sync.
3. **Run** -- After staging validation, a second PR updates `values-prod.yaml`. Merge triggers prod sync.

NEVER let CI directly `kubectl apply` or `helm upgrade` against production. All changes flow through Git.

## Observability (Grafana LGTM Stack)

All telemetry flows through Grafana Alloy, which replaces Promtail + standalone OTel collectors.

### Alloy Configuration

```hcl
// alloy-config.alloy -- deployed as ConfigMap in monitoring namespace

// Logs -> Loki
loki.source.kubernetes "pods" {
  targets    = discovery.kubernetes.pods.targets
  forward_to = [loki.write.default.receiver]
}
loki.write "default" {
  endpoint { url = "http://loki-gateway.monitoring:3100/loki/api/v1/push" }
}

// Metrics -> Mimir
prometheus.scrape "pods" {
  targets         = discovery.kubernetes.pods.targets
  forward_to      = [prometheus.remote_write.mimir.receiver]
  scrape_interval = "30s"
}
prometheus.remote_write "mimir" {
  endpoint { url = "http://mimir-distributor.monitoring:9009/api/v1/push" }
}

// Traces -> Tempo
otelcol.receiver.otlp "default" {
  grpc { endpoint = "0.0.0.0:4317" }
  http { endpoint = "0.0.0.0:4318" }
  output { traces = [otelcol.exporter.otlp.tempo.input] }
}
otelcol.exporter.otlp "tempo" {
  client { endpoint = "tempo-distributor.monitoring:4317" }
}
```

### Application Instrumentation

Logs are event streams written to stdout -- the platform ships them. NEVER write log files inside containers.

```typescript
// src/logger.ts -- structured JSON logs -> stdout -> Alloy -> Loki
import pino from "pino";

export const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  timestamp: pino.stdTimeFunctions.isoTime,
  base: {
    service: process.env.OTEL_SERVICE_NAME || "myapp",
    environment: process.env.NODE_ENV || "development",
  },
});
```

```typescript
// src/tracing.ts -- OpenTelemetry traces -> Alloy -> Tempo
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT + "/v1/traces",
  }),
  instrumentations: [getNodeAutoInstrumentations()],
  serviceName: process.env.OTEL_SERVICE_NAME || "myapp",
});
sdk.start();
process.on("SIGTERM", () => sdk.shutdown());
```

### Dashboard as Code & Alerting

NEVER create dashboards by clicking in Grafana without exporting to code. Provision via sidecar ConfigMaps.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-dashboard
  namespace: monitoring
  labels: { grafana_dashboard: "1" }
data:
  myapp-overview.json: |
    {
      "dashboard": {
        "title": "MyApp Overview", "uid": "myapp-overview",
        "panels": [
          { "title": "Request Rate", "type": "timeseries",
            "datasource": { "type": "prometheus", "uid": "mimir" },
            "targets": [{ "expr": "sum(rate(http_requests_total{service=\"myapp\"}[5m])) by (status_code)" }] },
          { "title": "P99 Latency", "type": "timeseries",
            "datasource": { "type": "prometheus", "uid": "mimir" },
            "targets": [{ "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=\"myapp\"}[5m])) by (le))" }] },
          { "title": "Error Logs", "type": "logs",
            "datasource": { "type": "loki", "uid": "loki" },
            "targets": [{ "expr": "{service=\"myapp\"} | json | level = \"error\"" }] }
        ]
      }
    }
```

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata: { name: myapp-alerts, namespace: monitoring }
spec:
  groups:
    - name: myapp.rules
      rules:
        - alert: HighErrorRate
          expr: |
            sum(rate(http_requests_total{service="myapp",status_code=~"5.."}[5m]))
            / sum(rate(http_requests_total{service="myapp"}[5m])) > 0.05
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "Error rate > 5% on myapp"
            runbook: "https://runbooks.example.com/myapp/high-error-rate"
        - alert: PodRestartLoop
          expr: increase(kube_pod_container_status_restarts_total{namespace="myapp-prod"}[15m]) > 3
          for: 5m
          labels: { severity: warning }
```

## CI/CD Pipeline

Strict build/release/run separation. Build produces an immutable container. Release updates GitOps repo. Run is ArgoCD.

```yaml
# .github/workflows/ci-cd.yaml
name: CI/CD
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: 123456789012.dkr.ecr.us-east-1.amazonaws.com
  ECR_REPOSITORY: myapp
permissions: { id-token: write, contents: read, pull-requests: write }

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm test && pnpm lint

  helm-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      - run: helm plugin install https://github.com/helm-unittest/helm-unittest --version v0.7.2
      - run: helm unittest charts/myapp --color --output-type JUnit --output-file helm-test-results.xml

  terraform-plan:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with: { role-to-assume: "arn:aws:iam::123456789012:role/gh-terraform", aws-region: us-east-1 }
      - uses: gruntwork-io/terragrunt-action@v2
        with: { tg_version: "0.68", tg_dir: infra/live/staging, tg_command: "run-all plan --terragrunt-non-interactive" }

  build-push:
    needs: [test, helm-test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    outputs: { image_tag: "${{ steps.meta.outputs.version }}" }
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with: { role-to-assume: "arn:aws:iam::123456789012:role/gh-ecr", aws-region: us-east-1 }
      - uses: aws-actions/amazon-ecr-login@v2
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}
          tags: |
            type=sha,prefix=
            type=semver,pattern=v{{version}}
      - uses: docker/build-push-action@v6
        with: { context: ., push: true, tags: "${{ steps.meta.outputs.tags }}", target: production, cache-from: "type=gha", cache-to: "type=gha,mode=max" }

  deploy-staging:
    needs: build-push
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITOPS_PAT }}
          script: |
            await github.rest.actions.createWorkflowDispatch({
              owner: 'myorg', repo: 'gitops-config', workflow_id: 'promote.yaml', ref: 'main',
              inputs: { app: 'myapp', environment: 'staging', image_tag: '${{ needs.build-push.outputs.image_tag }}' }
            });

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: { name: production, url: "https://myapp.example.com" }
    steps:
      - uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITOPS_PAT }}
          script: |
            await github.rest.actions.createWorkflowDispatch({
              owner: 'myorg', repo: 'gitops-config', workflow_id: 'promote.yaml', ref: 'main',
              inputs: { app: 'myapp', environment: 'production', image_tag: '${{ needs.build-push.outputs.image_tag }}' }
            });
```

## Deployment Strategies

### Rolling Update (Default)

ALWAYS set `maxUnavailable: 0` to maintain full capacity during deploys.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
```

### Blue-Green

Run two environments, swap the Service selector for instant cutover and rollback.

```yaml
apiVersion: v1
kind: Service
metadata: { name: myapp }
spec:
  selector: { app.kubernetes.io/name: myapp, app.kubernetes.io/slot: green }
  ports: [{ port: 80, targetPort: http }]
```

### Canary (Argo Rollouts)

Gradual traffic shifting with automated analysis against Mimir metrics.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata: { name: myapp }
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - analysis:
            templates: [{ templateName: success-rate }]
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 100
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata: { name: success-rate }
spec:
  metrics:
    - name: success-rate
      interval: 60s
      successCondition: result[0] > 0.95
      failureLimit: 3
      provider:
        prometheus:
          address: http://mimir-query-frontend.monitoring:9009
          query: |
            sum(rate(http_requests_total{service="myapp",status_code!~"5.."}[5m]))
            / sum(rate(http_requests_total{service="myapp"}[5m]))
```

## Docker

### GOOD -- Production Dockerfile

```dockerfile
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile --prod
COPY . .

FROM base AS build
RUN pnpm install --frozen-lockfile && pnpm build

FROM node:22-alpine AS production
WORKDIR /app
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup
USER appuser
COPY --from=build --chown=appuser:appgroup /app/.output ./.output
COPY --from=build --chown=appuser:appgroup /app/package.json ./
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
```

### BAD -- Common Mistakes

```dockerfile
# BAD: No multi-stage, root user, unpinned version, no lockfile
FROM node:latest
COPY . .
RUN npm install
CMD ["npm", "start"]
```

### Docker Rules

- One process per container. Pin base image versions. Non-root user.
- `.dockerignore` excludes `node_modules`, `.git`, `.env`, tests.
- Multi-stage builds. NEVER store secrets in images. NEVER install debug tools in prod images.

## Quality Checklist

- [ ] Infrastructure defined in Terraform modules with Terragrunt environment wiring
- [ ] State in S3 with DynamoDB locking -- NEVER local state
- [ ] Module sources pinned to Git tags, not branches
- [ ] Every Helm chart has `tests/` with helm-unittest YAML files
- [ ] All pods have startup, readiness, and liveness probes
- [ ] Resource requests AND limits set on every container
- [ ] Secrets from External Secrets Operator, never from Git
- [ ] IRSA for pod-level AWS access, never node-level IAM roles
- [ ] Structured JSON logs to stdout, shipped to Loki via Alloy
- [ ] Metrics scraped by Alloy, remote-written to Mimir
- [ ] Dashboards committed as JSON ConfigMaps
- [ ] CI runs `helm unittest` and `terraform plan` on every PR

## Anti-Patterns

- **ClickOps infrastructure** -- If it is not in Terraform, it does not exist.
- **Snowflake environments** -- Same Helm chart, different values. Dev/prod parity is mandatory.
- **`kubectl apply` from laptops** -- All production changes flow through ArgoCD and Git.
- **Secrets in Git** -- Use External Secrets Operator backed by AWS Secrets Manager.
- **Logs to files inside containers** -- Logs go to stdout. NEVER write to `/var/log` in a container.
- **No health probes** -- A pod without probes is a pod K8s cannot manage.
- **Node-level IAM roles** -- Use IRSA for least-privilege pod identity.
- **`latest` image tags** -- You cannot rollback to "latest." Use immutable SHA or semver tags.
- **Helm charts without tests** -- No `tests/` directory means not ready to merge.
- **Manual promotion** -- Promotion is automated: dev -> staging -> prod, each gated.
