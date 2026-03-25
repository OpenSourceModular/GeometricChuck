from __future__ import annotations

from datetime import datetime
from fractions import Fraction
import json
import math
from pathlib import Path
import random

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons, Slider

from chuck import GeometricChuck, build_stages


PRESETS: dict[str, list[dict]] = {
    "Default": [
        {"radius": 40.0, "p": 4.0, "q": 1.0, "phase": 0.0},
        {"radius": 26.0, "p": 9.0, "q": 3.0, "phase": 0.0},
    ],
}
def draw_interactive(
    preset: str,
    turns: float,
    samples: int,
    save_path: Path | None,
) -> None:
    min_stages = 2
    stage_data = [dict(item) for item in PRESETS[preset]]
    initial_stage_data = [dict(item) for item in PRESETS[preset]]
    state = {"syncing_controls": False}

    fig = plt.figure(figsize=(10, 9), dpi=120)
    fig.patch.set_facecolor("#f7f4ef")
    ax = fig.add_axes([0.08, 0.38, 0.84, 0.57])
    ax.set_facecolor("#fdfcf8")

    def build_path() -> tuple[list[float], list[float]]:
        chuck = GeometricChuck(build_stages(stage_data))
        return chuck.sample_path(turns=turns_slider.val, samples=samples)

    xs, ys = GeometricChuck(build_stages(stage_data)).sample_path(turns=turns, samples=samples)
    (line,) = ax.plot(xs, ys, color="#083d77", linewidth=0.5)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    def update_plot() -> None:
        xs2, ys2 = build_path()
        line.set_data(xs2, ys2)
        line.set_linewidth(0.5)
        ax.relim()
        ax.autoscale_view()
        ax.set_aspect("equal", adjustable="box")
        selected_stage = int(stage_index_slider.val)
        ax.set_title(f"Geometric Chuck - {preset} (stage {selected_stage}/{len(stage_data) - 1})")
        fig.canvas.draw_idle()

    ax_stage_index = fig.add_axes([0.10, 0.34, 0.56, 0.03], facecolor="#fdfcf8")
    ax_radius = fig.add_axes([0.10, 0.29, 0.56, 0.03], facecolor="#fdfcf8")
    ax_p = fig.add_axes([0.10, 0.24, 0.56, 0.03], facecolor="#fdfcf8")
    ax_q = fig.add_axes([0.10, 0.19, 0.56, 0.03], facecolor="#fdfcf8")
    ax_phase = fig.add_axes([0.10, 0.14, 0.56, 0.03], facecolor="#fdfcf8")
    ax_turns = fig.add_axes([0.10, 0.09, 0.56, 0.03], facecolor="#fdfcf8")
    ax_integer_toggle = fig.add_axes([0.70, 0.18, 0.26, 0.07], facecolor="#fdfcf8")
    ax_invert_toggle = fig.add_axes([0.70, 0.10, 0.26, 0.07], facecolor="#fdfcf8")
    ax_add_stage = fig.add_axes([0.72, 0.24, 0.10, 0.05])
    ax_delete_stage = fig.add_axes([0.84, 0.24, 0.10, 0.05])

    stage_index_slider = Slider(
        ax_stage_index,
        "Stage",
        0,
        len(stage_data) - 1,
        valinit=0,
        valstep=1,
    )
    radius_slider = Slider(ax_radius, "Radius", 0.0, 100.0, valinit=stage_data[0]["radius"])
    p_slider = Slider(ax_p, "p", -10.0, 10.0, valinit=stage_data[0]["p"])
    q_slider = Slider(ax_q, "q", -10.0, 10.0, valinit=stage_data[0]["q"])
    phase_slider = Slider(ax_phase, "Phase", -180.0, 180.0, valinit=stage_data[0]["phase"])
    turns_slider = Slider(ax_turns, "Turns", 1.0, 200.0, valinit=turns)
    integer_toggle = CheckButtons(ax_integer_toggle, ["Integerize stage vars"], [True])
    invert_toggle = CheckButtons(ax_invert_toggle, ["Invert stage"], [False])
    add_stage_button = Button(ax_add_stage, "Add Stage")
    delete_stage_button = Button(ax_delete_stage, "Delete Stage")

    ax_reset = fig.add_axes([0.70, 0.06, 0.06, 0.05])
    reset_button = Button(ax_reset, "Reset")

    ax_randomize = fig.add_axes([0.77, 0.06, 0.06, 0.05])
    randomize_button = Button(ax_randomize, "Random")

    ax_export = fig.add_axes([0.84, 0.06, 0.06, 0.05])
    export_button = Button(ax_export, "Export")

    ax_save = fig.add_axes([0.91, 0.06, 0.06, 0.05])
    save_button = Button(ax_save, "Save")

    def selected_index() -> int:
        return int(stage_index_slider.val)

    def clamp_stage_value(value: int) -> int:
        return max(0, min(len(stage_data) - 1, value))

    def refresh_stage_selector(target_stage: int | None = None) -> None:
        stage_index_slider.valmin = 0
        stage_index_slider.valmax = len(stage_data) - 1
        stage_index_slider.valstep = 1
        ax_stage_index.set_xlim(0, len(stage_data) - 1)

        if target_stage is None:
            target_stage = clamp_stage_value(int(round(stage_index_slider.val)))
        else:
            target_stage = clamp_stage_value(target_stage)

        current_stage = int(round(stage_index_slider.val))
        if current_stage != target_stage:
            stage_index_slider.set_val(target_stage)
        else:
            sync_controls_from_stage()
            update_plot()

    def should_integerize() -> bool:
        return integer_toggle.get_status()[0]

    def is_stage_inverted(stage: dict) -> bool:
        return (stage["p"] < 0.0) != (stage["q"] < 0.0)

    def sync_invert_toggle_from_stage() -> None:
        current_state = invert_toggle.get_status()[0]
        desired_state = is_stage_inverted(stage_data[selected_index()])
        if current_state != desired_state:
            invert_toggle.set_active(0)

    def sanitize_stage_values(radius_value: float, p_value: float, q_value: float, phase_value: float) -> tuple[float, float, float, float]:
        if should_integerize():
            radius_value = float(round(radius_value))
            p_value = float(round(p_value))
            q_value = float(round(q_value))
            phase_value = float(round(phase_value))

        if q_value == 0.0:
            q_value = -1.0 if (p_value < 0.0 or q_slider.val < 0.0) else 1.0

        return radius_value, p_value, q_value, phase_value

    def random_nonzero_value() -> float:
        if should_integerize():
            choices = [value for value in range(-10, 11) if value != 0]
            return float(random.choice(choices))

        q_value = 0.0
        while q_value == 0.0:
            q_value = random.uniform(-10.0, 10.0)
        return q_value

    def random_stage() -> dict[str, float]:
        if should_integerize():
            return {
                "radius": float(random.randint(0, 50)),
                "p": float(random.randint(-10, 10)),
                "q": random_nonzero_value(),
                "phase": float(random.randint(0, 180)),
            }

        return {
            "radius": random.uniform(0.0, 50.0),
            "p": random.uniform(-10.0, 10.0),
            "q": random_nonzero_value(),
            "phase": random.uniform(0.0, 180.0),
        }

    def compute_periods() -> int:
        multipliers = GeometricChuck(build_stages(stage_data)).angle_multipliers()
        denominators = []
        for multiplier in multipliers:
            frac = Fraction(multiplier).limit_denominator(1000)
            denominators.append(abs(frac.denominator))
        unique_denominators = set(denominators) or {1}
        return math.lcm(*unique_denominators)

    def compact_number(value: float) -> int | float:
        if float(value).is_integer():
            return int(value)
        return float(value)

    def stage_entry(stage: dict) -> dict[str, int | float]:
        return {
            "p": compact_number(stage["p"]),
            "q": compact_number(stage["q"]),
            "radius": float(stage["radius"]),
            "phase": float(stage["phase"]),
        }

    def sync_controls_from_stage() -> None:
        idx = selected_index()
        stage = stage_data[idx]
        radius_value, p_value, q_value, phase_value = sanitize_stage_values(
            stage["radius"], stage["p"], stage["q"], stage["phase"]
        )
        stage_data[idx]["radius"] = radius_value
        stage_data[idx]["p"] = p_value
        stage_data[idx]["q"] = q_value
        stage_data[idx]["phase"] = phase_value
        state["syncing_controls"] = True
        radius_slider.set_val(radius_value)
        p_slider.set_val(p_value)
        q_slider.set_val(q_value)
        phase_slider.set_val(phase_value)
        sync_invert_toggle_from_stage()
        state["syncing_controls"] = False

    def update_stage_from_controls(_value: object = None) -> None:
        if state["syncing_controls"]:
            return

        idx = selected_index()
        radius_value, p_value, q_value, phase_value = sanitize_stage_values(
            radius_slider.val,
            p_slider.val,
            q_slider.val,
            phase_slider.val,
        )
        if (
            radius_slider.val != radius_value
            or p_slider.val != p_value
            or q_slider.val != q_value
            or phase_slider.val != phase_value
        ):
            state["syncing_controls"] = True
            radius_slider.set_val(radius_value)
            p_slider.set_val(p_value)
            q_slider.set_val(q_value)
            phase_slider.set_val(phase_value)
            state["syncing_controls"] = False

        stage_data[idx]["radius"] = radius_value
        stage_data[idx]["p"] = p_value
        stage_data[idx]["q"] = q_value
        stage_data[idx]["phase"] = phase_value
        state["syncing_controls"] = True
        sync_invert_toggle_from_stage()
        state["syncing_controls"] = False
        update_plot()

    def on_stage_change(_value: float) -> None:
        clamped_stage = clamp_stage_value(int(round(stage_index_slider.val)))
        if int(round(stage_index_slider.val)) != clamped_stage:
            stage_index_slider.set_val(clamped_stage)
            return

        sync_controls_from_stage()
        update_plot()

    def on_add_stage(_event: object) -> None:
        idx = selected_index()
        new_stage = dict(stage_data[idx])
        stage_data.insert(idx + 1, new_stage)
        refresh_stage_selector(target_stage=idx + 1)

    def on_delete_stage(_event: object) -> None:
        if len(stage_data) <= min_stages:
            print("Cannot delete stage: at least 2 stages are required.")
            return

        idx = selected_index()
        stage_data.pop(idx)
        refresh_stage_selector(target_stage=idx)

    def on_reset(_event: object) -> None:
        stage_data[:] = [dict(stage) for stage in initial_stage_data]

        refresh_stage_selector(target_stage=0)
        turns_slider.set_val(turns)

    def on_randomize(_event: object) -> None:
        for index in range(len(stage_data)):
            stage_data[index] = random_stage()

        refresh_stage_selector(target_stage=selected_index())

    def on_save(_event: object) -> None:
        target = save_path if save_path is not None else Path("output") / f"{preset}_interactive.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target, bbox_inches="tight", pad_inches=0.2)
        print(f"Saved image to: {target}")

    def on_export(_event: object) -> None:
        update_stage_from_controls()

        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "geometric",
            "periods": compute_periods(),
            "samples": samples,
            "stages": [stage_entry(stage) for stage in stage_data],
        }

        target = Path("saved_geos.json")
        entries: list[dict] = []

        if target.exists():
            try:
                with target.open("r", encoding="utf-8") as file_handle:
                    loaded = json.load(file_handle)
                if isinstance(loaded, list):
                    entries = loaded
            except (json.JSONDecodeError, OSError):
                entries = []

        entries.append(record)
        with target.open("w", encoding="utf-8") as file_handle:
            json.dump(entries, file_handle, indent=2)

        print(f"Exported settings to: {target}")

    def on_integer_toggle(_label: str) -> None:
        sync_controls_from_stage()
        update_plot()

    def on_invert_toggle(_label: str) -> None:
        if state["syncing_controls"]:
            return

        idx = selected_index()
        stage = stage_data[idx]
        desired_inverted = invert_toggle.get_status()[0]
        current_inverted = is_stage_inverted(stage)
        if desired_inverted == current_inverted:
            return

        if stage["p"] != 0.0:
            stage["p"] *= -1.0
        elif stage["q"] != 0.0:
            stage["q"] *= -1.0

        sync_controls_from_stage()
        update_plot()

    stage_index_slider.on_changed(on_stage_change)
    radius_slider.on_changed(update_stage_from_controls)
    p_slider.on_changed(update_stage_from_controls)
    q_slider.on_changed(update_stage_from_controls)
    phase_slider.on_changed(update_stage_from_controls)
    turns_slider.on_changed(lambda _value: update_plot())
    integer_toggle.on_clicked(on_integer_toggle)
    invert_toggle.on_clicked(on_invert_toggle)
    add_stage_button.on_clicked(on_add_stage)
    delete_stage_button.on_clicked(on_delete_stage)
    reset_button.on_clicked(on_reset)
    randomize_button.on_clicked(on_randomize)
    export_button.on_clicked(on_export)
    save_button.on_clicked(on_save)

    update_plot()
    plt.show()


def main() -> None:
    draw_interactive(
        preset="Default",
        turns=10.0,
        samples=6000,
        save_path=None,
    )


if __name__ == "__main__":
    main()
