FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_API_URL must be baked in at build time.
# Passed via --build-env-vars in gcloud run deploy --source.
ARG NEXT_PUBLIC_API_URL=https://cineyield-api-placeholder.run.app
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Production runner ──────────────────────────────────────────────────────
FROM node:20-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

# Copy Next.js standalone output (requires output: 'standalone' in next.config)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Cloud Run injects $PORT
ENV PORT=3000
EXPOSE 3000

CMD ["node", "server.js"]
