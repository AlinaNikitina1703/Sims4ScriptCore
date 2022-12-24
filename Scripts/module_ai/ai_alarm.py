import alarms
import date_and_time
from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai import AIMain
from module_ai.ai_socials import Behavior
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap


class AIAlarm(AIMain):

    def __init__(self):
        super().__init__()
        self.alarm_handle = None

    def pick_on_sim_alarm(self):
        try:
            if self.alarm_handle is not None:
                self.end_alarm()
            self.init_socials()
            self.alarm_handle = alarms.add_alarm(self, (date_and_time.TimeSpan(4000)),
                                                    self.pick_on_sim_callback,
                                                    repeating=True, cross_zone=False)
        except BaseException as e:
            error_trap(e)

    def socialize_alarm(self):
        try:
            if self.alarm_handle is not None:
                self.end_alarm()
            self.init_socials()
            self.alarm_handle = alarms.add_alarm(self, (date_and_time.TimeSpan(4000)),
                                                    self.socialize_callback,
                                                    repeating=True, cross_zone=False)
        except BaseException as e:
            error_trap(e)

    def snowball_fight_alarm(self):
        try:
            if self.alarm_handle is not None:
                self.end_alarm()
            self.alarm_handle = alarms.add_alarm(self, (date_and_time.TimeSpan(2000)),
                                                    self.snowball_fight_callback,
                                                    repeating=True, cross_zone=False)
        except BaseException as e:
            error_trap(e)

    def basketball_alarm(self):
        try:
            if self.alarm_handle is not None:
                self.end_alarm()
            self.alarm_handle = alarms.add_alarm(self, (date_and_time.TimeSpan(6000)),
                                                    self.basketball_callback,
                                                    repeating=True, cross_zone=False)
        except BaseException as e:
            error_trap(e)

    def pick_on_sim_callback(self, _):
        self.socialize(Behavior.MEAN)
        if not len(AI_Autonomy.behavior_queue):
            self.end_alarm()

    def socialize_callback(self, _):
        self.socialize()
        if not len(AI_Autonomy.behavior_queue):
            self.end_alarm()

    def snowball_fight_callback(self, _):
        self.snowball_fight()
        if not len(AI_Autonomy.behavior_queue):
            self.end_alarm()

    def basketball_callback(self, _):
        self.basketball()
        if not len(AI_Autonomy.behavior_queue):
            self.end_alarm()

    def end_alarm(self, title=None, text=None):
        if self.alarm_handle is None:
            return
        alarms.cancel_alarm(self.alarm_handle)
        self.alarm_handle = None
        if title and text:
            message_box(None, None, title, text, "GREEN")

    def get_alarm(self):
        return self.alarm_handle
