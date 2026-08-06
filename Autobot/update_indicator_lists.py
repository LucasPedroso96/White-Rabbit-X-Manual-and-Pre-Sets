# -*- coding: utf-8 -*-
"""Atualiza a lista de indicadores nos manuais quando a EA ganha motores.

Toda frase que enumera os motores de entrada fica incompleta a cada indicador
novo. O texto esta em 11 idiomas e cada um escreve o numeral por extenso, entao
trocar o algarismo nao resolve -- e "Sete" que precisa virar "Doze", "Sieben"
virar "Zwoelf", "Yedi" virar "On iki", e assim por diante.

Tambem entra a coluna de opcoes do enum no CSV de referencia, que listava seis
constantes.

Todos os indicadores da EA sao nativos do terminal (iMACD, iMA, iMomentum,
iStochastic, iTriX, iRSI, iCCI, iWPR, iDeMarker, iMFI, iOsMA, iIchimoku,
iADX, iATR). Nao ha iCustom em lugar
nenhum, e por isso os textos dizem "nativos".
"""
from __future__ import annotations

import sys
from pathlib import Path

import wrx_paths

ROOT = wrx_paths.manuals_staging_root()

# (frase antiga, frase nova) por idioma, na mesma ordem do enum: o Ichimoku
# fica sempre por ultimo porque exige faixa de periodos propria.
SENTENCES = {
    '00_Portuguese_Brazil': ('- Sete motores nativos: MACD, cruzamento de EMA, Momentum, Estocástico, TRIX, RSI e Ichimoku.',
        '- Doze motores nativos: MACD, cruzamento de EMA, Momentum, Estocástico, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA e Ichimoku.'),
    '01_English': ('- Seven native engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI and Ichimoku.',
        '- Twelve native engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA and Ichimoku.'),
    '02_Russian': ('- Семь встроенных движков: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI и Ichimoku.',
        '- Двенадцать встроенных движков: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA и Ichimoku.'),
    '03_Chinese': ('- 七种原生引擎：MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、Ichimoku。',
        '- 十二种原生引擎：MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、CCI、Williams %R、DeMarker、MFI、OsMA、Ichimoku。'),
    '04_Spanish': ('- Siete motores nativos: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI e Ichimoku.',
        '- Doce motores nativos: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA e Ichimoku.'),
    '05_Japanese': ('- 7 つのネイティブエンジン: MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、Ichimoku。',
        '- 12 のネイティブエンジン: MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、CCI、Williams %R、DeMarker、MFI、OsMA、Ichimoku。'),
    '06_German': ('- Sieben native Engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI und Ichimoku.',
        '- Zwölf native Engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA und Ichimoku.'),
    '07_Korean': ('- 7개 네이티브 엔진: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, Ichimoku.',
        '- 12개 네이티브 엔진: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA, Ichimoku.'),
    '08_French': ('- Sept moteurs natifs : MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI et Ichimoku.',
        '- Douze moteurs natifs : MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA et Ichimoku.'),
    '09_Italian': ('- Sette motori nativi: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI e Ichimoku.',
        '- Dodici motori nativi: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA e Ichimoku.'),
    '10_Turkish': ('- Yedi yerel motor: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI ve Ichimoku.',
        '- On iki yerel motor: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA ve Ichimoku.'),
}

# Listas de constantes do enum, iguais em todos os idiomas.
ENUM_OLD = ("EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, "
            "Ichimoku.")
ENUM_NEW = ("EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, "
            "CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.")
CSV_OLD = ("EntryIndicator_MACD, EntryIndicator_EMA_Cross, "
           "EntryIndicator_Momentum, EntryIndicator_Stochastic, "
           "EntryIndicator_TRIX, EntryIndicator_RSI, "
           "EntryIndicator_Ichimoku")
CSV_NEW = ("EntryIndicator_MACD, EntryIndicator_EMA_Cross, "
           "EntryIndicator_Momentum, EntryIndicator_Stochastic, "
           "EntryIndicator_TRIX, EntryIndicator_RSI, EntryIndicator_CCI, "
           "EntryIndicator_WPR, EntryIndicator_DeMarker, "
           "EntryIndicator_MFI, EntryIndicator_OsMA, "
           "EntryIndicator_Ichimoku")


def main() -> int:
    touched = 0
    for lang, (old, new) in SENTENCES.items():
        folder = ROOT / lang
        if not folder.is_dir():
            print(f"AUSENTE: {lang}")
            continue
        for path in sorted(folder.glob("*")):
            if path.is_dir() or path.suffix.lower() not in (".md", ".txt", ".csv"):
                continue
            body = original = path.read_text(encoding="utf-8-sig")
            body = body.replace(old, new)
            # Em .txt o marcador de lista some, entao troca tambem sem o hifen.
            body = body.replace(old.lstrip("- "), new.lstrip("- "))
            body = body.replace(ENUM_OLD, ENUM_NEW)
            body = body.replace(CSV_OLD, CSV_NEW)
            if body != original:
                path.write_text(body, encoding="utf-8-sig")
                touched += 1
    print(f"Arquivos atualizados: {touched}")

    restantes = 0
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".md", ".txt", ".csv"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if "TRIX" in text and "RSI" not in text:
                print(f"  ainda sem RSI: {path.relative_to(ROOT)}")
                restantes += 1
    if restantes:
        print(f"Arquivos que citam TRIX sem citar RSI: {restantes}")
    else:
        print("Nenhum texto lista os motores sem incluir o RSI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
