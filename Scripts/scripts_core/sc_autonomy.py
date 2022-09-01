import os

import build_buy
import date_and_time
import enum
import services
import sims4
from interactions.base.super_interaction import SuperInteraction
from interactions.interaction_finisher import FinishingType
from interactions.interaction_queue import BucketBase
from server_commands.argument_helpers import get_tunable_instance
from sims.sim import Sim
from sims.sim_info import SimInfo
from sims.sim_log import log_interaction
from sims4.resources import Types
from sims4.resources import Types, get_resource_key

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import distance_to, push_sim_function, clear_sim_queue_of, clear_sim_instance, \
    make_sim_leave, update_interaction_tuning, \
    get_filters, assign_routine, get_object_info, distance_to_by_room, get_venue
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap, clean_string


class AutonomyState(enum.Int):
    UNDEFINED = -1
    DISABLED = 0
    LIMITED_ONLY = 1
    MEDIUM = 2
    FULL = 3
    ROUTINE_MEDICAL = 4
    ROUTINE_ORDERLY = 5
    NO_CLEANING = 6
    ON_BREAK = 7
    ROUTINE_PATIENT = 8
    ROUTINE_FOOD = 9
    ROUTINE_WORKER = 10
    ROUTINE_OFFICE = 11
    ROUTINE_POLICE = 12
    ROUTINE_MILITARY = 14
    CUSTOM_AI = 15


setattr(SimInfo, "autonomy", AutonomyState.FULL)
setattr(SimInfo, "choice", 0)
setattr(Sim, "autonomy", AutonomyState.FULL)

class sc_AutonomyQueue:
    def __init__(self, sim, autonomy, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.autonomy = autonomy
        self.sim = sim

class sc_Autonomy:
    behavior_queue = []
    action_queue = []
    autonomy_queue = []
    sim_callback_queue = []
    keep_in_room = []
    posture_target_list = []
    add_to_world_flag = False

    def __init__(self):
        super().__init__()

    def sleeping_in_room(self, sim):
        interactions = sim.get_all_running_and_queued_interactions()
        room = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)
        if [action for action in interactions if "sleep" in str(action).lower()]:
            return room
        return -2

    def can_do_in_room(self):
        try:
            room = build_buy.get_room_id(self.target.zone_id, self.target.position, self.target.level)
        except:
            room = -1
            pass
        if [sim for sim in services.sim_info_manager().instanced_sims_gen() if
            sc_Autonomy.sleeping_in_room(self, sim) == room and room > 0]:
            if "clean" in str(self).lower():
                for commodity in self.target.commodity_tracker:
                    if "exambed_dirtiness" in str(commodity).lower():
                        commodity.set_value(100)
                    if "commodity_dirtiness" in str(commodity).lower():
                        commodity.set_value(100)
            elif "puddle" in str(self.target).lower() or "dust" in str(self.target).lower():
                self.target.destroy()
            elif "seating_sit" in str(self).lower():
                for obj in services.object_manager().get_all():
                    if "sit" in str(obj).lower() or "chair" in str(obj).lower() or "sofa" in str(obj).lower():
                        obj_room = build_buy.get_room_id(obj.zone_id, obj.position, obj.level)
                        dist = distance_to(self.sim, obj)
                        if dist < 10:
                            if not [s for s in services.sim_info_manager().instanced_sims_gen() if
                                    sc_Autonomy.sleeping_in_room(self, s) == obj_room]:
                                self.cancel(FinishingType.KILLED, 'Filtered')
                                push_sim_function(self.sim, obj, 31564)
                                return True
            elif "sleep" in str(self).lower():
                return True
            return False
        return True

    def get_si(self, guid64):
        # Get the tuning manager for interaction instance types
        tuning_manager = services.get_instance_manager(Types.INTERACTION)
        # Return the SI tuning from the manager
        return tuning_manager.get(guid64)

    def update_si(self, guid64, enable):
        # Get the tuning manager for interaction instance types
        tuning_manager = services.get_instance_manager(Types.INTERACTION)
        # Get the SI tuning from the manager
        si = sc_Autonomy.get_si(self, guid64)
        if si is not None:
            # And set the allow_autonomous tuning entry
            if hasattr(si, 'shortname'):
                debugger('Setting allow_autonomous for {} to {}'.format(si.shortname(), enable))
            else:
                debugger('Setting allow_autonomous for {} to {}'.format(si.__name__, enable))
            si.allow_autonomous = enable
            return True
        else:
            # SI no longer exists
            debugger('Invalid or removed SI: {}'.format(guid64))
            return False

    def get_sim_count_in_social_group(self, target):
        # EA only counts sims in the active social group that are with a queue.
        # This counts all sims in the target groups that have social ties to each other active or not.
        this_count = sum((1 for sim in self.social_group))
        if target.is_sim:
            for that_group in target.get_groups_for_sim_gen():
                if that_group is not None:
                    if that_group != self.social_group:
                        that_count = sum((1 for sim in that_group))
                        if that_count > this_count:
                            this_count = that_count
        return this_count

    def notify_queue_head(self):
        return

    def append(self, interaction):
        result = None

        if not sc_Vars.DISABLE_MOD:
            if not sc_Autonomy.run_interaction_filter(self, interaction):
                return result

            if not sc_Autonomy.run_routine_filter(self, interaction):
                return result

        if sc_Vars.DEBUG_AUTONOMY and not interaction.is_user_directed:
            action = interaction.__class__.__name__.lower()
            debugger("Sim: {} {} - Append: {}".format(interaction.sim.first_name, interaction.sim.last_name, action), 0, True)

        log_interaction('Enqueue', interaction)
        result = self._append(interaction)
        return result

    def insert_next(self, interaction, **kwargs):
        result = None

        if not sc_Vars.DISABLE_MOD:
            if not sc_Autonomy.run_interaction_filter(self, interaction):
                return result

            if not sc_Autonomy.run_routine_filter(self, interaction):
                return result

        if sc_Vars.DEBUG_AUTONOMY and not interaction.is_user_directed:
            action = interaction.__class__.__name__.lower()
            debugger("Sim: {} {} - Insert Next: {}".format(interaction.sim.first_name, interaction.sim.last_name, action), 0, True)

        log_interaction('Enqueue_Next', interaction)
        result = (self._insert_next)(interaction, **kwargs)
        return result

    def run_interaction_filter(self, interaction):
        zone = services.current_zone_id()
        current_venue = build_buy.get_current_venue(zone)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)

        action = interaction.__class__.__name__.lower()
        target = interaction.target.__class__.__name__.lower()

        if sc_Vars.tag_sim_for_debugging:
            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
            if name in sc_Vars.tag_sim_for_debugging:
                if interaction.target:
                    info_string = get_object_info(interaction.target, True)
                    datapath = os.path.abspath(os.path.dirname(__file__))
                    filename = datapath + r"\{}.log".format("object_info")
                    file = open(filename, 'w')
                    file.write("{}\n{}\n".format(target, info_string))
                    file.close()

        autonomy = interaction.sim.sim_info.autonomy
        now = services.time_service().sim_now
        if not hasattr(interaction, "interaction_timeout"):
            update_interaction_tuning(interaction.guid64, "interaction_timeout", now)
        elif not interaction.interaction_timeout:
            interaction.interaction_timeout = now

        if not hasattr(interaction, "is_user_directed"):
            update_interaction_tuning(interaction.guid64, "is_user_directed", False)

        if current_venue is not None:
            venue_tuning = venue_manager.get(current_venue)

            if "residential" not in str(venue_tuning).lower():
                # Neat Sims will not clean on any lot other than residential
                instance_manager = services.get_instance_manager(Types.TRAIT)
                key = instance_manager.get(get_resource_key(16858, Types.TRAIT))
                if interaction.sim.sim_info.has_trait(key) and autonomy == AutonomyState.FULL:
                    autonomy = AutonomyState.NO_CLEANING
                    interaction.sim.sim_info.autonomy = AutonomyState.NO_CLEANING

        if "mixer_social" in action:
            if now - interaction.interaction_timeout > date_and_time.create_time_span(minutes=1):
                debugger("Sim: {} {} - Timeout: {}".format(interaction.sim.first_name, interaction.sim.last_name, action))
                interaction.cancel(FinishingType.KILLED, 'Filtered')
                return False

        if autonomy == AutonomyState.DISABLED and "chat" in action and not interaction.is_user_directed or \
                autonomy == AutonomyState.DISABLED and "social" in action and not interaction.is_user_directed:
            if distance_to_by_room(interaction.sim, interaction.target) > 5:
                debugger("Sim: {} {} - Long Distance: {} Autonomy: {}".format(interaction.sim.first_name, interaction.sim.last_name, action, interaction.allow_autonomous), 2, True)
                for social_group in interaction.sim.get_groups_for_sim_gen():
                    social_group.remove(interaction.target)
                    social_group._resend_members()
                interaction.cancel(FinishingType.KILLED, 'Filtered')
                return False

        if autonomy == AutonomyState.DISABLED and not interaction.is_user_directed:
            filters = get_filters("enabled")
            if filters is not None:
                indexes = [f for f in filters if f in action or f in str(interaction.guid64)]
                if not indexes:
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("Sim: {} {} - Enable Filtered: {} Autonomy: {}".format(interaction.sim.first_name, interaction.sim.last_name, action, interaction.allow_autonomous), 2, True)
                    interaction.cancel(FinishingType.KILLED, 'Filtered')
                    return False
                else:
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("Sim: {} - Indexes: {}".format(name, indexes))

        elif not interaction.is_user_directed:
            filters = get_filters("disabled")
            if filters is not None:
                indexes = [f for f in filters if f in action or f in str(interaction.guid64)]
                if indexes:
                    for index in indexes:
                        #update_interaction_tuning(interaction.guid64, "allow_autonomous", False)
                        if sc_Vars.tag_sim_for_debugging:
                            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                            if name in sc_Vars.tag_sim_for_debugging:
                                debugger("Sim: {} {} - Index: {} Filtered: {} Autonomy: {}".format(interaction.sim.first_name, interaction.sim.last_name, index, action, interaction.allow_autonomous), 2, True)
                        interaction.cancel(FinishingType.KILLED, 'Filtered')
                        return False

            if hasattr(interaction.sim.sim_info, "routine_info"):
                filters = interaction.sim.sim_info.routine_info.filtered_actions
                if filters is not None:
                    if [f for f in filters if f in action or f in str(interaction.guid64)]:
                        if sc_Vars.tag_sim_for_debugging:
                            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                            if name in sc_Vars.tag_sim_for_debugging:
                                debugger("Sim: {} {} - Role Filtered: {} Target: {} Autonomy: {}".format(interaction.sim.first_name, interaction.sim.last_name, action, interaction.target, interaction.allow_autonomous), 2, True)
                        interaction.cancel(FinishingType.USER_CANCEL, 'Filtered')
                        return False
        return True

    def run_routine_filter(self, interaction):
        action = interaction.__class__.__name__.lower()
        autonomy = interaction.sim.sim_info.autonomy
        zone = services.current_zone_id()
        venue = get_venue()

        if autonomy == AutonomyState.FULL:
            if "residential" not in venue and "mop" not in action and "vacuum" not in action and "dust" not in action and "trash" not in action \
                    and "dish" not in action and "wash" not in action and "clean" not in action:
                return True
            elif "residential" in venue:
                return True

        if autonomy == AutonomyState.DISABLED:
            return True

        if interaction.is_user_directed:
            return True

        if autonomy == AutonomyState.ROUTINE_MEDICAL:
            if "research" in action or "chemistry" in action or "analysis" in action or "browse" in action \
                    or "examine" in action or "hospital" in action or "xray" in action or "treadmill" in action \
                    or "sit" in action or "computer_use" in action or "social" in action or "chat" in action \
                    or "stand" in action or "analyze" in action or "makecall" in action or "takecall" in action \
                    or "page" in action:
                return True
            if "hospitalexambed" in action:
                if "cleanbed" not in action:
                    return True

        if autonomy == AutonomyState.ROUTINE_FOOD:
            if "cook" in action or "bake" in action or "food" in action or "put_away" in action \
                    or "oven" in action or "fridge" in action or "espresso" in action or "stove" in action \
                    or "craft" in action or "tend" in action or "counter" in action or "carry" in action \
                    or "loaddishes" in action or "bar" in action or "chat" in action or "makedrink" in action \
                    or "cleanup" in action or "stand" in action or "clean" in action or "collect" in action \
                    or "practice" in action or "tricks" in action or "createglass" in action or "waiter" in action \
                    or "putdown" in action or "put_down" in action or "drink" in action or "shaker" in action:
                return True

        if autonomy == AutonomyState.ON_BREAK:
            if "order" in action or "tobacco_purchase" in action:
                return True
            if [i for i in interaction.sim.get_all_running_and_queued_interactions()
                if "frontdesk_staff" in str(i).lower()]:
                clear_sim_queue_of(interaction.sim.sim_info, 104626)
                return True

        if autonomy == AutonomyState.ROUTINE_ORDERLY:
            # front desk check
            # if a call to use the front desk pops up and sim is browsing web it will be killed
            if "frontdesk" in action:
                if not [i for i in interaction.sim.get_all_running_and_queued_interactions()
                        if "browse" in str(i).lower()]:
                    return True
            # if a call to browse web pops up and sim is using front desk it will be killed
            if "browse" in action:
                if not [i for i in interaction.sim.get_all_running_and_queued_interactions()
                        if "frontdesk" in str(i).lower()]:
                    return True

            if "mop" in action or "vacuum" in action or "dust" in action or "trash" in action \
                    or "dish" in action or "wash" in action or "clean" in action or "frontdesk" in action \
                    or "browse" in action or "throw_away" in action or "carry" in action:
                return True

        if autonomy == AutonomyState.NO_CLEANING:
            if "mop" not in action and "vacuum" not in action and "dust" not in action and "trash" not in action \
                    and "dish" not in action and "wash" not in action and "clean" not in action:
                return True

        if sc_Vars.tag_sim_for_debugging:
            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
            if name in sc_Vars.tag_sim_for_debugging:
                debugger("Routine Sim: {} {} - Killed: {}".format(interaction.sim.first_name, interaction.sim.last_name, action))

        interaction.cancel(FinishingType.KILLED, 'Filtered')
        return False

    def on_added_to_queue(self: SuperInteraction, *args, **kwargs):
        action = self.__class__.__name__.lower()
        target = self.target.__class__.__name__.lower()
        autonomy = self.sim.sim_info.autonomy

        # HACK: Drinks added to world from inventory are auto refilled.
        if "add_to_world" in action:
            sc_Autonomy.add_to_world_flag = True
            return

        # HACK: Drinks added to world from inventory are auto refilled.
        if "put_down_anywhere" in action and sc_Autonomy.add_to_world_flag:
            push_sim_function(self.sim, self.target, 99066, False)
            sc_Autonomy.add_to_world_flag = False
            return

        # HACK Bartender fix
        if autonomy == AutonomyState.ROUTINE_FOOD:
            if sc_Vars.tag_sim_for_debugging:
                name = "{} {}".format(self.sim.first_name, self.sim.last_name)
                if name in sc_Vars.tag_sim_for_debugging:
                    debugger("Sim: {} {} - Queue: {}".format(self.sim.first_name, self.sim.last_name, action))

            if "createglass" in action:
                clear_sim_instance(self.sim.sim_info, "practice|tricks|chat")
                return
            if "practice" in action or "tricks" in action:
                clear_sim_instance(self.sim.sim_info, "chat")
                return
            if "chat" in action:
                clear_sim_instance(self.sim.sim_info, "practice|tricks")
                return

    def kill_interaction(self: SuperInteraction):
        action = self.__class__.__name__
        debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
        self.cancel(FinishingType.KILLED, 'Filtered')

    def prepare_gen(self: SuperInteraction):
        try:
            action = self.__class__.__name__.lower()
            result = None

            if sc_Vars.tag_sim_for_debugging:
                name = "{} {}".format(self.sim.first_name, self.sim.last_name)
                if name in sc_Vars.tag_sim_for_debugging:
                    debugger("Sim: {} {} - Interaction: {} Target: {} User Directed: {}".format(self.sim.first_name, self.sim.last_name, action,
                        clean_string(str(self.target)), self.is_user_directed))

            if [i for i in self.sim.get_all_running_and_queued_interactions()
                    if "sleep" in str(i).lower() or "_nap" in str(i).lower()]:
                cur_stat = get_tunable_instance((Types.STATISTIC), 'motive_energy', exact_match=True)
                tracker = self.sim.get_tracker(cur_stat)
                cur_value = tracker.get_value(cur_stat) if tracker is not None else 0
                if cur_value < 95:
                    clear_sim_instance(self.sim.sim_info, "sleep|nap|relax", True)
                    return
                else:
                    clear_sim_instance(self.sim.sim_info, "sleep|nap")
                    return

            if not sc_Autonomy.run_interaction_filter(self, self):
                return

        except BaseException as e:
            error_trap(e)

def set_autonomy(sim_info, routine=4):
    sim_info.autonomy = AutonomyState(routine)

def send_sim_home(sim):
    try:
        ensemble_service = services.ensemble_service()
        ensemble = ensemble_service.get_visible_ensemble_for_sim(sim)
        if ensemble is not None:
            ensemble.end_ensemble()
        set_autonomy(sim.sim_info, AutonomyState.FULL)
        assign_routine(sim.sim_info, "leave")
        make_sim_leave(sim)

    except BaseException as e:
        error_trap(e)

BucketBase.append = sc_Autonomy.append
BucketBase.insert_next = sc_Autonomy.insert_next
