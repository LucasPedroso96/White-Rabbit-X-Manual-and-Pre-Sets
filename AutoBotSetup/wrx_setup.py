# -*- coding: utf-8 -*-
"""White Rabbit X - Instalador automatico para o comprador.

O comprador baixa o EA no MQL5 Market, mas os sets ficam de fora: o Market
entrega o .ex5 e nada mais. Ele entao teria de descobrir a pasta de dados do
terminal, copiar 3.738 arquivos no lugar certo, e ainda descobrir sozinho que
o corretor dele chama EURUSD de "EURUSDm" -- porque um .set com o simbolo
errado simplesmente nao carrega.

Este instalador faz isso: acha o terminal, copia os sets, le a conta e ajusta
simbolo, lote e capital base ao corretor do comprador.

Roda sem Python instalado (empacotado com PyInstaller) e sem argumentos: e
para alguem que comprou um robo, nao para um programador.

Alem dos sets, tambem instala o Autobot -- o mesmo painel de controle
(dashboard + campanhas de otimizacao) usado internamente -- com um Python
proprio embutido (pasta "AutobotRuntime" ao lado do instalador ou
empacotada no exe), entao o comprador tambem nao precisa de Python
instalado pra isso.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VERSAO = "1.12"
TELEGRAM = "https://t.me/MrRabbit_MT5"


def titulo(texto: str) -> None:
    print()
    print("=" * 66)
    print(f"  {texto}")
    print("=" * 66)


def desbloquear(destino: Path) -> None:
    """Remove a marca "veio de outro computador" (NTFS Zone.Identifier) de
    tudo que o instalador acabou de copiar.

    Achado do dono, 2026-08-08: cliente instalando de verdade viu o Windows
    pedir pra "desbloquear" o .bat manualmente (Propriedades > Desbloquear)
    antes de rodar -- SmartScreen marca qualquer arquivo que passou por
    download/rede com esse fluxo de zona, .bat nao aceita assinatura
    Authenticode (isso e so pra .exe/.dll, e exige certificado comprado, so
    o dono pode fazer isso). O que da pra fazer sem certificado: o Windows
    grava a marca como um Alternate Data Stream (NOME:Zone.Identifier) --
    apagar esse stream especifico e equivalente a marcar "Desbloquear" na
    caixa de dialogo, sem o comprador precisar fazer nada. So funciona em
    volume NTFS (sempre e o caso do Windows); FileNotFoundError e o normal
    quando o arquivo nunca teve a marca.
    """
    alvos = [destino] if destino.is_file() else destino.rglob("*")
    for item in alvos:
        if not item.is_file():
            continue
        try:
            os.remove(f"{item}:Zone.Identifier")
        except OSError:
            pass


def tem_o_ea(terminal: Path) -> bool:
    """O White Rabbit X ja foi baixado neste terminal?"""
    experts = terminal / "MQL5" / "Experts"
    if not experts.is_dir():
        return False
    padroes = ("White Rabbit X*.ex5", "Market/**/White Rabbit X*.ex5",
               "**/White Rabbit X*.ex5")
    return any(next(experts.glob(p), None) for p in padroes)


def achar_terminais() -> list[Path]:
    """Pastas de dados do MT5 instaladas na maquina.

    O MetaTrader guarda os dados fora da pasta de instalacao, num diretorio
    cujo nome e um hash -- por isso a busca e por conteudo, nao por nome.

    Quem ja tem o EA baixado vem primeiro: e quase sempre o terminal certo, e
    poupa o comprador de escolher entre instalacoes que ele nem lembra que
    existem. Depois deles, os usados mais recentemente.
    """
    raiz = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if not raiz.is_dir():
        return []
    achados = []
    for pasta in raiz.iterdir():
        if not pasta.is_dir() or not (pasta / "MQL5" / "Experts").is_dir():
            continue
        try:
            recencia = pasta.stat().st_mtime
        except OSError:
            recencia = 0.0
        achados.append((not tem_o_ea(pasta), -recencia, pasta))
    achados.sort()
    return [p for _, _, p in achados]


def descrever(terminal: Path) -> str:
    origem = terminal / "origin.txt"
    if origem.exists():
        try:
            texto = origem.read_text(encoding="utf-16").strip()
            return texto or terminal.name
        except Exception:
            pass
    return terminal.name


def escolher(terminais: list[Path]) -> Path | None:
    if not terminais:
        return None
    if len(terminais) == 1:
        print(f"Terminal encontrado: {descrever(terminais[0])}")
        return terminais[0]
    print("Mais de um MetaTrader encontrado:\n")
    for i, t in enumerate(terminais, 1):
        marca = "  <- White Rabbit X esta aqui" if tem_o_ea(t) else ""
        print(f"  [{i}] {descrever(t)}{marca}")
    while True:
        escolha = input("\nQual usar? (numero, ou Enter para o 1) ").strip()
        if not escolha:
            return terminais[0]
        if escolha.isdigit() and 1 <= int(escolha) <= len(terminais):
            return terminais[int(escolha) - 1]
        print("Numero invalido.")


def copiar_sets(origem: Path, terminal: Path) -> int:
    destino = terminal / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets"
    destino.mkdir(parents=True, exist_ok=True)
    total = 0
    for arquivo in origem.rglob("*"):
        if not arquivo.is_file():
            continue
        alvo = destino / arquivo.relative_to(origem)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
        total += 1
    desbloquear(destino)
    return total


def conectar_mt5() -> tuple[object | None, str]:
    """Devolve (modulo, motivo). O motivo separa 'faltou biblioteca' de
    'terminal fechado' -- sao problemas diferentes, com solucoes diferentes,
    e dizer o errado faz o comprador procurar no lugar errado."""
    try:
        import MetaTrader5 as mt5
    except ImportError as erro:
        return None, f"biblioteca ausente no instalador ({erro})"
    if not mt5.initialize():
        return None, f"terminal fechado ou sem login ({mt5.last_error()})"
    return mt5, ""


def simbolo_do_corretor(mt5, base: str) -> str | None:
    """Encontra o nome real, com o sufixo que o corretor usa."""
    if mt5.symbol_info(base):
        return base
    candidatos = [s.name for s in mt5.symbols_get()
                  if re.fullmatch(rf"{re.escape(base)}[.\-_a-zA-Z0-9]*", s.name)]
    return min(candidatos, key=len) if candidatos else None


def ajustar_sets(mt5, pasta: Path) -> dict:
    """Reescreve simbolo e lote conforme o corretor do comprador."""
    relatorio = {"ajustados": 0, "sufixos": {}, "ausentes": [], "lotes": {}}
    ativos = {d.name for c in pasta.iterdir() if c.is_dir()
              for d in c.iterdir() if d.is_dir()}

    mapa: dict[str, str] = {}
    specs: dict[str, dict] = {}
    for base in sorted(ativos):
        real = simbolo_do_corretor(mt5, base)
        if real is None:
            relatorio["ausentes"].append(base)
            continue
        mapa[base] = real
        if real != base:
            relatorio["sufixos"][base] = real
        info = mt5.symbol_info(real)
        if info:
            specs[base] = {"min": info.volume_min, "passo": info.volume_step}

    for caminho in pasta.rglob("*.set"):
        partes = caminho.relative_to(pasta).parts
        if len(partes) < 2:
            continue
        ativo = partes[1]
        if ativo not in mapa:
            continue
        linhas = caminho.read_text(encoding="utf-16").splitlines()
        saida, mudou = [], False
        for linha in linhas:
            if linha.startswith("NomedaEstrategia=") and mapa[ativo] != ativo:
                linha = linha.replace(ativo, mapa[ativo])
                mudou = True
            elif linha.startswith("PositionSizeValue="):
                m = re.match(r"^PositionSizeValue=([^|]+)\|\|", linha)
                spec = specs.get(ativo)
                if m and spec:
                    try:
                        atual = float(m.group(1))
                    except ValueError:
                        atual = 0.0
                    # So mexe no lote fixo: valores >= 1 sao percentual de
                    # risco do Fixed-R e nao devem virar volume.
                    if 0 < atual < 1 and atual < spec["min"]:
                        novo = f"{spec['min']:g}"
                        linha = (f"PositionSizeValue={novo}||{novo}||"
                                 f"{spec['passo']:g}||{novo}||N")
                        mudou = True
                        relatorio["lotes"][ativo] = spec["min"]
            saida.append(linha)
        if mudou:
            caminho.write_text("\r\n".join(saida) + "\r\n", encoding="utf-16")
            relatorio["ajustados"] += 1
    return relatorio


def copiar_autobot(origem: Path, icone: Path | None = None) -> Path | None:
    """Copia o Autobot (dashboard + Python embutido) pra pasta do usuario.

    origem e a pasta "AutobotRuntime" (python-embed/, Autobot/,
    Iniciar_Dashboard.bat) vinda junto do instalador -- mesma logica de
    precedencia de copiar_sets(): pasta ao lado do exe tem prioridade
    sobre a empacotada, pra dar pra atualizar sem gerar instalador novo.

    O icone (se existir) e copiado junto: o atalho aponta pra ele DENTRO
    do destino permanente, nunca pro temporario do PyInstaller -- aquele
    some assim que o instalador termina.
    """
    if not origem.is_dir():
        return None
    destino = Path(os.environ.get("USERPROFILE", str(Path.home()))) \
        / "Documents" / "White Rabbit X - Autobot"
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)
    if icone and icone.is_file():
        shutil.copy2(icone, destino / icone.name)
    desbloquear(destino)
    return destino


def criar_atalho(alvo: Path, nome: str, icone: Path | None = None) -> bool:
    """Cria um atalho na area de trabalho, via VBScript (sem depender de
    pywin32 -- cscript.exe ja vem em qualquer Windows)."""
    area_trabalho = Path(os.environ.get("USERPROFILE", str(Path.home()))) \
        / "Desktop"
    if not area_trabalho.is_dir():
        return False
    atalho = area_trabalho / f"{nome}.lnk"
    linha_icone = (f'link.IconLocation = "{icone}"\n'
                   if icone and icone.is_file() else "")
    vbs = (
        'Set ws = CreateObject("WScript.Shell")\n'
        f'Set link = ws.CreateShortcut("{atalho}")\n'
        f'link.TargetPath = "{alvo}"\n'
        f'link.WorkingDirectory = "{alvo.parent}"\n'
        f'link.Description = "{nome}"\n'
        f'{linha_icone}'
        'link.Save\n'
    )
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".vbs", delete=False, encoding="utf-8") as f:
        f.write(vbs)
        caminho_vbs = f.name
    try:
        r = subprocess.run(["cscript", "//nologo", caminho_vbs],
                            capture_output=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        os.unlink(caminho_vbs)


def main() -> int:
    titulo(f"White Rabbit X {VERSAO} - Instalacao dos sets")
    print("Este instalador copia os sets de otimizacao para o seu MetaTrader")
    print("e ajusta os arquivos ao seu corretor.\n")
    print("O Expert Advisor em si voce baixa pelo MQL5 Market, na aba")
    print("Terminal > Mercado > Comprados.")

    # Os sets vem embutidos no executavel (sys._MEIPASS, que o PyInstaller
    # extrai num temporario). Uma pasta "Sets" ao lado do .exe tem
    # precedencia: e assim que se entrega uma biblioteca atualizada sem
    # precisar gerar um instalador novo.
    #
    # Atencao: com onefile, __file__ aponta para o temporario, nao para onde o
    # comprador colocou o programa. O caminho ao lado sai de sys.executable.
    ao_lado = (Path(sys.executable).parent if getattr(sys, "frozen", False)
               else Path(__file__).parent)
    origem = ao_lado / "Sets"
    if not origem.is_dir():
        origem = Path(getattr(sys, "_MEIPASS", ao_lado)) / "Sets"
    if not origem.is_dir():
        if not getattr(sys, "frozen", False):
            # Rodando o .py cru (sys.frozen == False): quase sempre e alguem
            # que baixou o ZIP do repositorio no GitHub e caiu direto nesta
            # pasta, achando que "wrx_setup.py" e o instalador. Nao e -- e o
            # CODIGO-FONTE do instalador. A pasta Sets (3.738 arquivos) e o
            # runtime Python embutido ficam de fora do repositorio de
            # proposito (.gitignore) e so existem dentro do .exe empacotado.
            # Achado real, 2026-08-08: cliente reproduziu exatamente isso.
            print("\nERRO: voce esta rodando o codigo-fonte, nao o instalador.")
            print("\n'wrx_setup.py' e o programa-fonte que GERA o instalador --")
            print("baixar o ZIP do GitHub e rodar este arquivo direto nunca vai")
            print("funcionar, porque a pasta 'Sets' nao fica no repositorio")
            print("(sao milhares de arquivos, ela so existe dentro do .exe pronto).")
            print(f"\nBaixe o instalador pronto (arquivo .exe) em: {TELEGRAM}")
        else:
            print("\nERRO: a pasta 'Sets' nao veio junto com o instalador.")
            print(f"Baixe o pacote completo em {TELEGRAM}")
        input("\nEnter para sair.")
        return 1

    # Mesma logica de precedencia do Sets: pasta ao lado do exe tem
    # prioridade sobre a empacotada.
    origem_autobot = ao_lado / "AutobotRuntime"
    if not origem_autobot.is_dir():
        origem_autobot = Path(getattr(sys, "_MEIPASS", ao_lado)) / "AutobotRuntime"
    origem_icone = ao_lado / "wrx_icon.ico"
    if not origem_icone.is_file():
        origem_icone = Path(getattr(sys, "_MEIPASS", ao_lado)) / "wrx_icon.ico"

    titulo("1. Procurando o MetaTrader")
    terminais = achar_terminais()
    if not terminais:
        print("Nenhum MetaTrader 5 encontrado neste computador.")
        print("Abra o terminal ao menos uma vez e rode este instalador de novo.")
        input("\nEnter para sair.")
        return 1
    terminal = escolher(terminais)
    if terminal is None:
        return 1

    titulo("2. Copiando os sets")
    total = copiar_sets(origem, terminal)
    destino = terminal / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets"
    print(f"{total} arquivos copiados para:")
    print(f"  {destino}")

    titulo("3. Ajustando ao seu corretor")
    mt5, motivo = conectar_mt5()
    if mt5 is None:
        print(f"Nao foi possivel ler a conta: {motivo}")
        print("\nOs sets ficaram no padrao — vao funcionar em corretores que")
        print("usam os simbolos sem sufixo (EURUSD, XAUUSD).")
        if "terminal" in motivo:
            print("\nDeixe o MetaTrader ABERTO e logado e rode de novo, para")
            print("que o instalador acerte o sufixo e o lote minimo.")
        else:
            print(f"\nIsso e falha do instalador, nao sua. Avise no {TELEGRAM}")
            print("que sai uma versao corrigida.")
    else:
        conta = mt5.account_info()
        if conta:
            print(f"Conta {conta.login} em {conta.server}")
            print(f"  saldo {conta.balance:.2f} {conta.currency}")
        r = ajustar_sets(mt5, destino)
        print(f"\n{r['ajustados']} sets ajustados.")
        if r["sufixos"]:
            print(f"\nSeu corretor usa sufixo em {len(r['sufixos'])} simbolos:")
            for base_s, real in list(r["sufixos"].items())[:6]:
                print(f"  {base_s} -> {real}")
        if r["lotes"]:
            print(f"\nLote minimo do corretor aplicado em "
                  f"{len(r['lotes'])} ativos.")
        if r["ausentes"]:
            print(f"\nSeu corretor nao oferece {len(r['ausentes'])} ativos "
                  f"da biblioteca:")
            print("  " + ", ".join(r["ausentes"][:12])
                  + (" ..." if len(r["ausentes"]) > 12 else ""))
            print("  Os sets deles ficaram instalados, mas nao vao carregar.")
        registro = {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "versao": VERSAO,
            "terminal": str(terminal),
            **r,
        }
        (destino / "INSTALACAO.json").write_text(
            json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
        mt5.shutdown()

    titulo("4. Instalando o Autobot (painel de controle)")
    pasta_autobot = copiar_autobot(origem_autobot, origem_icone)
    if pasta_autobot is None:
        print("O pacote do Autobot nao veio junto com este instalador --")
        print("so os sets foram instalados. Baixe o pacote completo em")
        print(f"{TELEGRAM} se quiser o painel de campanhas.")
    else:
        print(f"Autobot instalado em:\n  {pasta_autobot}")
        icone_instalado = pasta_autobot / origem_icone.name
        atalho_ok = criar_atalho(
            pasta_autobot / "Iniciar_Dashboard.bat", "White Rabbit X - Autobot",
            icone_instalado if icone_instalado.is_file() else None)
        if atalho_ok:
            print("\nAtalho criado na area de trabalho: "
                  "\"White Rabbit X - Autobot\"")
        else:
            print(f"\nPara abrir o painel: {pasta_autobot / 'Iniciar_Dashboard.bat'}")

    titulo("Pronto")
    print("No Strategy Tester: aba Inputs > Load > escolha um set em")
    print("  Profiles\\Tester\\White_Rabbit_X_Sets\\<classe>\\<ativo>\\<sistema>")
    print("\nComece pelo sistema 01_SLTP do ativo que voce opera.")

    # O comprador precisa saber que recebeu a FASE 1 de um circuito, nao um
    # preset pronto. Sem isso ele abre o arquivo, ve filtros desligados e acha
    # que faltou alguma coisa -- quando na verdade eles estao desligados de
    # proposito, porque filtro so significa algo depois do sinal resolvido.
    titulo("O circuito de otimizacao")
    print("Estes arquivos vem configurados para a FASE 1. A biblioteca nao e")
    print("um conjunto de presets prontos: e o primeiro passo de um circuito,")
    print("e cada fase reduz o que a seguinte precisa procurar.\n")
    print("  fase 1 (o que voce recebeu)  sinal e geometria de saida, em OHLC")
    print("  fase 2                       filtros: MTF, media movel, ADX")
    print("  fase 3                       sessao: spread, horario, dias")
    print("  fase 4                       confirmacao em TICKS REAIS\n")
    # O criterio muda com a fase, e nao e detalhe: filtro REDUZ o numero de
    # operacoes, entao otimizar a fase 2 por lucro total pune justamente o
    # filtro que corta entrada ruim, mesmo melhorando cada entrada restante.
    print("O criterio de otimizacao MUDA a cada fase, e isso importa:\n")
    print("  fase 1   Pessimistic Average Profit    o sinal tem vantagem, ou")
    print("                                         foram poucas operacoes")
    print("                                         felizes?")
    print("  fase 2   Profit per Trade ajustado     qualidade POR OPERACAO --")
    print("           por drawdown                  nao pune o filtro por")
    print("                                         operar menos")
    print("  fase 3   Return Uniformity             filtro de horario existe")
    print("                                         para tirar periodo ruim\n")
    print("Usar o mesmo criterio nas tres fases atrapalha: um filtro que corta")
    print("entrada ruim opera MENOS, e por lucro total ele pontua pior mesmo")
    print("melhorando a qualidade de cada entrada que sobrou.\n")
    print("Os filtros vem DESLIGADOS de proposito. Filtro nao significa nada")
    print("antes do sinal estar resolvido, e deixa-los abertos multiplica o")
    print("espaco de busca por 384 vezes sem trazer informacao nenhuma.")
    print("As faixas deles ja estao escritas no arquivo, marcadas com N --")
    print("a fase 2 e so trocar para Y, voce nao precisa inventar a faixa.\n")
    print("Entre as fases, TRAVE o que descobriu: ponha o valor vencedor nos")
    print("quatro campos e mude a marca para N. Cada trava derruba o espaco")
    print("em ordens de magnitude, e e isso que faz a fase seguinte ser mais")
    print("precisa em vez de mais demorada.")

    # Aviso que muda o resultado, nao apenas conveniencia: medido nesta EA,
    # comparando o mesmo set nos dois modos ao longo de 3 anos, o modo rapido
    # subestima a perda em 3,3x nos sistemas de trailing e em 23x no grid --
    # sempre para o lado otimista. So SL/TP fixo fica dentro de 3%. Quem nao
    # souber disso vai otimizar em cima de um caminho de preco que nao existiu.
    titulo("IMPORTANTE: modo de modelagem")
    print("Na aba Settings do Strategy Tester, campo Modeling:")
    print("\n  'Every tick based on real ticks'  <- use este")
    print("  'OHLC 1 minute'                    <- so para 01_SLTP e 02_SLTP_ORGANIC")
    print("\nOs demais sistemas dependem de QUANDO o preco tocou cada nivel")
    print("dentro da barra. O modo OHLC interpola isso e suaviza justamente as")
    print("excursoes que derrubariam um trailing ou uma perna de grid: o")
    print("resultado sai melhor do que a realidade, nao pior.")
    print("\nOs sistemas 07 e 08 (grid) exigem conta HEDGING. Em conta netting")
    print("as pernas se anulam e o sistema nao funciona como projetado.")

    print(f"\nDuvidas e atualizacoes: {TELEGRAM}")
    input("\nEnter para sair.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(1)
    except Exception as erro:  # noqa: BLE001 - o comprador nao ve traceback
        print(f"\nERRO inesperado: {erro}")
        print(f"Mande esta mensagem no {TELEGRAM} que a gente resolve.")
        input("\nEnter para sair.")
        sys.exit(1)
