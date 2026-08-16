# -*- coding: utf-8 -*-
"""Alinha os manuais a biblioteca de sets atual.

Os manuais descreviam a Asset Library antiga: 6.029 sets espalhados em dez
pastas tematicas (06_Research_Matrix, 07_Entry_System_Matrix, ...) e uma tabela
de status BASELINE_WFO / CONTROLLED_RESEARCH / HIGH_RISK_REOPTIMIZE.

Essa biblioteca foi substituida por 3.738 sets organizados por TIPO DE SISTEMA
(classe / ativo / sistema / lado), em que cada arquivo e um sistema completo
com todos os eixos otimizaveis ao mesmo tempo. Deixar o manual descrevendo a
estrutura antiga faz o comprador procurar pastas que nao existem.

O que muda aqui:
  - contagens e nomes de pasta;
  - a secao de fluxo do guia WFO, reescrita nos 11 idiomas para o metodo real
    da EA (Insample para otimizar, InSampleAndOutSample para validar) e para a
    armadilha do input_end_date, que zera todos os passes quando esta errado;
  - a tabela de status vira a tabela dos 11 sistemas;
  - SHA-256 e versao da EA.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import wrx_paths

ROOT = wrx_paths.manuals_staging_root()
EA = (wrx_paths.data_dir() / "MQL5" / "Experts"
      / "White Rabbit X (Global Multi-Indicator).mq5")

OLD_SHA = "3054418250AFB540F93CC05038E4F93FA15F50903D57E38FB08052CFFA99862A"
NEW_SHA = hashlib.sha256(EA.read_bytes()).hexdigest().upper()
SET_COUNT_OLD = ["6029", "6.029", "6 029", "6,029"]
SET_COUNT_NEW = "3738"

# Fluxo de trabalho reescrito, por idioma: (titulo, paragrafo, passos).
WORKFLOW = {
    "00_Portuguese_Brazil": (
        "Fluxo de trabalho",
        "Cada .set e um sistema completo: indicador, metodo de entrada, "
        "timeframe, periodos, ATR, filtros e a geometria de saida daquele "
        "sistema estao todos marcados para otimizacao no mesmo arquivo. "
        "Voce roda, descobre, e trava na mao o que ja resolveu.",
        ["Confirme que o EX5, o codigo-fonte e a biblioteca de sets sao da "
         "mesma versao.",
         "Copie a biblioteca para MQL5\\Profiles\\Tester.",
         "Mapeie o ativo para o simbolo exato do broker: sufixo, sessao, "
         "moeda de lucro e tamanho de contrato.",
         "Escolha o tipo de sistema que quer estudar e carregue o arquivo do "
         "ativo e do lado (BUY ou SELL) em Inputs > Load.",
         "Otimize com o algoritmo genetico. Acima de 100 milhoes de "
         "combinacoes o MT5 ja seleciona o genetico sozinho.",
         "Trave o que descobriu: mude o Y do parametro para N e deixe o valor "
         "vencedor. O espaco de busca cai em ordens de magnitude e a rodada "
         "seguinte fica muito mais precisa.",
         "Repita ate sobrar apenas a geometria de saida; ai o Complete Search "
         "ja e viavel.",
         "Ligue o walk-forward com AtivarWFO=true e MetodoDeEntradawfo=Insample "
         "para que a otimizacao veja apenas o In-Sample.",
         "Valide o vencedor com MetodoDeEntradawfo=InSampleAndOutSample e leia "
         "a Walk Forward Efficiency no log.",
         "Rode o WhiteRabbit Filters SelfTest e prossiga apenas com zero "
         "falhas.",
         "Para testes com noticias, gere WhiteRabbit_News.csv cobrindo todo o "
         "periodo e todas as moedas necessarias.",
         "Faca forward-demo antes de assumir risco financeiro."],
    ),
    "01_English": (
        "Workflow",
        "Every .set is a complete system: indicator, entry method, timeframe, "
        "periods, ATR, filters and that system's exit geometry are all flagged "
        "for optimization in the same file. You run it, you learn, and you "
        "lock down by hand what you have already settled.",
        ["Confirm that the EX5, the source code and the set library belong to "
         "the same release.",
         "Copy the library to MQL5\\Profiles\\Tester.",
         "Map the asset to the broker's exact symbol: suffix, session, profit "
         "currency and contract size.",
         "Pick the system type you want to study and load the file for that "
         "asset and side (BUY or SELL) under Inputs > Load.",
         "Optimize with the genetic algorithm. Above 100 million combinations "
         "MT5 switches to genetic on its own.",
         "Lock down what you found: change that parameter's Y to N and keep "
         "the winning value. The search space drops by orders of magnitude and "
         "the next run becomes far more precise.",
         "Repeat until only the exit geometry is left; Complete Search becomes "
         "practical at that point.",
         "Enable walk-forward with AtivarWFO=true and "
         "MetodoDeEntradawfo=Insample so the optimization only sees In-Sample.",
         "Validate the winner with MetodoDeEntradawfo=InSampleAndOutSample and "
         "read the Walk Forward Efficiency in the log.",
         "Run WhiteRabbit Filters SelfTest and proceed only on zero failures.",
         "For news tests, generate WhiteRabbit_News.csv covering the whole "
         "period and every required currency.",
         "Run a forward demo before taking financial risk."],
    ),
}

# Nota sobre a armadilha da data, por idioma.
DATE_TRAP = {
    "00_Portuguese_Brazil":
        "**Atencao a data.** Com o WFO ligado, o OnTester compara o fim real "
        "do teste com input_end_date e devolve zero se o teste terminou antes "
        "(tolerancia de 80 horas). Data errada zera todos os passes e a "
        "otimizacao inteira parece quebrada. Ajuste input_end_date para a "
        "mesma data final configurada no Strategy Tester.",
    "01_English":
        "**Mind the date.** With WFO enabled, OnTester compares the real end "
        "of the test against input_end_date and returns zero if the test "
        "ended earlier (80-hour tolerance). A wrong date zeroes every pass and "
        "the whole optimization looks broken. Set input_end_date to the same "
        "end date configured in the Strategy Tester.",
    "02_Russian":
        "**Внимание к дате.** При включённом WFO функция OnTester сравнивает "
        "реальное окончание теста с input_end_date и возвращает ноль, если "
        "тест закончился раньше (допуск 80 часов). Неверная дата обнуляет все "
        "проходы, и вся оптимизация выглядит сломанной. Укажите в "
        "input_end_date ту же конечную дату, что и в тестере стратегий.",
    "03_Chinese":
        "**注意日期。** 启用 WFO 后，OnTester 会将测试的实际结束时间与 "
        "input_end_date 比较；如果测试提前结束（容差 80 小时），则返回零。"
        "日期设置错误会使所有测试遍次归零，整个优化看起来像是坏掉了。"
        "请将 input_end_date 设为与策略测试器中相同的结束日期。",
    "04_Spanish":
        "**Atención a la fecha.** Con el WFO activado, OnTester compara el "
        "final real de la prueba con input_end_date y devuelve cero si la "
        "prueba terminó antes (tolerancia de 80 horas). Una fecha equivocada "
        "pone a cero todas las pasadas y toda la optimización parece rota. "
        "Ajuste input_end_date a la misma fecha final configurada en el "
        "Probador de Estrategias.",
    "05_Japanese":
        "**日付に注意。** WFO を有効にすると、OnTester はテストの実際の終了時刻を "
        "input_end_date と比較し、テストがそれより早く終わっていた場合はゼロを"
        "返します（許容範囲 80 時間）。日付を誤ると全パスがゼロになり、"
        "最適化全体が壊れているように見えます。input_end_date は"
        "ストラテジーテスターで設定した終了日と同じにしてください。",
    "06_German":
        "**Auf das Datum achten.** Bei aktiviertem WFO vergleicht OnTester das "
        "tatsächliche Testende mit input_end_date und liefert null zurück, "
        "wenn der Test früher endete (Toleranz 80 Stunden). Ein falsches Datum "
        "setzt jeden Durchlauf auf null und die gesamte Optimierung wirkt "
        "defekt. Setzen Sie input_end_date auf dasselbe Enddatum, das im "
        "Strategietester konfiguriert ist.",
    "07_Korean":
        "**날짜에 주의하십시오.** WFO를 켜면 OnTester가 테스트의 실제 종료 "
        "시점을 input_end_date와 비교하여, 테스트가 더 일찍 끝났으면 0을 "
        "반환합니다(허용 오차 80시간). 날짜가 틀리면 모든 패스가 0이 되고 "
        "최적화 전체가 고장난 것처럼 보입니다. input_end_date를 전략 "
        "테스터에 설정한 종료일과 동일하게 맞추십시오.",
    "08_French":
        "**Attention à la date.** Avec le WFO activé, OnTester compare la fin "
        "réelle du test à input_end_date et renvoie zéro si le test s'est "
        "terminé plus tôt (tolérance de 80 heures). Une date erronée met "
        "toutes les passes à zéro et l'optimisation entière semble cassée. "
        "Réglez input_end_date sur la même date de fin que celle configurée "
        "dans le Testeur de Stratégies.",
    "09_Italian":
        "**Attenzione alla data.** Con il WFO attivo, OnTester confronta la "
        "fine reale del test con input_end_date e restituisce zero se il test "
        "è terminato prima (tolleranza di 80 ore). Una data sbagliata azzera "
        "tutte le passate e l'intera ottimizzazione sembra rotta. Imposta "
        "input_end_date sulla stessa data finale configurata nello Strategy "
        "Tester.",
    "10_Turkish":
        "**Tarihe dikkat.** WFO açıkken OnTester, testin gerçek bitişini "
        "input_end_date ile karşılaştırır ve test daha erken bittiyse sıfır "
        "döndürür (80 saatlik tolerans). Yanlış tarih tüm geçişleri sıfırlar "
        "ve optimizasyonun tamamı bozulmuş gibi görünür. input_end_date "
        "değerini Strateji Test Cihazında ayarladığınız bitiş tarihiyle aynı "
        "yapın.",
}

# Tabela dos 11 sistemas, cabecalho por idioma.
SYSTEM_TABLE_HEADER = {
    "00_Portuguese_Brazil": ("Sistema", "Gestao", "Sets"),
    "01_English": ("System", "Management", "Sets"),
    "02_Russian": ("Система", "Управление", "Наборы"),
    "03_Chinese": ("系统", "管理方式", "参数集"),
    "04_Spanish": ("Sistema", "Gestión", "Sets"),
    "05_Japanese": ("システム", "管理方式", "セット"),
    "06_German": ("System", "Management", "Sets"),
    "07_Korean": ("시스템", "관리 방식", "세트"),
    "08_French": ("Système", "Gestion", "Sets"),
    "09_Italian": ("Sistema", "Gestione", "Set"),
    "10_Turkish": ("Sistem", "Yönetim", "Set"),
}

SYSTEMS = {
    "00_Portuguese_Brazil": [
        ("01_SLTP", "Stop Loss + Take Profit em multiplos de ATR"),
        ("02_SLTP_ORGANIC", "SL + take organico ancorado no ultimo trade"),
        ("03_TRAIL_ONLY", "SL + trailing, sem TP: deixa correr"),
        ("04_SLTP_TRAIL", "SL + TP + trailing atras"),
        ("05_BE_TRAIL", "Breakeven obrigatorio + trailing"),
        ("06_REVERSAL_EXIT", "Fecha no sinal contrario do indicador"),
        ("07_GRID_SEPARATE", "Grid com alvo por lado (conta hedging)"),
        ("09_MARTINGALE", "Lote dobra apos perda, 1 posicao por lado"),
        ("10_DALEMBERT", "Lote cresce em passo aritmetico apos perda"),
        ("11_SIGNAL_ONLY", "Sem SL e sem TP: mede o sinal cru"),
    ],
    "01_English": [
        ("01_SLTP", "Stop Loss + Take Profit as ATR multiples"),
        ("02_SLTP_ORGANIC", "SL + organic take anchored on the last trade"),
        ("03_TRAIL_ONLY", "SL + trailing, no TP: let it run"),
        ("04_SLTP_TRAIL", "SL + TP + trailing behind"),
        ("05_BE_TRAIL", "Mandatory breakeven + trailing"),
        ("06_REVERSAL_EXIT", "Closes on the indicator's opposite signal"),
        ("07_GRID_SEPARATE", "Grid with a target per side (hedging account)"),
        ("09_MARTINGALE", "Lot doubles after a loss, one position per side"),
        ("10_DALEMBERT", "Lot grows in arithmetic steps after a loss"),
        ("11_SIGNAL_ONLY", "No SL and no TP: measures the raw signal"),
    ],
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8-sig")


def system_table(lang: str) -> str:
    cols = SYSTEM_TABLE_HEADER.get(lang, SYSTEM_TABLE_HEADER["01_English"])
    rows = SYSTEMS.get(lang, SYSTEMS["01_English"])
    out = [f"| {cols[0]} | {cols[1]} | {cols[2]} |", "| --- | --- | ---: |"]
    for code, desc in rows:
        out.append(f"| `{code}` | {desc} | 356 |")
    return "\n".join(out)


def replace_status_table(body: str, lang: str) -> str:
    """Troca a tabela de status da biblioteca antiga pela dos 11 sistemas."""
    pattern = re.compile(
        r"\|\s*Manifest status.*?\n(?:\|.*\n)+", re.IGNORECASE)
    if not pattern.search(body):
        pattern = re.compile(r"\|[^\n]*BASELINE_WFO[^\n]*\n(?:\|.*\n)*")
        # tabela sem cabecalho reconhecivel: pega o bloco todo que contem
        # BASELINE_WFO e as linhas de tabela ao redor
        m = re.search(r"((?:\|[^\n]*\n){1,4})\|[^\n]*BASELINE_WFO[^\n]*\n"
                      r"((?:\|[^\n]*\n)*)", body)
        if not m:
            return body
        return body[:m.start()] + system_table(lang) + "\n" + body[m.end():]
    return pattern.sub(system_table(lang) + "\n", body)


def main() -> int:
    langs = sorted(d.name for d in ROOT.iterdir()
                   if d.is_dir() and re.match(r"^\d\d_", d.name))
    counts = {"numeros": 0, "sha": 0, "tabela": 0, "data": 0}

    for lang in langs:
        for path in sorted((ROOT / lang).glob("*")):
            if path.is_dir() or path.suffix.lower() not in (".md", ".txt", ".csv"):
                continue
            body = original = read(path)

            for old in SET_COUNT_OLD:
                if old in body:
                    body = body.replace(old, SET_COUNT_NEW)
            if OLD_SHA in body:
                body = body.replace(OLD_SHA, NEW_SHA)
                body = body.replace(OLD_SHA.lower(), NEW_SHA)

            if "BASELINE_WFO" in body:
                body = replace_status_table(body, lang)
                counts["tabela"] += 1

            # A armadilha da data entra no guia WFO, logo apos o titulo.
            if path.name[:2] == "03" and path.suffix.lower() == ".md":
                note = DATE_TRAP.get(lang)
                if note and "input_end_date" not in body:
                    m = re.search(r"^## .+$", body, re.MULTILINE)
                    if m:
                        body = (body[:m.start()] + note + "\n\n"
                                + body[m.start():])
                        counts["data"] += 1

            if body != original:
                write(path, body)
                counts["numeros"] += 1

    print(f"Arquivos atualizados: {counts['numeros']}")
    print(f"Tabelas de status substituidas pelos 11 sistemas: {counts['tabela']}")
    print(f"Aviso da armadilha da data inserido: {counts['data']} guias WFO")
    print(f"SHA-256 da EA agora: {NEW_SHA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
