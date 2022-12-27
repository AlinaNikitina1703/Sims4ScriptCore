from interactions.interaction_finisher import FinishingType

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import get_guid64, get_filters, get_venue, clear_sim_queue_of, enable_distance_autonomy, \
    check_interaction_on_private_objects, push_sim_function, clear_sim_instance
from scripts_core.sc_script_vars import sc_Vars, AutonomyState, sc_DisabledAutonomy
from scripts_core.sc_util import error_trap


def sc_filter_autonomy_actions(self, interaction):
    try:
        if filter_disabled_autonomy_actions(interaction):
            interaction.cancel(FinishingType.KILLED, 'Filtered')
            return False
        if filter_full_autonomy_actions(interaction):
            interaction.cancel(FinishingType.KILLED, 'Filtered')
            return False
        if filter_routine_autonomy(interaction):
            interaction.cancel(FinishingType.KILLED, 'Filtered')
            return False
        if filter_private_objects(interaction):
            interaction.cancel(FinishingType.KILLED, 'Filtered')
            return False
        return True
    except BaseException as e:
        error_trap(e)
        return True

def sc_filter_queue_actions(self, *args, **kwargs):
    action = self.__class__.__name__.lower()
    sim_autonomy = self.sim.sim_info.autonomy

    if sc_Vars.enable_distance_autonomy:
        if enable_distance_autonomy(self, sc_Vars.action_distance_autonomy, sc_Vars.chat_distance_autonomy, sc_Vars.distance_autonomy_messages):
            return

    # HACK: Currently not used.
    if "add_to_world" in action:
        return

    # HACK: Drinks added to world from inventory are auto refilled.
    if "put_down_anywhere" in action:
        push_sim_function(self.sim, self.target, 99066, False)
        return

    # HACK Bartender fix
    if sim_autonomy == AutonomyState.ROUTINE_FOOD:
        if sc_Vars.tag_sim_for_debugging:
            name = "{} {}".format(self.sim.first_name, self.sim.last_name)
            if name in sc_Vars.tag_sim_for_debugging:
                debugger("Sim: {} {} - Queue: {}".format(self.sim.first_name, self.sim.last_name, action), 2, True)

        if "createglass" in action:
            clear_sim_instance(self.sim.sim_info, "practice|tricks|chat")
            return
        if "practice" in action or "tricks" in action:
            clear_sim_instance(self.sim.sim_info, "chat")
            return
        if "chat" in action:
            clear_sim_instance(self.sim.sim_info, "practice|tricks")
            return

def filter_disabled_autonomy_actions(interaction):
    sim_autonomy = interaction.sim.sim_info.autonomy
    action = interaction.__class__.__name__.lower()

    if sim_autonomy == AutonomyState.DISABLED and not interaction.is_user_directed:
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
                return True
            else:
                if sc_Vars.tag_sim_for_debugging:
                    name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
                    if name in sc_Vars.tag_sim_for_debugging:
                        debugger("Sim: {} - Indexes: {}".format(name, indexes), 2, True)
    return False

def filter_full_autonomy_actions(interaction):
    if not hasattr(interaction, "guid64"):
        return True
    sim_autonomy = interaction.sim.sim_info.autonomy
    action = interaction.__class__.__name__.lower()

    if sim_autonomy == AutonomyState.FULL and not interaction.is_user_directed or \
            sim_autonomy == AutonomyState.LIMITED_ONLY and not interaction.is_user_directed or \
            sim_autonomy == AutonomyState.NO_CLEANING and not interaction.is_user_directed:
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
                    return True
    return False

def filter_routine_autonomy(interaction):
    if not hasattr(interaction, "guid64"):
        return False
    action = interaction.__class__.__name__.lower()
    sim_autonomy = interaction.sim.sim_info.autonomy
    venue = get_venue()
    if not interaction.sim.sim_info.routine:
        return False
    if sim_autonomy == AutonomyState.FULL:
        if "residential" not in venue and "mop" not in action and "vacuum" not in action and "dust" not in action and "trash" not in action \
                and "dish" not in action and "wash" not in action and "clean" not in action:
            return False
        elif "residential" in venue:
            return False

    if sim_autonomy == AutonomyState.DISABLED:
        return False

    if interaction.is_user_directed:
        return False

    if sim_autonomy == AutonomyState.ROUTINE_MEDICAL:
        if "research" in action or "chemistry" in action or "analysis" in action or "browse_web" in action \
                or "examine" in action or "hospital" in action or "xray" in action or "treadmill" in action \
                or "sit" in action or "computer_use" in action or "social" in action or "chat" in action \
                or "stand" in action or "analyze" in action or "makecall" in action or "takecall" in action \
                or "page" in action:
            return False
        if "hospitalexambed" in action:
            if "cleanbed" not in action:
                return False

    if sim_autonomy == AutonomyState.ROUTINE_FOOD:
        if "cook" in action or "bake" in action or "food" in action or "put_away" in action \
                or "oven" in action or "fridge" in action or "espresso" in action or "stove" in action \
                or "craft" in action or "tend" in action or "counter" in action or "carry" in action \
                or "loaddishes" in action or "bar" in action or "chat" in action or "makedrink" in action \
                or "cleanup" in action or "stand" in action or "clean" in action or "collect" in action \
                or "practice" in action or "tricks" in action or "createglass" in action or "waiter" in action \
                or "putdown" in action or "put_down" in action or "drink" in action or "shaker" in action:
            return False

    if sim_autonomy == AutonomyState.ON_BREAK:
        if "order" in action or "tobacco_purchase" in action:
            return False
        if [i for i in interaction.sim.get_all_running_and_queued_interactions()
            if "frontdesk_staff" in str(i).lower()]:
            clear_sim_queue_of(interaction.sim.sim_info, 104626)
            return False

    if sim_autonomy == AutonomyState.ROUTINE_ORDERLY:
        # front desk check
        # if a call to use the front desk pops up and sim is browsing web it will be killed
        if "frontdesk" in action:
            if not [i for i in interaction.sim.get_all_running_and_queued_interactions()
                    if "browse" in str(i).lower()]:
                return False
        # if a call to browse web pops up and sim is using front desk it will be killed
        if "browse" in action:
            if not [i for i in interaction.sim.get_all_running_and_queued_interactions()
                    if "frontdesk" in str(i).lower()]:
                return False

        if "mop" in action or "vacuum" in action or "dust" in action or "trash" in action \
                or "dish" in action or "wash" in action or "clean" in action or "frontdesk" in action \
                or "browse" in action or "throw_away" in action or "carry" in action:
            return False

    if sim_autonomy == AutonomyState.NO_CLEANING:
        if "mop" not in action and "vacuum" not in action and "dust" not in action and "trash" not in action \
                and "dish" not in action and "wash" not in action and "clean" not in action:
            return False

    if sc_Vars.tag_sim_for_debugging:
        name = "{} {}".format(interaction.sim.first_name, interaction.sim.last_name)
        if name in sc_Vars.tag_sim_for_debugging:
            debugger("Routine Sim: {} {} - Killed: {}".format(interaction.sim.first_name, interaction.sim.last_name,
                                                              action), 2, True)

    sc_Vars.disabled_autonomy_list.insert(0, sc_DisabledAutonomy(interaction.sim.sim_info, get_guid64(interaction)))
    if len(sc_Vars.disabled_autonomy_list) > 999:
        sc_Vars.disabled_autonomy_list.pop()
    return True

def filter_private_objects(interaction):
    # New private objects code
    if sc_Vars.private_objects and not interaction.sim.sim_info.is_selectable and not interaction.sim.sim_info.routine and interaction.target:
        if not check_interaction_on_private_objects(interaction.sim, interaction.target, interaction):
            return True
    return False

