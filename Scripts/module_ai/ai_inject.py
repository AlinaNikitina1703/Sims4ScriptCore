from interactions.base.mixer_interaction import MixerInteraction

from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai_util import error_trap
from scripts_core.sc_inject import safe_inject


@safe_inject(MixerInteraction, 'notify_queue_head')
def ai_notify_queue_head_inject(original, self, *args, **kwargs):
    try:
        AI_Autonomy.notify_queue_head(self)
    except BaseException as e:
        error_trap(e)
        pass
    result = original(self, *args, **kwargs)
    return result
