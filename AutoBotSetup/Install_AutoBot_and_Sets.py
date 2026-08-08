# -*- coding: utf-8 -*-
"""White Rabbit X - Automatic installer for the buyer.

The buyer downloads the EA from the MQL5 Market, but the sets are left out: the
Market ships the .ex5 and nothing else. They would otherwise have to find the
terminal's data folder, copy 3,738 files into the right place, and still figure
out on their own that their broker calls EURUSD "EURUSDm" -- because a .set
with the wrong symbol simply doesn't load.

This installer does that: finds the terminal, copies the sets, reads the
account and adjusts symbol, lot size and base capital to the buyer's broker.

Runs without Python installed (packaged with PyInstaller) and without
arguments: it's for someone who bought a robot, not a programmer.

Besides the sets, it also installs the Autobot -- the same control panel
(dashboard + optimization campaigns) used internally -- with its own embedded
Python (an "AutobotRuntime" folder next to the installer, or packaged inside
the exe), so the buyer doesn't need Python installed for that either.
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

VERSION = "1.12"
TELEGRAM = "https://t.me/MrRabbit_MT5"


def title(text: str) -> None:
    print()
    print("=" * 66)
    print(f"  {text}")
    print("=" * 66)


def unblock(target: Path) -> None:
    """Removes the "downloaded from another computer" mark (NTFS
    Zone.Identifier) from everything the installer just copied.

    Owner's finding, 2026-08-08: a real buyer saw Windows ask them to
    manually "unblock" the .bat (Properties > Unblock) before running it --
    SmartScreen flags any file that went through a download/network with
    this zone workflow, and .bat files can't carry an Authenticode signature
    anyway (that's only for .exe/.dll, and requires a purchased certificate
    only the owner can get). What can be done without a certificate: Windows
    stores the mark as an Alternate Data Stream (NAME:Zone.Identifier) --
    deleting that specific stream is equivalent to ticking "Unblock" in the
    dialog, without the buyer having to do anything. Only works on an NTFS
    volume (always the case on Windows); FileNotFoundError is normal when
    the file never had the mark.
    """
    targets = [target] if target.is_file() else target.rglob("*")
    for item in targets:
        if not item.is_file():
            continue
        try:
            os.remove(f"{item}:Zone.Identifier")
        except OSError:
            pass


def has_the_ea(terminal: Path) -> bool:
    """Has White Rabbit X already been downloaded into this terminal?"""
    experts = terminal / "MQL5" / "Experts"
    if not experts.is_dir():
        return False
    patterns = ("White Rabbit X*.ex5", "Market/**/White Rabbit X*.ex5",
                "**/White Rabbit X*.ex5")
    return any(next(experts.glob(p), None) for p in patterns)


def find_terminals() -> list[Path]:
    """MT5 data folders installed on this machine.

    MetaTrader keeps its data outside the install folder, in a directory
    whose name is a hash -- so the search is by content, not by name.

    Whoever already has the EA downloaded comes first: that's almost always
    the right terminal, and it saves the buyer from choosing between
    installs they don't even remember having. After those, the most
    recently used ones.
    """
    root = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if not root.is_dir():
        return []
    found = []
    for folder in root.iterdir():
        if not folder.is_dir() or not (folder / "MQL5" / "Experts").is_dir():
            continue
        try:
            recency = folder.stat().st_mtime
        except OSError:
            recency = 0.0
        found.append((not has_the_ea(folder), -recency, folder))
    found.sort()
    return [p for _, _, p in found]


def describe(terminal: Path) -> str:
    origin = terminal / "origin.txt"
    if origin.exists():
        try:
            text = origin.read_text(encoding="utf-16").strip()
            return text or terminal.name
        except Exception:
            pass
    return terminal.name


def choose(terminals: list[Path]) -> Path | None:
    if not terminals:
        return None
    if len(terminals) == 1:
        print(f"Terminal found: {describe(terminals[0])}")
        return terminals[0]
    print("More than one MetaTrader found:\n")
    for i, t in enumerate(terminals, 1):
        mark = "  <- White Rabbit X is here" if has_the_ea(t) else ""
        print(f"  [{i}] {describe(t)}{mark}")
    while True:
        choice = input("\nWhich one? (number, or Enter for the 1st) ").strip()
        if not choice:
            return terminals[0]
        if choice.isdigit() and 1 <= int(choice) <= len(terminals):
            return terminals[int(choice) - 1]
        print("Invalid number.")


def copy_sets(source: Path, terminal: Path) -> int:
    target = terminal / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets"
    target.mkdir(parents=True, exist_ok=True)
    total = 0
    for file in source.rglob("*"):
        if not file.is_file():
            continue
        dest = target / file.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
        total += 1
    unblock(target)
    return total


def connect_mt5() -> tuple[object | None, str]:
    """Returns (module, reason). The reason separates 'missing library' from
    'terminal closed' -- they're different problems with different fixes,
    and telling the buyer the wrong one sends them looking in the wrong
    place."""
    try:
        import MetaTrader5 as mt5
    except ImportError as error:
        if getattr(sys, "frozen", False):
            return None, f"library missing from the installer ({error})"
        return None, (f"MetaTrader5 not installed in your Python ({error}) "
                       f"-- run: pip install -r requirements.txt")
    if not mt5.initialize():
        return None, f"terminal closed or not logged in ({mt5.last_error()})"
    return mt5, ""


def broker_symbol(mt5, base: str) -> str | None:
    """Finds the real name, with whatever suffix the broker uses."""
    if mt5.symbol_info(base):
        return base
    candidates = [s.name for s in mt5.symbols_get()
                  if re.fullmatch(rf"{re.escape(base)}[.\-_a-zA-Z0-9]*", s.name)]
    return min(candidates, key=len) if candidates else None


def adjust_sets(mt5, folder: Path) -> dict:
    """Rewrites symbol and lot size to match the buyer's broker."""
    report = {"adjusted": 0, "suffixes": {}, "missing": [], "lots": {}}
    assets = {d.name for c in folder.iterdir() if c.is_dir()
              for d in c.iterdir() if d.is_dir()}

    symbol_map: dict[str, str] = {}
    specs: dict[str, dict] = {}
    for base in sorted(assets):
        real = broker_symbol(mt5, base)
        if real is None:
            report["missing"].append(base)
            continue
        symbol_map[base] = real
        if real != base:
            report["suffixes"][base] = real
        info = mt5.symbol_info(real)
        if info:
            specs[base] = {"min": info.volume_min, "step": info.volume_step}

    for path in folder.rglob("*.set"):
        parts = path.relative_to(folder).parts
        if len(parts) < 2:
            continue
        asset = parts[1]
        if asset not in symbol_map:
            continue
        lines = path.read_text(encoding="utf-16").splitlines()
        output, changed = [], False
        for line in lines:
            if line.startswith("NomedaEstrategia=") and symbol_map[asset] != asset:
                line = line.replace(asset, symbol_map[asset])
                changed = True
            elif line.startswith("PositionSizeValue="):
                m = re.match(r"^PositionSizeValue=([^|]+)\|\|", line)
                spec = specs.get(asset)
                if m and spec:
                    try:
                        current = float(m.group(1))
                    except ValueError:
                        current = 0.0
                    # Only touches the fixed lot: values >= 1 are Fixed-R
                    # risk percentage and must not become volume.
                    if 0 < current < 1 and current < spec["min"]:
                        new = f"{spec['min']:g}"
                        line = (f"PositionSizeValue={new}||{new}||"
                                f"{spec['step']:g}||{new}||N")
                        changed = True
                        report["lots"][asset] = spec["min"]
            output.append(line)
        if changed:
            path.write_text("\r\n".join(output) + "\r\n", encoding="utf-16")
            report["adjusted"] += 1
    return report


def copy_autobot(source: Path, icon: Path | None = None) -> Path | None:
    """Copies the Autobot (dashboard + embedded Python) to the user's folder.

    source is the "AutobotRuntime" folder (python-embed/, Autobot/,
    Iniciar_Dashboard.bat) shipped with the installer -- same precedence
    logic as copy_sets(): a folder next to the exe takes priority over the
    packaged one, so an update can ship without rebuilding the installer.

    The icon (if present) is copied along with it: the shortcut points to it
    INSIDE the permanent destination, never to PyInstaller's temp folder --
    that one disappears as soon as the installer exits.
    """
    if not source.is_dir():
        return None
    target = Path(os.environ.get("USERPROFILE", str(Path.home()))) \
        / "Documents" / "White Rabbit X - Autobot"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    if icon and icon.is_file():
        shutil.copy2(icon, target / icon.name)
    unblock(target)
    return target


def create_shortcut(target: Path, name: str, icon: Path | None = None) -> bool:
    """Creates a desktop shortcut via VBScript (no pywin32 dependency --
    cscript.exe already ships with every Windows)."""
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) \
        / "Desktop"
    if not desktop.is_dir():
        return False
    shortcut = desktop / f"{name}.lnk"
    icon_line = (f'link.IconLocation = "{icon}"\n'
                 if icon and icon.is_file() else "")
    vbs = (
        'Set ws = CreateObject("WScript.Shell")\n'
        f'Set link = ws.CreateShortcut("{shortcut}")\n'
        f'link.TargetPath = "{target}"\n'
        f'link.WorkingDirectory = "{target.parent}"\n'
        f'link.Description = "{name}"\n'
        f'{icon_line}'
        'link.Save\n'
    )
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".vbs", delete=False, encoding="utf-8") as f:
        f.write(vbs)
        vbs_path = f.name
    try:
        r = subprocess.run(["cscript", "//nologo", vbs_path],
                            capture_output=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        os.unlink(vbs_path)


def main() -> int:
    title(f"White Rabbit X {VERSION} - Sets Installation")
    print("This installer copies the optimization sets to your MetaTrader")
    print("and adjusts the files to your broker.\n")
    print("The Expert Advisor itself is downloaded from the MQL5 Market, in")
    print("the Terminal > Market > Purchased tab.")

    # The sets ship embedded in the executable (sys._MEIPASS, which
    # PyInstaller extracts to a temp folder). A "Sets" folder next to the
    # .exe takes precedence: that's how an updated library is shipped
    # without generating a new installer.
    #
    # Careful: with onefile, __file__ points to the temp folder, not to
    # where the buyer placed the program. The "next to it" path comes from
    # sys.executable.
    next_to_it = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                  else Path(__file__).parent)
    source = next_to_it / "Sets"
    if not source.is_dir():
        source = Path(getattr(sys, "_MEIPASS", next_to_it)) / "Sets"
    if not source.is_dir() and not getattr(sys, "frozen", False):
        # Running the raw .py inside a repo clone/ZIP: AutoBotSetup/Sets is
        # gitignored (only exists inside the .exe), but the REPO ROOT Sets/
        # is versioned -- same library, published for anyone who just wants
        # to copy it manually. A plain clone, that never went through the
        # installer build, is already enough to install from -- it shouldn't
        # depend on downloading the separate .exe just for this to work.
        candidate = next_to_it.parent / "Sets"
        if candidate.is_dir():
            source = candidate
    if not source.is_dir():
        if not getattr(sys, "frozen", False):
            # Real finding, 2026-08-08: a client downloaded the GitHub ZIP
            # and ran this script directly, thinking it was the installer.
            # The folder next to it (AutoBotSetup/Sets) only
            # exists inside the .exe, but the fallback above already covers
            # a normal clone -- if we got here, even the root Sets/ is
            # missing (partial ZIP, or wrong folder).
            print("\nERROR: couldn't find the 'Sets' folder, neither next to")
            print("this script nor at the repository root.")
            print("\nThis script is the installer's SOURCE CODE -- run this way,")
            print("it also knows how to install straight from the repository's")
            print("root Sets/, but it needs to be in the right place: download")
            print("the FULL ZIP of the repository from GitHub (not just the")
            print("AutoBotSetup/ folder) and run it from there.")
            print(f"\nIf you'd rather use the ready-made installer (.exe): {TELEGRAM}")
        else:
            print("\nERROR: the 'Sets' folder didn't ship with the installer.")
            print(f"Download the full package at {TELEGRAM}")
        input("\nPress Enter to exit.")
        return 1

    # Same precedence logic as Sets: a folder next to the exe takes priority
    # over the packaged one.
    autobot_source = next_to_it / "AutobotRuntime"
    if not autobot_source.is_dir():
        autobot_source = Path(getattr(sys, "_MEIPASS", next_to_it)) / "AutobotRuntime"
    icon_source = next_to_it / "wrx_icon.ico"
    if not icon_source.is_file():
        icon_source = Path(getattr(sys, "_MEIPASS", next_to_it)) / "wrx_icon.ico"

    title("1. Looking for MetaTrader")
    terminals = find_terminals()
    if not terminals:
        print("No MetaTrader 5 found on this computer.")
        print("Open the terminal at least once and run this installer again.")
        input("\nPress Enter to exit.")
        return 1
    terminal = choose(terminals)
    if terminal is None:
        return 1

    title("2. Copying the sets")
    total = copy_sets(source, terminal)
    target = terminal / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets"
    print(f"{total} files copied to:")
    print(f"  {target}")

    title("3. Adjusting to your broker")
    mt5, reason = connect_mt5()
    if mt5 is None:
        print(f"Couldn't read the account: {reason}")
        print("\nThe sets stayed at their defaults -- they'll work on brokers")
        print("that use the symbols without a suffix (EURUSD, XAUUSD).")
        if "terminal" in reason:
            print("\nLeave MetaTrader OPEN and logged in and run this again,")
            print("so the installer can get the suffix and minimum lot right.")
        else:
            print(f"\nThis is the installer's fault, not yours. Let us know at "
                  f"{TELEGRAM}")
            print("and a fixed version will come out.")
    else:
        account = mt5.account_info()
        if account:
            print(f"Account {account.login} at {account.server}")
            print(f"  balance {account.balance:.2f} {account.currency}")
        r = adjust_sets(mt5, target)
        print(f"\n{r['adjusted']} sets adjusted.")
        if r["suffixes"]:
            print(f"\nYour broker uses a suffix on {len(r['suffixes'])} symbols:")
            for base_s, real in list(r["suffixes"].items())[:6]:
                print(f"  {base_s} -> {real}")
        if r["lots"]:
            print(f"\nYour broker's minimum lot was applied on "
                  f"{len(r['lots'])} assets.")
        if r["missing"]:
            print(f"\nYour broker doesn't offer {len(r['missing'])} assets "
                  f"from the library:")
            print("  " + ", ".join(r["missing"][:12])
                  + (" ..." if len(r["missing"]) > 12 else ""))
            print("  Their sets were still installed, but won't load.")
        record = {
            "when": datetime.now().isoformat(timespec="seconds"),
            "version": VERSION,
            "terminal": str(terminal),
            **r,
        }
        (target / "INSTALACAO.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        mt5.shutdown()

    title("4. Installing the Autobot (control panel)")
    autobot_folder = copy_autobot(autobot_source, icon_source)
    if autobot_folder is None:
        # The embedded Python (AutobotRuntime/python-embed) only exists
        # inside the .exe -- there's no way to package that in the
        # repository. But the Autobot CODE (Autobot/) is versioned and runs
        # with any of the buyer's own Python 3.11+, as long as they install
        # the same dependencies. Saying so instead of just telling them to
        # buy the .exe: anyone who already has Python (like whoever made a
        # .venv to run this) can carry on without waiting for anything.
        autobot_folder_source = next_to_it.parent / "Autobot"
        if not getattr(sys, "frozen", False) and autobot_folder_source.is_dir():
            requirements = autobot_folder_source / "requirements.txt"
            dashboard_script = autobot_folder_source / "dashboard_campanha.py"
            print("The embedded Autobot (its own Python) didn't ship -- normal")
            print("when running the source code directly, it only exists inside")
            print("the .exe. Installing the dependencies in your Python now")
            print("(may take a few minutes, numpy/pandas are heavy):\n")
            # Actually runs pip instead of just printing the command -- a
            # buyer starting from zero shouldn't have to copy/paste
            # anything. Uses sys.executable (the SAME Python that's running
            # this installer right now, unfrozen) to make sure it installs
            # into the right interpreter, the same one that'll run the
            # dashboard afterward. Not capturing stdout/stderr: pip stays
            # visible while running, otherwise numpy/pandas look stuck for
            # 1-2 minutes with no output at all.
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements)])
            if result.returncode == 0:
                print("\nDependencies installed. To open the panel:")
                print(f"  python \"{dashboard_script}\"")
            else:
                print("\nCouldn't install on my own (pip error above).")
                print("Run it manually:")
                print(f"  pip install -r \"{requirements}\"")
                print(f"  python \"{dashboard_script}\"")
            print(f"\nQuestions, or if you'd rather use the ready-made installer: "
                  f"{TELEGRAM}")
        else:
            print("The Autobot package didn't ship with this installer --")
            print("only the sets were installed. Download the full package at")
            print(f"{TELEGRAM} if you want the campaign control panel.")
    else:
        print(f"Autobot installed at:\n  {autobot_folder}")
        installed_icon = autobot_folder / icon_source.name
        shortcut_ok = create_shortcut(
            autobot_folder / "Iniciar_Dashboard.bat", "White Rabbit X - Autobot",
            installed_icon if installed_icon.is_file() else None)
        if shortcut_ok:
            print("\nDesktop shortcut created: "
                  "\"White Rabbit X - Autobot\"")
        else:
            print(f"\nTo open the panel: {autobot_folder / 'Iniciar_Dashboard.bat'}")

    title("Done")
    print("In the Strategy Tester: Inputs tab > Load > pick a set at")
    print("  Profiles\\Tester\\White_Rabbit_X_Sets\\<class>\\<asset>\\<system>")
    print("\nStart with the 01_SLTP system on the asset you trade.")

    # The buyer needs to know they received PHASE 1 of a circuit, not a
    # finished preset. Without this they open the file, see filters turned
    # off and think something's missing -- when they're actually off on
    # purpose, because a filter only means something once the signal is
    # already resolved.
    title("The optimization circuit")
    print("These files come configured for PHASE 1. The library isn't a set")
    print("of ready-made presets: it's the first step of a circuit, and each")
    print("phase narrows down what the next one needs to search.\n")
    print("  phase 1 (what you got)   signal and exit geometry, in OHLC")
    print("  phase 2                  filters: MTF, moving average, ADX")
    print("  phase 3                  session: spread, hours, days")
    print("  phase 4                  confirmation in REAL TICKS\n")
    # The criterion changes with each phase, and that's not a detail: a
    # filter REDUCES the number of trades by construction, so optimizing
    # phase 2 by total profit would punish exactly the filter that cuts a
    # bad entry, even while improving every entry that's left.
    print("The optimization criterion CHANGES with each phase, and that matters:\n")
    print("  phase 1   Pessimistic Average Profit    does the signal have an")
    print("                                          edge, or were there just")
    print("                                          a few lucky trades?")
    print("  phase 2   Drawdown-adjusted profit       quality PER TRADE --")
    print("            per trade                      doesn't punish a filter")
    print("                                          for trading less")
    print("  phase 3   Return Uniformity              a session filter exists")
    print("                                          to cut a bad period\n")
    print("Using the same criterion in all three phases backfires: a filter that")
    print("cuts a bad entry trades LESS, and by total profit it scores worse even")
    print("while improving the quality of every entry left standing.\n")
    print("The filters ship TURNED OFF on purpose. A filter means nothing before")
    print("the signal is resolved, and leaving them open multiplies the search")
    print("space by 384x without adding any information.")
    print("Their ranges are already written into the file, marked with N --")
    print("phase 2 is just switching them to Y, you don't need to invent the range.\n")
    print("Between phases, LOCK what you found: put the winning value in all")
    print("four fields and switch the mark to N. Each lock collapses the search")
    print("space by orders of magnitude, and that's what makes the next phase")
    print("more precise instead of just slower.")

    # Warning that changes the RESULT, not just convenience: measured on
    # this EA, comparing the same set in both modes over 3 years, the fast
    # mode underestimates the loss by 3.3x on trailing systems and 23x on
    # grid -- always toward the optimistic side. Only fixed SL/TP stays
    # within 3%. Anyone who doesn't know this will optimize against a price
    # path that never happened.
    title("IMPORTANT: modeling mode")
    print("In the Strategy Tester's Settings tab, Modeling field:")
    print("\n  'Every tick based on real ticks'  <- use this one")
    print("  'OHLC 1 minute'                     <- only for 01_SLTP and 02_SLTP_ORGANIC")
    print("\nEvery other system depends on WHEN the price touched each level")
    print("within the bar. OHLC mode interpolates that and smooths out exactly")
    print("the excursions that would break a trailing stop or a grid leg: the")
    print("result comes out better than reality, not worse.")
    print("\nSystems 07 and 08 (grid) require a HEDGING account. On a netting")
    print("account the legs cancel each other out and the system doesn't work")
    print("as designed.")

    print(f"\nQuestions and updates: {TELEGRAM}")
    input("\nPress Enter to exit.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001 - the buyer doesn't see a traceback
        print(f"\nUNEXPECTED ERROR: {error}")
        print(f"Send this message to {TELEGRAM} and we'll sort it out.")
        input("\nPress Enter to exit.")
        sys.exit(1)
