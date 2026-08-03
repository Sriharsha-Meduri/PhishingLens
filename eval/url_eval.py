# -*- coding: utf-8 -*-
"""
Honest URL evaluation for PhishingLens.

Scores a balanced labelled URL benchmark (pirocheto/phishing-url, ~11k URLs) with
(a) the deployed interpretable lexical engine (serve/app.py:_url_lexical) and
(b) the DistilBERT text model applied to the bare URL. The second measurement is
the empirical justification for the system's routing choice: the transformer, an
email/text classifier, is close to useless on bare URLs, so URL verdicts use the
lexical engine. Reports ROC-AUC, operating-point metrics, a leave-one-signal-group
ablation of the lexical engine, and latency. All numbers measured.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "paper"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "serve"))
import app as serveapp  # the deployed engine  # noqa: E402

MODEL_ID = "cybersectony/phishing-email-detection-distilbert_v2.4.1"
RNG = np.random.RandomState(42)

# signal-name keywords -> ablation group (matches serve/app.py:_url_lexical labels)
GROUPS = {
    "ip_at": ["raw IP", "'@'"],
    "tld": ["top-level domain"],
    "brand": ["Impersonates", "Look-alike"],
    "keywords": ["keyword"],
    "structure": ["long URL", "subdomains", "hyphenated", "entropy", "encoding"],
    "https": ["No HTTPS"],
}


def _logistic(score):
    return 1.0 / (1.0 + math.exp(-4.0 * (score - 0.45)))


def _metrics(y, pred):
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn = int(((y == 0) & (pred == 0)).sum()); fp = int(((y == 0) & (pred == 1)).sum())
    return {"precision": float(pr), "recall": float(rc), "f1": float(f1),
            "accuracy": float(accuracy_score(y, pred)),
            "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0}


def _best_f1(y, risk):
    best = (0.5, -1.0, None)
    for t in np.linspace(0.05, 0.95, 91):
        m = _metrics(y, (risk >= t).astype(int))
        if m["f1"] > best[1]:
            best = (float(t), m["f1"], m)
    return best


def _at_fpr(y, risk, max_fpr=0.05):
    chosen = None
    for t in np.linspace(0.99, 0.01, 99):
        m = _metrics(y, (risk >= t).astype(int))
        if m["fpr"] <= max_fpr:
            chosen = (float(t), m)
        else:
            break
    return chosen


def main():
    print("[url] loading pirocheto/phishing-url ...", flush=True)
    rows = []
    for split in ("train", "test"):
        ds = load_dataset("pirocheto/phishing-url", split=split)
        for u, s in zip(ds["url"], ds["status"]):
            rows.append((str(u), 1 if str(s).lower() == "phishing" else 0))
    urls = [u for u, _ in rows]
    y = np.array([l for _, l in rows], dtype=int)
    n = len(urls)
    print(f"[url] {n} URLs, phishing={int(y.sum())} legit={int((1-y).sum())}", flush=True)

    # (a) deployed lexical engine
    lex_risk = np.zeros(n, dtype=np.float32)
    grp_weight = {g: np.zeros(n, dtype=np.float32) for g in GROUPS}
    raw_score = np.zeros(n, dtype=np.float32)
    t0 = time.time()
    for i, u in enumerate(urls):
        risk, signals, _ = serveapp._url_lexical(u)
        lex_risk[i] = risk
        sc = sum(s.get("weight", 0.0) for s in signals)
        raw_score[i] = sc
        for s in signals:
            for g, kws in GROUPS.items():
                if any(k in s["name"] for k in kws):
                    grp_weight[g][i] += s.get("weight", 0.0)
        if (i + 1) % 2000 == 0:
            print(f"  lexical {i+1}/{n}", flush=True)
    lex_latency_ms = 1000 * (time.time() - t0) / n

    # (b) transformer on the bare URL (expected to fail -> routing justification)
    print("[url] scoring bare URLs with DistilBERT ...", flush=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(dev).eval()
    tf_prob = np.zeros(n, dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, 128):
            enc = tok(urls[i:i + 128], max_length=128, padding=True, truncation=True, return_tensors="pt")
            enc = {k: v.to(dev) for k, v in enc.items()}
            p = torch.softmax(mdl(**enc).logits, dim=-1).cpu().numpy()
            tf_prob[i:i + len(p)] = (p[:, 1] + p[:, 3]) if p.shape[1] >= 4 else p[:, -1]

    lex_bf1 = _best_f1(y, lex_risk)
    tf_bf1 = _best_f1(y, tf_prob)
    lex_fpr = _at_fpr(y, lex_risk, 0.05)

    # ablation: remove each signal group, recompute logistic risk, AUC drop
    ablation = {}
    base_auc = float(roc_auc_score(y, lex_risk))
    for g in GROUPS:
        r = np.array([_logistic(raw_score[i] - grp_weight[g][i]) for i in range(n)], dtype=np.float32)
        ablation[g] = round(base_auc - float(roc_auc_score(y, r)), 4)

    res = {
        "task": "url", "dataset": "pirocheto/phishing-url (train+test)",
        "n": n, "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
        "lexical": {
            "auc": base_auc,
            "operating_point_best_f1": {"threshold": lex_bf1[0], **lex_bf1[2]},
            "operating_point_fpr5": ({"threshold": lex_fpr[0], **lex_fpr[1]} if lex_fpr else None),
            "latency_ms_per_url": lex_latency_ms,
        },
        "transformer_on_urls": {
            "auc": float(roc_auc_score(y, tf_prob)),
            "operating_point_best_f1": {"threshold": tf_bf1[0], **tf_bf1[2]},
        },
        "lexical_ablation_auc_drop": ablation,
    }
    json.dump(res, open(OUT / "url_eval.json", "w"), indent=2)
    np.save(OUT / "url_scores.npy", np.column_stack([lex_risk, tf_prob, y]))
    print("[url]", json.dumps(res, indent=2), flush=True)


if __name__ == "__main__":
    main()
    print("URL EVAL DONE", flush=True)
