from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.base.super_interaction import SuperInteraction
from interactions.context import QueueInsertStrategy
from interactions.utils.tunable import TunableContinuation
from sims4.localization import LocalizationHelperTuning, _create_localized_string
from sims4.tuning.tunable import OptionalTunable


class ASM_PoseInteraction(SuperInteraction):
    __qualname__ = 'ASM_PoseInteraction'

    def __init__(self, *args, pose_name=None, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.pose_name = pose_name

    def setup_asm_default(self, asm, *args, **kwargs):
        asm.set_parameter('pose_name', self.pose_name)
        return (super().setup_asm_default)(asm, *args, **kwargs)

class ASM_PoseSuperInteraction(ImmediateSuperInteraction):
    pose_name = "a2a_mischief_NT_youFarted_fail_x"
    __qualname__ = 'ASM_PoseSuperInteraction'
    TEXT_INPUT_POSE_NAME = 'pose_name'
    INSTANCE_TUNABLES = {'actor_continuation':OptionalTunable(tunable=TunableContinuation(locked_args={'actor': ParticipantType.Actor}))}

    def _run_interaction_gen(self, timeline):
        self.interaction_parameters['pose_name'] = ASM_PoseSuperInteraction.pose_name
        self.push_tunable_continuation((self.actor_continuation), pose_name=ASM_PoseSuperInteraction.pose_name,
                                       insert_strategy=(QueueInsertStrategy.LAST),
                                       actor=(self.target))

