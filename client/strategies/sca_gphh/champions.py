"""The five shipped champions, one per training stage. Each pins the trees
its run produced. Stage E is the final champion and the policy that placed
2nd in the DynStack GECCO 2026 crane-scheduling competition.

The Stage-D champion is deployed in the Stage-E runtime: its genome comes
from the bare Stage-D search, but as a shipped policy it runs with the
overlays on, which is how it is reported as a champion variant.
"""
from __future__ import annotations

from . import genomes as g
from .stage_a import GPStageA
from .stage_b import GPStageB
from .stage_c import GPStageC
from .stage_e import GPStageE


class ScaGphhStageA(GPStageA):

    def __init__(self) -> None:
        super().__init__(tree4=g.STAGE_A_TREE4, tree5=g.STAGE_A_TREE5)


class ScaGphhStageB(GPStageB):

    def __init__(self) -> None:
        super().__init__(tree2=g.STAGE_B_TREE2)


class ScaGphhStageC(GPStageC):

    def __init__(self) -> None:
        super().__init__(
            tree2=g.STAGE_C_TREE2, tree4=g.STAGE_C_TREE4, tree5=g.STAGE_C_TREE5,
        )


class ScaGphhStageD(GPStageE):

    def __init__(self) -> None:
        super().__init__(
            tree2=g.STAGE_D_TREE2, tree4=g.STAGE_D_TREE4, tree5=g.STAGE_D_TREE5,
        )


class ScaGphhStageE(GPStageE):

    def __init__(self) -> None:
        super().__init__(
            tree2=g.STAGE_E_TREE2, tree4=g.STAGE_E_TREE4, tree5=g.STAGE_E_TREE5,
        )
