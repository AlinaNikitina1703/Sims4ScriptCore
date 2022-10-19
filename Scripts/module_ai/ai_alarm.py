import alarms
import date_and_time
from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai import AIMain
from module_ai.ai_util import error_trap, message_box
from scripts_core.sc_jobs import push_sim_function


class AIAlarm(AIMain):
    ALARM = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def pick_on_sim_alarm(self):
        try:
            if AIAlarm.ALARM is not None:
                self.end_alarm()
            self.init_socials()
            AIAlarm.ALARM = alarms.add_alarm(self, (date_and_time.TimeSpan(4000)),
                                                    self.pick_on_sim_callback,
                                                    repeating=True, cross_zone=False)
        except BaseException as e:
            error_trap(e)

    def pick_on_sim_callback(self, _):
        self.pick_on_sim()
        if not len(AI_Autonomy.behavior_queue):
            self.end_alarm()

    def end_alarm(self):
        if AIAlarm.ALARM is None:
            return
        alarms.cancel_alarm(AIAlarm.ALARM)
        AIAlarm.ALARM = None
        message_box(None, None, "Pick on Sim", "Stopped picking on sim.", False, "GREEN")
