# -*- coding: utf-8 -*-
"""Conversao pra ONNX, PORTE LITERAL do export_onnx.py do Zeus (ver plano
2026-08-30) -- inclui o gate de qualidade obrigatorio (paridade Python vs
ONNX) e o mesmo cuidado documentado com formatacao do scaler sidecar
(fixed-point, NUNCA notacao cientifica -- bug real ja documentado no Zeus:
StringToDouble do MQL5 nao parseia '1.2e-05' de forma confiavel).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxmltools
import onnxruntime as ort
import pandas as pd
from onnxmltools.convert.common.data_types import FloatTensorType

from ml_features import FEATURE_NAMES, N_FEATURES

AQUI = Path(__file__).resolve().parent
DADOS_DIR = AQUI / "ml_data"
MODELOS_DIR = AQUI / "ml_models"

MEDIAN_DIFF_TOLERANCE = 1e-4
MIN_LABEL_AGREEMENT = 0.97


def find_latest(pattern: str) -> Path | None:
    arquivos = sorted(MODELOS_DIR.glob(pattern))
    return arquivos[-1] if arquivos else None


def convert_to_onnx(model):
    initial_type = [("input", FloatTensorType([None, N_FEATURES]))]
    onnx_model = onnxmltools.convert_lightgbm(
        model, initial_types=initial_type, target_opset=12, zipmap=False)
    op_types = {n.op_type for n in onnx_model.graph.node}
    if "ZipMap" in op_types:
        import skl2onnx
        from skl2onnx import convert_sklearn
        from onnxmltools.convert.lightgbm.operator_converters.LightGbm import (
            convert_lightgbm as _convert_lgbm_op)
        skl2onnx.update_registered_converter(
            type(model), "LightGbmLGBMClassifier", None, _convert_lgbm_op)
        onnx_model = convert_sklearn(
            model, initial_types=initial_type,
            options={id(model): {"zipmap": False}}, target_opset=12)
        op_types = {n.op_type for n in onnx_model.graph.node}
    assert "ZipMap" not in op_types, "ZipMap ainda presente apos fallback"
    return onnx_model


def validate_parity(model, scaler: pd.DataFrame, onnx_path: Path) -> dict:
    """Roda inferencia linha por linha (batch=1), replicando exatamente
    como a EA ao vivo vai chamar OnnxRun -- uma barra por vez. Validar em
    batch compararia contra um shape que a producao nunca usa."""
    feats = pd.read_parquet(DADOS_DIR / "XAUUSD_M15_features.parquet")
    labels = pd.read_parquet(DADOS_DIR / "XAUUSD_M15_labels.parquet")
    df = feats.merge(labels[["time", "label"]], on="time")
    df = df.dropna(subset=[*FEATURE_NAMES, "label"]).tail(2000).reset_index(drop=True)

    Xz = (df[list(FEATURE_NAMES)] - scaler["mean"]) / scaler["std"]
    Xz32 = Xz.to_numpy(dtype=np.float32)

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    proba_output = sess.get_outputs()[1] if len(sess.get_outputs()) > 1 else sess.get_outputs()[0]
    proba_idx = sess.get_outputs().index(proba_output)
    input_name = sess.get_inputs()[0].name

    diffs, acordos = [], []
    for i in range(len(df)):
        raw = model.predict_proba(Xz.iloc[i:i + 1])[0]
        onnx_out = sess.run(None, {input_name: Xz32[i:i + 1]})[proba_idx][0]
        diffs.append(np.max(np.abs(np.asarray(onnx_out) - raw)))
        acordos.append(int(np.argmax(raw)) == int(np.argmax(onnx_out)))

    diffs = np.array(diffs)
    return {
        "mean_diff": float(diffs.mean()), "median_diff": float(np.median(diffs)),
        "max_diff": float(diffs.max()), "label_agreement": float(np.mean(acordos)),
        "n": len(df),
    }


def write_scaler_sidecar(scaler: pd.DataFrame, path: Path) -> None:
    linhas = [str(len(FEATURE_NAMES))]
    for nome in FEATURE_NAMES:
        linhas.append(f"{nome} {scaler.loc[nome, 'mean']:.15f} {scaler.loc[nome, 'std']:.15f}")
    path.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> int:
    pkl_path = find_latest("wrx_lgbm_*.pkl")
    scaler_path = find_latest("wrx_scaler_*.csv")
    if pkl_path is None or scaler_path is None:
        print("Sem modelo/scaler treinado -- rode ml_train.py primeiro.")
        return 1
    print(f"modelo: {pkl_path.name} | scaler: {scaler_path.name}")

    import joblib
    # joblib.load de um .pkl: seguro aqui porque e sempre o proprio output
    # do ml_train.py rodado momentos antes, nunca arquivo externo/de
    # terceiros -- mesma justificativa ja documentada no export_onnx.py do
    # Zeus pro mesmo padrao.
    model = joblib.load(pkl_path)
    scaler = pd.read_csv(scaler_path, index_col=0)

    onnx_model = convert_to_onnx(model)
    ts = pkl_path.stem.replace("wrx_lgbm_", "")
    onnx_path = MODELOS_DIR / f"wrx_model_{ts}.onnx"
    with onnx_path.open("wb") as fh:
        fh.write(onnx_model.SerializeToString())
    print(f"onnx gravado: {onnx_path.name}")

    metricas = validate_parity(model, scaler, onnx_path)
    print(f"\nparidade Python vs ONNX ({metricas['n']} linhas, batch=1):")
    print(f"  mean_diff={metricas['mean_diff']:.6g} "
          f"median_diff={metricas['median_diff']:.6g} "
          f"max_diff={metricas['max_diff']:.6g}")
    print(f"  label_agreement={metricas['label_agreement']:.4f}")

    if (metricas["median_diff"] >= MEDIAN_DIFF_TOLERANCE
            or metricas["label_agreement"] < MIN_LABEL_AGREEMENT):
        print(f"\nABORTADO: paridade fora do gate (median_diff < "
              f"{MEDIAN_DIFF_TOLERANCE} e label_agreement >= "
              f"{MIN_LABEL_AGREEMENT} exigidos). Do not deploy this model.")
        return 1

    scaler_txt_path = MODELOS_DIR / f"wrx_scaler_{ts}.txt"
    write_scaler_sidecar(scaler, scaler_txt_path)
    print(f"\nOK -- prontos pro deploy: {onnx_path.name}, {scaler_txt_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
