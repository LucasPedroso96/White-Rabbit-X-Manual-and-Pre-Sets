# -*- coding: utf-8 -*-
"""Sincroniza a referencia de inputs dos manuais com a EA.

O CSV lista um input por linha, na ordem em que a EA os declara. Quando a EA
ganha inputs, o CSV fica curto e o comprador nao encontra o parametro que esta
vendo na tela.

Este script reconstroi o CSV na ordem atual do .mq5: mantem a descricao ja
traduzida de cada linha existente e acrescenta as novas com texto no idioma do
arquivo. Nada e reescrito por cima do que ja estava traduzido.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lucas Pedroso\OneDrive\SantoGral\Santo Gral"
            r"\venda mql5\Pacote_Completo_White_Rabbit_X\Languages")
EA = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
          r"\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Experts"
          r"\White Rabbit X (Global Multi-Indicator).mq5")
EA_VERSION = "1.12"

# Descricao das linhas novas, por idioma: nome -> (descricao, nota operacional)
NEW_ROWS = {
    "StochasticSlowing": {
        "00_Portuguese_Brazil": ("Stochastic: suavizacao do %K",
                                 "So tem efeito quando o indicador de entrada e o Stochastic."),
        "01_English": ("Stochastic: %K slowing",
                       "Only has effect when the entry indicator is Stochastic."),
        "02_Russian": ("Стохастик: замедление %K",
                       "Действует только когда индикатор входа — Стохастик."),
        "03_Chinese": ("随机指标：%K 平滑", "仅当入场指标为随机指标时生效。"),
        "04_Spanish": ("Estocástico: suavizado de %K",
                       "Solo tiene efecto cuando el indicador de entrada es el Estocástico."),
        "05_Japanese": ("ストキャスティクス：%K の平滑化",
                        "エントリーインジケーターがストキャスティクスの場合のみ有効です。"),
        "06_German": ("Stochastik: %K-Glättung",
                      "Wirkt nur, wenn der Einstiegsindikator Stochastik ist."),
        "07_Korean": ("스토캐스틱: %K 평활화",
                      "진입 지표가 스토캐스틱일 때만 적용됩니다."),
        "08_French": ("Stochastique : lissage du %K",
                      "N'a d'effet que si l'indicateur d'entrée est le Stochastique."),
        "09_Italian": ("Stocastico: smorzamento del %K",
                       "Ha effetto solo quando l'indicatore di ingresso è lo Stocastico."),
        "10_Turkish": ("Stokastik: %K yumuşatma",
                       "Yalnızca giriş göstergesi Stokastik olduğunda etkilidir."),
    },
    "StochasticMethod": {
        "00_Portuguese_Brazil": ("Stochastic: metodo de suavizacao",
                                 "SMA, EMA, SMMA ou LWMA."),
        "01_English": ("Stochastic: smoothing method", "SMA, EMA, SMMA or LWMA."),
        "02_Russian": ("Стохастик: метод сглаживания", "SMA, EMA, SMMA или LWMA."),
        "03_Chinese": ("随机指标：平滑方法", "SMA、EMA、SMMA 或 LWMA。"),
        "04_Spanish": ("Estocástico: método de suavizado", "SMA, EMA, SMMA o LWMA."),
        "05_Japanese": ("ストキャスティクス：平滑化方式", "SMA、EMA、SMMA、LWMA。"),
        "06_German": ("Stochastik: Glättungsmethode", "SMA, EMA, SMMA oder LWMA."),
        "07_Korean": ("스토캐스틱: 평활화 방식", "SMA, EMA, SMMA 또는 LWMA."),
        "08_French": ("Stochastique : méthode de lissage", "SMA, EMA, SMMA ou LWMA."),
        "09_Italian": ("Stocastico: metodo di smorzamento", "SMA, EMA, SMMA o LWMA."),
        "10_Turkish": ("Stokastik: yumuşatma yöntemi", "SMA, EMA, SMMA veya LWMA."),
    },
    "StochasticPriceField": {
        "00_Portuguese_Brazil": ("Stochastic: Low/High ou Close/Close",
                                 "Close/Close usa fechamentos em vez de maximas e minimas; costuma ser menos ruidoso."),
        "01_English": ("Stochastic: Low/High or Close/Close",
                       "Close/Close uses closing prices instead of highs and lows; usually less noisy."),
        "02_Russian": ("Стохастик: Low/High или Close/Close",
                       "Close/Close использует цены закрытия вместо максимумов и минимумов; обычно менее шумный."),
        "03_Chinese": ("随机指标：Low/High 或 Close/Close",
                       "Close/Close 使用收盘价而非最高最低价，通常噪音更少。"),
        "04_Spanish": ("Estocástico: Low/High o Close/Close",
                       "Close/Close usa cierres en vez de máximos y mínimos; suele ser menos ruidoso."),
        "05_Japanese": ("ストキャスティクス：Low/High または Close/Close",
                        "Close/Close は高値安値ではなく終値を使い、通常ノイズが少なくなります。"),
        "06_German": ("Stochastik: Low/High oder Close/Close",
                      "Close/Close nutzt Schlusskurse statt Hochs und Tiefs; meist weniger verrauscht."),
        "07_Korean": ("스토캐스틱: Low/High 또는 Close/Close",
                      "Close/Close는 고가·저가 대신 종가를 사용하며 보통 노이즈가 적습니다."),
        "08_French": ("Stochastique : Low/High ou Close/Close",
                      "Close/Close utilise les clôtures au lieu des plus hauts et plus bas ; généralement moins bruité."),
        "09_Italian": ("Stocastico: Low/High o Close/Close",
                       "Close/Close usa le chiusure invece di massimi e minimi; di solito meno rumoroso."),
        "10_Turkish": ("Stokastik: Low/High veya Close/Close",
                       "Close/Close, en yüksek/en düşük yerine kapanışları kullanır; genellikle daha az gürültülüdür."),
    },
    "IchimokuUseKumo": {
        "00_Portuguese_Brazil": ("Ichimoku: cruzamento de referencia usa a nuvem",
                                 "Ligado, o gatilho de referencia e o rompimento da nuvem; desligado, o cruzamento do preco com o Kijun."),
        "01_English": ("Ichimoku: reference cross uses the cloud",
                       "On, the reference trigger is the cloud breakout; off, the price/Kijun cross."),
        "02_Russian": ("Ишимоку: опорное пересечение по облаку",
                       "Включено — сигналом служит пробой облака; выключено — пересечение цены с Киджун."),
        "03_Chinese": ("一目均衡表：参考交叉使用云层",
                       "开启时以突破云层为参考信号；关闭时使用价格与基准线的交叉。"),
        "04_Spanish": ("Ichimoku: el cruce de referencia usa la nube",
                       "Activado, el disparador es la ruptura de la nube; desactivado, el cruce del precio con el Kijun."),
        "05_Japanese": ("一目均衡表：基準の判定に雲を使う",
                        "オンで雲のブレイクアウト、オフで価格と基準線のクロスになります。"),
        "06_German": ("Ichimoku: Referenzkreuzung nutzt die Wolke",
                      "An: Ausbruch aus der Wolke; aus: Kreuzung von Preis und Kijun."),
        "07_Korean": ("일목균형표: 기준 교차에 구름 사용",
                      "켜면 구름 돌파가 기준 신호이고, 끄면 가격과 기준선의 교차입니다."),
        "08_French": ("Ichimoku : le croisement de référence utilise le nuage",
                      "Activé, le déclencheur est la cassure du nuage ; désactivé, le croisement prix/Kijun."),
        "09_Italian": ("Ichimoku: l'incrocio di riferimento usa la nuvola",
                       "Attivo, il segnale è la rottura della nuvola; disattivo, l'incrocio prezzo/Kijun."),
        "10_Turkish": ("Ichimoku: referans kesişimi bulutu kullanır",
                       "Açıkken tetikleyici bulut kırılımıdır; kapalıyken fiyat/Kijun kesişimi."),
    },
    "IchimokuChikouFilter": {
        "00_Portuguese_Brazil": ("Ichimoku: exigir confirmacao do Chikou",
                                 "A linha atrasada precisa estar acima (compra) ou abaixo (venda) do preco de Kijun barras atras."),
        "01_English": ("Ichimoku: require Chikou confirmation",
                       "The lagging line must sit above (buy) or below (sell) the price from Kijun bars ago."),
        "02_Russian": ("Ишимоку: требовать подтверждение Чику",
                       "Запаздывающая линия должна быть выше (покупка) или ниже (продажа) цены Киджун баров назад."),
        "03_Chinese": ("一目均衡表：要求迟行线确认",
                       "迟行线须高于（买入）或低于（卖出）基准线周期数之前的价格。"),
        "04_Spanish": ("Ichimoku: exigir confirmación del Chikou",
                       "La línea retrasada debe estar por encima (compra) o por debajo (venta) del precio de hace Kijun barras."),
        "05_Japanese": ("一目均衡表：遅行スパンの確認を必須にする",
                        "遅行線が基準線期間前の価格より上（買い）または下（売り）にある必要があります。"),
        "06_German": ("Ichimoku: Chikou-Bestätigung verlangen",
                      "Die verzögerte Linie muss über (Kauf) oder unter (Verkauf) dem Preis von vor Kijun Bars liegen."),
        "07_Korean": ("일목균형표: 후행스팬 확인 요구",
                      "후행선이 기준선 기간 이전 가격보다 위(매수) 또는 아래(매도)에 있어야 합니다."),
        "08_French": ("Ichimoku : exiger la confirmation du Chikou",
                      "La ligne retardée doit être au-dessus (achat) ou en dessous (vente) du prix d'il y a Kijun barres."),
        "09_Italian": ("Ichimoku: richiedere conferma del Chikou",
                       "La linea ritardata deve stare sopra (acquisto) o sotto (vendita) al prezzo di Kijun barre fa."),
        "10_Turkish": ("Ichimoku: Chikou onayı iste",
                       "Gecikmeli çizgi, Kijun bar önceki fiyatın üstünde (alış) veya altında (satış) olmalıdır."),
    },
}

SEPARATOR_NOTE = {
    "00_Portuguese_Brazil": "Separador visual mantido para compatibilidade do schema .set; nao otimizar.",
    "01_English": "Visual separator retained for .set schema compatibility; do not optimize.",
    "02_Russian": "Визуальный разделитель для совместимости схемы .set; не оптимизировать.",
    "03_Chinese": "为保持 .set 结构兼容而保留的视觉分隔符；请勿优化。",
    "04_Spanish": "Separador visual mantenido por compatibilidad del esquema .set; no optimizar.",
    "05_Japanese": ".set のスキーマ互換のために残した視覚的な区切りです。最適化しないでください。",
    "06_German": "Visueller Trenner zur Kompatibilität des .set-Schemas; nicht optimieren.",
    "07_Korean": ".set 스키마 호환을 위해 남긴 시각적 구분자입니다. 최적화하지 마십시오.",
    "08_French": "Séparateur visuel conservé pour la compatibilité du schéma .set ; ne pas optimiser.",
    "09_Italian": "Separatore visivo mantenuto per compatibilità dello schema .set; non ottimizzare.",
    "10_Turkish": "'.set' şeması uyumluluğu için korunan görsel ayırıcı; optimize etmeyin.",
}


def ea_inputs() -> list[tuple[str, str, str, str]]:
    """(nome, tipo, default, comentario) na ordem declarada, com a secao."""
    rows: list[tuple[str, str, str, str]] = []
    section = "General"
    for line in EA.read_text(encoding="utf-8").splitlines():
        grp = re.match(r'^\s*input\s+group\s+"([^"]*)"', line)
        if grp:
            section = grp.group(1)
            continue
        m = re.match(
            r"^\s*input\s+(?!group\b)([A-Za-z_][A-Za-z0-9_]*)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);\s*(?://\s*(.*))?", line)
        if m:
            rows.append((m.group(2), m.group(1), m.group(3).strip(),
                         (m.group(4) or "").strip()))
    return rows


def csv_escape(value: str) -> str:
    if ";" in value or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def main() -> int:
    inputs = ea_inputs()
    sha = hashlib.sha256(EA.read_bytes()).hexdigest().upper()
    print(f"Inputs na EA: {len(inputs)}")

    for lang_dir in sorted(ROOT.iterdir()):
        if not lang_dir.is_dir() or not re.match(r"^\d\d_", lang_dir.name):
            continue
        lang = lang_dir.name
        csv_path = next(lang_dir.glob("06_*.csv"), None)
        if not csv_path:
            print(f"{lang}: CSV nao encontrado")
            continue

        rows = csv_path.read_text(encoding="utf-8-sig").splitlines()
        header = rows[0]
        existing: dict[str, list[str]] = {}
        for row in rows[1:]:
            cols = row.split(";")
            if len(cols) > 3:
                existing[cols[3].strip()] = cols

        out = [header]
        added = 0
        for index, (name, ctype, default, comment) in enumerate(inputs, 1):
            old = existing.get(name)
            if old:
                old[0] = str(index)
                old[-2] = EA_VERSION
                old[-1] = sha
                out.append(";".join(old))
                continue
            # Linha nova: texto no idioma do arquivo.
            if name.startswith("myBlankSpace"):
                desc, note = comment, SEPARATOR_NOTE[lang]
            else:
                desc, note = NEW_ROWS.get(name, {}).get(
                    lang, (comment, comment))
            section = "Entries, Signal and Position Management"
            out.append(";".join([
                str(index), csv_escape(section), "", name, ctype,
                csv_escape(default), csv_escape(desc), "",
                csv_escape(note), EA_VERSION, sha,
            ]))
            added += 1

        csv_path.write_text("\n".join(out) + "\n", encoding="utf-8-sig")
        print(f"{lang}: {len(out) - 1} linhas ({added} novas)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
