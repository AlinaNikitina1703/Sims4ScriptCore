import alarms
import sims4

import services
from reset import ResettableElement

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import clear_sim_instance
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import clean_string, error_trap, error_trap_console


def simulation_timeout(timeline, handle):
    try:
        element_str = clean_string(str(handle.element))

        sim_info = get_sim_from_timeline(handle)
        if sim_info:
            name = "{} {}".format(sim_info.first_name, sim_info.last_name)
        else:
            name = None

        action = None
        debug_text = "\nClogged element on timeline: Sim: {} - Action: {}\nTimeline:\n{}\nElement:\n{}". \
            format(name, action, clean_string(str(timeline)), element_str)
        client = services.client_manager().get_first_client()
        sims4.commands.cheat_output(debug_text, client.id)
        if sc_Vars.DEBUG:
            debugger(debug_text, 1, False, True)

        if timeline is services.time_service().sim_timeline:
            timeline.hard_stop(handle)
        else:
            timeline.hard_stop(handle)

    except BaseException as e:
        error_trap(e)
        pass

def simulation_handler(timeline):
    try:
        if timeline is services.time_service().sim_timeline:
            for i, handle in enumerate(timeline.heap):
                if handle.element is not None:
                    if isinstance(handle.element, ResettableElement):
                        element_str = clean_string(str(handle.element))
                        if sc_Vars.DEBUG:
                            debugger(element_str, 1, False, True)

    except BaseException as e:
        error_trap_console(e)
        pass

def hard_stop_or_soft(timeline, handle):
    sim_info = get_sim_from_timeline(handle)
    if sim_info:
        clear_sim_instance(sim_info, "sit", True)
    else:
        timeline.hard_stop(handle)

def get_sim_from_timeline(handle):
    sim_info = None
    try:
        element_str = clean_string(str(handle.element))
        sim = None
        sim_info = None
        v1 = element_str.split("of sim")
        v2 = ["", ""]
        if len(v1):
            v2 = v1[1].split(", interaction")
            if len(v2):
                sim_id = int(v2[0], 16)
                sim_info = services.sim_info_manager().get(sim_id)
                sim = sim_info.get_sim_instance()
    except:
        pass
    return sim_info

