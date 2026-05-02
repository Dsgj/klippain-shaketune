# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Shake&Tune is a Klipper plugin (loaded as a Python module under `klippy/extras/shaketune`) that runs resonance tests on a 3D printer, captures accelerometer data, and renders diagnostic graphs (input shaper calibration, belt comparison, axes map detection, vibration profiles, static-frequency excitation). It also ships a standalone CLI that re-renders graphs from previously captured data without a live Klipper.

## Common commands

- Lint: `ruff check` (config in `pyproject.toml`: line length 120, single-quote strings, target Py3.9, rules `E4 E7 E9 F B`).
- Format: `ruff format`.
- Smoke test (matches CI in `.github/workflows/test.yml`): clone Klipper next to this repo, symlink `shaketune/` into `klipper/klippy/extras/shaketune`, install `requirements.txt` into Klipper's venv, then `python klippy/klippy.py --import-test` and `python scripts/test_klippy.py -d <dicts> ci/smoke-test/klippy-tests/simple.test`. CI runs this against both `klipper3d/klipper` and `KalicoCrew/kalico` on `master` and `v0.13.0` × Python 3.9 and 3.11 — keep changes working across that matrix.
- CLI (regenerate graphs from data files): `python -m shaketune.cli <static_freq|axes_map|belts|input_shaper|vibrations> -o out.png [--klipper_dir ~/klipper] <files...>`. The CLI sets `SHAKETUNE_IN_CLI=1` so the package imports `shaper_calibrate` from a user-supplied Klipper checkout instead of the in-process Klipper.
- Install on a printer: `install.sh` symlinks `shaketune/` into `~/klipper/klippy/extras/`, installs deps into Klipper's venv (`KLIPPER_VENV` or `~/klippy-env`), and registers a `[update_manager]` entry in `moonraker.conf`.

There is no `pytest` suite — correctness is verified by the Klippy smoke test plus lint.

## Architecture

### Two execution modes, one codebase
- **Klipper plugin**: `shaketune/__init__.py` exposes `load_config()` so Klipper instantiates `ShakeTune` from `[shaketune]` in `printer.cfg`. Heavy graph generation runs in a forked `multiprocessing.Process` (see `shaketune_process.py`) with `SCHED_BATCH` / minimum priority so it doesn't trip Klipper's `Timer too close` / `Move queue overflow` errors. The wrapper also sets a `threading.Timer` inside the child for hard timeouts.
- **CLI**: `shaketune/cli.py` reuses the same `GraphCreator` / `Computation` / `Plotter` pipeline but reads `.stdata` or legacy Klipper `.csv` from disk. It detects mode via `os.environ['SHAKETUNE_IN_CLI']` (set in `cli.__main__`); the rest of the code branches on this to decide whether to import Klipper modules relatively (`from ... import shaper_calibrate`) or pull them from `sys.modules` after `cli.load_klipper_module()` has injected them.

### Command → Computation → Plotter pipeline
1. **Commands** (`shaketune/commands/*.py`): one per macro (`AXES_SHAPER_CALIBRATION`, `COMPARE_BELTS_RESPONSES`, `AXES_MAP_CALIBRATION`, `CREATE_VIBRATIONS_PROFILE`, `EXCITATE_AXIS_AT_FREQ`). Each parses `gcmd` args, drives the toolhead/resonance tester, records via `helpers/accelerometer.py`, writes a `.stdata` file, and hands the path to a `ShakeTuneProcess`.
2. **GraphCreator** (`graph_creators/graph_creator.py`): abstract base with a class-level `registry` populated by the `@GraphCreator.register('graph type')` decorator on each subclass. `GraphCreatorFactory.create_graph_creator(name, config)` looks the subclass up by name; the `ShakeTune._cmd_helper` already passes the right string. Each subclass composes a `Computation` and a `PlotterStrategy` (see `base_models.py`).
3. **Computation** (`graph_creators/computations/`): pure data — loads measurements from `MeasurementsManager`, runs FFT/PSD/shaper math, returns a `ComputationResult`.
4. **Plotter** (`graph_creators/plotters/`): turns the result into a matplotlib `Figure`, which `GraphCreator._save_figure` writes as PNG (and optionally retains the `.stdata` if `keep_raw_data` is set).

When adding a new graph type: write a `Computation` and a `Plotter`, then a `GraphCreator` subclass decorated with `@GraphCreator.register('your name')`, then plumb a command and add the type to `RESULTS_SUBFOLDERS` in `shaketune_config.py`. Add a CLI subparser in `cli.py` if you want CLI access.

### Macro injection hack
`ShakeTune._register_commands` registers every command twice when `show_macros_in_webui` is true: once as `_NAME` via `gcode.register_command` (callable from console), then it parses `dummy_macros.cfg` and *injects* its `[gcode_macro NAME]` sections into Klipper's already-loaded config (mutating `configfile.fileconfig` and `_config.access_tracking`) so Mainsail/Fluidd render buttons. This is intentional — the comments call it out as "not a good way" but the only path to UI buttons. Touch with care; the access-tracking poke is what stops Klipper from flagging the sections as unused.

### Klipper version compatibility
The Klipper API is unstable across releases (and Kalico diverges further). All version-aware code lives in two places — keep it there:
- `helpers/compat.py` — `KlipperCompatibility` does feature detection (e.g. `set_max_velocities` vs `cmd_M204`, legacy `res_tester.test.*` vs modern `res_tester.generator.*`) and caches results. Never branch on version strings; check capabilities.
- `graph_creators/__init__.py` — `_has_name_param_in_process_accel_data` and `_normalize_find_best_shaper_result` wrap the `shaper_calibrate` API changes from late-2024/2025 Klipper commits. Use `process_accelerometer_data_compat` and `find_best_shaper_compat` instead of calling Klipper directly.

DangerKlipper is detected via `importlib.util.find_spec('extras.danger_options')` and exposed as `ShakeTune.IN_DANGER`.

### Measurement format
`.stdata` is newline-delimited JSON measurements (`{"name": ..., "samples": [(t, ax, ay, az), ...]}`) wrapped in zstandard (level 11). `MeasurementsManager` runs a dedicated writer `Process` fed by a `multiprocessing.Queue`, flushing chunks of `chunk_size` (default 2 — kept low to avoid `Timer too close` on weak SBCs). The plugin path always blocks on the writer between chunks via Klipper's reactor; the CLI path skips the writer entirely and just appends in memory. Legacy Klipper `.csv` (header `#time,accel_x,accel_y,accel_z`) is still loadable for backward compatibility.

## Conventions

- Single-quoted strings (enforced by `ruff format`).
- Don't print directly — use `helpers/console_output.py::ConsoleOutput.print`. Inside the plugin it routes to `gcode.respond_info`; in the CLI it falls back to `print`.
- New files start with the standard GPL-3.0 header block (see any existing file). The first non-blank lines are `# Shake&Tune: 3D printer analysis tools` … `# File:` … `# Description:`.
- `.git-blame-ignore-revs` exists — large reformat commits are listed there; preserve it when touching git history.
