import services
from sims.sim_info_types import Age

from scripts_core.sc_debugger import debugger
from scripts_core.sc_file import get_config
from scripts_core.sc_jobs import is_sim_in_group, get_venue, get_number_of_sims, \
    has_role, assign_role_title, get_number_of_role_sims, remove_sim_role, get_sim_role, get_work_hours, \
    get_number_of_routine_sims, distance_to_by_room, assign_routine
from scripts_core.sc_script_vars import sc_Vars


class sc_Filter:

    def __init__(self):
        super().__init__()
        self.disallowed_roles = get_config("spawn.ini", "spawn", "roles")
        self.leave_roles = get_config("spawn.ini", "spawn", "leave")

    def has_allowed_role(self, sim):
        zone = services.current_zone()
        venue = get_venue()
        roles = sim.autonomy_component.active_roles()

        if sim.sim_info.routine:
            return True
        if sim == services.get_active_sim():
            return True
        elif sim.sim_info.is_selectable:
            return True
        elif is_sim_in_group(sim):
            return True
        elif sim.sim_info in services.active_household():
            return True
        elif sim.sim_info.household.home_zone_id == zone.id:
            return True
        if sc_Vars.DISABLE_SPAWNS:
            return False
        if not sc_Vars.DISABLE_CULLING and services.time_service().sim_now.hour() < sc_Vars.spawn_time_start and sc_Vars.spawn_time_start > 0 or \
                not sc_Vars.DISABLE_CULLING and services.time_service().sim_now.hour() > sc_Vars.spawn_time_end - 1 and sc_Vars.spawn_time_end > 0:
            return False
        if len(roles) > 1:
            if "leave" in get_sim_role(sim):
                remove_sim_role(sim, "leave")
                return True
        if [role for role in roles if [leave for leave in self.leave_roles if leave == str(role.__class__.__name__).lower()]]:
            assign_routine(sim.sim_info, "leave", False)
            return False
        if not self.add_role_and_trait_sims_to_routine(sim):
            return False
        if [role for role in self.disallowed_roles if has_role(sim, role)] and not sc_Vars.DISABLE_ROUTINE and not sim.sim_info.routine and not "venue_stripclub" in venue:
            return False


        sims_on_lot = get_number_of_sims()
        if sims_on_lot > sc_Vars.MAX_SIMS and not len(sim.autonomy_component.active_roles()):
            return False

        role_sims_on_lot = get_number_of_role_sims()
        if role_sims_on_lot > sc_Vars.MAX_SIMS:
            return False

        if sims_on_lot + role_sims_on_lot > sc_Vars.MAX_SIMS * 1.2:
            return False


        # if disable culling is true that means no sims will be removed, always return true role sims or not.
        # no role sims get auto removed.
        if not sc_Vars.DISABLE_CULLING and not len(sim.autonomy_component.active_roles()):
            return False

        if not sc_Vars.DISABLE_ROLE_TITLES:
            assign_role_title(sim)
        return True

    def add_role_and_trait_sims_to_routine(self, sim):
        venue = get_venue()

        if sc_Vars.DISABLE_ROUTINE:
            return True

        roles = [role for role in sc_Vars.roles if [r for r in sim.autonomy_component.active_roles() if role.title in
            str(r).lower() or role.career.lower() in str(r).lower() and role.career != "None"] or [trait for trait in sim.sim_info.trait_tracker
            if role.title in str(trait).lower() or role.career.lower() in str(trait).lower()] and role.career != "None"]
        if not roles:
            return True

        for role in roles:
            if role.venue and not [v for v in role.venue if v in venue]:
                return False
            if not get_work_hours(role.on_duty, role.off_duty) or get_number_of_routine_sims(role.title) >= role.max_staff != -1:
                return False

            # Sims based on traits
            if "metalhead" in role.title:
                stereos = [stereo for stereo in sc_Vars.stereos_on_lot if "broadcaster_Stereo_Metal" in str(stereo._on_location_changed_callbacks)]
                if stereos:
                    stereos.sort(key=lambda obj: distance_to_by_room(obj, sim))
                    for stereo in stereos:
                        if sim.sim_info.age > Age.CHILD and distance_to_by_room(sim, stereo) < 10:
                            assign_routine(sim.sim_info, "metalhead", True, (not sc_Vars.DISABLE_ROLE_TITLES))
                            if sc_Vars.DEBUG:
                                debugger("Metalhead: {}".format(sim.first_name))
                            return True

            # Sims based on roles
            if "butler" in role.title:
                assign_routine(sim.sim_info, "butler", False)
                if sc_Vars.DEBUG:
                    debugger("Butler: {}".format(sim.first_name))
                return True

            if "patient" in role.title:
                assign_routine(sim.sim_info, "patient", False)
                if sc_Vars.DEBUG:
                    debugger("Patient: {}".format(sim.first_name))
                return True

            if "visitor" in role.title:
                assign_routine(sim.sim_info, "visitor", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                if sc_Vars.DEBUG:
                    debugger("Visitor: {}".format(sim.first_name))
                return True

            if "invited" in role.title:
                assign_routine(sim.sim_info, "invited", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                if sc_Vars.DEBUG:
                    debugger("Invited: {}".format(sim.first_name))
                return True

            if "park" in role.title:
                assign_routine(sim.sim_info, "park", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                if sc_Vars.DEBUG:
                    debugger("Park: {}".format(sim.first_name))
                return True

            if "hiker" in role.title:
                assign_routine(sim.sim_info, "hiker", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                if sc_Vars.DEBUG:
                    debugger("Hiker: {}".format(sim.first_name))
                return True

            if "traveler" in role.title:
                if len(sc_Vars.beds_on_lot):
                    assign_routine(sim.sim_info, "traveler", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                    if sc_Vars.DEBUG:
                        debugger("Traveler: {}".format(sim.first_name))
                    return True

            if "gamer" in role.title:
                if not len(sc_Vars.beds_on_lot):
                    assign_routine(sim.sim_info, "gamer", False, (not sc_Vars.DISABLE_ROLE_TITLES))
                    if sc_Vars.DEBUG:
                        debugger("Gamer: {}".format(sim.first_name))
                    return True

            if "mailman" in role.title:
                assign_routine(sim.sim_info, "mailman", False)
                if sc_Vars.DEBUG:
                    debugger("Mailman: {}".format(sim.first_name))
                return True

            if "scientist" in role.title:
                assign_routine(sim.sim_info, "scientist", False)
                if sc_Vars.DEBUG:
                    debugger("Scientist: {}".format(sim.first_name))
                return True

            if "conspiracist" in role.title:
                assign_routine(sim.sim_info, "conspiracist", False)
                if sc_Vars.DEBUG:
                    debugger("Conspiracist: {}".format(sim.first_name))
                return True
        return True