import ast
import configparser
import os
import random

import services
import sims4
from sims.sim_info_types import Age
from sims.sim_spawner_service import SimSpawnerService

from scripts_core.sc_clubs import C_ZoneClubs
from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import is_sim_in_group, get_venue, get_number_of_sims, \
    update_lights, \
    add_career_to_sim, set_proper_sim_outfit, remove_all_careers, \
    remove_annoying_buffs, has_role, \
    assign_role_title, clear_jobs, assign_title, assign_routine, clamp, get_work_hours, keep_sims_outside, \
    keep_sim_outside, make_sim_leave, set_autonomy, send_sim_home, get_number_of_role_sims, check_actions, \
    unassign_role, clear_leaving
from scripts_core.sc_message_box import message_box
from scripts_core.sc_routine import ScriptCoreRoutine
from scripts_core.sc_script_vars import sc_Vars, AutonomyState
from scripts_core.sc_sim_tracker import track_sim, load_sim_tracking, save_sim_tracking, update_sim_tracking_info
from scripts_core.sc_spawn_handler import sc_SpawnHandler
from scripts_core.sc_util import error_trap_console, init_sim


class ScriptCoreMain:
    timestamp = None
    index = 0

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def check_sims_ini(self):
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\sims.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        sections = [section for section in config.sections() if section]
        for section in sections:
            sim_list = [sim_info for sim_info in services.sim_info_manager().get_all()
                    if [career for career in sim_info.career_tracker if section in str(career)]
                    or [trait for trait in sim_info.trait_tracker if section in str(trait)]]

            for sim_info in sim_list:
                sim_name = "{} {}".format(sim_info.first_name, sim_info.last_name)

                if "career" in section.lower():
                    career_names = [career for career in sim_info.career_tracker if section in str(career)]
                    if career_names:
                        ScriptCoreMain.update_sims_ini(self, section, sim_name)

                if "trait" in section.lower():
                    available_trait_types = [trait for trait in sim_info.trait_tracker if section in str(trait)]
                    if available_trait_types:
                        ScriptCoreMain.update_sims_ini(self, section, sim_name)

    def sims_ini(self):
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\sims.ini"
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        for career in config.sections():
            if "career" in career.lower():
                trait_list = "Assign Career: {}".format(career)
                sim_names = ast.literal_eval(config.get(career, "sims"))
                for sim_name in sim_names:
                    sim_infos = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.first_name in
                        sim_name and sim_info.last_name in sim_name]
                    for sim_info in sim_infos:
                        trait_list = trait_list + "\nSim: {}".format(sim_name)
                        remove_all_careers(sim_info, "batuu")
                        career_name = add_career_to_sim(career, sim_info)
                if sc_Vars.DEBUG:
                    debugger("{}".format(trait_list))

            elif "trait" in career.lower():
                trait_list = "Assign Trait: {}".format(career)
                sim_names = ast.literal_eval(config.get(career, "sims"))
                for sim_name in sim_names:
                    sim_infos = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.first_name in
                        sim_name and sim_info.last_name in sim_name]
                    for sim_info in sim_infos:
                        trait_list = trait_list + "\nSim: {}".format(sim_name)
                        available_trait_types = [trait for trait in trait_manager.types.values() if not
                            sim_info.has_trait(trait) and career in str(trait)]
                        if available_trait_types:
                            for trait in available_trait_types:
                                if not sim_info.has_trait(trait):
                                    sim_info.add_trait(trait)
                                    if sc_Vars.DEBUG:
                                        debugger("Sim: {} Added Trait: {}".format(sim_name, str(trait)))
                if sc_Vars.DEBUG:
                    debugger("{}".format(trait_list))

    def update_sims_ini(self, career: str, sim_name: str):
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\sims.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section(career):
            if config.has_option(career, "sims"):
                sim_names = ast.literal_eval(config.get(career, "sims"))
            else:
                sim_names = []
        else:
            sim_names = []

        if not [name for name in sim_names if sim_name in name]:
            sim_names.append(sim_name)

        if not config.has_section(career):
            config.add_section(career)
        config.set(career, "sims", str(sim_names))

        with open(filename, 'w') as configfile:
            config.write(configfile)

    def config_ini(self, live=False):
        try:
            from module_simulation.sc_simulation import reset_simulation_to_vanilla, set_simulation_to_custom
        except:
            message_box(None, None, "Simulation", "Cannot load simulation mode!", "GREEN")
            pass
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\config.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        sc_Vars.SELECTED_SIMS_AUTONOMY = config.getint("control", "selected_sims_autonomy")
        sc_Vars.MAX_SIMS = config.getint("control", "max_sims")
        sc_Vars.DEBUG = config.getboolean("control", "debug")
        sc_Vars.DEBUG_AUTONOMY = config.getboolean("control", "debug_autonomy")
        sc_Vars.DISABLE_MOD = config.getboolean("control", "disable_mod")
        sc_Vars.DISABLE_ROUTINE = config.getboolean("control", "disable_routine")
        sc_Vars.DISABLE_SPAWNS = config.getboolean("control", "disable_spawns")
        sc_Vars.DISABLE_CULLING = config.getboolean("control", "disable_culling")
        sc_Vars.DISABLE_ROLE_TITLES = config.getboolean("control", "disable_role_titles")
        sc_Vars.DISABLE_CAREER_TITLES = config.getboolean("control", "disable_career_titles")
        sc_Vars.keep_sims_outside = config.getboolean("control", "keep_sims_outside")
        sc_Vars.select_when_teleport = config.getboolean("control", "select_when_teleport")
        sc_Vars.dont_sleep_on_lot = config.getboolean("control", "dont_sleep_on_lot")
        sc_Vars.disable_tracking = config.getboolean("control", "disable_tracking")
        sc_Vars.disable_forecasts = config.getboolean("control", "disable_forecasts")
        sc_Vars.disable_social_autonomy = config.getboolean("control", "disable_social_autonomy")
        services.weather_service()._icy_conditions_option = not config.getboolean("control", "disable_icy_conditions")
        sc_Vars.update_speed = config.getfloat("control", "update_speed")
        sc_Vars.chance_switch_action = config.getfloat("control", "chance_switch_action")
        sc_Vars.interaction_minutes_run = config.getfloat("control", "action_timeout")
        sc_Vars.chance_role_trait = config.getfloat("control", "chance_role_trait")
        SimSpawnerService.NPC_SOFT_CAP = 255
        sc_Vars.timestamp = 0
        services.sim_spawner_service().set_npc_soft_cap_override(sc_Vars.MAX_SIMS)

    def show_mod_status(self, live=False):
        venue = get_venue()
        zone = services.current_zone()
        lot_x_size = int(services.current_zone().lot.size_x)
        lot_z_size = int(services.current_zone().lot.size_z)
        objects = services.object_manager().get_all()
        number_objects = len(objects)
        number_sims = get_number_of_sims()
        font_color1 = "000000"
        font_color2 = "aa88ff"
        font_color3 = "aa4444"
        font_text1 = "<font color='#{}'>".format(font_color1)
        font_text2 = "<font color='#{}'>".format(font_color2)
        font_text3 = "<font color='#{}'>".format(font_color3)
        end_font_text = "</font>"
        config_text = ""
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\config.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        status_text = "[Venue:] {}\n".format(venue)
        status_text = status_text + "[Zone:] {}\n".format(zone.id)
        status_text = status_text + "[# Objects:] {}\n".format(number_objects)
        status_text = status_text + "[# Sims:] {}\{}\n".format(number_sims, SimSpawnerService.NPC_SOFT_CAP)
        status_text = status_text + "[Lot Size:] {}x{}\n".format(lot_x_size, lot_z_size)

        for each_section in config.sections():
            for (each_key, each_val) in config.items(each_section):
                if live and "disable" in each_key:
                    if "spawns" in each_key:
                        each_val = sc_Vars.DISABLE_SPAWNS
                    elif "mod" in each_key:
                        each_val = sc_Vars.DISABLE_MOD
                    elif "routine" in each_key:
                        each_val = sc_Vars.DISABLE_ROUTINE
                    elif "culling" in each_key:
                        each_val = sc_Vars.DISABLE_CULLING
                    config_text = config_text + "[{}:] ({})\n".format(each_key, each_val)
                elif live and "max_sims" in each_key:
                    each_val = sc_Vars.MAX_SIMS
                    config_text = config_text + "[{}:] ({})\n".format(each_key, each_val)
                else:
                    config_text = config_text + "[{}:] {}\n".format(each_key, each_val)


        config_text = config_text.replace("[", font_text1).replace("]", end_font_text)
        config_text = config_text.replace("(", font_text3).replace(")", end_font_text)
        status_text = status_text.replace("[", font_text2).replace("]", end_font_text)
        message_box(None, None, "Script Core Menu", "{}\n{}".format(status_text, config_text), "PURPLE")

    def load(self):
        ScriptCoreMain.config_ini(self)
        ScriptCoreMain.assign_all_sims(self)

    def spawn_load(self):
        try:
            # TODO: Future tracking system for sims on load. Place sims where they were last time you play
            ScriptCoreMain.config_ini(self)
            if not sc_Vars.disable_tracking:
                for sim in services.sim_info_manager().instanced_sims_gen():
                    load_sim_tracking(sim.sim_info)

        except BaseException as e:
            error_trap_console(e)
            pass

    def spawn_save(self):
        try:
            # TODO: Future tracking system for sims on load. Place sims where they were last time you play
            for sim in services.sim_info_manager().instanced_sims_gen():
                save_sim_tracking(sim.sim_info)

        except BaseException as e:
            error_trap_console(e)
            pass

    def assign_all_sims(self):
        for sim_info in services.sim_info_manager().get_all():
            sim_info.use_object_index = 0
            sim_info.routine = False
            if not sc_Vars.disable_tracking:
                load_sim_tracking(sim_info)
            if sim_info.is_instanced():
                sim = init_sim(sim_info)
                ScriptCoreMain.assign_sim(self, sim)

    def assign_sim(self, sim):
        zone = services.current_zone()
        now = services.time_service().sim_now
        autonomy_service = services.autonomy_service()
        selected_sim_autonomy_enabled = autonomy_service._selected_sim_autonomy_enabled
        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        options_proto = account_data_msg.gameplay_account_data.gameplay_options

        if sim == services.get_active_sim() and options_proto.autonomy_level == options_proto.OFF:
            autonomy_setting = AutonomyState(sc_Vars.SELECTED_SIMS_AUTONOMY)
        elif sim.sim_info.is_selectable and sim != services.get_active_sim() and options_proto.autonomy_level == options_proto.LIMITED:
            autonomy_setting = AutonomyState(sc_Vars.SELECTED_SIMS_AUTONOMY)
        elif sim.sim_info.routine:
            autonomy_setting = sim.sim_info.routine_info.autonomy
        else:
            autonomy_setting = AutonomyState.FULL

        remove_annoying_buffs(sim.sim_info)
        track_sim(sim.sim_info)
        update_sim_tracking_info(sim.sim_info)

        if sim.sim_info.routine and [start_time for start_time in sc_Vars.routine_start_times if
                                     start_time == now.hour()]:
            sc_Vars.routine_sim_index = 0
            sc_Vars._running = False
            sc_Vars._config_loaded = False
            return
        elif sim.sim_info.routine:
            if not sim.sim_info.routine_info.title:
                if not has_role(sim):
                    send_sim_home(sim)
                    return
            if now.hour() >= sim.sim_info.routine_info.off_duty and not sim.sim_info.routine_info.off_duty == 0 or \
                    now.hour() < sim.sim_info.routine_info.on_duty and not sim.sim_info.routine_info.on_duty == 0:
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - off_duty: {}/{}".format(sim.first_name, sim.sim_info.routine_info.off_duty, now.hour()))
                clear_jobs(sim.sim_info)
                assign_title(sim.sim_info, "")
                sim.sim_info.routine = False
                if not sim.sim_info.is_selectable:
                    send_sim_home(sim)
                return
            if sim == services.get_active_sim():
                clear_leaving(sim)
                if not selected_sim_autonomy_enabled:
                    set_autonomy(sim.sim_info, sc_Vars.SELECTED_SIMS_AUTONOMY)
                else:
                    set_autonomy(sim.sim_info, sim.sim_info.routine_info.autonomy)
            elif sim.sim_info.is_selectable:
                clear_leaving(sim)
                set_autonomy(sim.sim_info, autonomy_setting)
            elif sim.sim_info.routine:
                clear_leaving(sim)
                set_autonomy(sim.sim_info, sim.sim_info.routine_info.autonomy)
            if sc_Vars.career_function and sim.sim_info.autonomy != AutonomyState.DISABLED and sim.sim_info.routine:
                sc_Vars.career_function.routine_handler(sim.sim_info)
            return
        elif sim == services.get_active_sim():
            if not selected_sim_autonomy_enabled:
                set_autonomy(sim.sim_info, sc_Vars.SELECTED_SIMS_AUTONOMY)
            else:
                set_autonomy(sim.sim_info, AutonomyState.FULL)
            return
        elif sim.sim_info.is_selectable:
            set_autonomy(sim.sim_info, autonomy_setting)
            return
        elif is_sim_in_group(sim):
            clear_leaving(sim)
            set_autonomy(sim.sim_info, autonomy_setting)
            return
        elif sim.sim_info in services.active_household():
            set_autonomy(sim.sim_info, autonomy_setting)
            return
        elif sim.sim_info.vacation_or_home_zone_id == zone.id:
            clear_leaving(sim)
            set_autonomy(sim.sim_info, AutonomyState.FULL)
            return
        elif has_allowed_role(sim):
            set_autonomy(sim.sim_info, AutonomyState.FULL)
            if sc_Vars.keep_sims_outside:
                keep_sim_outside(sim)
            return
        if sc_Vars.DEBUG:
            debugger("Sim: {} - Filtered".format(sim.first_name))
        make_sim_leave(sim)

    def init_routine(self):
        try:
            if sc_Vars._running and not sc_Vars.DISABLE_MOD:
                sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]
                if not len(sims):
                    return

                if sc_Vars.routine_sim_index >= len(sims):
                    sc_Vars.routine_sim_index = 0
                sim = sims[sc_Vars.routine_sim_index] if len(sims) > sc_Vars.routine_sim_index else sims[0]
                if sc_Vars.DEBUG:
                    debugger("Routine Sim: {} - index: {} autonomy_setting: {}".format(sim.first_name,
                                                                                       sc_Vars.routine_sim_index,
                                                                                       sim.sim_info.autonomy))
                sc_Vars.routine_sim_index += 1
                if sc_Vars.routine_sim_index >= len(sims):
                    sc_Vars.routine_sim_index = 0

                update_lights(False, 0.0)

                if sim.sim_info.is_instanced():
                    ScriptCoreMain.assign_sim(self, sim)

        except BaseException as e:
            error_trap_console(e)

    def init(self):
        try:
            zone = services.current_zone()
            venue = get_venue()
            sc_club = C_ZoneClubs()
            if sc_Vars.DISABLE_MOD:
                return
            if not sc_Vars._config_loaded and not sc_Vars._running:
                if sc_Vars.DEBUG:
                    debugger("\n\n>>>>>>>>>>>>Begin Routine\n\n")
                client = services.client_manager().get_first_client()
                sc_Vars.sim_index = 0
                sc_Vars.routine_sim_index = 0
                if not sc_Vars.custom_routine:
                    sc_Vars.custom_routine = ScriptCoreRoutine()
                sc_Vars.custom_routine.alarm_ini()
                ScriptCoreMain.sims_ini(self)
                ScriptCoreMain.config_ini(self)
                ScriptCoreMain.show_mod_status(self)
                sims4.commands.client_cheat("fps off", client.id)
                update_lights(True, 0.0)
                sc_club.club_setup_on_load(services.get_club_service())
                sc_Vars._config_loaded = True

            if sc_Vars._running:

                for sim_info in list(sc_SpawnHandler.spawned_sims):
                    sim = init_sim(sim_info)
                    if sim:
                        if sim == services.get_active_sim() or sim_info.is_selectable or is_sim_in_group(sim) or sim_info in services.active_household():
                            set_proper_sim_outfit(sim, True)
                        else:
                            set_proper_sim_outfit(sim, False)
                        sc_SpawnHandler.spawned_sims.remove(sim_info)

                sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if not sim.sim_info.routine]
                if not len(sims):
                    return
                if sc_Vars.sim_index >= len(sims):
                    sc_Vars.sim_index = 0
                sim = sims[sc_Vars.sim_index] if len(sims) > sc_Vars.sim_index else sims[0]
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - index: {} autonomy_setting: {}".format(sim.first_name, sc_Vars.sim_index, sim.sim_info.autonomy))
                sc_Vars.sim_index += 1
                if sc_Vars.sim_index >= len(sims):
                    sc_Vars.sim_index = 0

                update_lights(False, 0.0)

                if sim.sim_info.is_instanced():
                    ScriptCoreMain.assign_sim(self, sim)

        except BaseException as e:
            error_trap_console(e)

    def on_build_buy_enter_handler(self):
        update_lights(True, 0.0)

def has_allowed_role(sim):
    zone = services.current_zone()
    venue = get_venue()
    disallowed_roles = ["leave", "patient", "gym", "barista", "bartender", "walkby_wait_for",
                        "infected", "frontdesk", "caterer", "doctor_npc", "gaming", "maid", "celebrity",
                        "chef", "computeruser", "landlord", "vendor", "military"]

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
    if set_random_trait_role(sim):
        return True
    if [role for role in disallowed_roles if has_role(sim, role)] and not sc_Vars.DISABLE_ROUTINE and not "venue_stripclub" in venue:
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

def set_random_trait_role(sim):
    venue = get_venue()
    zone = services.current_zone()
    now = services.time_service().sim_now
    seed = int(sim.sim_id * 0.00000000000001) * int(now.second())
    random.seed(seed)

    roles = [role for role in sc_Vars.roles if [r for r in sim.autonomy_component.active_roles() if role.title in
        str(r).lower()] or [trait for trait in sim.sim_info.trait_tracker if role.career in str(trait)]]

    if roles:
        for role in roles:
            if "butler" in role.title:
                if not role.venue and get_work_hours(role.on_duty, role.off_duty) or \
                        [v for v in role.venue if v in venue] and get_work_hours(role.on_duty, role.off_duty):
                    assign_routine(sim.sim_info, "butler", False)
                    if sc_Vars.DEBUG:
                        debugger("Butler: {}".format(sim.first_name))
                    return True

            if "trait_Lifestyles_FrequentTraveler" in role.career:
                hour = clamp(now.hour(), 0, 20)
                chance = random.uniform(0, 100) * clamp(float(float(hour - 5) * 0.25), 0.0, 1.0)
                if [v for v in role.venue if v in venue] and [obj for obj in services.object_manager().get_all()
                        if role.use_object1 in str(obj).lower()] and chance >= (100 - sc_Vars.chance_role_trait):
                    assign_routine(sim.sim_info, "traveler")
                    if sc_Vars.DEBUG:
                        debugger("Traveler: {} On Chance: {}".format(sim.first_name, chance))
                    return True

            if "Trait_SimPreference_Likes_Music_Metal" in role.career:
                chance = random.uniform(0, 100) * clamp(float(float(now.hour() - 15) * 0.25), 0.0, 1.0)
                if not role.venue and chance >= (100 - sc_Vars.chance_role_trait) and sim.sim_info.age > Age.CHILD or \
                        [v for v in role.venue if v in venue] and chance >= (100 - sc_Vars.chance_role_trait) and \
                        sim.sim_info.age > Age.CHILD:
                    assign_routine(sim.sim_info, "metalhead")
                    if sc_Vars.DEBUG:
                        debugger("Metalhead: {} On Chance: {}".format(sim.first_name, chance))
                    return True

            if "patient" in role.title:
                if not role.venue and get_work_hours(role.on_duty, role.off_duty) or \
                        [v for v in role.venue if v in venue] and get_work_hours(role.on_duty, role.off_duty):
                    assign_routine(sim.sim_info, "patient", False)
                    if sc_Vars.DEBUG:
                        debugger("Patient: {}".format(sim.first_name))
                    return True

            if "visitor" in role.title:
                assign_routine(sim.sim_info, "visitor", False)
                if sc_Vars.DEBUG:
                    debugger("Visitor: {}".format(sim.first_name))
                return True

            if "invited" in role.title:
                if not role.venue and get_work_hours(role.on_duty, role.off_duty) or \
                        [v for v in role.venue if v in venue] and get_work_hours(role.on_duty, role.off_duty):
                    assign_routine(sim.sim_info, "invited", False)
                    if sc_Vars.DEBUG:
                        debugger("Visitor: {}".format(sim.first_name))
                    return True

            if "park" in role.title:
                if not role.venue and get_work_hours(role.on_duty, role.off_duty) or \
                        [v for v in role.venue if v in venue] and get_work_hours(role.on_duty, role.off_duty):
                    assign_routine(sim.sim_info, "park", False)
                    if sc_Vars.DEBUG:
                        debugger("Park: {}".format(sim.first_name))
                    return True

            if "hiker" in role.title:
                if not role.venue and get_work_hours(role.on_duty, role.off_duty) or \
                        [v for v in role.venue if v in venue] and get_work_hours(role.on_duty, role.off_duty):
                    assign_routine(sim.sim_info, "hiker", False)
                    if sc_Vars.DEBUG:
                        debugger("Hiker: {}".format(sim.first_name))
                    return True

    return False

