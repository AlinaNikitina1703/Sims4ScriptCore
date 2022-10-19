import inspect
import os

import alarms
import clock
import date_and_time
import element_utils
import enum
import services
import sims4
from module_ai.ai_util import error_trap, clean_string
from autonomy.autonomy_modes_tuning import AutonomyModesTuning
from interactions.base.mixer_interaction import MixerInteraction
from interactions.base.super_interaction import SuperInteraction
from interactions.context import InteractionSource
from interactions.utils.route_fail import route_failure
from routing.route_events.route_event import RouteEvent
from sims.sim import Sim
from sims.sim_info import SimInfo
from socials.group import SocialGroup

setattr(MixerInteraction, "EXIT_SOCIALS_ENABLED", True)
setattr(SuperInteraction, "FILTER_QUEUE_ENABLED", False)
setattr(MixerInteraction, "DEBUG", False)
setattr(SuperInteraction, "DEBUG", False)
setattr(SuperInteraction, "DEBUG_TRACK", None)
setattr(SuperInteraction, "EXIT_SOCIALS_ENABLED", True)
setattr(SuperInteraction, "FILTER_CLEANUP_ENABLED", True)
setattr(MixerInteraction, "DEBUG_ONLY_MEAN", False)
setattr(MixerInteraction, "DEBUG_TRACK", None)
setattr(SuperInteraction, "interaction_timeout", None)
setattr(MixerInteraction, "interaction_timeout", None)
setattr(SimInfo, "autonomy", 3)
setattr(Sim, "autonomy", 3)

SocialGroup.maximum_sim_count = 16
SocialGroup.radius_scale = 1.0

def check_object(obj):
    output = ""
    for att in dir(obj):
        if hasattr(obj, att):
            output = output + "\n(" + str(att) + "): " + clean_string(str(getattr(obj, att)))
    datapath = os.path.abspath(os.path.dirname(__file__))
    filename = datapath + r"\{}.log".format("check")
    if os.path.exists(filename):
        append_write = 'a'  # append if already exists
    else:
        append_write = 'w'  # make a new file if not
    file = open(filename, append_write)
    file.write("{}".format(output))
    file.close()

class Behavior(enum.Int):
    MEAN = 1
    FRIENDLY = 2
    ROMANTIC = 3

class AISimCallback:
    def __init__(self, sim, behavior, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.behavior = behavior
        self.sim = sim

class AIBehavior:
    def __init__(self, sim, target, behavior, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.behavior = behavior
        self.sim = sim
        self.target = target

class AIAutonomy:
    def __init__(self, sim, autonomy, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.autonomy = autonomy
        self.sim = sim

class AIAction:
    def __init__(self, sim, action, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.action = action
        self.sim = sim

class AICheckSimQueue:
    def __init__(self, sim, action, action_id, timeout, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.action = action
        self.action_id = action_id
        self.sim = sim
        self.timeout = timeout

class AIKeepInRoom:
    def __init__(self, sim, target, room, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.room = room
        self.target = target
        self.sim = sim

class AIObjectTracker:
    def __init__(self, sim, target, obj, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.obj = obj
        self.target = target
        self.sim = sim


class AISocials(SocialGroup):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def _create_adjustment_alarm(self):
        if self._adjustment_alarm is not None:
            alarms.cancel_alarm(self._adjustment_alarm)
        self._adjustment_alarm = alarms.add_alarm(self, clock.interval_in_sim_minutes(1), self._adjustment_alarm_callback)

    def _adjustment_alarm_callback(self, _):
        # ld_notice(None, "Adjustment Alarm", "Running!", False, "GREEN")
        if self._adjustment_alarm is not None:
            self._adjustment_alarm = None
            self._create_adjustment_alarm()

    def attach(self, interaction):
        try:

            sim_count = self.get_active_sim_count()
            mood = interaction.sim.sim_info.get_mood()
            if mood is not None:
                sim_mood = mood.guid64
            else:
                sim_mood = 0
            if sim_mood == 14632 and sim_count > 2:
                return

            sis = self._si_registry.setdefault(interaction.sim, set())
            should_add = not sis
            sis.add(interaction)

            if should_add:
                self._add(interaction.sim, interaction)
            self._refresh_all_attached_si_conditional_actions()
        except BaseException as e:
            error_trap(e)

    def create_time_span(self, days=0, hours=0, minutes=0, seconds=0):
        num_sim_seconds = days * date_and_time.SECONDS_PER_DAY + hours * date_and_time.SECONDS_PER_HOUR + \
            minutes * date_and_time.SECONDS_PER_MINUTE + seconds
        time_in_ticks = num_sim_seconds * date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND
        return date_and_time.TimeSpan(time_in_ticks)

def ai_handle_transition_failure(sim, source_interaction_target, transition_interaction, failure_reason=None, failure_object_id=None):
    if not transition_interaction.visible:
        if not transition_interaction.always_show_route_failure:
            pass
        return
    elif not transition_interaction.route_fail_on_transition_fail:
        return
    elif transition_interaction.is_adjustment_interaction():
        return
    else:

        def _do_transition_failure(timeline):
            if source_interaction_target is not None:
                sim.add_lockout(source_interaction_target, AutonomyModesTuning.LOCKOUT_TIME)
            if transition_interaction is None:
                return
            if transition_interaction.context.source == InteractionSource.AUTONOMY:
                return
            yield from element_utils.run_child(timeline, route_failure(sim, transition_interaction, failure_reason, failure_object_id))

        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\{}.log".format("social")
        if os.path.exists(filename):
            append_write = 'a'  # append if already exists
        else:
            append_write = 'w'  # make a new file if not
        file = open(filename, append_write)
        file.write("\n{} {}\nAction: {} Failed!\n\n".format(sim.first_name, sim.last_name, str(transition_interaction)))
        file.close()

        return _do_transition_failure

class AIRouteEvent(RouteEvent):

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def debugger(self, debug_text, frame=1, full_frame=False, write=False, force=False):
        try:
            if self.DEBUG or self.DEBUG_TRACK == self.sim or force:
                # 0 is root function info, 1 is function info from where its running and 2 is parent calling function
                now = services.time_service().sim_now
                total_stack = inspect.stack()  # total complete stack
                total_depth = len(total_stack)  # length of total stack
                frameinfo = total_stack[frame][0]  # info on rel frame

                func_name = frameinfo.f_code.co_name
                filename = os.path.basename(frameinfo.f_code.co_filename)
                line_number = frameinfo.f_lineno  # of the call
                func_firstlineno = frameinfo.f_code.co_firstlineno

                debug_text = "\n{}\n".format(now) + debug_text
                if full_frame:
                    for stack in total_stack:
                        frameinfo = stack[0]
                        func_name = frameinfo.f_code.co_name
                        filename = os.path.basename(frameinfo.f_code.co_filename)
                        line_number = frameinfo.f_lineno
                        debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
                else:
                    debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
                if write:
                    datapath = os.path.abspath(os.path.dirname(__file__))
                    filename = datapath + r"\{}.log".format("debugger")
                    if os.path.exists(filename):
                        append_write = 'a'  # append if already exists
                    else:
                        append_write = 'w'  # make a new file if not
                    file = open(filename, append_write)
                    file.write("\n{}".format(debug_text))
                    file.close()
                else:
                    client = services.client_manager().get_first_client()
                    sims4.commands.cheat_output(debug_text, client.id)
        except:
            pass

    def prepare_route_event(self, sim, defer_process_until_execute=False):
        try:
            self.event_data = self.event_type()
            if hasattr(self.event_data, "animation_elements"):
                action = str(self.event_data.animation_elements).lower()
                if "environmentalreaction_smell_positive" in action:
                    AIRouteEvent.debugger(self, "Sim: {} {} - Killed: {}".format(sim.first_name,
                                                                            sim.last_name, action))
                    return
            if hasattr(self.event_data, 'defer_process_until_execute'):
                self.event_data.defer_process_until_execute = defer_process_until_execute
            self.event_data.prepare(sim)
        except BaseException as e:
            error_trap(e)


SocialGroup.attach = AISocials.attach
SocialGroup._create_adjustment_alarm = AISocials._create_adjustment_alarm
SocialGroup._adjustment_alarm_callback = AISocials._adjustment_alarm_callback
RouteEvent.prepare_route_event = AIRouteEvent.prepare_route_event
