# AutoBotSetup — installer for the buyer

> **This is source code, not the installer.** `Install_AutoBot_and_Sets.py`
> only runs raw on the machine that builds it -- without the `Sets/` and
> `AutobotRuntime/` folders (excluded from git on purpose, see
> `.gitignore`) it ALWAYS fails with "the Sets folder didn't ship with the
> installer". If you downloaded the repository from GitHub and ended up
> here: the right file is `White Rabbit X - Instalador.exe`, distributed
> through Telegram (<https://t.me/MrRabbit_MT5>), never through the
> repository's "Download ZIP". This really happened to a buyer on
> 2026-08-08.

The MQL5 Market ships the `.ex5` and nothing else. The 3,738 optimization
sets are left out, and without them the buyer would have to find the
terminal's data folder, copy the files into the right place, and still
notice on their own that their broker calls `EURUSD` `EURUSDm` — because a
`.set` with the wrong symbol simply doesn't load, without saying why.

This installer solves that in a double-click — and since 2026-08-06 it also
installs the Autobot (the same control panel used internally), with its own
embedded Python, for anyone who wants to run optimization campaigns on their
own account.

## What it does

1. **Finds MetaTrader.** MT5's data lives in a directory whose name is a
   hash, outside the install folder. The installer scans for it and, when
   there's more than one, puts **the one where White Rabbit X is already
   downloaded first** — which is almost always the right one.
2. **Copies the sets** to `MQL5\Profiles\Tester\White_Rabbit_X_Sets`.
3. **Adjusts to the broker**: finds each symbol's real suffix, applies each
   one's minimum lot, and warns which assets that broker doesn't offer.
4. **Installs the Autobot** (dashboard + optimization circuit) at
   `Documents\White Rabbit X - Autobot`, with embedded Python — and creates
   a "White Rabbit X - Autobot" desktop shortcut.
5. **Writes `INSTALACAO.json`** with what was done, for support.

If the terminal is closed, it copies the sets at their defaults and warns
that the broker adjustment needs a second pass with MT5 open.

## For the buyer

Just one file. No Python or anything else to install — neither for the
sets, nor for the Autobot:

```
White Rabbit X - Instalador.exe
```

Opening MetaTrader and logging in **before** running it gives the full
result, because that's the only way the installer can see the broker.

## To build the executable

Two parts: assemble the `AutobotRuntime` folder (embedded Python + Autobot)
once, then compile the `.exe` (this part, every time something changes).

### 1. Assemble `AutobotRuntime/`

Only needs redoing if the Autobot's dependencies change —
numpy/pandas/fastapi/uvicorn/MetaTrader5.

```bash
# Download the official embeddable Python (same version used here: 3.13.6)
curl -LO https://www.python.org/ftp/python/3.13.6/python-3.13.6-embed-amd64.zip
mkdir -p AutobotRuntime/python-embed
unzip python-3.13.6-embed-amd64.zip -d AutobotRuntime/python-embed

# Enables Lib\site-packages in ._pth (WITHOUT enabling "import site" -- that
# would make the embeddable see %APPDATA%\Python\PythonXXX\site-packages,
# i.e. the personal packages of whoever is building it, which breaks on the
# client). And adds "..\Autobot" -- that's how the Autobot scripts (sibling
# of python-embed\) become importable without PYTHONPATH, because a ._pth
# file ignores both PYTHONPATH and the normal Python's default "add the
# script's directory".
cat > AutobotRuntime/python-embed/python313._pth <<'EOF'
python313.zip
.
Lib\site-packages
..\Autobot
#import site
EOF

# Bootstrap pip (the embeddable doesn't ship with it)
curl -LO https://bootstrap.pypa.io/get-pip.py
AutobotRuntime/python-embed/python.exe get-pip.py --no-warn-script-location

# Autobot dependencies, INSIDE the embedded Python
AutobotRuntime/python-embed/python.exe -m pip install --no-warn-script-location \
  fastapi uvicorn MetaTrader5 numpy pandas

# Autobot: only the operational subset (dashboard + 5-stage circuit +
# set generation/validation) -- NOT the manual-maintenance tools
# (align_manuals, audit_manuals, enrich_manuals, render_manuals,
# sync_input_reference, sync_set_count, update_indicator_lists,
# write_library_docs, build_br_version) nor the *.ps1/test_*.py files.
mkdir -p AutobotRuntime/Autobot
# copy the operational .py files + dashboard_static/ from ../Autobot/

# Launcher and icon: source tracked in git, they live in AutoBotSetup/
# itself (not inside AutobotRuntime/, which is a generated folder only) --
# copied into the runtime on every build.
cp Iniciar_Dashboard.bat AutobotRuntime/
cp wrx_icon.ico AutobotRuntime/
```

`Iniciar_Dashboard.bat` and `wrx_icon.ico` **are** versioned (they live loose
in `AutoBotSetup/`, next to `Install_AutoBot_and_Sets.py`) -- only the
generated content (`AutobotRuntime/python-embed/`, the copy of the Autobot's
`.py` files, `build/`) is excluded from git. If you edit the launcher, edit
the one in `AutoBotSetup/`, not the copy inside `AutobotRuntime/` (that one
is disposable, recreated on every build).

### 2. Compile the `.exe`

```bash
python -m pip install pyinstaller
python -m PyInstaller --onefile --console \
  --name "White Rabbit X - Instalador" \
  --add-data "<absolute path>/Sets;Sets" \
  --add-data "<absolute path>/AutobotRuntime;AutobotRuntime" \
  --hidden-import MetaTrader5 \
  --collect-all numpy \
  --distpath . --workpath build/tmp --specpath build --noconfirm \
  Install_AutoBot_and_Sets.py
```

`--collect-all numpy` **is not optional**: `MetaTrader5` (a compiled module,
not pure Python) uses numpy internally, and PyInstaller can't see that
dependency on its own — without it the installer runs, copies the sets, but
the broker-adjustment step fails with
`ModuleNotFoundError: No module named 'numpy'` / `numpy._core.multiarray
failed to import`, silently (it falls back to "sets at their defaults").

The `Sets` and `AutobotRuntime` folders get embedded. A folder placed **next
to the .exe** takes precedence over the embedded one — that's how an updated
version is shipped without generating a new installer.

Detail that breaks silently if forgotten: with `--onefile`, `__file__`
points to the temp directory that PyInstaller extracts to, not to where the
buyer placed the program. The "next to the exe" path needs to come from
`sys.executable`.

Expected `.exe` size: ~150-220MB (`AutobotRuntime` alone is already ~176MB
before compression — numpy+pandas dominate).

## Distribution

The executable goes into the Telegram channel's RAR, alongside the Market
listing. Before publishing a new version, regenerate the sets and rebuild
the `.exe`:

```bash
python ../Autobot/generate_system_sets.py
python ../Autobot/validate_system_sets.py
```
