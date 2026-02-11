---
name: security-hardening
description: >
  Apply security best practices to code and infrastructure. Covers OWASP Top 10,
  input validation, authentication, authorization, secrets management, injection
  prevention, CSRF/XSS protection, and secure configuration. Trigger this skill
  for any task involving security review, hardening, authentication, authorization,
  secret handling, or vulnerability remediation. Also trigger when the task mentions
  security, auth, token, encryption, sanitize, or vulnerability.
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
---

# Security Hardening

Security is not a feature — it's a property of every line of code. Every input is hostile, every dependency is suspect, every configuration is an attack surface. Build defensively from the start, because retrofitting security is ten times harder than building it in.

## Mindset

1. **Defense in depth** — Never rely on a single security control. Layer validation, authentication, authorization, and monitoring.
2. **Least privilege** — Every component gets the minimum access it needs. No more.
3. **Fail secure** — When something goes wrong, deny access. Never fail open.

## Input Validation (The First Line)

Every piece of external input is untrusted: request bodies, query params, path params, headers, cookies, file uploads, environment variables from unknown sources.

### Validation Rules
```typescript
// ALWAYS validate at system boundaries
function validateProjectName(name: unknown): string {
  if (typeof name !== 'string') throw createError({ statusCode: 400, statusMessage: 'Name must be a string' })
  if (name.length === 0 || name.length > 100) throw createError({ statusCode: 400, statusMessage: 'Name must be 1-100 chars' })
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(name)) throw createError({ statusCode: 400, statusMessage: 'Invalid name format' })
  return name
}

// Validate types strictly — don't coerce
if (typeof body.count !== 'number') throw error  // Don't parseInt(body.count)

// Validate ranges
if (body.limit < 1 || body.limit > 100) throw error

// Validate enums
const VALID_STATUSES = ['active', 'archived', 'deleted'] as const
if (!VALID_STATUSES.includes(body.status)) throw error
```

### Path Traversal Prevention
```typescript
// NEVER concatenate user input into file paths without validation
const name = getRouterParam(event, 'name')

// BAD — allows ../../../etc/passwd
const filePath = join(projectsDir, name, 'state.json')

// GOOD — validate then resolve and check containment
const safeName = validateProjectName(name)
const resolved = resolve(projectsDir, safeName, 'state.json')
if (!resolved.startsWith(resolve(projectsDir))) {
  throw createError({ statusCode: 400, statusMessage: 'Invalid path' })
}
```

### Command Injection Prevention
```typescript
// NEVER pass user input to shell commands
// BAD — command injection via projectName
exec(`git clone ${url} ${projectName}`)

// GOOD — use parameterized APIs
execFile('git', ['clone', url, projectName])

// GOOD — use spawn with explicit args array
spawn('git', ['clone', '--', url, projectName], {
  cwd: safeDir,
  stdio: 'pipe',
})

// If you MUST use exec, escape everything
import { quote } from 'shell-quote'
exec(quote(['git', 'clone', url, projectName]))
```

## Authentication

### Token Handling
```typescript
// Store tokens securely
setCookie(event, 'auth_token', token, {
  httpOnly: true,        // Not accessible via JavaScript
  secure: isHttps,       // Only sent over HTTPS
  sameSite: 'lax',       // CSRF protection
  maxAge: 60 * 60 * 24,  // Reasonable expiry
  path: '/',
})

// Validate tokens with constant-time comparison
import { timingSafeEqual } from 'crypto'

function validateToken(provided: string, expected: string): boolean {
  if (provided.length !== expected.length) return false
  return timingSafeEqual(
    Buffer.from(provided),
    Buffer.from(expected)
  )
}

// NEVER log tokens
console.log(`Auth attempt for user ${userId}`)  // GOOD
console.log(`Token: ${token}`)  // BAD — appears in logs
```

### Session Security
```typescript
// Regenerate session ID after authentication state changes
// Invalidate sessions on logout (don't just delete cookie)
// Set reasonable session timeouts
// Track active sessions for audit
```

## Authorization

### Check Permissions at Every Layer
```typescript
// Route-level: middleware
export default defineEventHandler(async (event) => {
  requireAuth(event)  // Is the user authenticated?

  const project = await getProject(name)

  // Resource-level: can this user access this project?
  if (project.ownerId !== event.context.userId) {
    throw createError({ statusCode: 403, statusMessage: 'Forbidden' })
  }

  // Operation-level: can this user do this action?
  if (action === 'delete' && !event.context.user.isAdmin) {
    throw createError({ statusCode: 403, statusMessage: 'Admin required' })
  }
})
```

### Localhost Trust — Be Careful
```typescript
// If you trust localhost for agent callbacks, verify THOROUGHLY
function isLocalhostRequest(event: any): boolean {
  const remoteAddr = event.node?.req?.socket?.remoteAddress || ''
  // Check actual socket address, not headers (headers can be spoofed)
  return remoteAddr === '127.0.0.1' || remoteAddr === '::1' || remoteAddr === '::ffff:127.0.0.1'
}

// DON'T trust X-Forwarded-For alone — it's client-controlled
// DON'T trust Host header for auth decisions
```

## Secrets Management

### Rules
```typescript
// NEVER hardcode secrets
const token = 'eaa3cf1ca047c50b...'  // BAD

// ALWAYS use environment variables
const token = process.env.GATEWAY_TOKEN  // GOOD

// NEVER commit secrets to git
// .gitignore must include: .env, *.key, *.pem, credentials.json

// NEVER log secrets
console.log(`Config: ${JSON.stringify(config)}`)  // BAD — might include tokens

// NEVER include secrets in error messages
throw new Error(`Auth failed with token ${token}`)  // BAD

// NEVER send secrets to the client
return { config: runtimeConfig }  // BAD — includes server-only secrets
```

### Environment Variable Safety
```typescript
// Validate required secrets exist at startup
const required = ['GATEWAY_TOKEN', 'DATABASE_URL']
for (const key of required) {
  if (!process.env[key]) {
    console.error(`Missing required env var: ${key}`)
    process.exit(1)
  }
}
```

## Injection Prevention

### SQL Injection
```typescript
// NEVER concatenate user input into queries
// BAD
db.query(`SELECT * FROM users WHERE name = '${name}'`)

// GOOD — parameterized queries
db.query('SELECT * FROM users WHERE name = ?', [name])
```

### XSS Prevention
```typescript
// In Vue/Nuxt, v-text and {{ }} are auto-escaped — safe by default
// NEVER use v-html with user-controlled content
<div v-html="userContent" />  // BAD — XSS vector

// If you must render HTML, sanitize first
import DOMPurify from 'dompurify'
const safeHtml = DOMPurify.sanitize(userContent)

// Set Content Security Policy headers
headers: {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
}
```

### Prototype Pollution
```typescript
// NEVER use user input as object keys without validation
const key = body.field
config[key] = body.value  // BAD — __proto__, constructor, etc.

// GOOD — allowlist valid keys
const ALLOWED_FIELDS = ['name', 'email', 'role']
if (!ALLOWED_FIELDS.includes(key)) throw error

// GOOD — use Map instead of plain objects for dynamic keys
const store = new Map<string, string>()
store.set(key, value)
```

## HTTP Security Headers

```typescript
// Set these on all responses
const securityHeaders = {
  'X-Frame-Options': 'DENY',                              // Prevent clickjacking
  'X-Content-Type-Options': 'nosniff',                     // Prevent MIME sniffing
  'Referrer-Policy': 'strict-origin-when-cross-origin',    // Control referrer info
  'X-XSS-Protection': '0',                                // Disable (CSP is better)
  'Strict-Transport-Security': 'max-age=31536000',         // Force HTTPS
  'Content-Security-Policy': "default-src 'self'",         // Restrict resource loading
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',  // Limit browser APIs
}
```

## Dependency Security

```typescript
// Audit dependencies regularly
// npm audit / pnpm audit

// Pin dependency versions (use lockfile)
// Review new dependencies before adding:
// - How many maintainers?
// - When was the last update?
// - How many downloads?
// - Any known vulnerabilities?

// Minimize dependencies — every dependency is attack surface
// Don't add a package for something you can write in 10 lines
```

## File Operations

```typescript
// Validate file paths before any operation
function safePath(base: string, userInput: string): string {
  const resolved = resolve(base, userInput)
  if (!resolved.startsWith(resolve(base) + sep) && resolved !== resolve(base)) {
    throw new Error('Path traversal detected')
  }
  return resolved
}

// Set restrictive permissions on created files
await writeFile(path, data, { mode: 0o600 })  // Owner read/write only

// Don't follow symlinks blindly
const stats = await lstat(path)  // lstat, not stat — doesn't follow symlinks
if (stats.isSymbolicLink()) throw new Error('Symlinks not allowed')
```

## Security Review Checklist

- [ ] All user input validated at system boundaries
- [ ] No user input in file paths, shell commands, or SQL without sanitization
- [ ] Authentication required on all sensitive endpoints
- [ ] Authorization checked per resource and per operation
- [ ] Secrets in environment variables, not code
- [ ] No secrets in logs, error messages, or client responses
- [ ] Cookies are httpOnly, secure, sameSite
- [ ] Security headers set on all responses
- [ ] Dependencies audited for known vulnerabilities
- [ ] No v-html with user-controlled content
- [ ] File operations validate paths against traversal
- [ ] Error responses don't leak internal details
- [ ] Constant-time comparison for token validation
- [ ] Rate limiting on authentication endpoints

## Anti-Patterns

- "Security through obscurity" — hiding endpoints instead of protecting them
- Trusting client-side validation as the only validation
- Using MD5 or SHA1 for password hashing (use bcrypt/argon2)
- Storing passwords in plaintext or reversible encryption
- Disabling security features for convenience (`--no-verify`, `secure: false`)
- Catching and swallowing authentication errors
- Using eval() or Function() with any external input
- Trusting HTTP headers (X-Forwarded-For, Host) for security decisions
- "We'll add security later" — later never comes
