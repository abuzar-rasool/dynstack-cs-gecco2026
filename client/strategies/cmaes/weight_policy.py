"""Linear weight-vector policy: the same runtime and overlays as the GP
champion, but each hook scores candidates with a dot product instead of a
tree. Twenty signed weights, split 6 / 8 / 6 over hooks 2, 4 and 5, in the
feature order of primitives.FEATURES_2/4/5. The defaults are the warm
start; the trainer passes its own."""
from __future__ import annotations

from typing import Sequence

from framework.overlays import OverlayMixin

from strategies.sca_gphh.policy import ScoredStrategy


def _dot(weights: Sequence[float]):
    w = [float(x) for x in weights]
    return lambda *feats: sum(wi * fi for wi, fi in zip(w, feats))


class WeightVectorPolicy(OverlayMixin, ScoredStrategy):

    _WARM_W2: list[float] = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    _WARM_W4: list[float] = [0.0, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    _WARM_W5: list[float] = [0.0, 1.0, 0.0, 0.0, 1.0, 0.0]

    def __init__(
        self,
        *,
        weights2: Sequence[float] | None = None,
        weights4: Sequence[float] | None = None,
        weights5: Sequence[float] | None = None,
    ) -> None:
        super().__init__(
            score2=_dot(weights2 if weights2 is not None else self._WARM_W2),
            score4=_dot(weights4 if weights4 is not None else self._WARM_W4),
            score5=_dot(weights5 if weights5 is not None else self._WARM_W5),
        )
        self._init_overlays(headline_fix=True, digout=True)
