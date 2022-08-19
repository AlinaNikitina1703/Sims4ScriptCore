import inspect
from functools import wraps
from threading import Event

import services
from clock import ClockSpeedMode
from clubs.club_enums import ClubGatheringStartSource
from clubs.club_gathering_situation import ClubGatheringSituation
from clubs.club_service import ClubService
from interactions.base.mixer_interaction import MixerInteraction
from interactions.base.super_interaction import SuperInteraction
from scheduling import Timeline
from singletons import DEFAULT

from scripts_core.sc_autonomy import sc_Autonomy
from scripts_core.sc_clubs import sc_club_gathering_start_handler, sc_club_gathering_end_handler, \
    sc_club_on_zone_load_handler
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_thread import sc_Watcher
from scripts_core.sc_util import error_trap
from zone import Zone


def safe_inject(target_object, target_function_name, safe=False):
    if safe is True:
        if not hasattr(target_object, target_function_name):

            def _self_wrap(wrap_function):
                return wrap_function

            return _self_wrap

    def _wrap_original_function(original_function, new_function):

        @wraps(original_function)
        def _wrapped_function(*args, **kwargs):
            return new_function(original_function, *args, **kwargs)

        if not inspect.ismethod(original_function):
            return _wrapped_function
        return classmethod(_wrapped_function)

    def _injected(wrap_function):
        original_function = getattr(target_object, target_function_name)
        setattr(target_object, target_function_name, _wrap_original_function(original_function, wrap_function))
        return wrap_function

    return _injected

@safe_inject(ClubService, 'on_gathering_started')
def c_zone_club_gathering_start(original, self, gathering, *args, **kwargs):
    result = original(self, gathering, *args, **kwargs)
    try:
        sc_club_gathering_start_handler(self, gathering.associated_club)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(ClubService, 'on_gathering_ended')
def c_zone_club_gathering_end(original, self, gathering, *args, **kwargs):
    result = original(self, gathering, *args, **kwargs)
    try:
        sc_club_gathering_end_handler(self, gathering.associated_club)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(ClubService, 'on_zone_load')
def c_zone_club_on_zone_load(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        sc_club_on_zone_load_handler(self)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(ClubService, 'start_gathering')
def start_gathering(original, self, club,
                    start_source=ClubGatheringStartSource.DEFAULT,
                    host_sim_id=0,
                    invited_sims=(),
                    zone_id=DEFAULT,
                    ignore_zone_validity=False, **kwargs):

    result = original(self, club,
                      start_source=start_source,
                      host_sim_id=host_sim_id,
                      invited_sims=invited_sims,
                      zone_id=zone_id,
                      ignore_zone_validity=True, **kwargs)
    return result

@safe_inject(ClubGatheringSituation, 'start_situation')
def c_zone_club_situation_start(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        sc_club_gathering_start_handler(self, self.associated_club)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(MixerInteraction, 'notify_queue_head')
def sc_notify_queue_head_inject(original, self, *args, **kwargs):
    sc_Autonomy.notify_queue_head(self)
    result = original(self, *args, **kwargs)
    return result

@safe_inject(SuperInteraction, 'on_added_to_queue')
def sc_on_added_to_queue_inject(original, self, *args, **kwargs):
    sc_Autonomy.on_added_to_queue(self)
    result = original(self, *args, **kwargs)
    return result

@safe_inject(SuperInteraction, 'prepare_gen')
def sc_prepare_gen_inject(original, self, *args, **kwargs):
    sc_Autonomy.prepare_gen(self)
    result = original(self, *args, **kwargs)
    return result

#@safe_inject(Timeline, 'simulate')
def sc_run_timeline_simulate_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)

    try:
        if services.current_zone().is_zone_running:
            is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
            if not is_paused:
                ScriptCoreMain.init(self)
        elif services.current_zone().is_in_build_buy:
            ScriptCoreMain.on_build_buy_enter_handler(self)
        else:
            sc_Vars._running = False
            sc_Vars._config_loaded = False
    except BaseException as e:
        error_trap(e)
        pass

    return result

#@safe_inject(Zone, 'update')
def sc_run_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        if self.is_zone_running:
            is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
            if not is_paused:
                ScriptCoreMain.init(self)
        elif self.is_in_build_buy:
            ScriptCoreMain.on_build_buy_enter_handler(self)
        else:
            sc_Vars._running = False
            sc_Vars._config_loaded = False
    except BaseException as e:
        error_trap(e)
        pass

    return result

#@safe_inject(Zone, 'on_client_connect')
def sc_thread_on_client_connect_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)

    try:
        sc_Event = Event()
        sc_Event.clear()
        thread = sc_Watcher(sc_Event)
        thread.start()
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(Zone, 'on_loading_screen_animation_finished')
def sc_run_zone_load_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        #ScriptCoreMain.load(self)
        sc_Event = Event()
        sc_Event.clear()
        thread = sc_Watcher(sc_Event, True)
        thread.start()
    except BaseException as e:
        error_trap(e)
        pass

    return result