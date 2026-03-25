# Geometric Chuck (Python)
![Sample Screen](GeoChuck.png)
A small Python app that simulates a geometric chuck with multiple gear stages and draws the resulting output path.

When launched, the app opens directly into interactive mode using the `test` preset.

## What this app does

- Models a chain of gear stages with:
  - Radius
  - p
  - q
  - phase
- Samples points over many rotations
- Plots the resulting curve with Matplotlib
- Optionally saves output to PNG/SVG/PDF
- Includes an interactive slider UI for live stage tuning

## Quick start

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python app.py
```

Interactive controls include:

- Stage selector
- Add stage button (duplicates the currently selected stage)
- Delete stage button
- Randomize button (randomizes all stages for the current stage count)
- Export button (appends current settings to `saved_geos.json`)
- Radius, p, q, and phase sliders for the selected stage
- Integerize checkbox (forces Radius, p, q, and phase to integer values)
- Invert stage checkbox (flips the selected stage direction)
- Turns slider (changes path length)
- Reset and Save buttons

The interactive editor always keeps at least 2 stages.

## Editing gear stages

Presets are defined near the top of `app.py` as a dictionary of stage lists.

Each stage looks like:

```python
{"radius": 26.0, "p": -3.0, "q": 1.0, "phase": 20.0}
```

- `radius`: vector length contribution
- `p`: numerator-like angular factor
- `q`: denominator-like angular factor (cannot be `0`)
- `phase`: fixed offset in degrees

The stage ratio is computed as `p / q`. Negative values in `p` or `q` reverse rotational direction.

Experiment by changing `p`, `q`, and phase values to discover new patterns.
