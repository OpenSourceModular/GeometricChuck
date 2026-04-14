#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Library General Public
#   License as published by the Free Software Foundation; either
#   version 2 of the License, or (at your option) any later version.
#
#   This library  is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Library General Public License for more details.
#
#   You should have received a copy of the GNU Library General Public
#   License along with this library; see the file COPYING.LIB. If not,
#   write to the Free Software Foundation, Inc., 59 Temple Place,
#   Suite 330, Boston, MA  02111-1307, USA
#   Author: Justin Ahrens <justin@ahrens.net>
from __future__ import annotations

from datetime import datetime
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from chuck import GeometricChuck, build_stages


PRESETS: dict[str, list[dict]] = {
    "Default": [
        {"radius": 40.0, "p": 4.0, "q": 1.0, "phase": 0.0},
        {"radius": 26.0, "p": 9.0, "q": 3.0, "phase": 0.0},
    ],
}


class GeometricChuckTkApp:
    def __init__(self, root: tk.Tk, preset: str, turns: float, samples: int, save_path: Path | None) -> None:
        self.root = root
        self.preset = preset
        self.samples = samples
        self.save_path = save_path
        self.min_stages = 2

        self.stage_data = [dict(item) for item in PRESETS[preset]]
        self.initial_stage_data = [dict(item) for item in PRESETS[preset]]
        self.syncing_controls = False

        self.selected_stage_var = tk.IntVar(value=0)
        self.integerize_var = tk.BooleanVar(value=True)
        self.invert_var = tk.BooleanVar(value=False)
        self.auto_turns_var = tk.BooleanVar(value=True)

        self.radius_var = tk.DoubleVar(value=self.stage_data[0]["radius"])
        self.p_var = tk.DoubleVar(value=self.stage_data[0]["p"])
        self.q_var = tk.DoubleVar(value=self.stage_data[0]["q"])
        self.phase_var = tk.DoubleVar(value=self.stage_data[0]["phase"])
        self.turns_var = tk.DoubleVar(value=turns)
        self.initial_turns = turns

        self.polar_guides: list = []

        self.root.title("Geometric Chuck")
        self.root.configure(bg="#f7f4ef")
        self.root.minsize(1200, 760)

        self._build_layout()
        self._build_controls()
        self._build_plot_area()
        self.refresh_stage_selector(target_stage=0)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.controls_frame = ttk.Frame(self.root, padding=12)
        self.controls_frame.grid(row=0, column=0, sticky="ns")

        self.plot_frame = ttk.Frame(self.root, padding=10)
        self.plot_frame.grid(row=0, column=1, sticky="nsew")
        self.plot_frame.columnconfigure(0, weight=1)
        self.plot_frame.rowconfigure(0, weight=1)

    def _build_controls(self) -> None:
        row = 0

        ttk.Label(self.controls_frame, text="Stage").grid(row=row, column=0, sticky="w")
        row += 1

        self.stage_selector = ttk.Combobox(self.controls_frame, state="readonly", width=20)
        self.stage_selector.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self.stage_selector.bind("<<ComboboxSelected>>", self.on_stage_selected)
        row += 1

        button_row = ttk.Frame(self.controls_frame)
        button_row.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_row, text="Add Stage", command=self.on_add_stage).pack(side="left", padx=(0, 4))
        ttk.Button(button_row, text="Delete Stage", command=self.on_delete_stage).pack(side="left")
        row += 1

        self.radius_scale = self._make_scale(row, "Radius", self.radius_var, 0.0, 100.0, self.update_stage_from_controls)
        row += 1
        self.p_scale = self._make_scale(row, "p", self.p_var, -32.0, 32.0, self.update_stage_from_controls)
        row += 1
        self.q_scale = self._make_scale(row, "q", self.q_var, -32.0, 32.0, self.update_stage_from_controls)
        row += 1
        self.phase_scale = self._make_scale(row, "Phase", self.phase_var, -180.0, 180.0, self.update_stage_from_controls)
        row += 1
        self.turns_scale = self._make_scale(row, "Turns", self.turns_var, 1.0, 200.0, self.on_turns_changed)
        row += 1

        ttk.Checkbutton(
            self.controls_frame,
            text="Integerize stage vars",
            variable=self.integerize_var,
            command=self.on_integer_toggle,
        ).grid(row=row, column=0, sticky="w", pady=(6, 0))
        row += 1

        ttk.Checkbutton(
            self.controls_frame,
            text="Invert stage",
            variable=self.invert_var,
            command=self.on_invert_toggle,
        ).grid(row=row, column=0, sticky="w")
        row += 1

        ttk.Checkbutton(
            self.controls_frame,
            text="Auto turns",
            variable=self.auto_turns_var,
            command=self.on_auto_turns_toggle,
        ).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        actions_1 = ttk.Frame(self.controls_frame)
        actions_1.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(actions_1, text="Reset", command=self.on_reset).pack(side="left", padx=(0, 4))
        ttk.Button(actions_1, text="Random", command=self.on_randomize).pack(side="left", padx=(0, 4))
        ttk.Button(actions_1, text="Export", command=self.on_export).pack(side="left")
        row += 1

        actions_2 = ttk.Frame(self.controls_frame)
        actions_2.grid(row=row, column=0, sticky="ew")
        ttk.Button(actions_2, text="SVG", command=self.on_export_svg).pack(side="left", padx=(0, 4))
        ttk.Button(actions_2, text="Save", command=self.on_save).pack(side="left")

    def _build_plot_area(self) -> None:
        self.figure = Figure(figsize=(8.8, 6.8), dpi=110, facecolor="#f7f4ef")
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#fdfcf8")
        (self.line,) = self.ax.plot([], [], color="#083d77", linewidth=0.5)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        self.configure_axes()

    def _make_scale(
        self,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        min_value: float,
        max_value: float,
        callback,
    ) -> tk.Scale:
        frame = ttk.Frame(self.controls_frame)
        frame.grid(row=row, column=0, sticky="ew", pady=2)
        ttk.Label(frame, text=label).pack(anchor="w")
        scale = tk.Scale(
            frame,
            orient="horizontal",
            from_=min_value,
            to=max_value,
            resolution=0.1,
            variable=variable,
            command=lambda _value: callback(),
            length=320,
            bg="#f7f4ef",
            highlightthickness=0,
            troughcolor="#ddd6c9",
        )
        scale.pack(anchor="w")
        return scale

    def selected_index(self) -> int:
        return int(self.selected_stage_var.get())

    def clamp_stage_value(self, value: int) -> int:
        return max(0, min(len(self.stage_data) - 1, value))

    def stage_label(self, index: int) -> str:
        return f"Stage {index}"

    def rebuild_stage_selector(self, target_stage: int) -> None:
        labels = [self.stage_label(index) for index in range(len(self.stage_data))]
        self.stage_selector["values"] = labels
        self.selected_stage_var.set(target_stage)
        self.stage_selector.set(self.stage_label(target_stage))

    def refresh_stage_selector(self, target_stage: int | None = None) -> None:
        if target_stage is None:
            target_stage = self.clamp_stage_value(self.selected_index())
        else:
            target_stage = self.clamp_stage_value(target_stage)

        self.selected_stage_var.set(target_stage)
        self.rebuild_stage_selector(target_stage)
        self.sync_controls_from_stage()
        self.auto_set_turns()
        self.update_plot()

    def should_integerize(self) -> bool:
        return bool(self.integerize_var.get())

    def should_auto_turns(self) -> bool:
        return bool(self.auto_turns_var.get())

    def auto_set_turns(self) -> None:
        if not self.should_auto_turns():
            return

        periods = self.compute_periods()
        new_turns = float(max(1, min(periods, 1000)))

        self.syncing_controls = True
        if new_turns > float(self.turns_scale.cget("to")):
            self.turns_scale.configure(to=new_turns)
        self.turns_var.set(new_turns)
        self.syncing_controls = False

    def is_stage_inverted(self, stage: dict) -> bool:
        return (stage["p"] < 0.0) != (stage["q"] < 0.0)

    def sync_invert_toggle_from_stage(self) -> None:
        desired_state = self.is_stage_inverted(self.stage_data[self.selected_index()])
        self.invert_var.set(desired_state)

    def sanitize_stage_values(
        self,
        radius_value: float,
        p_value: float,
        q_value: float,
        phase_value: float,
    ) -> tuple[float, float, float, float]:
        if self.should_integerize():
            radius_value = float(round(radius_value))
            p_value = float(round(p_value))
            q_value = float(round(q_value))
            phase_value = float(round(phase_value))

        if q_value == 0.0:
            q_value = -1.0 if (p_value < 0.0 or self.q_var.get() < 0.0) else 1.0

        return radius_value, p_value, q_value, phase_value

    def random_nonzero_value(self) -> float:
        if self.should_integerize():
            choices = [value for value in range(-10, 11) if value != 0]
            return float(random.choice(choices))

        q_value = 0.0
        while q_value == 0.0:
            q_value = random.uniform(-10.0, 10.0)
        return q_value

    def random_stage(self) -> dict[str, float]:
        if self.should_integerize():
            return {
                "radius": float(random.randint(0, 50)),
                "p": float(random.randint(-10, 10)),
                "q": self.random_nonzero_value(),
                "phase": float(random.randint(0, 180)),
            }

        return {
            "radius": random.uniform(0.0, 50.0),
            "p": random.uniform(-10.0, 10.0),
            "q": self.random_nonzero_value(),
            "phase": random.uniform(0.0, 180.0),
        }

    def compute_periods(self) -> int:
        multipliers = GeometricChuck(build_stages(self.stage_data)).angle_multipliers()
        denominators = []
        for multiplier in multipliers:
            frac = Fraction(multiplier).limit_denominator(1000)
            denominators.append(abs(frac.denominator))
        unique_denominators = set(denominators) or {1}
        return math.lcm(*unique_denominators)

    def compact_number(self, value: float) -> int | float:
        if float(value).is_integer():
            return int(value)
        return float(value)

    def stage_entry(self, stage: dict) -> dict[str, int | float]:
        return {
            "p": self.compact_number(stage["p"]),
            "q": self.compact_number(stage["q"]),
            "radius": float(stage["radius"]),
            "phase": float(stage["phase"]),
        }

    def build_path(self) -> tuple[list[float], list[float]]:
        chuck = GeometricChuck(build_stages(self.stage_data))
        return chuck.sample_path(turns=float(self.turns_var.get()), samples=self.samples)

    def configure_axes(self) -> None:
        self.ax.spines["left"].set_visible(False)
        self.ax.spines["bottom"].set_visible(False)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")

        for guide in self.polar_guides:
            guide.remove()
        self.polar_guides.clear()

        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        radius = min(abs(x_min), abs(x_max), abs(y_min), abs(y_max))
        radius = max(radius, 1.0)

        for angle_deg in range(0, 360, 45):
            theta = math.radians(angle_deg)
            x_end = radius * math.cos(theta)
            y_end = radius * math.sin(theta)
            (guide_line,) = self.ax.plot(
                [0.0, x_end],
                [0.0, y_end],
                color="#9ca3af",
                linewidth=0.6,
                linestyle="--",
                zorder=0,
            )
            self.polar_guides.append(guide_line)

    def update_plot(self) -> None:
        xs2, ys2 = self.build_path()
        self.line.set_data(xs2, ys2)
        self.line.set_linewidth(0.5)

        max_x = max((abs(value) for value in xs2), default=1.0)
        max_y = max((abs(value) for value in ys2), default=1.0)
        x_limit = max(max_x * 1.05, 1.0)
        y_limit = max(max_y * 1.05, 1.0)

        self.ax.set_xlim(-x_limit, x_limit)
        self.ax.set_ylim(-y_limit, y_limit)
        self.ax.set_aspect("equal", adjustable="box")
        self.configure_axes()

        selected_stage = self.selected_index()
        self.ax.set_title(f"Geometric Chuck - {self.preset} (stage {selected_stage}/{len(self.stage_data) - 1})")
        self.canvas.draw_idle()

    def sync_controls_from_stage(self) -> None:
        idx = self.selected_index()
        stage = self.stage_data[idx]
        radius_value, p_value, q_value, phase_value = self.sanitize_stage_values(
            stage["radius"],
            stage["p"],
            stage["q"],
            stage["phase"],
        )
        self.stage_data[idx]["radius"] = radius_value
        self.stage_data[idx]["p"] = p_value
        self.stage_data[idx]["q"] = q_value
        self.stage_data[idx]["phase"] = phase_value

        self.syncing_controls = True
        self.radius_var.set(radius_value)
        self.p_var.set(p_value)
        self.q_var.set(q_value)
        self.phase_var.set(phase_value)
        self.sync_invert_toggle_from_stage()
        self.syncing_controls = False

    def on_stage_selected(self, _event: object = None) -> None:
        label = self.stage_selector.get()
        try:
            target_stage = self.clamp_stage_value(int(label.rsplit(" ", 1)[-1]))
        except (ValueError, IndexError):
            return

        self.selected_stage_var.set(target_stage)
        self.sync_controls_from_stage()
        self.update_plot()

    def update_stage_from_controls(self) -> None:
        if self.syncing_controls:
            return

        idx = self.selected_index()
        radius_value, p_value, q_value, phase_value = self.sanitize_stage_values(
            self.radius_var.get(),
            self.p_var.get(),
            self.q_var.get(),
            self.phase_var.get(),
        )

        if (
            self.radius_var.get() != radius_value
            or self.p_var.get() != p_value
            or self.q_var.get() != q_value
            or self.phase_var.get() != phase_value
        ):
            self.syncing_controls = True
            self.radius_var.set(radius_value)
            self.p_var.set(p_value)
            self.q_var.set(q_value)
            self.phase_var.set(phase_value)
            self.syncing_controls = False

        self.stage_data[idx]["radius"] = radius_value
        self.stage_data[idx]["p"] = p_value
        self.stage_data[idx]["q"] = q_value
        self.stage_data[idx]["phase"] = phase_value

        self.syncing_controls = True
        self.sync_invert_toggle_from_stage()
        self.syncing_controls = False

        self.auto_set_turns()
        self.update_plot()

    def on_turns_changed(self) -> None:
        if self.syncing_controls:
            return
        self.update_plot()

    def on_add_stage(self) -> None:
        idx = self.selected_index()
        new_stage = dict(self.stage_data[idx])
        self.stage_data.insert(idx + 1, new_stage)
        self.refresh_stage_selector(target_stage=idx + 1)

    def on_delete_stage(self) -> None:
        if len(self.stage_data) <= self.min_stages:
            messagebox.showinfo("Geometric Chuck", "Cannot delete stage: at least 2 stages are required.")
            return

        idx = self.selected_index()
        self.stage_data.pop(idx)
        self.refresh_stage_selector(target_stage=idx)

    def on_reset(self) -> None:
        self.stage_data[:] = [dict(stage) for stage in self.initial_stage_data]
        self.refresh_stage_selector(target_stage=0)

        if not self.should_auto_turns():
            self.syncing_controls = True
            self.turns_var.set(self.initial_turns)
            self.syncing_controls = False
            self.update_plot()

    def on_randomize(self) -> None:
        for index in range(len(self.stage_data)):
            self.stage_data[index] = self.random_stage()

        self.refresh_stage_selector(target_stage=self.selected_index())

    def on_save(self) -> None:
        target = self.save_path if self.save_path is not None else Path("output") / f"{self.preset}_interactive.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.figure.savefig(target, bbox_inches="tight", pad_inches=0.2)
        print(f"Saved image to: {target}")

    def on_export_svg(self) -> None:
        xs2, ys2 = self.build_path()
        pattern_fig = Figure(figsize=(8, 8), dpi=120)
        pattern_ax = pattern_fig.add_axes([0.0, 0.0, 1.0, 1.0])
        pattern_fig.patch.set_alpha(0.0)
        pattern_ax.set_facecolor("none")
        pattern_ax.plot(xs2, ys2, color="#083d77", linewidth=0.5)
        pattern_ax.set_aspect("equal", adjustable="box")
        pattern_ax.axis("off")

        max_x = max((abs(value) for value in xs2), default=1.0)
        max_y = max((abs(value) for value in ys2), default=1.0)
        x_limit = max(max_x * 1.05, 1.0)
        y_limit = max(max_y * 1.05, 1.0)
        pattern_ax.set_xlim(-x_limit, x_limit)
        pattern_ax.set_ylim(-y_limit, y_limit)

        target = Path("output") / f"{self.preset}_interactive.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        pattern_fig.savefig(target, format="svg", bbox_inches="tight", pad_inches=0.0, transparent=True)
        print(f"Exported SVG to: {target}")

    def on_export(self) -> None:
        self.update_stage_from_controls()

        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": "geometric",
            "periods": self.compute_periods(),
            "samples": self.samples,
            "stages": [self.stage_entry(stage) for stage in self.stage_data],
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

    def on_integer_toggle(self) -> None:
        self.sync_controls_from_stage()
        self.auto_set_turns()
        self.update_plot()

    def on_invert_toggle(self) -> None:
        if self.syncing_controls:
            return

        idx = self.selected_index()
        stage = self.stage_data[idx]
        desired_inverted = bool(self.invert_var.get())
        current_inverted = self.is_stage_inverted(stage)

        if desired_inverted == current_inverted:
            return

        if stage["p"] != 0.0:
            stage["p"] *= -1.0
        elif stage["q"] != 0.0:
            stage["q"] *= -1.0

        self.sync_controls_from_stage()
        self.update_plot()

    def on_auto_turns_toggle(self) -> None:
        self.auto_set_turns()
        self.update_plot()


def main() -> None:
    root = tk.Tk()
    GeometricChuckTkApp(
        root=root,
        preset="Default",
        turns=1.0,
        samples=6000,
        save_path=None,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
