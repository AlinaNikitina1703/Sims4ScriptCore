import build_buy
import date_and_time
import services
import sims4
from interactions.base.super_interaction import SuperInteraction
from interactions.interaction_finisher import FinishingType
from server_commands.argument_helpers import get_tunable_instance
from sims4.resources import Types
from sims4.resources import Types, get_resource_key

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import distance_to, push_sim_function, clear_sim_instance, \
    update_interaction_tuning, \
    get_filters, get_venue, get_guid64
from scripts_core.sc_script_vars import sc_Vars, sc_DisabledAutonomy, AutonomyState
from scripts_core.sc_util import error_trap, clean_string


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
            if sc_Vars.DEBUG:
                if hasattr(si, 'shortname'):
                    debugger('Setting allow_autonomous for {} to {}'.format(si.shortname(), enable))
                else:
                    debugger('Setting allow_autonomous for {} to {}'.format(si.__name__, enable))
            si.allow_autonomous = enable
            return True
        else:
            # SI no longer exists
            if sc_Vars.DEBUG:
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

    def run_interaction_filter(self, interaction):
        if not hasattr(interaction, "guid64"):
            return False
        zone = services.current_zone_id()
        current_venue = build_buy.get_current_venue(zone)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)

        action = interaction.__class__.__name__.lower()
        target = interaction.target.__class__.__name__.lower()

        autonomy = interaction.sim.sim_info.autonomy
        now = services.time_service().sim_now
        if not hasattr(interaction, "interaction_timeout"):
            update_interaction_tuning(get_guid64(interaction), "interaction_timeout", now)
        elif not interaction.interaction_timeout:
            interaction.interaction_timeout = now

        if not hasattr(interaction, "is_user_directed"):
            update_interaction_tuning(get_guid64(interaction), "is_user_directed", False)

        venue = get_venue()
        # Add new stereos for metalheads
        if "metal" in action:
            sc_Vars.stereos_on_lot = [obj for obj in services.object_manager().get_all() if "stereo" in str(obj).lower()]

        if "residential" not in venue:
            # Neat Sims will not clean on any lot other than residential
            instance_manager = services.get_instance_manager(Types.TRAIT)
            key = instance_manager.get(get_resource_key(16858, Types.TRAIT))
            if interaction.sim.sim_info.has_trait(key) and autonomy == AutonomyState.FULL:
                autonomy = AutonomyState.NO_CLEANING
                interaction.sim.sim_info.autonomy = AutonomyState.NO_CLEANING

        if "mixer_social" in action:
            if now - interaction.interaction_timeout > date_and_time.create_time_span(minutes=1):
                if sc_Vars.tag_sim_for_debugging:
                    name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                    if name in sc_Vars.tag_sim_for_debugging:
                        debugger("Sim: {} {} - Timeout: ({}) {}".format(interaction.sim.first_name,
                                                                        interaction.sim.last_name, get_guid64(interaction),
                                                                        action), 2, True)
                sc_Vars.disabled_autonomy_list.insert(0, sc_DisabledAutonomy(interaction.sim.sim_info, get_guid64(interaction)))
                if len(sc_Vars.disabled_autonomy_list) > 24:
                    sc_Vars.disabled_autonomy_list.pop()
                interaction.cancel(FinishingType.KILLED, 'Filtered')
                return False

        if autonomy == AutonomyState.DISABLED and not interaction.is_user_directed:
            # Filter code
            filters = get_filters("enabled")
            if filters is not None:
                indexes = [f for f in filters if f in action or f in str(get_guid64(interaction))]
                if not indexes:
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("Sim: {} {} - Enable Filtered: ({}) {} Target: {} Autonomy: {}".format(
                                interaction.sim.first_name, interaction.sim.last_name, get_guid64(interaction), action,
                                interaction.target, interaction.allow_autonomous), 2, True)

                    sc_Vars.disabled_autonomy_list.insert(0, sc_DisabledAutonomy(interaction.sim.sim_info,
                                                                                 get_guid64(interaction)))
                    if len(sc_Vars.disabled_autonomy_list) > 999:
                        sc_Vars.disabled_autonomy_list.pop()
                    interaction.cancel(FinishingType.KILLED, 'Filtered')
                    return False
                else:
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("Sim: {} - Indexes: {}".format(name, indexes), 2, True)

        if autonomy == AutonomyState.LIMITED_ONLY and not interaction.is_user_directed:
            if hasattr(interaction.target, "is_outside"):
                if not interaction.target.is_outside:
                    interaction.cancel(FinishingType.KILLED, 'Filtered')
                    return False

        if autonomy == AutonomyState.FULL and not interaction.is_user_directed or \
                autonomy == AutonomyState.LIMITED_ONLY and not interaction.is_user_directed or \
                autonomy == AutonomyState.NO_CLEANING and not interaction.is_user_directed:
            filters = get_filters("disabled")
            if filters is not None:
                indexes = [f for f in filters if f in action or f in str(get_guid64(interaction))]
                if indexes:
                    for index in indexes:
                        if sc_Vars.tag_sim_for_debugging:
                            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                            if name in sc_Vars.tag_sim_for_debugging:
                                debugger("Sim: {} {} - Index: {} Filtered: ({}) {} Target: {} Autonomy: {}".format(
                                    interaction.sim.first_name, interaction.sim.last_name, index, get_guid64(interaction),
                                    action, interaction.target, interaction.allow_autonomous), 2, True)

                        sc_Vars.disabled_autonomy_list.insert(0, sc_DisabledAutonomy(interaction.sim.sim_info,
                                                                                     get_guid64(interaction)))
                        if len(sc_Vars.disabled_autonomy_list) > 999:
                            sc_Vars.disabled_autonomy_list.pop()
                        interaction.cancel(FinishingType.KILLED, 'Filtered')
                        return False

        if hasattr(interaction.sim.sim_info, "routine_info"):
            if not interaction.is_user_directed:
                filters = interaction.sim.sim_info.routine_info.filtered_actions
                if filters is not None:
                    if [f for f in filters if f in action or f in str(get_guid64(interaction))]:
                        if sc_Vars.tag_sim_for_debugging:
                            name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                            if name in sc_Vars.tag_sim_for_debugging:
                                debugger("Sim: {} {} - Role Filtered: ({}) {} Target: {} Autonomy: {}".format(
                                    interaction.sim.first_name, interaction.sim.last_name, get_guid64(interaction), action,
                                    interaction.target, interaction.allow_autonomous), 2, True)

                        sc_Vars.disabled_autonomy_list.insert(0, sc_DisabledAutonomy(interaction.sim.sim_info,
                                                                                     get_guid64(interaction)))
                        if len(sc_Vars.disabled_autonomy_list) > 999:
                            sc_Vars.disabled_autonomy_list.pop()
                        interaction.cancel(FinishingType.USER_CANCEL, 'Filtered')
                        return False
        return True

    def prepare_gen(self: SuperInteraction):
        try:
            if sc_Vars.DISABLE_MOD:
                return True
            action = self.__class__.__name__.lower()
            name = "{} {}".format(self.sim.first_name, self.sim.last_name)

            if sc_Vars.tag_sim_for_debugging:
                if name in sc_Vars.tag_sim_for_debugging:
                    debugger("Sim: {} {} - Interaction: {} Target: {} User Directed: {}".format(self.sim.first_name,
                                                                                                self.sim.last_name,
                                                                                                action,
                                                                                                clean_string(
                                                                                                    str(self.target)),
                                                                                                self.is_user_directed), 2, True)

            if not self.is_user_directed:
                if [i for i in self.sim.get_all_running_and_queued_interactions() if "sleep" in str(i).lower() or "_nap" in str(i).lower()]:
                    cur_stat = get_tunable_instance((Types.STATISTIC), 'motive_energy', exact_match=True)
                    tracker = self.sim.get_tracker(cur_stat)
                    cur_value = tracker.get_value(cur_stat) if tracker is not None else 0
                    if cur_value < 95:
                        clear_sim_instance(self.sim.sim_info, "sleep|nap|relax", True)
                        return False
                    else:
                        clear_sim_instance(self.sim.sim_info, "sleep|nap")
                        return False

            if not sc_Autonomy.run_interaction_filter(self, self):
                return False

            sc_Vars.non_filtered_autonomy_list.insert(0, sc_DisabledAutonomy(self.sim.sim_info, get_guid64(self)))
            autonomy_choices = []
            [autonomy_choices.append(x) for x in sc_Vars.non_filtered_autonomy_list if x not in autonomy_choices]
            sc_Vars.non_filtered_autonomy_list = autonomy_choices
            if len(sc_Vars.non_filtered_autonomy_list) > 24:
                sc_Vars.non_filtered_autonomy_list.pop()
            return True
        except BaseException as e:
            error_trap(e)
