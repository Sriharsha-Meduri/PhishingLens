# 🛡️ PhishingLens

> **Live:** [web app](https://sriharshameduri-phishinglens.static.hf.space) - [API](https://sriharshameduri-phishinglens-api.hf.space/health)

Multi-modal phishing detection for the surfaces people actually get hit on: **email, SMS, and URLs**. PhishingLens pairs a fine-tuned DistilBERT text classifier with a lexical URL forensics engine behind one explainable API, and ships as a web app **and** a Chrome extension.

Every verdict comes with a calibrated **risk score (0-100)**, a **phishing / suspicious / safe** label, and the exact **signals** that fired, never an opaque yes/no.

---

## What it detects

| Lens | How |
|------|-----|
| **Text & email** | Fine-tuned DistilBERT (`cybersectony/phishing-email-detection-distilbert_v2.4.1`) reads the language of the message: urgency, credential lures, impersonation. |
| **URL forensics** | Lexical analysis: look-alike/typo-squat domains, brand tokens outside their real domain, suspicious TLDs, raw-IP hosts, entropy, credential keywords, obfuscation. |
| **Links in context** | URLs found inside a message are extracted and scored, so a clean-looking email with a poisoned link is still caught. |

> The DistilBERT model is an email/text classifier and over-predicts phishing on bare URLs, so **URL verdicts use the interpretable lexical engine**. The transformer drives text/email analysis, where it is strong.

---

## Architecture

Two ways to run the same detection logic:

- **Consolidated API (`serve/`)** - a single FastAPI process (text + URL) that fits a free CPU host. This is the deploy target.
- **Full microservice stack (`backend/`, `deployment/`)** - the original SIH build: separate `gateway`, `text`, `url`, `image` (OCR + YOLO brand detection), and `graph` (GNN) services, with Prometheus/Grafana monitoring and Kubernetes manifests. Run locally with docker-compose.

```
frontend/            React + Vite web app
extension/           Chrome MV3 extension (popup + context-menu scan)
serve/               Consolidated FastAPI API (deploy target)
backend/             Full microservice stack (gateway/text/url/image/graph)
deployment/          docker-compose, k8s, monitoring
models/              DistilBERT, GNN, YOLO/MobileNet (Git LFS)
docs/                API, architecture, deployment, user manual
```

---

## Quick start

### Option A - Docker (full local stack)

```bash
docker compose up --build
# Web  -> http://localhost:5173
# API  -> http://localhost:8000   (Swagger docs at /docs)
```

### Option B - Manual

```bash
# 1) API
cd serve
python -m venv .venv && . .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install "torch>=2.6" --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# 2) Web (new terminal)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The first API start downloads the DistilBERT weights (~270 MB) and caches them.

---

## API

```
GET  /health
POST /analyze         { "content": "<text or url>", "mode": "auto" }
POST /analyze_text    { "text": "..." }
POST /analyze_url     { "url": "https://..." }
```

```bash
curl -s localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"content":"http://paypal.com.account-verify.xyz/login"}'
```

```json
{
  "type": "url",
  "verdict": "phishing",
  "is_phishing": true,
  "risk_score": 91.7,
  "confidence": 0.917,
  "signals": [
    { "name": "Impersonates a known brand ('paypal') outside its real domain", "severity": "high" },
    { "name": "Suspicious top-level domain (.xyz)", "severity": "high" }
  ]
}
```

---

## Deploy (free tier)

**Backend → Hugging Face Spaces (Docker).** Create a Space (SDK = Docker, CPU basic), push the contents of `serve/`. The model is baked into the image, so it boots ready. Serves at `https://<user>-<space>.hf.space`; check `/health`.

**Frontend → Vercel.** Import the repo, root directory `frontend/`, framework auto-detects Vite. Set env var `VITE_API_URL` to your Space URL. Deploy. CORS already allows any origin.

**Extension.** Edit `extension/config.js` and set `API_URL` to your Space URL, then load `extension/` as an unpacked extension (chrome://extensions → Developer mode → Load unpacked).

---

## Chrome extension

- **Popup** - scan the current tab, or paste any email/SMS/URL.
- **Right-click** any link or selected text → *Scan with PhishingLens* → verdict notification.
- Talks to the same `/analyze` API as the web app.

---

## Models

Tracked with Git LFS under `models/`:
- `text/` - DistilBERT phishing classifier (safetensors + tokenizer)
- `image/`, `yolo/` - MobileNet + YOLOv5 for the full-stack image service (brand/logo detection)
- `graph/` - GNN for the domain-graph service

---

## Limitations

- URL detection is lexical/heuristic. It catches look-alike and structurally suspicious URLs well, but a phishing page on a clean, reputable-looking domain can evade purely-lexical checks. Threat-intel enrichment (OTX) is available in the full stack to help.
- The text model is tuned for email/SMS phishing; very short or out-of-distribution snippets are less certain.
- Risk scores are indicators, not proof. Treat a high score as "verify before trusting."

---

## License

Technical demonstration / educational project.
