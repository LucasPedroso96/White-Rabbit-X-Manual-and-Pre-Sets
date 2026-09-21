# -*- coding: utf-8 -*-
"""Vigia de SAUDE dos dois terminais (original = calibracao/revalidacao,
clone = campanha oficial). Pedido do dono, 2026-09-21: "monitorando sempre os
dois terminais". So emite evento quando ha ANOMALIA (silencio = saudavel);
o evento vai pra auditoria_eventos.log (o Monitor acorda o revisor).

Anomalias:
  OCIOSO    -- terminal sem nenhum driver (sweep/revalidador/campanha) vivo por
               2 checagens seguidas (o dono ja pegou terminal parado sem aviso);
  TRAVADO   -- driver vivo e terminal aberto, mas agentes ~sem CPU e log parado
               por 3 checagens seguidas;
  CRITERIO_ZERADO -- otimizacao genetica em curso com "Best result 0" nas
               ultimas 6 geracoes (o OnTester zerou: busca as cegas -- achado
               2026-09-21, input_end_date velho no WFA);
  MEMORIA   -- memoria fisica livre < 3 GB (o crash do LSTM da Zeus, 09-17/18,
               foi vazamento de memoria).
Cada tipo por terminal repete no maximo a cada 60 min.

    python vigia_saude.py            # loop (5 min)
    python vigia_saude.py --uma-vez  # uma checagem, imprime o que emitiria
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EVENTOS = AQUI / "auditoria_eventos.log"
MEIO = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal")
TERMINAIS = {
    "ORIGINAL": {
        "instalacao": "RoboForex MT5 Terminal (WhiteRabbitEA)",
        "dados": MEIO / "D2A36B4A61A508797F5C460B1F34DC5D",
        "drivers": re.compile(r"sweep_formulas\.py|revalidar_aprovados\.py"),
    },
    "CLONE": {
        "instalacao": "MT5_Optimizer2",
        "dados": MEIO / "4A85BF7BB91E709E95066E8432253C88",
        "drivers": re.compile(r"campanha\.py"),
    },
}
MEMORIA_MIN_MB = 3000
COOLDOWN_MIN = 60
INTERVALO = 300
_BEST = re.compile(r"Best result ([-\d.eE+]+) produced at generation (\d+)")

_PS = r"""
$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|terminal64|metatester64' } |
     Select-Object ProcessId, Name, ExecutablePath, CommandLine
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-Process metatester64 -ErrorAction SilentlyContinue | Select-Object Id, CPU, Path
[pscustomobject]@{ procs = @($p); livre_mb = [int]($os.FreePhysicalMemory/1024); cpu = @($cpu) } |
    ConvertTo-Json -Depth 4 -Compress
"""


def snapshot() -> dict:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", _PS],
                         capture_output=True, text=True, timeout=90)
    return json.loads(out.stdout)


def cpu_agentes(s1: dict, s2: dict, dt: float, chave: str) -> tuple[int, float]:
    """(n de agentes da instalacao `chave`, uso medio de CPU em % de 1 nucleo)."""
    a1 = {c["Id"]: c["CPU"] for c in s1["cpu"] if chave in (c.get("Path") or "")}
    deltas = [(c["CPU"] - a1[c["Id"]]) / dt * 100 for c in s2["cpu"]
              if chave in (c.get("Path") or "") and c["Id"] in a1
              and c["CPU"] is not None and a1[c["Id"]] is not None]
    return len(deltas), (sum(deltas) / len(deltas) if deltas else 0.0)


def ultimas_geracoes(dados: Path, n: int = 8) -> tuple[list[str], float]:
    """Ultimos `n` 'Best result' do log do tester (le so o fim do arquivo) e a
    idade (min) da ultima escrita."""
    logs = sorted((dados / "Tester" / "logs").glob("*.log"))
    if not logs:
        return [], 1e9
    f = logs[-1]
    idade = (time.time() - f.stat().st_mtime) / 60
    tam = f.stat().st_size
    ini = max(0, tam - 600_000) & ~1  # alinhado em 2 bytes (UTF-16)
    with f.open("rb") as fh:
        fh.seek(ini)
        texto = fh.read().decode("utf-16-le", errors="replace")
    achados = [m.group(1) for m in _BEST.finditer(texto)]
    return achados[-n:], idade


def idade_log_principal(dados: Path) -> float:
    logs = sorted((dados / "logs").glob("*.log"))
    return (time.time() - logs[-1].stat().st_mtime) / 60 if logs else 1e9


class Vigia:
    def __init__(self) -> None:
        self.ocioso = {k: 0 for k in TERMINAIS}
        self.parado = {k: 0 for k in TERMINAIS}
        self.ultimo_alerta: dict[tuple[str, str], float] = {}

    def _pode(self, terminal: str, tipo: str) -> bool:
        agora = time.time()
        if agora - self.ultimo_alerta.get((terminal, tipo), 0) < COOLDOWN_MIN * 60:
            return False
        self.ultimo_alerta[(terminal, tipo)] = agora
        return True

    def checar(self) -> list[str]:
        s1 = snapshot()
        t0 = time.time()
        time.sleep(10)
        s2 = snapshot()
        dt = time.time() - t0
        eventos: list[str] = []
        hora = datetime.now().strftime("%d/%m %H:%M")
        if s2["livre_mb"] < MEMORIA_MIN_MB and self._pode("MAQUINA", "MEMORIA"):
            eventos.append(f"SAUDE MEMORIA [{hora}] memoria fisica livre "
                           f"{s2['livre_mb']} MB (< {MEMORIA_MIN_MB}): risco de "
                           "crash (ver o vazamento do treino LSTM da Zeus)")
        for nome, cfg in TERMINAIS.items():
            procs = s2["procs"]
            drivers = [p for p in procs if p["Name"] == "python.exe"
                       and cfg["drivers"].search(p.get("CommandLine") or "")]
            terminais = [p for p in procs if p["Name"] == "terminal64.exe"
                         and cfg["instalacao"] in (p.get("ExecutablePath") or "")]
            n_ag, cpu = cpu_agentes(s1, s2, dt, cfg["instalacao"])
            # OCIOSO: nenhum driver vivo (duas checagens seguidas)
            self.ocioso[nome] = self.ocioso[nome] + 1 if not drivers else 0
            if self.ocioso[nome] >= 2 and self._pode(nome, "OCIOSO"):
                eventos.append(f"SAUDE {nome} OCIOSO [{hora}] nenhum "
                               "sweep/revalidador/campanha vivo neste terminal "
                               "por >= 5 min: esta parado sem trabalho")
            # TRAVADO: driver + terminal vivos, agentes sem CPU e log parado
            if drivers and terminais:
                sem_cpu = n_ag > 0 and cpu < 10
                log_parado = min(idade_log_principal(cfg["dados"]),
                                 ultimas_geracoes(cfg["dados"])[1]) > 20
                self.parado[nome] = (self.parado[nome] + 1
                                     if (sem_cpu and log_parado) else 0)
            else:
                self.parado[nome] = 0
            if self.parado[nome] >= 3 and self._pode(nome, "TRAVADO"):
                eventos.append(f"SAUDE {nome} TRAVADO? [{hora}] terminal aberto, "
                               f"agentes a {cpu:.0f}% de CPU e logs parados "
                               "ha >= 15 min")
            # CRITERIO_ZERADO: genetico em curso com Best result 0
            gens, idade = ultimas_geracoes(cfg["dados"])
            if (len(gens) >= 6 and idade < 10 and n_ag > 0 and cpu > 30
                    and all(float(g) == 0.0 for g in gens[-6:])
                    and self._pode(nome, "CRITERIO_ZERADO")):
                eventos.append(f"SAUDE {nome} CRITERIO_ZERADO [{hora}] otimizacao "
                               "em curso com 'Best result 0' nas ultimas 6 "
                               "geracoes: o OnTester zerou (input_end_date "
                               "velho?) e o genetico evolui as cegas. Conferir "
                               "qual etapa esta rodando (formula 1 num sistema "
                               "sem grid zera legitimamente)")
        return eventos


def emitir(txt: str) -> None:
    print(txt, flush=True)
    with EVENTOS.open("a", encoding="utf-8") as fh:
        fh.write(txt + "\n")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--uma-vez", action="store_true")
    args = ap.parse_args()
    v = Vigia()
    if args.uma_vez:
        s = snapshot()
        print(f"memoria livre: {s['livre_mb']} MB")
        time.sleep(1)
        for nome, cfg in TERMINAIS.items():
            gens, idade = ultimas_geracoes(cfg["dados"])
            drivers = [p["CommandLine"][-60:] for p in s["procs"]
                       if p["Name"] == "python.exe"
                       and cfg["drivers"].search(p.get("CommandLine") or "")]
            print(f"{nome}: drivers={len(drivers)} | ultimas geracoes={gens[-6:]} "
                  f"(log ha {idade:.0f} min) | log principal ha "
                  f"{idade_log_principal(cfg['dados']):.0f} min")
        for e in v.checar():
            print("EVENTO:", e)
        return 0
    emitir(f"SAUDE vigia armado [{datetime.now():%d/%m %H:%M}]: monitorando "
           "ORIGINAL e CLONE a cada 5 min (so avisa em anomalia).")
    while True:
        try:
            for e in v.checar():
                emitir(e)
        except Exception as exc:  # silencio nao pode parecer saude
            emitir(f"SAUDE ERRO no vigia_saude (segue tentando): {exc!r}")
        time.sleep(INTERVALO)


if __name__ == "__main__":
    sys.exit(main())
