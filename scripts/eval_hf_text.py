#!/usr/bin/env python3
import os
import sys
import time
import json
import math
import argparse
from pathlib import Path
from typing import Tuple, List

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

import torch
try:
    import psutil  # optional
except Exception:
    psutil = None
from transformers import AutoTokenizer, AutoModelForSequenceClassification
try:
    from tqdm import tqdm  # optional progress
except Exception:
    tqdm = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from backend.common.config import settings


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x, axis=-1, keepdims=True)
    ex = np.exp(x)
    return ex / np.sum(ex, axis=-1, keepdims=True)


def load_holdout(path: Path, text_col: str = None, label_col: str = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Holdout file not found: {path}")
    df = pd.read_csv(path)
    cols = set(df.columns)
    
    # Support multiple schemas:
    # 1) text,label (0/1) - default
    # 2) Email Text, Email Type ("Safe Email"/"Phishing Email")
    # 3) body,label (0/1) - CEAS08 format
    # 4) Custom columns via text_col, label_col args
    
    if text_col and label_col:
        # Custom column mapping
        if text_col not in cols or label_col not in cols:
            raise ValueError(f"Custom columns not found: {text_col}, {label_col}")
        out = pd.DataFrame({
            "text": df[text_col].astype(str),
            "label": df[label_col].astype(int)
        })
        return out.dropna(subset=["text", "label"]).copy()
    
    if {"Email Text", "Email Type"}.issubset(cols):
        out = pd.DataFrame({
            "text": df["Email Text"].astype(str),
            "label": (df["Email Type"].astype(str) == "Phishing Email").astype(int)
        })
        return out.dropna(subset=["text", "label"]).copy()
    
    if {"body", "label"}.issubset(cols):
        # CEAS08 format
        out = pd.DataFrame({
            "text": df["body"].astype(str),
            "label": df["label"].astype(int)
        })
        return out.dropna(subset=["text", "label"]).copy()
    
    # Default: text,label
    required = {"text", "label"}
    if not required.issubset(cols):
        raise ValueError(f"Holdout must have columns {required}, {'{Email Text, Email Type}'}, {'{body, label}'}, or custom columns via --text_col/--label_col")
    return df.dropna(subset=["text", "label"]).copy()


def load_model(model_id: str) -> Tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    tok = AutoTokenizer.from_pretrained(model_id)
    mdl = AutoModelForSequenceClassification.from_pretrained(model_id)
    mdl.eval()
    return tok, mdl


def score_texts(tok, mdl, texts: list[str], device: str = "cpu") -> Tuple[np.ndarray, np.ndarray]:
    mdl.to(device)
    ph_probs = []
    ham_probs = []
    latencies = []
    with torch.no_grad():
        for t in texts:
            enc = tok(t, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            start = time.time()
            out = mdl(**enc)
            latencies.append(time.time() - start)
            logits = out.logits.cpu().numpy()
            probs = softmax(logits)
            if probs.shape[-1] >= 4:
                # [legitimate_email, phishing_url, legitimate_url, phishing_url_alt]
                ph = float(probs[0, 1] + probs[0, 3])
                ham = float(probs[0, 0] + probs[0, 2])
            else:
                ph = float(probs[0, 1] if probs.shape[-1] > 1 else probs[0, 0])
                ham = float(1.0 - ph)
            ph_probs.append(ph)
            ham_probs.append(ham)
    return np.array(ph_probs, dtype=np.float32), np.array(ham_probs, dtype=np.float32), np.array(latencies, dtype=np.float32)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    # Simple temperature scaling using grid search on T in [0.5, 3.0]
    best_T, best_nll = 1.0, float("inf")
    for T in np.linspace(0.5, 3.0, 26):
        probs = softmax(logits / T)
        # binary from 4-way: phishing = p1+p3
        p = (probs[:, 1] + (probs[:, 3] if probs.shape[1] >= 4 else 0.0))
        p = np.clip(p, 1e-6, 1 - 1e-6)
        nll = -np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p))
        if nll < best_nll:
            best_nll, best_T = nll, T
    return float(best_T)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", default=str(ROOT / "data/holdout/emails_eval.csv"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--use_fallback", action="store_true")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--calib_samples", type=int, default=20000, help="Max samples used to fit temperature")
    parser.add_argument("--text_col", type=str, help="Custom text column name (e.g., 'body')")
    parser.add_argument("--label_col", type=str, help="Custom label column name (e.g., 'label')")
    args = parser.parse_args()

    # Prechecks
    holdout_path = Path(args.holdout)
    if not holdout_path.exists():
        alt = ROOT / "Phishing_Email.csv"
        if alt.exists():
            holdout_path = alt
    df = load_holdout(holdout_path, text_col=args.text_col, label_col=args.label_col)

    # Ensure report dirs
    reports_dir = ROOT / "reports" / "text"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Model selection
    model_id = settings.SERVICE_FALLBACK_MODEL_ID if args.use_fallback else settings.SERVICE_MODEL_ID
    print(f"[INFO] Using model_id={model_id}")
    print(f"[INFO] Dataset={holdout_path}")

    # Load model
    tok, mdl = load_model(model_id)

    # Split holdout for calibration
    from sklearn.model_selection import train_test_split
    train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])

    # Score (store raw logits for calibration)
    def collect_logits(texts: List[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        mdl.to(args.device)
        latencies = []
        all_logits = []
        bs = max(1, int(args.batch_size))
        rng = range(0, len(texts), bs)
        iterator = rng if tqdm is None else tqdm(rng, desc="scoring", unit="batch")
        with torch.no_grad():
            for i in iterator:
                batch_texts = texts[i:i+bs]
                enc = tok(batch_texts, max_length=512, padding=True, truncation=True, return_tensors="pt")
                enc = {k: v.to(args.device, non_blocking=True) for k, v in enc.items()}
                start = time.time()
                out = mdl(**enc)
                latencies.append(time.time() - start)
                all_logits.extend(out.logits.cpu().numpy())
        return np.stack(all_logits, axis=0), np.array(latencies, dtype=np.float32), all_logits

    # measure baseline RSS
    rss_before = psutil.Process().memory_info().rss if psutil else None
    # Use full dataset for calibration (no downsampling)
    calib_train = train_df
    calib_valid = val_df

    train_logits, train_lat, _ = collect_logits(calib_train["text"].tolist())
    val_logits, val_lat, _ = collect_logits(calib_valid["text"].tolist())

    # Calibration (temperature scaling)
    T = fit_temperature(train_logits, train_df["label"].to_numpy().astype(int))
    print(f"[INFO] Chosen calibration: temperature (T={T:.3f})")

    # Apply calibration and compute phishing probs
    def phishing_from_logits(logits: np.ndarray, T: float) -> np.ndarray:
        probs = softmax(logits / T)
        if probs.shape[1] >= 4:
            return (probs[:, 1] + probs[:, 3]).astype(np.float32)
        return (probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]).astype(np.float32)

    val_ph_cal = phishing_from_logits(val_logits, T)

    # Threshold sweep
    ths = np.arange(0.05, 0.20, 0.005)
    labels = val_df["label"].to_numpy().astype(int)
    rows = []
    best = None
    for t in ths:
        pred = (val_ph_cal >= t).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(labels, pred, average="macro", zero_division=0)
        acc = accuracy_score(labels, pred)
        rows.append({"threshold": float(round(t, 3)), "precision": float(precision), "recall": float(recall), "accuracy": float(acc), "macro_f1": float(f1)})
        if recall >= 0.60:
            if best is None or f1 > best[0]:
                best = (f1, t, precision, recall, acc)

    if best is None:
        best = (0.0, float(ths[0]), 0.0, 0.0, 0.0)

    # Score full holdout with calibrated probs
    all_logits, lat_all, raw_logits = collect_logits(df["text"].tolist())
    rss_after = psutil.Process().memory_info().rss if psutil else None
    all_ph = phishing_from_logits(all_logits, 1.0)
    all_ph_cal = phishing_from_logits(all_logits, T)

    # Log raw class probabilities for first 5 samples
    print("[DEBUG] Raw class probabilities for first 5 samples:")
    for i in range(min(5, len(raw_logits))):
        probs = softmax(raw_logits[i])
        if len(probs) >= 4:
            print(f"  Sample {i}: legitimate_email={probs[0]:.3f}, phishing_url={probs[1]:.3f}, legitimate_url={probs[2]:.3f}, phishing_url_alt={probs[3]:.3f}")
        else:
            print(f"  Sample {i}: probs={probs}")

    # Write artifacts
    (reports_dir / "hf_eval_scores.csv").write_text("")
    scores_df = pd.DataFrame({
        "id": np.arange(len(df)),
        "row_index": np.arange(len(df)),
        "label": df["label"].to_numpy().astype(int),
        "phishing_prob": all_ph.astype(float),
        "phishing_prob_cal": all_ph_cal.astype(float),
        "model_id": model_id,
        "dataset": str(holdout_path),
    })
    scores_df.to_csv(reports_dir / "hf_eval_scores.csv", index=False)

    sweep_df = pd.DataFrame(rows)
    sweep_df["model_id"] = model_id
    sweep_df["dataset"] = str(holdout_path)
    sweep_df.to_csv(reports_dir / "threshold_sweep_hf.csv", index=False)

    selection = {
        "threshold": float(round(best[1], 3)),
        "constraints": {"recall_min": 0.60},
        "metrics": {"macro_f1": float(best[0]), "precision": float(best[2]), "recall": float(best[3]), "accuracy": float(best[4])},
        "model_id": model_id,
        "dataset_path": str(holdout_path),
    }
    with open(reports_dir / "threshold_selection_hf.json", "w") as f:
        json.dump(selection, f, indent=2)

    # model size estimates
    try:
        num_params = sum(p.numel() for p in mdl.parameters())
    except Exception:
        num_params = None
    approx_model_mem_mb = float(num_params * 4 / (1024**2)) if num_params else None

    manifest = {
        "model_id": model_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "calibration": "temperature",
        "latency_ms": {"mean": float(np.mean(lat_all) * 1000.0), "p95": float(np.percentile(lat_all, 95) * 1000.0)},
        "hardware": {"device": args.device},
        "model_params": int(num_params) if num_params is not None else None,
        "approx_model_memory_mb": approx_model_mem_mb,
        "memory_rss_mb": {
            "before": float(rss_before / (1024**2)) if rss_before is not None else None,
            "after": float(rss_after / (1024**2)) if rss_after is not None else None,
        },
    }
    with open(reports_dir / "model_manifest_hf.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Console summary
    pos = int(df["label"].sum()); neg = int(len(df) - pos)
    print(f"[SUMMARY] Class balance: phishing={pos} ({pos/len(df):.2%}), safe={neg} ({neg/len(df):.2%})")
    top = sorted(rows, key=lambda r: (r["macro_f1"], r["recall"]), reverse=True)[:5]
    print("[TOP-5] Thresholds by macro_f1 (with recall):")
    for r in top:
        print(f"  t={r['threshold']:.3f} f1={r['macro_f1']:.3f} recall={r['recall']:.3f} precision={r['precision']:.3f}")
    print(f"[CHOSEN] t*={selection['threshold']:.3f} metrics={selection['metrics']}")
    
    # Sample rows with text length, calibrated score, and final verdict
    print("[SAMPLES] Sample rows with text length, calibrated score, and final verdict:")
    t_star = selection['threshold']
    for i in range(min(5, len(df))):
        text_len = len(df.iloc[i]["text"])
        cal_score = all_ph_cal[i]
        verdict = "PHISHING" if cal_score >= t_star else "SAFE"
        print(f"  Row {i}: len={text_len}, cal_score={cal_score:.3f}, verdict={verdict}")
    
    print(f"[DONE] Artifacts written under {reports_dir}")


if __name__ == "__main__":
    main()


