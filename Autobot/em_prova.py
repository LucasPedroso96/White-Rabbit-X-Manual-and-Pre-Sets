# -*- coding: utf-8 -*-
"""EM_PROVA: loop de promocao/rebaixamento ao vivo do AutoManagerLive -- ver
PLANO_TREINAMENTO_100_A_MILHAO.md secao 8 ("Fora de escopo por enquanto").

So COMPUTA e EXPOE status a partir de trade ao vivo real; nunca abre, fecha
ou redimensiona ordem nenhuma -- isso continua fora de escopo, ver secao 8.

Todo combo recem-implantado (`sets_implantados.json`, dashboard_campanha.py)
entra em EM_PROVA ate acumular MIN_TRADES_PROVA trades ao vivo, com alocacao
reduzida. Passada a prova, compara o lucro medio por trade ao vivo (janela
movel) contra o expectancy_r OOS ja gravado no ledger PRA AQUELE COMBO
ESPECIFICO (nunca uma media de tier -- mesmo motivo do desempate por combo
individual da secao 6 do plano: agregar mascara o que importa).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

import ready_library
from generate_system_sets import ASSETS, MAGIC_BASE, MAGIC_SPAN, SYSTEMS

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "campanha_resultados.jsonl"
ESTADO_PATH = AQUI / "em_prova_estado.json"
EXCLUIDOS_PATH = AQUI / "em_prova_excluidos.json"

# Todos os numeros abaixo sao PRIMEIRO CORTE, sem trade ao vivo real
# suficiente pra calibrar contra (mesmo espirito do "script a construir
# depois" da secao 6 do plano) -- isolados aqui, faceis de achar e mudar,
# nunca espalhados pelo codigo.
JANELA_TRADES = 30                # rolling window por CONTAGEM de trade, nao
                                   # calendario -- cadencia varia demais por
                                   # tier (grid opera muito mais que
                                   # SLTP/trailing), contagem fixa normaliza
                                   # o tamanho da amostra entre sistemas
MIN_TRADES_PROVA = 20             # minimo de trades ao vivo pra sair de EM_PROVA
FAIXA_TOLERANCIA_REL = 0.35       # +-35% relativo ao expectancy_r do ledger
FAIXA_TOLERANCIA_ABS_MIN = 0.05   # piso absoluto em R -- evita faixa
                                   # degenerada quando o baseline do ledger
                                   # ja e perto de zero
N_STREAK_REBAIXAR = 5             # avaliacoes seguidas abaixo da faixa
N_STREAK_PROMOVER = 5             # avaliacoes seguidas acima da faixa
ALOCACAO_REDUZIDA_EM_PROVA = 0.5  # fracao do peso normal enquanto EM_PROVA

_TAG_HTML = re.compile(r"<[^>]+>")
_LINHA_HTML = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELULA_HTML = re.compile(r'<td([^>]*)>(.*?)</td>', re.S)
_CLASSE_HIDDEN = re.compile(r'class\s*=\s*"[^"]*\bhidden\b[^"]*"')

ASSET_CLASS_OF: dict[str, str] = {
    ativo: classe for classe, ativos in ASSETS.items() for ativo in ativos
}


# ------------------------------------------------------------- magic -> combo


def tabela_magics() -> dict[int, str]:
    """magic -> chave ("simbolo__sistema__variante", mesmo formato de
    _sets_certificados()/sets_implantados.json em dashboard_campanha.py).

    Le MANIFESTO_SISTEMAS.csv (ready_library.BIBLIOTECA) como fonte
    primaria: e o que generate_system_sets.py REALMENTE escreveu na ultima
    geracao, nunca desalinha da biblioteca publicada. So recomputa via
    magic_estavel() (mesmo loop de generate_system_sets.main(), chave
    "{classe}/{simbolo}/{sistema}/{lado}_{variante}") se o CSV nao existir
    -- confirmado 2026-08-20 que os dois batem, byte a byte, contra os 4
    magics reais vistos ao vivo na conta 77034660.
    """
    caminho = ready_library.BIBLIOTECA / "MANIFESTO_SISTEMAS.csv"
    if caminho.is_file():
        return _tabela_magics_do_manifesto(caminho)
    return _tabela_magics_recomputada()


def _tabela_magics_do_manifesto(caminho: Path) -> dict[int, str]:
    import csv
    tabela: dict[int, str] = {}
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        for linha in csv.DictReader(fh, delimiter=";"):
            try:
                magic = int(linha["MagicNumber"])
            except (KeyError, ValueError):
                continue
            simbolo = linha.get("Symbol", "")
            sistema = linha.get("System", "")
            lado = linha.get("Side", "")
            variante_tipo = linha.get("Variant", "")
            variante = f"{lado}_{variante_tipo}"
            tabela[magic] = f"{simbolo}__{sistema}__{variante}"
    return tabela


def _tabela_magics_recomputada() -> dict[int, str]:
    """Mesmo loop de generate_system_sets.py:main() (classe -> ativo ->
    sistema -> lado -> ichimoku), so pra achar o magic de cada combo -- nao
    gera set nenhum. So usado quando o manifesto nao existe no disco."""
    usados: dict[int, str] = {}
    tabela: dict[int, str] = {}
    for classe, ativos in ASSETS.items():
        for ativo in ativos:
            for sistema in SYSTEMS:
                lados = ("BOTH",) if sistema.code in _BILATERAL else ("BUY", "SELL")
                for lado in lados:
                    for ichimoku in (False, True):
                        tipo_variante = "ICHIMOKU" if ichimoku else "MULTI"
                        variante = f"{lado}_{tipo_variante}"
                        chave_magic = f"{classe}/{ativo}/{sistema.code}/{variante}"
                        magic = _magic_estavel(chave_magic, usados)
                        tabela[magic] = f"{ativo}__{sistema.code}__{variante}"
    return tabela


def _magic_estavel(chave: str, usados: dict[int, str]) -> int:
    """Copia de generate_system_sets.magic_estavel() -- duplicado aqui de
    proposito (nao importado) porque o fallback so roda quando o modulo
    principal nao pode gerar o manifesto; ver seu docstring pra motivo do
    hash e da resolucao de colisao."""
    bruto = hashlib.blake2s(chave.encode("utf-8"), digest_size=8).digest()
    magic = MAGIC_BASE + int.from_bytes(bruto, "big") % MAGIC_SPAN
    while magic in usados and usados[magic] != chave:
        magic = MAGIC_BASE + (magic - MAGIC_BASE + 1) % MAGIC_SPAN
    usados[magic] = chave
    return magic


try:
    from generate_system_sets import BILATERAL as _BILATERAL
except ImportError:
    _BILATERAL = set()


def combo_do_magic(magic: int | None, tabela: dict[int, str]) -> str | None:
    """None pra magic None/0/desconhecido -- "nao sei" ou "nao e nosso",
    nunca um erro. Confirmado ao vivo, 2026-08-20: ordem manual/mobile tem
    magic=0 e comentario vazio (rastreado o duplicado EURGBP dessa forma)."""
    if not magic:
        return None
    return tabela.get(magic)


# --------------------------------------------------------------- ingestao


def historico_mt5(dias: int = 90):
    """PRIMARIA. mt5.initialize() sem path e sem fechar terminal -- mesmo
    padrao SEGURO de calc_capital_base.py (ja rodado contra esta conta real,
    2026-08-19), ao contrario de mt5_runner.fechar_terminal()/
    garantir_terminal_livre(fechar=True), que da taskkill e mataria a EA ao
    vivo no meio de uma cesta aberta. NUNCA usar esse segundo padrao aqui.

    mt5.history_deals_get() ja traz magic direto da API (sem depender de
    coluna nenhuma configurada no relatorio), agrupado por position_id (uma
    posicao pode ter varios deals parciais -- soma-se o lucro, fica com o
    primeiro tempo de entrada e o ultimo de saida).

    None se o pacote MetaTrader5 nao estiver instalado ou o terminal nao
    responder (ex: dashboard rodando numa maquina sem terminal ao vivo) --
    quem chama cai pro relatorio HTML nesse caso.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize():
        return None
    try:
        from datetime import datetime, timedelta
        deals = mt5.history_deals_get(
            datetime.now() - timedelta(days=dias), datetime.now())
        if deals is None:
            return None
        por_posicao: dict[int, dict] = {}
        for d in deals:
            if d.entry not in (0, 1):  # 0=IN, 1=OUT -- ignora balanco/credito
                continue
            reg = por_posicao.setdefault(d.position_id, {
                "ticket": d.position_id, "simbolo": d.symbol,
                "magic": d.magic, "tempo_abertura": None,
                "tempo_fechamento": None, "lucro": 0.0, "volume": 0.0})
            reg["lucro"] += d.profit + d.commission + d.swap
            tempo = pd.to_datetime(d.time, unit="s")
            if d.entry == 0:
                reg["tempo_abertura"] = tempo
                reg["volume"] = d.volume
                if d.magic:
                    reg["magic"] = d.magic
            else:
                reg["tempo_fechamento"] = tempo
        linhas = [r for r in por_posicao.values() if r["tempo_fechamento"] is not None]
        if not linhas:
            return None
        return pd.DataFrame(linhas)
    finally:
        mt5.shutdown()


def ler_relatorio_historico(caminho_htm: Path):
    """SECUNDARIA/portatil. Parser IRMAO de auto_manager_live.
    _trades_do_relatorio() -- formato DIFERENTE (Trade History Report do
    History tab da conta real, "Salvar como Relatorio", nao o relatorio do
    Strategy Tester que aquela funcao le), nao da pra reusar direto:

    - UTF-16 com BOM (confirmado no arquivo real colado 2026-08-20; usa
      deteccao por BOM como optimize_sets.ler_relatorio(), nao encoding
      fixo, porque este formato nao e so gerado por este codebase).
    - Secao "Positions" achada pela PRIMEIRA <th colspan="14"> depois do
      bloco Name/Account/Company/Date -- mesma tecnica estrutural de
      _trades_do_relatorio, robusta a idioma do terminal.
    - Celulas com class="hidden" (comentario/custo, display:none no
      navegador mas presentes no HTML bruto) sao DESCARTADAS antes de
      indexar -- achado inspecionando o arquivo real: uma
      <td class="hidden" colspan="8"> aparece entre Type e Volume em toda
      linha de dado, mas NAO na linha de cabecalho, entao indexar por
      posicao sem filtrar desliza a partir da 5a coluna.
    - Depois de filtrar, indexa pela ORDEM do cabecalho lido (nao nome
      isolado: "Time" e "Price" aparecem duas vezes cada, abertura e
      fechamento -- usa a 1a e a 2a ocorrencia de cada). Coluna "Magic
      Number" so existe se o dono tiver ligado no customizador de coluna do
      MT5 (confirmado: o arquivo real testado 2026-08-20 NAO tinha) -- fica
      magic=None (nao 0) quando ausente: None e "nao sei", 0 e "sabidamente
      nao e nosso".

    None se o arquivo nao existir/nao tiver a secao Positions.
    """
    try:
        bruto = caminho_htm.read_bytes()
    except OSError:
        return None
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = bruto.decode("utf-16")
    else:
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            texto = bruto.decode("cp1252", errors="replace")

    m_secao = re.search(
        r'<th colspan="14"[^>]*>\s*<div[^>]*>\s*<b>Positions</b>', texto)
    if not m_secao:
        return None
    resto = texto[m_secao.end():]
    m_fim = re.search(r'<th colspan="14"', resto)
    secao = resto[:m_fim.start()] if m_fim else resto

    linhas_html = _LINHA_HTML.findall(secao)
    if len(linhas_html) < 2:
        return None

    def celulas_visiveis(linha_html: str) -> list[str]:
        saida = []
        for atributos, conteudo in _CELULA_HTML.findall(linha_html):
            if _CLASSE_HIDDEN.search(atributos):
                continue
            saida.append(html_unescape(_TAG_HTML.sub("", conteudo)).strip())
        return saida

    cabecalho = celulas_visiveis(linhas_html[0])
    if not cabecalho:
        return None
    idx_magic = next(
        (i for i, nome in enumerate(cabecalho) if "magic" in nome.lower()),
        None)
    ocorrencias_time = [i for i, nome in enumerate(cabecalho) if nome == "Time"]
    ocorrencias_price = [i for i, nome in enumerate(cabecalho) if nome == "Price"]
    idx_symbol = cabecalho.index("Symbol") if "Symbol" in cabecalho else None
    idx_type = cabecalho.index("Type") if "Type" in cabecalho else None
    idx_volume = cabecalho.index("Volume") if "Volume" in cabecalho else None
    idx_position = cabecalho.index("Position") if "Position" in cabecalho else None
    if idx_symbol is None or len(ocorrencias_time) < 2:
        return None

    registros = []
    for linha_html in linhas_html[1:]:
        celulas = celulas_visiveis(linha_html)
        if len(celulas) != len(cabecalho) or not celulas[idx_symbol]:
            continue
        tempo_abertura = pd.to_datetime(celulas[ocorrencias_time[0]], errors="coerce")
        tempo_fechamento = pd.to_datetime(celulas[ocorrencias_time[1]], errors="coerce")
        lucro_txt = celulas[-1]  # Profit e sempre a ultima coluna (colspan=2)
        lucro = pd.to_numeric(
            lucro_txt.replace(" ", "").replace(",", "."), errors="coerce")
        if pd.isna(tempo_abertura) or pd.isna(lucro):
            continue
        registros.append({
            "ticket": celulas[idx_position] if idx_position is not None else None,
            "simbolo": celulas[idx_symbol],
            "tipo": celulas[idx_type] if idx_type is not None else None,
            "volume": pd.to_numeric(celulas[idx_volume], errors="coerce")
                     if idx_volume is not None else None,
            "tempo_abertura": tempo_abertura,
            "tempo_fechamento": (tempo_fechamento
                                 if pd.notna(tempo_fechamento) else None),
            "magic": (pd.to_numeric(celulas[idx_magic], errors="coerce")
                     if idx_magic is not None else None),
            "lucro": lucro,
        })
    if not registros:
        return None
    return pd.DataFrame(registros)


def html_unescape(texto: str) -> str:
    import html
    return html.unescape(texto)


# ---------------------------------------------------------- estado / exclusao


def _carregar_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return padrao


def _salvar_json(caminho: Path, dado) -> None:
    caminho.write_text(json.dumps(dado, ensure_ascii=False, indent=2),
                       encoding="utf-8")


def carregar_excluidos() -> set[str]:
    """Tickets marcados A MAO pelo dono como ruido de infraestrutura (nao
    conta como amostra pro rebaixamento) -- em_prova_excluidos.json, lista
    plana, mesmo padrao de sets_implantados.json.

    Nao existe deteccao automatica: o "erro" do ledger (campanha.py:
    feitos()) so existe porque o CODIGO sabe que travou (subprocess.
    TimeoutExpired, sem JSON final) -- trade ao vivo nao carrega esse
    sinal. Fingir um classificador automatico aqui seria confianca que o
    dado nao sustenta; melhor deixar explicito e manual."""
    return set(str(t) for t in _carregar_json(EXCLUIDOS_PATH, []))


def _carregar_estado() -> dict[str, dict]:
    return _carregar_json(ESTADO_PATH, {})


def _salvar_estado(estado: dict[str, dict]) -> None:
    _salvar_json(ESTADO_PATH, estado)


# ------------------------------------------------------------------ status


def status_ao_vivo(chave: str, trades_live: pd.DataFrame,
                   ledger_path: Path = LEDGER,
                   estado: dict[str, dict] | None = None) -> dict:
    """Classifica um combo implantado em 5 estados, comparando o lucro
    medio por trade ao vivo (janela movel de JANELA_TRADES) contra o
    expectancy_r OOS do ledger PRA ESTE COMBO ESPECIFICO (nunca media de
    tier -- mesmo motivo do desempate por combo individual da secao 6).

    trades_live: DataFrame ja filtrado pra este combo (ver combo_do_magic),
    com colunas tempo_fechamento/lucro no minimo, ordenado por tempo.

    SEM_BASELINE   ledger nao tem expectancy_r pra este combo (comum:
                   07_GRID_SEPARATE/10_DALEMBERT/11_SIGNAL_ONLY nunca medem
                   R -- lote fixo/monetario, nao Fixed-R -- ver
                   generate_system_sets.py r_capable)
    EM_PROVA       baseline existe, mas < MIN_TRADES_PROVA trades vivos
    DENTRO_DA_FAIXA / REBAIXAR / PROMOVER
                   baseline existe, trades suficientes, streak de N
                   avaliacoes fora da faixa (estado anterior persiste o
                   streak entre chamadas -- ver _carregar_estado)
    """
    simbolo, sistema, variante = chave.split("__")
    baseline = ready_library.metricas_do_ledger(ledger_path).get(
        (simbolo, sistema, variante), {})
    expectancy_ledger = baseline.get("expectancy_r")

    excluidos = carregar_excluidos()
    validos = trades_live[~trades_live.get(
        "ticket", pd.Series(dtype=str)).astype(str).isin(excluidos)]
    n_trades = len(validos)

    if expectancy_ledger is None:
        return {"chave": chave, "status": "SEM_BASELINE",
               "trades_vividos": n_trades, "expectancy_ledger": None,
               "lucro_medio_live": None}

    if n_trades < MIN_TRADES_PROVA:
        return {"chave": chave, "status": "EM_PROVA",
               "trades_vividos": n_trades, "expectancy_ledger": expectancy_ledger,
               "lucro_medio_live": None,
               "alocacao": ALOCACAO_REDUZIDA_EM_PROVA}

    janela = validos.tail(JANELA_TRADES)
    lucro_medio_live = float(janela["lucro"].mean())

    faixa = max(abs(expectancy_ledger) * FAIXA_TOLERANCIA_REL,
               FAIXA_TOLERANCIA_ABS_MIN)
    # NOTA (gap conhecido, ver plano): comparando tendencia de lucro medio
    # $-por-trade contra expectancy_r em R -- nao e a mesma unidade. O
    # ledger mede R sob Fixed-R (CapitalBaseR); a entrega sai em
    # PositionSizeMode=Percentage. Conversao exata precisa confirmar a
    # formula contra MM_Size_* da EA antes de tratar como R literal --
    # primeiro corte usa o SINAL (acima/dentro/abaixo) da comparacao, nao
    # o valor absoluto, que e o que a classificacao abaixo faz.
    anterior = (estado or {}).get(chave, {})
    streak_abaixo = anterior.get("streak_abaixo", 0)
    streak_acima = anterior.get("streak_acima", 0)
    if lucro_medio_live < expectancy_ledger - faixa:
        streak_abaixo += 1
        streak_acima = 0
    elif lucro_medio_live > expectancy_ledger + faixa:
        streak_acima += 1
        streak_abaixo = 0
    else:
        streak_abaixo = streak_acima = 0

    if streak_abaixo >= N_STREAK_REBAIXAR:
        status = "REBAIXAR"
    elif streak_acima >= N_STREAK_PROMOVER:
        status = "PROMOVER"
    else:
        status = "DENTRO_DA_FAIXA"

    return {"chave": chave, "status": status, "trades_vividos": n_trades,
           "expectancy_ledger": expectancy_ledger,
           "lucro_medio_live": lucro_medio_live,
           "streak_abaixo": streak_abaixo, "streak_acima": streak_acima}
