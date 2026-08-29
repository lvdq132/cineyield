# CineYield — Google Cloud backend proof

Submit these three screenshots in numerical order.

1. `01-cloud-run-deployment-and-traffic.png`
   - Caption: **CineYield production backend deployed on Google Cloud Run.**
   - Shows the healthy `cineyield-api` service, `us-central1`, public Cloud Run URL,
     request traffic, latency, and active instances.

2. `02-vertex-ai-gemini-200-ok.png`
   - Caption: **Real Vertex AI Gemini request from the CineYield backend — HTTP 200.**
   - Shows a timestamped `POST` from Cloud Run to `aiplatform.googleapis.com`, the
     `gemini-2.5-flash:generateContent` endpoint, and `HTTP/1.1 200 OK`.

3. `03-production-readiness.png`
   - Caption: **Live production health checks for API, Gemini, Cloud Storage, and ClickHouse.**
   - Shows the public `/ready` response with API and ClickHouse healthy and Gemini/GCS
     configured.
