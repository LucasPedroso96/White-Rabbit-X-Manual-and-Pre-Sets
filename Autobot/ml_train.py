# -*- coding: utf-8 -*-
"""Treino do LightGBM, PORTE LITERAL do train.py do Zeus (ver plano
2026-08-30) -- mesmos hiperparametros de partida (documentados no Zeus
como ja batalhados: um grid search de 81 combinacoes achou hiperparametros
com CV MELHOR e resultado real >3x PIOR, foi revertido pra estes defaults;
mesma desconfianca de "CV vence, live perde" vale herdar aqui).

Timeline:
[---------- trainval (purged walk-forward CV'd, so diagnostico) ----------][ embargo ][ OOS_BARS reservado ]

A janela OOS final nunca e tocada aqui -- reservada pro backtest real via
passe_unico() (Passo 5 do plano), no MT5 de verdade, nao neste script.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from lightgbm import LGBMClassifier, early_stopping
from sklearn.metrics import balanced_accuracy_score, log_loss

import ml_cv as cv
from ml_features import FEATURE_NAMES

AQUI = Path(__file__).resolve().parent
DADOS_DIR = AQUI / "ml_data"
MODELOS_DIR = AQUI / "ml_models"
MODELOS_DIR.mkdir(exist_ok=True)

OOS_BARS = 24 * 4 * 30  # ~30 dias de M15 -- mesmo valor do Zeus

LGBM_PARAMS = dict(
    objective="multiclass",
    num_class=3,
    num_leaves=31,
    max_depth=6,
    learning_rate=0.05,
    n_estimators=400,
    min_child_samples=100,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    reg_lambda=1.0,
    class_weight="balanced",
    random_state=42,
    verbosity=-1,
)
EARLY_STOPPING_ROUNDS = 50


def load_dataset() -> pd.DataFrame:
    feats = pd.read_parquet(DADOS_DIR / "XAUUSD_M15_features.parquet")
    labels = pd.read_parquet(DADOS_DIR / "XAUUSD_M15_labels.parquet")
    # exit_idx precisa vir junto -- e o que ml_cv.purged_walk_forward_splits()
    # usa pra saber ate onde a janela de label de cada amostra se estende
    # (o purge em si). label sozinho nao basta.
    df = feats.merge(labels[["time", "label", "exit_idx"]], on="time")
    df = df.dropna(subset=[*FEATURE_NAMES, "label"]).reset_index(drop=True)
    df["label"] = df["label"].astype(int)
    return df


def compute_scaler(train_df: pd.DataFrame) -> pd.DataFrame:
    mean = train_df[list(FEATURE_NAMES)].mean()
    std = train_df[list(FEATURE_NAMES)].std(ddof=0).replace(0.0, 1.0)
    return pd.DataFrame({"mean": mean, "std": std})


def apply_scaler(df: pd.DataFrame, scaler: pd.DataFrame) -> pd.DataFrame:
    X = df[list(FEATURE_NAMES)]
    return (X - scaler["mean"]) / scaler["std"]


def run_cv_diagnostics(trainval: pd.DataFrame) -> None:
    print("\n=== CV purgado (so diagnostico, nao decide o modelo final) ===")
    for fold, (train_idx, val_idx) in enumerate(cv.purged_walk_forward_splits(trainval)):
        tr_df, va_df = trainval.iloc[train_idx], trainval.iloc[val_idx]
        scaler = compute_scaler(tr_df)
        X_tr, y_tr = apply_scaler(tr_df, scaler), tr_df["label"]
        X_va, y_va = apply_scaler(va_df, scaler), va_df["label"]
        modelo = LGBMClassifier(**LGBM_PARAMS)
        modelo.fit(X_tr, y_tr)
        pred = modelo.predict(X_va)
        proba = modelo.predict_proba(X_va)
        bal_acc = balanced_accuracy_score(y_va, pred)
        ll = log_loss(y_va, proba, labels=[0, 1, 2])
        print(f"  fold {fold}: treino={len(tr_df)} val={len(va_df)} "
              f"| balanced_acc={bal_acc:.4f} | log_loss={ll:.4f}")


def train_final_model(trainval: pd.DataFrame):
    cutoff = int(len(trainval) * 0.9)
    fit_df, es_df = trainval.iloc[:cutoff], trainval.iloc[cutoff:]

    scaler_fit = compute_scaler(fit_df)
    X_fit, y_fit = apply_scaler(fit_df, scaler_fit), fit_df["label"]
    X_es, y_es = apply_scaler(es_df, scaler_fit), es_df["label"]

    modelo_es = LGBMClassifier(**LGBM_PARAMS)
    modelo_es.fit(X_fit, y_fit, eval_set=[(X_es, y_es)],
                  callbacks=[early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)])
    best_iter = modelo_es.best_iteration_ or LGBM_PARAMS["n_estimators"]

    final_scaler = compute_scaler(trainval)
    X_all = apply_scaler(trainval, final_scaler)
    y_all = trainval["label"]
    params_final = dict(LGBM_PARAMS, n_estimators=best_iter)
    final_model = LGBMClassifier(**params_final)
    final_model.fit(X_all, y_all)

    return final_model, final_scaler, best_iter


def main() -> int:
    df = load_dataset()
    oos_cut = len(df) - OOS_BARS
    if oos_cut <= 0:
        print(f"dataset pequeno demais ({len(df)} linhas) pra reservar "
              f"{OOS_BARS} de OOS.")
        return 1
    trainval, oos = df.iloc[:oos_cut], df.iloc[oos_cut:]
    print(f"trainval: {len(trainval)} | oos reservado: {len(oos)} "
          f"({oos['time'].min()} a {oos['time'].max()})")

    run_cv_diagnostics(trainval)

    model, scaler, best_iter = train_final_model(trainval)
    print(f"\nmodelo final: {best_iter} arvores")
    importancias = pd.Series(model.feature_importances_, index=FEATURE_NAMES)
    print("\nfeature importances:")
    print(importancias.sort_values(ascending=False).to_string())

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pkl_path = MODELOS_DIR / f"wrx_lgbm_{ts}.pkl"
    scaler_path = MODELOS_DIR / f"wrx_scaler_{ts}.csv"
    meta_path = MODELOS_DIR / f"wrx_meta_{ts}.json"

    joblib.dump(model, pkl_path)
    scaler.to_csv(scaler_path)
    meta = {
        "timestamp": ts, "n_trees": int(best_iter),
        "feature_names": list(FEATURE_NAMES),
        "trainval_rows": len(trainval), "oos_rows": len(oos),
        "oos_from": str(oos["time"].min()), "oos_to": str(oos["time"].max()),
        "lgbm_params": dict(LGBM_PARAMS, n_estimators=int(best_iter)),
        "pkl_path": str(pkl_path), "scaler_path": str(scaler_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsalvo: {pkl_path.name}, {scaler_path.name}, {meta_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
