# ── Stage 1: Build ──────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency files first (layer caching)
COPY package.json package-lock.json ./

# Install dependencies
# - --ignore-scripts: prevent esbuild ETXTBSY race during postinstall
# - --force: skip Windows-only platform checks from lockfile
# Then run postinstall scripts separately after binaries are fully written
RUN npm ci --force --ignore-scripts && npm rebuild esbuild

# Copy source + configs
COPY index.html vite.config.js eslint.config.js ./
COPY src/ src/
COPY public/ public/

# Build the SPA
RUN npm run build

# ── Stage 2: Serve with nginx ──────────────────────────────────
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built SPA from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
