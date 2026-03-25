from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


@dataclass(frozen=True)
class GearStage:
    """Single stage in a geometric chuck chain.

    Attributes:
        radius: Radius contribution from this stage.
        p: Numerator-like angular factor.
        q: Denominator-like angular factor (must not be 0).
        phase_deg: Static angle offset in degrees.
    """

    radius: float
    p: float
    q: float
    phase_deg: float = 0.0

    @property
    def ratio(self) -> float:
        if self.q == 0:
            raise ValueError("q must not be 0")
        return self.p / self.q

    @property
    def phase_rad(self) -> float:
        return math.radians(self.phase_deg)


class GeometricChuck:
    """Simulates a multi-stage geometric chuck drawing head."""

    def __init__(self, stages: Sequence[GearStage]) -> None:
        if not stages:
            raise ValueError("At least one stage is required.")
        self.stages = list(stages)

    def angle_multipliers(self) -> list[float]:
        """Compute per-stage angular multipliers matching geometric.py.

        For stage n, the path uses:
        theta_n = M_n * base_angle + phase_n
        where M_0 = 1 and:
        M_n = M_(n-1) + product(-ratio_k) for k in [0, n-1]
        """
        multipliers = [1.0]

        for stage_index in range(1, len(self.stages)):
            product = 1.0
            for prior_stage in self.stages[:stage_index]:
                product *= -prior_stage.ratio
            multipliers.append(multipliers[-1] + product)

        return multipliers

    def point(self, base_angle: float) -> tuple[float, float]:
        """Compute a drawing point for a single base angle in radians."""
        x = 0.0
        y = 0.0

        for stage, multiplier in zip(self.stages, self.angle_multipliers()):
            theta = (multiplier * base_angle) + stage.phase_rad
            x += stage.radius * math.cos(theta)
            y += stage.radius * math.sin(theta)

        return x, y

    def sample_path(self, turns: float = 40.0, samples: int = 12_000) -> tuple[list[float], list[float]]:
        """Sample x/y points over several base rotations.

        More turns/samples produce denser and more closed curves.
        """
        if turns <= 0:
            raise ValueError("turns must be > 0")
        if samples < 10:
            raise ValueError("samples must be >= 10")

        xs: list[float] = []
        ys: list[float] = []
        max_angle = turns * 2.0 * math.pi

        for i in range(samples):
            t = max_angle * (i / (samples - 1))
            px, py = self.point(t)
            xs.append(px)
            ys.append(py)

        return xs, ys


def build_stages(raw_stages: Iterable[dict]) -> list[GearStage]:
    """Convert plain dictionaries into validated GearStage objects."""
    stages: list[GearStage] = []

    for index, item in enumerate(raw_stages, start=1):
        try:
            if {"radius", "p", "q"}.issubset(item.keys()):
                stage = GearStage(
                    radius=float(item["radius"]),
                    p=float(item["p"]),
                    q=float(item["q"]),
                    phase_deg=float(item.get("phase", item.get("phase_deg", 0.0))),
                )
            else:
                # Backward compatibility with ratio/arm_length/direction definitions.
                direction = int(item.get("direction", 1))
                if direction not in (-1, 1):
                    raise ValueError("direction must be -1 or 1")

                stage = GearStage(
                    radius=float(item["arm_length"]),
                    p=float(item["ratio"]) * direction,
                    q=1.0,
                    phase_deg=float(item.get("phase_deg", 0.0)),
                )

            if stage.q == 0:
                raise ValueError("q must not be 0")
        except KeyError as exc:
            raise ValueError(f"Stage {index} missing required field: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid values in stage {index}: {item}") from exc

        stages.append(stage)

    if not stages:
        raise ValueError("No stages were defined.")

    return stages
