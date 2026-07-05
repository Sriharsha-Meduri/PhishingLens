---
title: PhishingLens API
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# PhishingLens API

Consolidated phishing-detection API (text + URL) powering the PhishingLens web app
and browser extension. Built with FastAPI + a fine-tuned DistilBERT classifier and a
lexical URL scanner, behind one explainable contract.

## Endpoints

| Method | Path            | Body                          |
|--------|-----------------|-------------------------------|
| GET    | `/health`       | -                             |
| POST   | `/analyze`      | `{ "content": "...", "mode": "auto" }` |
| POST   | `/analyze_text` | `{ "text": "..." }`           |
| POST   | `/analyze_url`  | `{ "url": "https://..." }`    |

### Example

```bash
curl -s https://<space>.hf.space/analyze \
  -H 'content-type: application/json' \
  -d '{"content":"http://paypal.account-verify.xyz/login"}'
```

Response:

```json
{
  "type": "url",
  "verdict": "phishing",
  "is_phishing": true,
  "risk_score": 92.4,
  "confidence": 0.924,
  "signals": [{ "name": "Impersonates a known brand ('paypal') outside its real domain", "severity": "high" }]
}
```

`verdict` is `phishing` / `suspicious` / `safe`.
