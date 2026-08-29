#!/usr/bin/env bash
# CineYield full production deployment to Cloud Run.
#
# Prerequisites:
#   gcloud auth login              (run once, interactively)
#   gcloud auth application-default login   (for ADC in subsequent commands)
#
# Usage:  bash scripts/deploy.sh
#
# The script is idempotent — re-running it updates existing services.
set -euo pipefail

PROJECT="project-01cc020f-432a-4192-bc0"
REGION="us-central1"
BACKEND_SERVICE="cineyield-api"
FRONTEND_SERVICE="cineyield-web"
SA_NAME="cineyield-runtime"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
GCS_BUCKET="cineyield-videos-dev"
SECRET_NAME="cineyield-clickhouse-password"
CLICKHOUSE_HOST="ebx4kt121f.ca-central-1.aws.clickhouse.cloud"
GEMINI_MODEL="gemini-2.5-flash"
NANO_BANANA_MODEL="gemini-3.1-flash-image"
VEO_MODEL="veo-3.1-generate-001"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "══════════════════════════════════════════"
echo " CineYield Cloud Run Deployment"
echo " Project: $PROJECT  Region: $REGION"
echo "══════════════════════════════════════════"
echo ""

# ── Phase 2: Enable required APIs ─────────────────────────────────────────
echo "▸ Phase 2: Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT" --quiet
echo "  ✓ APIs enabled"

# ── Phase 3: Service Account + IAM ────────────────────────────────────────
echo "▸ Phase 3: Service account + IAM..."

gcloud iam service-accounts create "$SA_NAME" \
  --display-name="CineYield Runtime" \
  --project="$PROJECT" 2>/dev/null \
  && echo "  ✓ Service account created" \
  || echo "  ✓ Service account already exists"

# Vertex AI inference
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user" \
  --condition=None --quiet 2>/dev/null || true

# GCS bucket access (reads + writes for video upload)
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectUser" --quiet 2>/dev/null || true

# Secret Manager read
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None --quiet 2>/dev/null || true

# Cloud Run metrics / logs
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --condition=None --quiet 2>/dev/null || true

echo "  ✓ IAM bindings applied"

# ── Phase 4: ClickHouse password → Secret Manager ─────────────────────────
echo "▸ Phase 4: ClickHouse password → Secret Manager..."

ENV_FILE="${REPO_ROOT}/apps/agent-api/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Cannot read ClickHouse password."
  exit 1
fi

# Extract without printing
CH_PASS_LINE=$(grep '^CLICKHOUSE_PASSWORD=' "$ENV_FILE" 2>/dev/null || true)
if [ -z "$CH_PASS_LINE" ]; then
  echo "ERROR: CLICKHOUSE_PASSWORD not set in apps/agent-api/.env"
  exit 1
fi
CH_PASS="${CH_PASS_LINE#CLICKHOUSE_PASSWORD=}"

# Create or update secret (value piped directly, never echoed)
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT" >/dev/null 2>&1; then
  printf '%s' "$CH_PASS" | gcloud secrets versions add "$SECRET_NAME" \
    --data-file=- --project="$PROJECT" --quiet
  echo "  ✓ Secret version updated"
else
  printf '%s' "$CH_PASS" | gcloud secrets create "$SECRET_NAME" \
    --data-file=- --project="$PROJECT" --quiet
  echo "  ✓ Secret created"
fi

# ── Phase 6: Deploy Backend ────────────────────────────────────────────────
#
# NOTE ON --set-env-vars SYNTAX
# gcloud splits key=value pairs on commas by default, and CORS_ORIGINS is itself
# a comma-separated list, so the plain form fails with
#   "Bad syntax for dict arg: [http://localhost:8000]".
# The leading ^@^ selects @ as the delimiter instead, which lets a value keep
# its own commas. Do not "tidy" this back to commas.
echo "▸ Phase 6: Deploying backend (cineyield-api)..."
echo "  (Cloud Build will compile the container — this takes 3-5 minutes)"

gcloud run deploy "$BACKEND_SERVICE" \
  --source="${REPO_ROOT}/apps/agent-api" \
  --project="$PROJECT" \
  --region="$REGION" \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --timeout=300 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=5 \
  --concurrency=10 \
  --set-env-vars="^@^ENVIRONMENT=production\
@CINEYIELD_MODE=contest\
@GOOGLE_CLOUD_PROJECT=${PROJECT}\
@GOOGLE_CLOUD_REGION=${REGION}\
@GOOGLE_GENAI_USE_VERTEXAI=1\
@GCS_BUCKET_NAME=${GCS_BUCKET}\
@CLICKHOUSE_HOST=${CLICKHOUSE_HOST}\
@CLICKHOUSE_PORT=8443\
@CLICKHOUSE_USER=default\
@CLICKHOUSE_DATABASE=cineyield\
@CLICKHOUSE_SECURE=true\
@CLICKHOUSE_VERIFY=true\
@CLICKHOUSE_CONNECT_TIMEOUT=30\
@CLICKHOUSE_SEND_RECEIVE_TIMEOUT=60\
@CLICKHOUSE_MCP_AUTH_DISABLED=true\
@GEMINI_MODEL=${GEMINI_MODEL}\
@NANO_BANANA_MODEL=${NANO_BANANA_MODEL}\
@NANO_BANANA_REGION=global\
@VEO_MODEL=${VEO_MODEL}\
@VEO_REGION=${REGION}\
@CORS_ORIGINS=http://localhost:3000,http://localhost:8000" \
  --set-secrets="CLICKHOUSE_PASSWORD=${SECRET_NAME}:latest" \
  --quiet

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" \
  --format="value(status.url)")
echo "  ✓ Backend deployed: $BACKEND_URL"

# ── Phase 7: Quick backend smoke test ─────────────────────────────────────
echo "▸ Phase 7: Backend smoke test..."
sleep 5
HEALTH=$(curl -sf "${BACKEND_URL}/health" 2>/dev/null || echo '{}')
echo "  /health → $HEALTH"
READY=$(curl -sf "${BACKEND_URL}/ready" 2>/dev/null || echo '{}')
echo "  /ready  → $READY"

# ── Phase 9: Deploy Frontend ───────────────────────────────────────────────
echo "▸ Phase 9: Deploying frontend (cineyield-web)..."
echo "  Backend URL baked in: $BACKEND_URL"
echo "  (Cloud Build will compile the Next.js container — this takes 3-5 minutes)"

# The frontend CANNOT be built with `gcloud run deploy --source`.
# Next.js inlines every NEXT_PUBLIC_* value at BUILD time -- in server
# components as well as client ones -- and `--source` does not pass
# --set-build-env-vars through to the Dockerfile's ARG. The image therefore
# baked the placeholder URL, every fetch failed, and every page silently
# rendered fixtures that looked exactly like live data. So build explicitly
# with --build-arg, then deploy the resulting image.
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy/${FRONTEND_SERVICE}:$(date +%Y%m%d-%H%M%S)"

gcloud builds submit "${REPO_ROOT}/apps/web" \
  --project="$PROJECT" \
  --config="${REPO_ROOT}/apps/web/cloudbuild.yaml" \
  --substitutions="_API_URL=${BACKEND_URL},_IMAGE=${FRONTEND_IMAGE}" \
  --quiet

gcloud run deploy "$FRONTEND_SERVICE" \
  --image="$FRONTEND_IMAGE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --allow-unauthenticated \
  --timeout=60 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --set-env-vars="^@^NEXT_PUBLIC_API_URL=${BACKEND_URL}@NODE_ENV=production" \
  --quiet

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" \
  --format="value(status.url)")
echo "  ✓ Frontend deployed: $FRONTEND_URL"

# ── Phase 10: Update backend CORS with real frontend URL ──────────────────
echo "▸ Phase 10: Updating backend CORS with production frontend URL..."
gcloud run services update "$BACKEND_SERVICE" \
  --project="$PROJECT" --region="$REGION" \
  --update-env-vars="^@^CORS_ORIGINS=http://localhost:3000,http://localhost:8000,${FRONTEND_URL}" \
  --quiet
echo "  ✓ CORS updated"

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo " Deployment complete!"
echo ""
echo " Frontend : $FRONTEND_URL"
echo " Backend  : $BACKEND_URL"
echo " Docs     : ${BACKEND_URL}/docs"
echo "══════════════════════════════════════════"
echo ""
echo "Next: run  bash scripts/e2e-prod-smoke.sh  to verify all integrations."
echo ""
