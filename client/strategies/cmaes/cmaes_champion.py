"""The CMA-ES champion: the 20-weight vector selected by its training run.
Weight order follows primitives.FEATURES_2/4/5 and must stay in sync."""
from __future__ import annotations
from .weight_policy import WeightVectorPolicy

_W2 = [5.629581, 0.293981, 0.389349, -0.213181, 2.180611, -2.046250]
_W4 = [-1.868968, 1.769717, 0.157501, -2.235552, -0.243037,
        2.365934, -0.083771, 2.543770]
_W5 = [2.553148, 0.420740, 1.253326, 0.197567, -3.771075, -2.183565]


class CmaesChampion(WeightVectorPolicy):

    def __init__(self) -> None:
        super().__init__(weights2=_W2, weights4=_W4, weights5=_W5)
