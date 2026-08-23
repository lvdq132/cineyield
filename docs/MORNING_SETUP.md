# CineYield — Morning Setup

Everything has been built. You need 5–15 minutes to authenticate two cloud services.

---

## Step 1: ClickHouse Cloud credentials

### Find your credentials

1. Open **[clickhouse.cloud](https://clickhouse.cloud)** and sign in
2. Select your service (or create one — free trial available)
3. Click **Connect** in the left navigation menu
4. A connection dialog appears — select **Native** from the "Connect with" dropdown
5. The dialog shows your hostname, username, and password

Your hostname looks like:  
`abc123xyz.us-east-1.aws.clickhouse.cloud`

### Set them in `.env`

```
cd apps/agent-api
```

Edit `.env` and fill in:

```
CLICKHOUSE_HOST=<your-hostname-from-step-5>
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=<your-password-from-step-5>
CLICKHOUSE_SECURE=true
CLICKHOUSE_VERIFY=true
```

> The `CLICKHOUSE_USER` is `default` unless you created another user.  
> Leave `CLICKHOUSE_PORT=8443` — this is the HTTPS interface used by both  
> `clickhouse-connect` and `mcp-clickhouse`.

### Initialize and verify

```bash
cd apps/agent-api
make db-init     # creates cineyield database + 10 tables
make db-seed     # loads 27 brand campaigns + demo scenes/opportunities
make clickhouse-verify   # end-to-end: connectivity → MCP → scoring → Aurelius #1
```

`make clickhouse-verify` runs 20+ checks and prints ✓ PASS / ✗ FAIL for each.  
A clean run ends with `20/20 checks passed`.

### Optional: dedicated MCP user (recommended for demo)

For the judge demo, use a least-privilege runtime user instead of `default`:

1. Open the ClickHouse Cloud SQL console
2. Paste the contents of `infra/clickhouse/02_mcp_user.sql`, **replacing `{MCP_PASSWORD}`** with a generated secret:
   ```
   openssl rand -hex 32
   ```
3. Run the SQL
4. Update `.env`:
   ```
   CLICKHOUSE_USER=cineyield_mcp
   CLICKHOUSE_PASSWORD=<generated-secret>
   ```
5. Re-run `make clickhouse-verify` to confirm the MCP user can query

---

## Step 2: Google Cloud / Gemini credentials

You need a Google API key for Gemini multimodal scene analysis.

### Quickest path — API key

1. Open **[aistudio.google.com](https://aistudio.google.com)**
2. Click **Get API key** → **Create API key**
3. Copy the key

Edit `.env`:

```
GOOGLE_API_KEY=<your-key>
GEMINI_MODEL=gemini-2.0-flash
```

> `gemini-2.0-flash` is the recommended model. It handles video at ~300 tokens/second  
> and supports up to 1 hour of video at 1M context window.

### Alternative — Google Cloud (ADC)

If you prefer Application Default Credentials:

```bash
gcloud auth application-default login
```

Then set in `.env`:

```
GOOGLE_CLOUD_PROJECT=<your-project-id>
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.0-flash
```

### Verify Gemini

```bash
cd apps/agent-api
make dev   # starts the API on :8000
```

Then check:

```
GET http://localhost:8000/ready
```

Look for `"gemini": {"status": "ok"}` in the response.

---

## Step 3: Run the full system

```bash
# Terminal 1 — backend
cd apps/agent-api
make dev

# Terminal 2 — frontend
cd apps/web
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)**

### Canonical demo flow

1. The frontend displays the fixture demo (scenes, matches, proposals)
2. Upload a video via `POST /api/v1/ingest/upload` — SceneAgent runs Gemini
3. MarketAgent queries ClickHouse via mcp-clickhouse, scores 27 campaigns
4. Aurelius Systems "Focus Without Limits" scores highest for the rooftop scene
5. Vortex Energy is blocked (creative conflict: `dusk` excluded context)
6. Stride Apparel is blocked (category mismatch: Apparel vs Consumer audio)

### Contest smoke test

```bash
cd apps/agent-api
make test-contest   # FAILS if mcp-clickhouse can't reach ClickHouse
```

A passing contest test proves: real mcp-clickhouse subprocess → real SQL query → real campaign rows.

---

## Quick reference

| Command | What it does |
|---|---|
| `make db-init` | Create schema (10 tables) |
| `make db-seed` | Load 27 brand campaigns + demo data |
| `make db-health` | Direct connectivity check |
| `make mcp-health` | mcp-clickhouse MCP query check |
| `make clickhouse-verify` | Full end-to-end verification (20+ checks) |
| `make test-unit` | 70+ unit tests, no credentials needed |
| `make test-contest` | Contest smoke test — fails if MCP unreachable |
| `make dev` | Start FastAPI on :8000 |

---

## Troubleshooting

**`Connection refused` or `TLS handshake failed`**  
→ Check `CLICKHOUSE_HOST` has no `https://` prefix — it should be just the hostname.  
→ Confirm `CLICKHOUSE_PORT=8443` (not 9440, which is native TCP).

**`Authentication failed`**  
→ The password in the Connect dialog is your ClickHouse Cloud service password, not your Google/email password.

**`mcp-clickhouse binary not found`**  
→ Run `pip install mcp-clickhouse` inside the venv (`source .venv/bin/activate`).

**`gemini: not_configured` in /ready**  
→ Set `GOOGLE_API_KEY=...` or both `GOOGLE_CLOUD_PROJECT` + `GEMINI_MODEL`.

**Gemini quota errors**  
→ `gemini-2.0-flash` has a free tier with rate limits. For the contest demo, use short clips (<30s) to stay within limits.
