# -*- coding: utf-8 -*-
"""
Honest text/email + SMS evaluation of the PhishingLens DistilBERT detector.

For a labelled corpus we score every message once through the deployed transformer,
fit temperature scaling on a held-out split, sweep the decision threshold under a
recall floor, and report ROC-AUC, precision/recall/F1/accuracy at the operating
point, expected calibration error (ECE) before and after calibration, and latency.
Running it on CEAS-08 (email, in-domain) and the SMS Spam Collection (short message,
out-of-domain) measures both accuracy and cross-domain transfer. All numbers measured.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "paper"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_ID = "cybersectony/phishing-email-detection-distilbert_v2.4.1"
RNG = np.random.RandomState(42)


def _softmax(x):
    x = x - x.max(axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


def _phish_from_logits(logits, T=1.0):
    p = _softmax(logits / T)
    if p.shape[1] >= 4:      # [legit_email, phish_url, legit_url, phish_url_alt]
        return (p[:, 1] + p[:, 3]).astype(np.float32)
    return (p[:, 1] if p.shape[1] > 1 else p[:, 0]).astype(np.float32)


def _fit_temperature(logits, labels):
    best_T, best_nll = 1.0, float("inf")
    for T in np.linspace(0.5, 3.0, 26):
        p = np.clip(_phish_from_logits(logits, T), 1e-6, 1 - 1e-6)
        nll = -np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p))
        if nll < best_nll:
            best_nll, best_T = nll, float(T)
    return best_T


def _ece(probs, labels, bins=10):
    probs = np.clip(probs, 0, 1)
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for i in range(bins):
        m = (probs >= edges[i]) & (probs < edges[i + 1] if i < bins - 1 else probs <= edges[i + 1])
        if m.sum():
            e += (m.sum() / len(probs)) * abs(labels[m].mean() - probs[m].mean())
    return float(e)


def _pt(labels, pred):
    pr, rc, f1, _ = precision_recall_fscore_support(labels, pred, average="binary", zero_division=0)
    tn = int(((labels == 0) & (pred == 0)).sum()); fp = int(((labels == 0) & (pred == 1)).sum())
    return {"precision": float(pr), "recall": float(rc), "f1": float(f1),
            "accuracy": float(accuracy_score(labels, pred)),
            "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0}


def _load_corpus(path, text_col, label_col):
    df = pd.read_csv(path)
    if text_col and label_col and text_col in df.columns:
        out = pd.DataFrame({"text": df[text_col].astype(str), "label": df[label_col].astype(int)})
    elif {"body", "label"}.issubset(df.columns):
        out = pd.DataFrame({"text": df["body"].astype(str), "label": df["label"].astype(int)})
    elif {"text", "label"}.issubset(df.columns):
        out = pd.DataFrame({"text": df["text"].astype(str), "label": df["label"].astype(int)})
    else:
        raise ValueError(f"unrecognised columns in {path}: {list(df.columns)}")
    return out.dropna().reset_index(drop=True)


def _score(tok, mdl, texts, device, bs=128):
    logits, lat = [], []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], max_length=256, padding=True, truncation=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            t0 = time.time()
            out = mdl(**enc).logits.cpu().numpy()
            lat.append((time.time() - t0) / len(out))
            logits.extend(out)
            if (i // bs) % 50 == 0:
                print(f"  scored {i}/{len(texts)}", flush=True)
    return np.stack(logits), float(np.mean(lat) * 1000)


def evaluate(name, path, text_col, label_col, device):
    print(f"[{name}] loading {path}", flush=True)
    df = _load_corpus(path, text_col, label_col)
    y = df["label"].to_numpy().astype(int)
    print(f"[{name}] {len(df)} msgs, phishing/spam={int(y.sum())} safe={int((1-y).sum())}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device).eval()

    logits, lat_ms = _score(tok, mdl, df["text"].tolist(), device)
    # calibration + threshold on a stratified half, reported on the other half
    idx = RNG.permutation(len(y)); h = len(y) // 2
    va, te = idx[:h], idx[h:]
    T = _fit_temperature(logits[va], y[va])
    p_raw = _phish_from_logits(logits, 1.0)
    p_cal = _phish_from_logits(logits, T)

    # threshold: best binary-F1 on val subject to recall >= 0.6
    best = None
    for t in np.arange(0.02, 0.95, 0.01):
        pred = (p_cal[va] >= t).astype(int)
        m = _pt(y[va], pred)
        if m["recall"] >= 0.6 and (best is None or m["f1"] > best[1]):
            best = (float(t), m["f1"])
    t_star = best[0] if best else 0.5

    pred_te = (p_cal[te] >= t_star).astype(int)
    res = {
        "task": name, "dataset": str(path), "n": int(len(y)),
        "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
        "auc": float(roc_auc_score(y, p_cal)) if len(np.unique(y)) > 1 else float("nan"),
        "temperature": T, "threshold": t_star,
        "operating_point": _pt(y[te], pred_te),
        "ece_raw": _ece(p_raw[te], y[te]), "ece_calibrated": _ece(p_cal[te], y[te]),
        "latency_ms_per_msg": lat_ms, "device": device,
    }
    json.dump(res, open(OUT / f"text_{name}.json", "w"), indent=2)
    np.save(OUT / f"text_{name}_scores.npy", np.column_stack([p_raw, p_cal, y]))
    print(f"[{name}]", json.dumps(res, indent=2), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--text_col", default=None)
    ap.add_argument("--label_col", default=None)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    evaluate(a.name, a.path, a.text_col, a.label_col, a.device)
    print("TEXT EVAL DONE", flush=True)
