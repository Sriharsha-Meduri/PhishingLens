# PhishingLens - Improvement Backlog

A full, prioritized list of issues found in a line-by-line review of the codebase,
with the honest state of each "advanced" feature. Items marked **[fixed]** were
addressed in this pass; the rest are a concrete backlog.

## The core honest picture

The only end-to-end functional detection is:
- **Text/email/SMS**: a real fine-tuned DistilBERT classifier (`cybersectony/...v2.4.1`).
- **URL**: an interpretable lexical forensics engine (`serve/app.py:_url_lexical`).

The consolidated `serve/app.py` + `frontend/` + root `docker-compose.yml` + `extension/`
form one coherent, deployable product. Almost everything labelled "microservice /
4-source fusion / GNN / brand detection / continuous learning / monitoring / k8s"
is a second, half-wired system whose advanced claims are not backed by working code
(see below). The paper and the canonical product describe the consolidated system.

### Marketing vs. reality
| Claim (PROJECT_OVERVIEW) | Reality in code |
|---|---|
| "99.6% accuracy" | Measured CEAS08 macro-F1 is ~0.90, accuracy ~0.90. Unsubstantiated. |
| "4-source weighted 2-of-4 fusion" | Fixed boolean `scanner OR (hf AND otx)`; parsed `K`/`weights` never used; graph+OTX off by default -> scanner-only. |
| "GNN graph analysis" | `networkx` + 3 hardcoded bad domains + DNS/SSL rules. `models/graph/gnn_model.onnx` is never loaded by any code. |
| "YOLOv5/v8 top-50 brand detection" | Loads generic COCO `yolov5s`; maps a few object classes to the constant string `"tech_brand"`. No brand/logo recognition. |
| "Continuous learning + drift detection" | Script cannot import (missing `fetch_demo_data`), wrong project root, label-poisoning bug; no drift detection exists. |
| "OCR ensemble (Tesseract+EasyOCR+PaddleOCR)" | One engine selected by env var, not an ensemble. |
| "Rate limiting (100/min, X-RateLimit headers)" | No code enforces any rate limiting. |
| Text DistilBERT | Real and functional. |

## P0 - Security and crashes
1. **[fixed]** Leaked AlienVault **OTX API key** hardcoded in tracked `deployment/newdeployment/docker-compose.yml`. Replaced with `${OTX_KEY:-}`. **ACTION REQUIRED: rotate the key** (it was public) and scrub it from git history.
2. **`extension-production`**: `<all_urls>` + auto-scan on every navigation exfiltrates the full browsing history to an ephemeral `serveo.net` tunnel. Broken text scan (`urlResponse` out-of-scope ReferenceError + undefined `showUrlScanResults`). Popup and background talk to different backends (localhost vs serveo). `innerHTML` injection of analyzed content. Phantom `warning.html`, no icons, unused `scripting` permission.
3. **SSRF** in `image_service/main.py:load_image` (`requests.get(image_url)` with no scheme/host validation -> can fetch `169.254.169.254`, `localhost`, internal services). Same class of issue in the graph service's outbound DNS/SSL to arbitrary domains.
4. **`image_service/main.py`**: `logger` is never defined -> every v2 error path raises `NameError` and masks the real error. **[fixed]**
5. **`fetch_models.py`**: uses `Dict`/`List` annotations but only imports `Optional` -> `NameError` on load. **[fixed]**
6. **`continuous_learning.py`**: imports a non-existent module (`data.scripts.fetch_demo_data`), wrong `PROJECT_ROOT` (`parents[1]`), and a **label-poisoning bug** (stamps `label=1` on legitimate samples). Non-functional as shipped.
7. **`export_onnx.py` (image)** writes a text file containing `'onnx-placeholder'` instead of a real ONNX export.

## P1 - Correctness and consistency
8. **`serve/app.py` deployed thresholding differs from the evaluated one**: serve trusts the raw model prob at >=0.85 on messages of >=18 words, which is a deliberate precision-oriented gate for interactive short text; the reported email operating point instead uses temperature scaling (T~=3.0) + calibrated threshold ~0.125 for F1 on a corpus. These are two legitimate operating points for two contexts. Improvement: expose an env-selectable calibrated mode so the deployed and evaluated paths can be reconciled. (Design difference, not a bug.)
9. **`scripts/eval_fusion_v2.py` has two full `main()` implementations** concatenated in one file, so `main()` runs twice (a fixed-K summary, then a per-source threshold sweep). They happen to produce the two different URL reports, but the structure is confusing and should be split into two named functions.
10. **Two disjoint backend contracts**: `serve` (`/analyze`, `verdict/risk_score/signals`) vs gateway (`/analyze_url_v2`, `final_verdict/sources`). Frontend + dev extension target the former; docs + prod extension + k8s + monitoring target the latter. Pick one canonical backend and delete/relabel the other.
11. **API base-URL fragmentation** (localhost / hf.space / serveo.net / EC2 `13.127.222.13`). Settle on one and inject via env.
12. **`image_service`**: duplicate `@app.get("/health")` (telemetry-rich `health_v2` is unreachable); `/debug_image_v2` 500s (reads module globals as attributes); wrong ONNX path default (`tiny_cnn.onnx` vs real `mobilenet.onnx`).
13. **`url_service /analyze_url/human`** treats a dict as an object (`res.confidence`) -> AttributeError.
14. **gateway** metric bug: `/analyze_url` reads `is_phishing` from a v2 (`final_verdict`) response -> metric always counts "legitimate".
15. **`whitelist.py`** security: blanket `.gov.in` trust; parent-domain auto-whitelisting (`*.herokuapp.com` bypass); unescaped wildcard regex. **[fixed: removed .gov.in blanket + parent-domain auto-add + re.escape]**
16. **`config.py` / `fusion.py` env mismatch**: config documents `OTX_API_KEY`; fusion reads `OTX_KEY`. Fusion's 1.2s adapter cap is below OTX's own 5s timeout, so OTX never completes.
17. **`schemas.py`**: no max text length / base64 size cap -> DoS with large payloads.

## P1 - Deployment / CI / monitoring
18. **k8s**: `ingress.yaml`/`configmap.yaml`/`ci-cd.yml` reference `url-service`/`image-service`/`graph-service`/`frontend` deployments that do not exist. `continuous-learning` liveness probe hits a non-existent HTTP server -> CrashLoopBackOff. Placeholder image names.
19. **`newdeployment` compose**: placeholder images `yourdockerhubusername/...`; `graph` service commented out but referenced in fusion weights and `/graph_check`.
20. **Monitoring stack is orphaned** (nothing runs Prometheus/Grafana/Loki). Duplicate configs; Grafana dashboards query wrong metric names (`status` vs `status_code`, `phishing_detection_*` vs real names); two of three dashboards use an import envelope the file-provisioner rejects.
21. **CI `ci.yml`** is two workflows concatenated (invalid); references a non-existent compose path; runs `pytest` with no tests; `black`/`isort --check` on unformatted code.

## P2 - Frontend / quality
22. Frontend ships the **Vite dev server** as production; uses the **Tailwind play CDN** (not for production); dead `src/styles.css` (targets `#root`, unused design system); unused `axios`; name `phishguard-frontend` (branding drift).
23. Docs (`docs/*.md`, `PROJECT_OVERVIEW.md`) describe many files/endpoints/features that do not exist; leak `admin/admin123`; use stale `SIHPhishing` name. **[partly fixed: PROJECT_OVERVIEW honesty pass]**
24. Replace `print()` with logging; fix deprecated `datetime.utcnow()`; remove dead branches; bound the graph service's unbounded global graph memory; move blocking socket/ssl/whois off the async event loop.

## P2 - Make "genuine functionality" genuine (or drop the claim)
25. Brand detection: use a real logo/brand model or remove the claim (currently detects laptops and fruit).
26. Graph: wire the shipped `gnn_model.onnx` through `onnxruntime`, or rename the feature to "heuristic domain/DNS/SSL risk".
27. Visual checks: pass OCR text in (warning-phrase check is currently dead), seed the random color sampling, fix HSV ranges, or demote to labelled weak heuristics.
28. Drift detection: implement PSI/KS on score distributions and emit the already-defined Prometheus CL metrics, or drop the claim.

## P3 - Tests
29. No tests exist. Add unit tests for the lexical URL signals, the text trust-gate, whitelist matching, and SSRF guards.
