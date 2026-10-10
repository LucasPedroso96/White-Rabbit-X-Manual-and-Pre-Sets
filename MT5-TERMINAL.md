# Terminal MT5 do White Rabbit

_Gerado de `systems.json` por `mt5/docs_terminal.py` (VPS-PC-Control-Plane). Nao edite aqui: mude la, rode o gerador e abra PR._

## Definicao (no C:)

| Item | Valor |
|---|---|
| Instalacao | `C:\Program Files\RoboForex MT5 Terminal (White Rabbit Autobot)` |
| Executavel | `C:\Program Files\RoboForex MT5 Terminal (White Rabbit Autobot)\terminal64.exe` |
| Dados do terminal | `%APPDATA%\MetaQuotes\Terminal\6B2E73F745380AAE2FD25BE277501984` |
| MQL5 ativo (EAs, Include, Files) | `%APPDATA%\MetaQuotes\Terminal\6B2E73F745380AAE2FD25BE277501984\MQL5` |
| Conta | 77034660 REAL (RoboForex-ECN) |
| Atalho | `Trading\2 Terminais MT5\MT5 - White Rabbit (77034660 REAL).lnk` |
| Icone | `Terminal.ico` = `Trading\Icones\mt5-whiterabbit.ico` (arte: `VPS-PC-Control-Plane\icones\whiterabbit-Terminal.png`) |
| Repositorio | `White-Rabbit-X-Manual-and-Pre-Sets` |

A pasta de dados e o MD5 do caminho da instalacao (maiusculas, UTF-16LE): mover ou renomear a pasta do terminal cria outro perfil. So com o terminal fechado pelo dono.

## Regras

1. **Um sistema, um terminal, uma conta.** Nenhum sistema se anexa ao terminal de outro.
2. **Mesmo caminho em qualquer maquina** (VPS e PC), sempre em `C:\Program Files\`, aberto SEM `/portable` (dados e `MQL5` ativos em `%APPDATA%`).
3. O codigo do sistema acha o terminal por `terminal_padrao.resolver_caminho`: caminho explicito (config/env) > o padrao acima (se instalado) > legado dentro do projeto. Nunca fixe outro caminho.
4. **Nunca por script**: abrir, fechar ou logar o terminal, anexar EA, digitar senha. A senha nao vai em arquivo, commit nem chat.
5. Conta REAL: so com as duas travas do dono. Conta demo nunca e bloqueada.

## O que roda neste terminal/sistema no VPS

- WRX_Engine LIVE (Metatrader5EAS, branch feat/wrx-engine, pasta White Rabbit/WRX_Engine): Hub tools/live_hub.py (FastAPI 8030, WRX_HUB_TOKEN, so tailnet) + agente tools/live_agent.py (le saldo/trades pela API MetaTrader5 do terminal White Rabbit e grava o plano assinado wrx_plan_<login>.txt) + EAs WRX Gov (tools/live_deploy.py compila no terminal) lendo o plano (UsarPlanoWRX=true)

## Conferir e instalar

No VPS-PC-Control-Plane (nao mudam nada sem `-Apply`):

```
.\Conferir-Terminais.ps1                 # falta / sobra / icone fora do padrao
.\Instalar-Terminal.ps1 [-Apply]         # instala o que faltar (sem conta salva)
python mt5\terminal_padrao.py --sistema "White Rabbit Autobot"   # confere este terminal
```

Padrao completo: `PADRAO-TERMINAIS-MT5.md`; os 6 sistemas lado a lado: `MT5-POR-SISTEMA.md`; visual: `PADRAO-VISUAL-SISTEMAS.md`.
