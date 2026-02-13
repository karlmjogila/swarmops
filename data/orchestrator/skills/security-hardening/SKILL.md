---
name: security-hardening
description: >
  Apply production-grade security practices to application code and cloud infrastructure.
  Covers OWASP Top 10 mitigations, input validation, authentication and authorization
  (OAuth2/OIDC, JWT, RBAC), secrets management, injection prevention (SQL, XSS, command,
  prototype pollution), HTTP security headers, AWS IAM least-privilege policies, Kubernetes
  pod security and network policies, encryption at rest and in transit, and software supply
  chain security (dependency auditing, image scanning, SBOM, signed artifacts). Enforces
  defense in depth, least privilege, and fail-secure defaults across TypeScript/Node.js,
  Python, Go, Rust, and infrastructure-as-code (Terraform/Terragrunt, Kubernetes/EKS).
  Trigger this skill for any task involving security review, hardening, authentication,
  authorization, secret handling, vulnerability remediation, OAuth/OIDC flows, JWT
  validation, IAM policies, Kubernetes security contexts, encryption, or supply chain
  integrity.
triggers:
  - security
  - auth
  - authentication
  - authorization
  - token
  - encrypt
  - sanitize
  - vulnerability
  - owasp
  - xss
  - injection
  - csrf
  - cors
  - secret
  - password
  - permission
  - oauth
  - oidc
  - jwt
  - iam
  - rbac
  - supply chain
  - container security
  - network policy
  - sbom
---

# Security Hardening

Security is not a feature — it is a property of every line of code. Every input is hostile, every dependency is suspect, every configuration is an attack surface. Build defensively from the start, because retrofitting security is ten times harder than building it in.

## Core Principles

1. **Defense in depth** — Never rely on a single security control. Layer validation, authentication, authorization, encryption, and monitoring. If one layer fails, the next catches it.
2. **Least privilege** — Every component, user, service account, and pod gets the minimum access it needs. No more. Applies equally to IAM policies, K8s RBAC, database grants, and file permissions.
3. **Fail secure** — When something goes wrong, deny access. Never fail open. An error in your auth middleware means the request is rejected, not allowed through.

## Input Validation (The First Line)

Every piece of external input is untrusted: request bodies, query params, headers, cookies, file uploads, environment variables from unknown sources.

### TDD: Write the Security Test First

```typescript
// input-validator.test.ts — write this BEFORE the implementation
import { describe, it, expect } from 'vitest'
import { validateProjectName } from './input-validator'

describe('validateProjectName', () => {
  it('rejects empty strings', () => {
    expect(() => validateProjectName('')).toThrow('Name must be 1-100 chars')
  })
  it('rejects path traversal', () => {
    expect(() => validateProjectName('../etc/passwd')).toThrow('Invalid name format')
  })
  it('rejects null bytes', () => {
    expect(() => validateProjectName('legit\x00.exe')).toThrow()
  })
  it('accepts valid names', () => {
    expect(validateProjectName('my-project-01')).toBe('my-project-01')
  })
})
```

### Validation Rules

```typescript
// input-validator.ts — implement AFTER tests exist
function validateProjectName(name: unknown): string {
  if (typeof name !== 'string') throw createError({ statusCode: 400, statusMessage: 'Name must be a string' })
  if (name.length === 0 || name.length > 100) throw createError({ statusCode: 400, statusMessage: 'Name must be 1-100 chars' })
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(name)) throw createError({ statusCode: 400, statusMessage: 'Invalid name format' })
  return name
}

// Validate types strictly — don't coerce
if (typeof body.count !== 'number') throw error  // Don't parseInt(body.count)

// Validate enums
const VALID_STATUSES = ['active', 'archived', 'deleted'] as const
if (!VALID_STATUSES.includes(body.status)) throw error
```

### Path Traversal Prevention

```typescript
// BAD — allows ../../../etc/passwd
const filePath = join(projectsDir, name, 'state.json')

// GOOD — validate, resolve, and check containment
const safeName = validateProjectName(name)
const resolved = resolve(projectsDir, safeName, 'state.json')
if (!resolved.startsWith(resolve(projectsDir))) {
  throw createError({ statusCode: 400, statusMessage: 'Invalid path' })
}
```

### Command Injection Prevention

```typescript
// BAD — command injection via projectName
exec(`git clone ${url} ${projectName}`)

// GOOD — parameterized APIs that never invoke a shell
execFile('git', ['clone', url, projectName])
spawn('git', ['clone', '--', url, projectName], { cwd: safeDir, stdio: 'pipe' })
```

## Authentication

### Token Handling

```typescript
setCookie(event, 'auth_token', token, {
  httpOnly: true,        // Not accessible via JavaScript
  secure: true,          // Only sent over HTTPS
  sameSite: 'lax',       // CSRF protection
  maxAge: 60 * 60 * 24,  // 24h expiry
  path: '/',
})

// Constant-time comparison prevents timing attacks
import { timingSafeEqual } from 'crypto'
function validateToken(provided: string, expected: string): boolean {
  if (provided.length !== expected.length) return false
  return timingSafeEqual(Buffer.from(provided), Buffer.from(expected))
}

// GOOD — log the action, never the credential
console.log(`Auth attempt for user ${userId}`)
// BAD — token appears in logs, log aggregators, error tracking
console.log(`Token: ${token}`)
```

### OAuth2 / OIDC Patterns

Use Authorization Code flow with PKCE for all clients. Never use Implicit flow.

```typescript
import { generators } from 'openid-client'

// Step 1: Generate PKCE challenge at login start
const codeVerifier = generators.codeVerifier()
const codeChallenge = generators.codeChallenge(codeVerifier)
session.codeVerifier = codeVerifier  // Server-side only — never expose to client

const authUrl = new URL('https://idp.example.com/authorize')
authUrl.searchParams.set('client_id', process.env.OIDC_CLIENT_ID!)
authUrl.searchParams.set('response_type', 'code')
authUrl.searchParams.set('scope', 'openid profile email')
authUrl.searchParams.set('redirect_uri', process.env.OIDC_REDIRECT_URI!)
authUrl.searchParams.set('code_challenge', codeChallenge)
authUrl.searchParams.set('code_challenge_method', 'S256')
authUrl.searchParams.set('state', session.csrfState)

// Step 2: Exchange code for tokens at callback
async function handleOAuthCallback(code: string, codeVerifier: string) {
  const resp = await fetch('https://idp.example.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: process.env.OIDC_REDIRECT_URI!,
      client_id: process.env.OIDC_CLIENT_ID!,
      client_secret: process.env.OIDC_CLIENT_SECRET!,
      code_verifier: codeVerifier,
    }),
  })
  if (!resp.ok) throw createError({ statusCode: 401, statusMessage: 'Token exchange failed' })
  return resp.json()
}

// BAD — Implicit flow exposes tokens in URL fragments
authUrl.searchParams.set('response_type', 'token')  // NEVER
```

### JWT Best Practices

```typescript
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from 'jose'

// GOOD — RS256 with remote JWKS (asymmetric, keys rotate without redeployment)
const jwks = createRemoteJWKSet(new URL('https://idp.example.com/.well-known/jwks.json'))

async function verifyAccessToken(token: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, jwks, {
    issuer: 'https://idp.example.com',
    audience: 'https://api.example.com',
    algorithms: ['RS256'],       // Explicitly allowlist — reject 'none' and HS256
    clockTolerance: 30,
  })
  return payload
}

// BAD — HS256 with shared secret (compromise = full token forgery)
// BAD — No issuer/audience validation (accepts tokens from any provider)
// BAD — Accepting the 'none' algorithm (unsigned tokens bypass auth)

// Refresh token rotation: new refresh token on each use, invalidate previous.
// Detect reuse as a breach signal and revoke the entire token family.
async function rotateRefreshToken(oldToken: string) {
  const stored = await db.refreshToken.findUnique({ where: { token: oldToken } })
  if (!stored || stored.revoked) {
    await db.refreshToken.updateMany({ where: { familyId: stored?.familyId }, data: { revoked: true } })
    throw createError({ statusCode: 401, statusMessage: 'Refresh token reuse detected' })
  }
  await db.refreshToken.update({ where: { id: stored.id }, data: { revoked: true } })
  const newToken = generateSecureToken()
  await db.refreshToken.create({ data: { token: newToken, userId: stored.userId, familyId: stored.familyId } })
  return { accessToken: signAccessToken(stored.userId), refreshToken: newToken }
}
```

## Authorization

### Check Permissions at Every Layer

```typescript
export default defineEventHandler(async (event) => {
  const user = await requireAuth(event)                         // Layer 1: authenticated?
  const project = await getProject(name)
  if (project.ownerId !== user.id)                              // Layer 2: owns resource?
    throw createError({ statusCode: 403, statusMessage: 'Forbidden' })
  if (action === 'delete' && !user.roles.includes('admin'))     // Layer 3: permitted action?
    throw createError({ statusCode: 403, statusMessage: 'Admin required' })
})
```

### Localhost Trust

```typescript
function isLocalhostRequest(event: any): boolean {
  const addr = event.node?.req?.socket?.remoteAddress || ''
  return addr === '127.0.0.1' || addr === '::1' || addr === '::ffff:127.0.0.1'
}
// BAD — trusting X-Forwarded-For (client-controlled) or Host header for auth
```

## Secrets Management

Secrets NEVER live in code. They are environment configuration (12-Factor, Factor III). Backing services are attached resources configured via env URLs (Factor IV).

```typescript
// BAD
const token = 'eaa3cf1ca047c50b...'

// GOOD — from environment, validated at startup
const token = process.env.GATEWAY_TOKEN

const REQUIRED = ['GATEWAY_TOKEN', 'DATABASE_URL', 'OIDC_CLIENT_SECRET'] as const
for (const key of REQUIRED) {
  if (!process.env[key]) { console.error(`FATAL: Missing env var: ${key}`); process.exit(1) }
}

// NEVER log secrets, include in errors, or send to client
console.log(`Config: ${JSON.stringify(config)}`)        // BAD — might include tokens
throw new Error(`Auth failed with token ${token}`)      // BAD
return { config: runtimeConfig }                         // BAD — exposes server secrets
```

## Injection Prevention

### SQL Injection

```typescript
// BAD
db.query(`SELECT * FROM users WHERE name = '${name}'`)
// GOOD — parameterized queries
db.query('SELECT * FROM users WHERE name = ?', [name])
```

### XSS Prevention

```typescript
// Vue/Nuxt {{ }} is auto-escaped — safe by default
// NEVER use v-html with user content; sanitize if you must
import DOMPurify from 'dompurify'
const safeHtml = DOMPurify.sanitize(userContent)
```

### Prototype Pollution

```typescript
// BAD — user input as object key (__proto__, constructor)
config[body.field] = body.value

// GOOD — allowlist keys or use Map
const ALLOWED = ['name', 'email', 'role']
if (!ALLOWED.includes(body.field)) throw error
const store = new Map<string, string>()
```

## HTTP Security Headers

```typescript
const securityHeaders = {
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'X-XSS-Protection': '0',                                 // Disable legacy — CSP is the defense
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
}
```

## AWS IAM — Least Privilege

### Policy Authoring

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowS3ReadSpecificBucket",
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::my-app-assets-prod",
      "arn:aws:s3:::my-app-assets-prod/*"
    ],
    "Condition": {
      "StringEquals": { "aws:RequestedRegion": "us-east-1" }
    }
  }]
}
```

```json
// BAD — wildcard actions and resources
{ "Effect": "Allow", "Action": "s3:*", "Resource": "*" }
```

### IRSA (IAM Roles for Service Accounts)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-app-production
```

```hcl
resource "aws_iam_role" "app_role" {
  name = "my-app-production"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = "arn:aws:iam::123456789012:oidc-provider/${var.oidc_provider}" }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_provider}:sub" = "system:serviceaccount:production:my-app"
          "${var.oidc_provider}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "app_s3_read" {
  role   = aws_iam_role.app_role.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = ["arn:aws:s3:::my-app-assets-prod/*"] }]
  })
}
```

IAM rules: scope to specific ARNs, use Condition blocks, prefer IRSA over instance profiles, use service-linked roles, prune with IAM Access Analyzer.

## Kubernetes Security

### Pod Security (Restricted)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels: { app: my-app }
  template:
    metadata:
      labels: { app: my-app }
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: my-app
          image: my-registry/my-app:v1.2.3@sha256:abc123  # Pin by digest
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits: { cpu: 500m, memory: 512Mi }
          volumeMounts:
            - { name: tmp, mountPath: /tmp }
      volumes:
        - { name: tmp, emptyDir: { sizeLimit: 100Mi } }
```

```yaml
# BAD — privileged, root, writable filesystem
securityContext: { privileged: true, runAsUser: 0 }
```

### NetworkPolicy — Default Deny, Explicit Allow

```yaml
# Default deny all traffic in namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# Allow only required traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-my-app
  namespace: production
spec:
  podSelector:
    matchLabels: { app: my-app }
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector: { matchLabels: { name: ingress-nginx } }
      ports: [{ protocol: TCP, port: 3000 }]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { name: database } }
      ports: [{ protocol: TCP, port: 5432 }]
    - to:
        - namespaceSelector: {}
      ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
```

### Secrets — External Secrets Operator

```yaml
# GOOD — sync from AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef: { name: aws-secrets-manager, kind: ClusterSecretStore }
  target: { name: my-app-secrets, creationPolicy: Owner }
  data:
    - { secretKey: DATABASE_URL, remoteRef: { key: production/my-app/database-url } }
    - { secretKey: OIDC_CLIENT_SECRET, remoteRef: { key: production/my-app/oidc-client-secret } }
```

```yaml
# BAD — base64 Secret committed to git (base64 is encoding, NOT encryption)
apiVersion: v1
kind: Secret
data:
  DATABASE_URL: cG9zdGdyZXM6Ly91c2VyOnBhc3NAaG9zdA==
```

## Encryption

### At Rest

```hcl
# S3 — SSE with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.app.arn
    }
    bucket_key_enabled = true
  }
}

# RDS — must enable at creation (cannot add later)
resource "aws_db_instance" "main" {
  storage_encrypted = true
  kms_key_id        = aws_kms_key.app.arn
}

# EBS — account-level default encryption
resource "aws_ebs_encryption_by_default" "enabled" { enabled = true }
```

### In Transit

```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn
  default_action { type = "forward"; target_group_arn = aws_lb_target_group.app.arn }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect { port = "443"; protocol = "HTTPS"; status_code = "HTTP_301" }
  }
}
```

### Application-Level Encryption

```typescript
import { createCipheriv, createDecipheriv, randomBytes } from 'crypto'

const ALGORITHM = 'aes-256-gcm'

function encrypt(plaintext: string, keyBase64: string): string {
  const key = Buffer.from(keyBase64, 'base64')
  const iv = randomBytes(12)
  const cipher = createCipheriv(ALGORITHM, key, iv)
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()])
  const authTag = cipher.getAuthTag()
  return [iv.toString('base64'), authTag.toString('base64'), encrypted.toString('base64')].join(':')
}

function decrypt(token: string, keyBase64: string): string {
  const key = Buffer.from(keyBase64, 'base64')
  const [ivB64, tagB64, dataB64] = token.split(':')
  const decipher = createDecipheriv(ALGORITHM, key, Buffer.from(ivB64, 'base64'))
  decipher.setAuthTag(Buffer.from(tagB64, 'base64'))
  return decipher.update(Buffer.from(dataB64, 'base64')) + decipher.final('utf8')
}

// BAD — ECB mode, AES-CBC without HMAC, predictable IVs
// GOOD — AES-256-GCM (authenticated encryption: confidentiality + integrity)
```

### mTLS in Kubernetes

```yaml
# Istio PeerAuthentication — enforce strict mTLS between pods
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: production }
spec:
  mtls: { mode: STRICT }
```

## Supply Chain Security

### Dependency Auditing

```bash
# Run in CI, fail on high/critical
npm audit --audit-level=high        # Node.js
pip-audit --strict --desc           # Python
govulncheck ./...                   # Go
cargo audit                         # Rust
```

### Container Image Scanning

```yaml
- name: Scan container image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: my-registry/my-app:${{ github.sha }}
    format: table
    exit-code: 1
    severity: CRITICAL,HIGH
    ignore-unfixed: true
```

### SBOM and Signed Artifacts

```bash
# Generate SBOM
syft my-registry/my-app:v1.2.3 -o spdx-json > sbom.spdx.json

# Sign images with cosign (keyless via Sigstore for CI)
cosign sign --yes my-registry/my-app:v1.2.3@sha256:abc123

# Verify before deploying
cosign verify my-registry/my-app:v1.2.3@sha256:abc123 \
  --certificate-identity=deploy@my-org.iam.gserviceaccount.com \
  --certificate-oidc-issuer=https://accounts.google.com

# Signed commits
git config --global commit.gpgsign true
```

Supply chain rules: audit deps in CI, scan images before registry push, pin images by digest, generate SBOMs per release, sign and verify images, minimize dependencies, vet new deps (maintainers, freshness, CVEs).

## File Operations

```typescript
function safePath(base: string, userInput: string): string {
  const resolved = resolve(base, userInput)
  if (!resolved.startsWith(resolve(base) + sep) && resolved !== resolve(base)) {
    throw new Error('Path traversal detected')
  }
  return resolved
}

await writeFile(path, data, { mode: 0o600 })  // Owner read/write only
const stats = await lstat(path)                // lstat — doesn't follow symlinks
if (stats.isSymbolicLink()) throw new Error('Symlinks not allowed')
```

## Quality Checklist

- [ ] All user input validated at system boundaries (type, range, format)
- [ ] No user input in file paths, shell commands, or SQL without sanitization
- [ ] Auth on all sensitive endpoints; JWT validated with issuer/audience/algorithm checks
- [ ] Authorization checked per resource and per operation
- [ ] Secrets in env vars or secret manager, never in code or git
- [ ] No secrets in logs, error messages, or client responses
- [ ] Cookies are httpOnly, secure, sameSite; tokens use RS256 with rotation
- [ ] Security headers on all responses (CSP, HSTS, X-Frame-Options)
- [ ] Dependencies audited in CI; container images scanned before deployment
- [ ] K8s pods run non-root, read-only rootfs, dropped caps, NetworkPolicies enforced
- [ ] Encryption at rest for all stores (S3, RDS, EBS); TLS 1.2+ in transit
- [ ] IAM policies scoped to specific resources with conditions; IRSA for pod AWS access

## Anti-Patterns

- **"Security through obscurity"** — Hiding endpoints instead of protecting them. Assume attackers know your URL structure.
- **Client-side validation only** — Client validation is UX; server validation is security.
- **Weak password hashing** — MD5/SHA1 for passwords. Use bcrypt or argon2.
- **`"Resource": "*"` in IAM** — Every policy must scope to specific ARNs.
- **Running containers as root** — Always `runAsNonRoot`, `readOnlyRootFilesystem`, `drop: ["ALL"]`.
- **Base64 is not encryption** — K8s Secrets are encoded, not encrypted. Use External Secrets Operator.
- **Accepting JWT `none` algorithm** — Explicitly allowlist signing algorithms.
- **Disabling security for convenience** — `--no-verify`, `secure: false`, `privileged: true` are never acceptable in production.
- **"We'll add security later"** — Later never comes.
- **No NetworkPolicy** — Without default-deny, every pod talks to every pod. Lateral movement is trivial.
