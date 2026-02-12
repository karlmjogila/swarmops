# ===== Dependencies Stage =====
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    cp -R node_modules /prod_node_modules && \
    npm ci

# ===== Builder Stage =====
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
RUN npm run build

# ===== Production Stage =====
FROM node:20-alpine AS production

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup && \
    chown -R appuser:appgroup /app

# Copy production dependencies and built app
COPY --from=deps --chown=appuser:appgroup /prod_node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/build ./build
COPY --from=builder --chown=appuser:appgroup /app/package*.json ./

# Switch to non-root user
USER appuser

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Run production server
ENV NODE_ENV=production
CMD ["node", "build"]

# ===== Development Stage =====
FROM node:20-alpine AS development

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

# Development with hot reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
