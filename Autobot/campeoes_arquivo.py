# -*- coding: utf-8 -*-
"""Arquivamento/rollback de campeoes (VALIDADO_*.set), inspirado no
deploy.py do Zeus -- achado direto na pele hoje (2026-08-30): fiz um
backup manual (.bak_ml_pilot) do template do 12_GRID_INVERSO antes de
mexer nele pro piloto de ML, e precisei restaurar dele minutos depois. Sem
esse habito manual, um campeao pior promovido por engano (ou um bug no
gate) apagaria o unico registro do que estava rodando antes, sem
historico nenhum pra reverter.

Mesmo principio do Zeus: arquiva ANTES de sobrescrever, versoes numeradas
sequenciais (nunca reusa numero -- um rollback tambem vira uma versao
nova), metadata junto (quando, o registro do ledger daquele momento).

Uso:
    python campeoes_arquivo.py --listar --sistema 12_GRID_INVERSO \
        --simbolo XAUUSD --variante BUY_MULTI
    python campeoes_arquivo.py --rollback --sistema 12_GRID_INVERSO \
        --simbolo XAUUSD --variante BUY_MULTI [--versao N]
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import ready_library

AQUI = Path(__file__).resolve().parent
ARQUIVO_CAMPEOES = AQUI / "campeoes_arquivados"


def _pasta_combo(sistema: str, simbolo: str, variante: str) -> Path:
    return ARQUIVO_CAMPEOES / f"{simbolo.replace('.', '_')}__{sistema}__{variante}"


def _versoes(pasta: Path) -> list[int]:
    if not pasta.is_dir():
        return []
    return sorted(int(p.name) for p in pasta.iterdir() if p.is_dir() and p.name.isdigit())


def arquivar_campeao_anterior(sistema: str, simbolo: str, variante: str,
                              destino: Path) -> int | None:
    """Copia o VALIDADO_*.set ATUAL (prestes a ser sobrescrito) pra uma
    versao numerada nova, com o registro do ledger daquele momento
    junto. So arquiva se `destino` de fato existir -- combo novo (sem
    campeao anterior) nao tem o que arquivar. Devolve o numero da versao,
    ou None se nao havia nada pra arquivar.
    """
    if not destino.exists():
        return None
    pasta = _pasta_combo(sistema, simbolo, variante)
    pasta.mkdir(parents=True, exist_ok=True)
    nova_versao = (_versoes(pasta)[-1] + 1) if _versoes(pasta) else 1
    pasta_versao = pasta / str(nova_versao)
    pasta_versao.mkdir()
    shutil.copy2(destino, pasta_versao / destino.name)

    simbolo_norm = simbolo.replace(".", "_")
    registro = ready_library.metricas_do_ledger(ready_library.LEDGER).get(
        (simbolo_norm, sistema, variante), {})
    meta = {"versao": nova_versao,
           "arquivado_em": datetime.now().isoformat(timespec="seconds"),
           "arquivo_original": destino.name, "ledger": registro}
    (pasta_versao / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    campeao anterior arquivado: versao {nova_versao} "
          f"({pasta.name})", flush=True)
    return nova_versao


def listar(sistema: str, simbolo: str, variante: str) -> list[dict]:
    pasta = _pasta_combo(sistema, simbolo, variante)
    saida = []
    for v in _versoes(pasta):
        meta_path = pasta / str(v) / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        saida.append(meta)
    return saida


def rollback_campeao(sistema: str, simbolo: str, variante: str,
                     versao: int | None = None) -> int | None:
    """Restaura uma versao arquivada como o VALIDADO_*.set ao vivo. A
    versao ATUAL (se existir) e arquivada primeiro, pelo MESMO mecanismo
    -- um rollback tambem precisa ser revertivel, nunca um beco sem
    saida. versao=None restaura a mais recente arquivada. Devolve o
    numero restaurado, ou None se nao achou nada.
    """
    pasta = _pasta_combo(sistema, simbolo, variante)
    versoes = _versoes(pasta)
    if not versoes:
        return None
    alvo = versao if versao is not None else versoes[-1]
    pasta_versao = pasta / str(alvo)
    arquivos_set = list(pasta_versao.glob("*.set")) if pasta_versao.is_dir() else []
    if not arquivos_set:
        return None

    destino = ready_library.TESTER / arquivos_set[0].name
    arquivar_campeao_anterior(sistema, simbolo, variante, destino)
    shutil.copy2(arquivos_set[0], destino)
    print(f"restaurado: versao {alvo} -> {destino.name}", flush=True)
    return alvo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistema", required=True)
    ap.add_argument("--simbolo", required=True)
    ap.add_argument("--variante", default="BUY_MULTI")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--versao", type=int, default=None)
    args = ap.parse_args()

    if args.listar:
        for meta in listar(args.sistema, args.simbolo, args.variante):
            ledger = meta.get("ledger", {})
            print(f"  v{meta['versao']}: {meta['arquivado_em']} | "
                 f"{meta['arquivo_original']} | expectancy_r="
                 f"{ledger.get('expectancy_r')} composite_score="
                 f"{ledger.get('composite_score')}")
        return 0
    if args.rollback:
        v = rollback_campeao(args.sistema, args.simbolo, args.variante, args.versao)
        if v is None:
            print("Nada pra restaurar (sem versao arquivada pra esse combo).")
            return 1
        return 0
    print("Use --listar ou --rollback.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
