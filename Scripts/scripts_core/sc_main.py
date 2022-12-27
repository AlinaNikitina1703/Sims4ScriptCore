import ast
import configparser
import os

import objects
import services
import sims4
from filters.tunable import TunableSimFilter
from sims.sim_spawner_service import SimSpawnerService

from module_simulation.sc_simulate_autonomy import set_autonomy_distance_cutoff, set_update_autonomy, set_sim_delay
from module_simulation.sc_simulation import set_sim_buffer, set_time_slice
from scripts_core.sc_clubs import C_ZoneClubs
from scripts_core.sc_debugger import debugger
from scripts_core.sc_file import get_config
from scripts_core.sc_filter import sc_Filter
from scripts_core.sc_gohere import make_sim_leave, keep_sim_outside
from scripts_core.sc_jobs import is_sim_in_group, get_venue, get_number_of_sims, \
    fade_lights_in_live_mode, \
    add_career_to_sim, set_proper_sim_outfit, remove_all_careers, \
    remove_annoying_buffs, has_role, \
    clear_jobs, assign_title, clear_leaving, get_important_objects_on_lot, \
    doing_nothing, \
    push_sim_function, check_actions
from scripts_core.sc_message_box import message_box
from scripts_core.sc_routine import ScriptCoreRoutine
from scripts_core.sc_script_vars import sc_Vars, AutonomyState
from scripts_core.sc_sim_tracker import track_sim, load_sim_tracking, save_sim_tracking, update_sim_tracking_info
from scripts_core.sc_spawn_handler import sc_SpawnHandler
from scripts_core.sc_transmogrify import load_material
from scripts_core.sc_util import error_trap_console, init_sim


class ScriptCoreMain:
    timestamp = None
    index = 0
    sim_filter = None

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
        client = services.client_manager().get_first_client()
        if client:
            _connection = client.id
            sims4.commands.client_cheat('bb.moveobjects on', _connection)

        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\config.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        sc_Vars.SELECTED_SIMS_AUTONOMY = config.getint("control", "selected_sims_autonomy")
        sc_Vars.MAX_SIMS = config.getint("control", "max_sims")
        sc_Vars.DEBUG = config.getboolean("debugging", "debug")
        sc_Vars.DEBUG_FULL = config.getboolean("debugging", "full_debug")
        sc_Vars.DEBUG_SPAWN = config.getboolean("debugging", "spawn_debug")
        sc_Vars.DEBUG_AUTONOMY = config.getboolean("debugging", "debug_autonomy")
        sc_Vars.DEBUG_ROUTING = config.getboolean("debugging", "debug_routing")
        sc_Vars.DEBUG_SOCIALS = config.getboolean("debugging", "debug_socials")
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
        sc_Vars.disable_new_sims = config.getboolean("control", "disable_new_sims")
        sc_Vars.enable_distance_autonomy = config.getboolean("distance_autonomy", "enable_distance_autonomy")
        sc_Vars.distance_autonomy_messages = config.getboolean("distance_autonomy", "distance_autonomy_messages")
        sc_Vars.action_distance_autonomy = config.getfloat("distance_autonomy", "action_distance_autonomy")
        sc_Vars.chat_distance_autonomy = config.getfloat("distance_autonomy", "chat_distance_autonomy")
        services.weather_service()._icy_conditions_option = not config.getboolean("control", "disable_icy_conditions")
        sc_Vars.update_speed = config.getfloat("control", "update_speed")
        sc_Vars.chance_switch_action = config.getfloat("control", "chance_switch_action")
        sc_Vars.interaction_minutes_run = config.getfloat("control", "action_timeout")
        sc_Vars.chance_role_trait = config.getfloat("control", "chance_role_trait")
        sim_buffer = config.getfloat("simulation", "set_sim_buffer")
        sim_delay = config.getfloat("simulation", "set_sim_delay")
        autonomy_distance_cutoff = config.getfloat("simulation", "autonomy_distance_cutoff")
        update_autonomy = config.getint("simulation", "update_autonomy")
        time_slice = config.getint("simulation", "time_slice")

        set_sim_buffer(sim_buffer)
        set_sim_delay(sim_delay)
        set_autonomy_distance_cutoff(autonomy_distance_cutoff)
        set_time_slice(time_slice)
        set_update_autonomy(update_autonomy)
        SimSpawnerService.NPC_SOFT_CAP = 255
        sc_Vars.timestamp = 0
        services.sim_spawner_service().set_npc_soft_cap_override(sc_Vars.MAX_SIMS)
        services.fire_service.fire_enabled = False
        if sc_Vars.disable_new_sims:
            TunableSimFilter._template_chooser = None
        ScriptCoreMain.sim_filter = sc_Filter()

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

        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        options_proto = account_data_msg.gameplay_account_data.gameplay_options

        config_text = config_text + "[Autonomy Level:] {}\n[Selected Sim Autonomy Enabled:] {}\n".format(options_proto.autonomy_level, options_proto.selected_sim_autonomy_enabled)
        config_text = config_text.replace("[", font_text1).replace("]", end_font_text)
        config_text = config_text.replace("(", font_text3).replace(")", end_font_text)
        status_text = status_text.replace("[", font_text2).replace("]", end_font_text)
        message_box(None, None, "Script Core Menu", "{}\n{}".format(status_text, config_text), "PURPLE")

    def load(self):
        ScriptCoreMain.config_ini(self)
        ScriptCoreMain.assign_all_sims(self)
        ScriptCoreMain.load_object_data(self)

    # New transmog code
    def load_object_data(self):
        sc_Vars.transmog_objects = []
        for obj in services.object_manager().get_all():
            if load_material(obj):
                sc_Vars.transmog_objects.append(obj) if obj not in sc_Vars.transmog_objects else None

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
        if not sim.sim_info.is_instanced():
            return
        zone = services.current_zone()
        now = services.time_service().sim_now

        if not sim.sim_info.routine:
            set_proper_sim_outfit(sim, sim.sim_info.is_selectable, None, True)
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
                    make_sim_leave(sim)
                    return
            if now.hour() >= sim.sim_info.routine_info.off_duty and not sim.sim_info.routine_info.off_duty == 0 or \
                    now.hour() < sim.sim_info.routine_info.on_duty and not sim.sim_info.routine_info.on_duty == 0:
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - off_duty: {}/{}".format(sim.first_name, sim.sim_info.routine_info.off_duty, now.hour()))
                clear_jobs(sim.sim_info)
                assign_title(sim.sim_info, "")
                sim.sim_info.routine = False
                if not sim.sim_info.is_selectable:
                    make_sim_leave(sim)
                return
            if sim == services.get_active_sim() or sim.sim_info.is_selectable or sim.sim_info.routine:
                clear_leaving(sim)
            if sc_Vars.career_function and sim.sim_info.autonomy != AutonomyState.DISABLED and sim.sim_info.routine:
                sc_Vars.career_function.routine_handler(sim.sim_info)
            return
        elif sim == services.get_active_sim():
            return
        elif sim.sim_info.is_selectable:
            return
        elif is_sim_in_group(sim):
            clear_leaving(sim)
            return
        elif sim.sim_info in services.active_household():
            return
        elif sim.sim_info.vacation_or_home_zone_id == zone.id:
            clear_leaving(sim)
            return
        elif ScriptCoreMain.sim_filter.has_allowed_role(sim):
            # New private objects code
            if sc_Vars.keep_sims_outside:
                keep_sim_outside(sim, sc_Vars.private_objects)
            return
        if sc_Vars.DEBUG:
            debugger("Sim: {} - Filtered".format(sim.first_name))
        make_sim_leave(sim)

    def init_routine(self):
        try:
            if sc_Vars._running and not sc_Vars.DISABLE_MOD and not sc_Vars.DISABLE_ROUTINE:
                update_sim = None
                sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]
                sims_doing_nothing = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine and doing_nothing(sim) and not check_actions(sim, "sit") and sim.sim_info.routine_info.title != "patient"]
                if not len(sims):
                    return
                if len(sims_doing_nothing):
                    update_sim = sims_doing_nothing[0]

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

                fade_lights_in_live_mode(False, 0.0)

                if sim.sim_info.is_instanced():
                    ScriptCoreMain.assign_sim(self, sim)
                if update_sim:
                    if update_sim != sim and update_sim.sim_info.is_instanced() and sc_Vars.career_function and not sim.sim_info.is_selectable:
                        ScriptCoreMain.assign_sim(self, update_sim)

        except BaseException as e:
            error_trap_console(e)

    def init(self):
        try:
            zone = services.current_zone()
            venue = get_venue()
            sc_club = C_ZoneClubs()
            sc_Vars.DISABLE_MOD = get_config("config.ini", "control", "disable_mod")
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

                fade_lights_in_live_mode(True, 0.0)
                object_list = get_config("zones.ini", "global", "objects")
                actions = get_config("zones.ini", "global", "actions")
                if object_list:
                    for i, obj_id in enumerate(object_list):
                        obj = objects.system.find_object(int(obj_id), include_props=True)
                        if obj:
                            action = actions[i] if len(actions) > i else actions[0]
                            push_sim_function(client.active_sim, obj, action, False)

                sc_club.club_setup_on_load(services.get_club_service())
                get_important_objects_on_lot()
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

                sims = [sim for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=objects.ALL_HIDDEN_REASONS) if not sim.sim_info.routine]
                sims_doing_nothing = [sim for sim in sims if doing_nothing(sim) and not check_actions(sim, "sit")]
                update_sim = None
                if len(sims_doing_nothing):
                    update_sim = sims_doing_nothing[0]

                if not len(sims):
                    return
                if sc_Vars.sim_index >= len(sims):
                    sc_Vars.sim_index = 0
                sim = sims[sc_Vars.sim_index]
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - index: {} autonomy_setting: {}".format(sim.first_name, sc_Vars.sim_index, sim.sim_info.autonomy))
                sc_Vars.sim_index += 1
                if sc_Vars.sim_index >= len(sims):
                    sc_Vars.sim_index = 0

                fade_lights_in_live_mode(False, 0.0)
                ScriptCoreMain.assign_sim(self, sim)
                if update_sim:
                    if update_sim != sim and update_sim.sim_info.is_instanced() and sc_Vars.career_function and not sim.sim_info.is_selectable:
                        sc_Vars.career_function.default_routine(sim.sim_info)

        except BaseException as e:
            error_trap_console(e)

    def on_build_buy_enter_handler(self):
        fade_lights_in_live_mode(True, 0.0)
