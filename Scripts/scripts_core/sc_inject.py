import inspect
from functools import wraps

from clubs.club_enums import ClubGatheringStartSource
from clubs.club_gathering_situation import ClubGatheringSituation
from clubs.club_service import ClubService
from interactions.base.mixer_interaction import MixerInteraction
from interactions.base.super_interaction import SuperInteraction
from postures.posture_graph import PostureGraphService
from sims.sim_info_base_wrapper import SimInfoBaseWrapper
from sims.sim_info_manager import SimInfoManager
from singletons import DEFAULT
from zone import Zone

from module_outfit.sc_outfit_functions import generate_outfit
from scripts_core.sc_autonomy import sc_Autonomy
from scripts_core.sc_clubs import sc_club_gathering_start_handler, sc_club_gathering_end_handler, \
    sc_club_on_zone_load_handler
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_util import error_trap
from scripts_core.sc_zone import sc_zone_update, sc_zone_on_build_buy_enter_handler, sc_zone_on_build_buy_exit_handler


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

@safe_inject(Zone, 'update')
def sc_run_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    sc_zone_update(self)
    return result

@safe_inject(Zone, 'on_build_buy_enter')
def sc_run_zone_on_build_buy_enter(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    sc_zone_on_build_buy_enter_handler(self)
    return result

@safe_inject(Zone, 'on_build_buy_exit')
def sc_run_zone_on_build_buy_exit(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    sc_zone_on_build_buy_exit_handler(self)
    return result

@safe_inject(Zone, 'on_loading_screen_animation_finished')
def sc_run_zone_load_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        ScriptCoreMain.load(self)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(SimInfoManager, 'on_all_households_and_sim_infos_loaded')
def sc_on_all_households_and_sim_infos_loaded(original, self, client, *args, **kwargs):
    result = original(self, client, *args, **kwargs)
    try:
        ScriptCoreMain.load(self)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(Zone, 'on_teardown')
def sc_on_zone_teardown(original, self, client, *args, **kwargs):
    try:
        ScriptCoreMain.spawn_save(self)
    except BaseException as e:
        error_trap(e)
        pass

    result = original(self, client, *args, **kwargs)
    return result

@safe_inject(PostureGraphService, "get_segmented_paths")
def sc_get_segmented_paths(original, self,
                           sim, posture_dest_list,
                           additional_template_list,
                           interaction, participant_type,
                           valid_destination_test,
                           valid_edge_test, preferences,
                           final_constraint, included_sis, *args, **kwargs):
    result = None
    try:
        result = original(self, sim, posture_dest_list,
                          additional_template_list,
                          interaction, participant_type,
                          valid_destination_test,
                          valid_edge_test, preferences,
                          final_constraint, included_sis, *args, **kwargs)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(SimInfoBaseWrapper, 'generate_outfit')
def sc_generate_outfit(original, self, outfit_category, outfit_index=0, tag_list=(), filter_flag=DEFAULT, body_type_flags=DEFAULT, **kwargs):
    result = original(self, outfit_category, outfit_index, tag_list, filter_flag, body_type_flags, **kwargs)

    try:
        generate_outfit(self, outfit_category, outfit_index)
    except BaseException as e:
        error_trap(e)
        pass

    return result
