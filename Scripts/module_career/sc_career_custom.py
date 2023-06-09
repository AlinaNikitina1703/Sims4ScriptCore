import ast
import configparser
import os
import random

import services

from module_career.sc_career_medical import sc_CareerMedical
from scripts_core.sc_debugger import debugger
from scripts_core.sc_gohere import make_sim_leave
from scripts_core.sc_jobs import get_career_name, get_venue, assign_title, get_work_hours, check_actions, \
    function_options, assign_role, get_career_level, \
    clear_queue_of_duplicates, set_all_motives_by_sim, max_sims, clear_sim_instance, set_proper_sim_outfit, \
    get_awake_hours, assign_routine
from scripts_core.sc_routine_info import sc_RoutineInfo
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_spawn import sc_Spawn
from scripts_core.sc_util import init_sim, error_trap


class sc_CareerCustom(sc_CareerMedical):
    sim_infos = []
    routine_sims = []
    objects = []
    choice = 0

    def __init__(self):
        super().__init__()
        self.sc_career_spawn = sc_Spawn() 

    def init(self):
        if sc_Vars.DISABLE_MOD:
            return
        sc_career = sc_CareerCustom()
        if sc_Vars._config_loaded and not sc_Vars._running:
            sc_career.load_roles()
            sc_career.setup_sims()
            sc_career.load_sims()
            if not sc_Vars.career_function:
                sc_Vars.career_function = sc_CareerCustom()
            sc_Vars._running = True

    def load_roles(self):
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\roles.ini"
        if not os.path.exists(filename):
            return
        sc_Vars.roles = []
        config = configparser.ConfigParser()
        config.read(filename)
        for title in config.sections():
            sc_Vars.roles.append(sc_RoutineInfo(title,
                                                     config.getint(title, "autonomy"),
                                                     config.getint(title, "role"),
                                                     config.get(title, "career"),
                                                     config.getint(title, "level"),
                                                     config.getint(title, "max_staff"),
                                                     ast.literal_eval(config.get(title, "routine")),
                                                     ast.literal_eval(config.get(title, "buffs")),
                                                     ast.literal_eval(config.get(title, "actions")),
                                                     ast.literal_eval(config.get(title, "filtered_actions")),
                                                     ast.literal_eval(config.get(title, "autonomy_requests")),
                                                     ast.literal_eval(config.get(title, "autonomy_objects")),
                                                     config.getboolean(title, "off_lot"),
                                                     ast.literal_eval(config.get(title, "zone")),
                                                     ast.literal_eval(config.get(title, "venue")),
                                                     config.getint(title, "on_duty"),
                                                     config.getint(title, "off_duty"),
                                                     config.get(title, "use_object1"),
                                                     config.get(title, "use_object2"),
                                                     config.get(title, "use_object3"),
                                                     config.getint(title, "object_action1"),
                                                     config.getint(title, "object_action2"),
                                                     config.getint(title, "object_action3"),
                                                     ast.literal_eval(config.get(title, "role_buttons"))))

    def setup_sims(self):
        sc_Vars.exam_list = []
        sc_CareerCustom.sim_infos = []
        sc_Vars.routine_objects = []
        venue = get_venue()
        zone = services.current_zone()
        now = services.time_service().sim_now
        seed = self.get_random_seed_by_zone()
        random.seed(seed)
        routines = self.get_filter_routines_by_zone()

        sc_Vars.routine_objects = [obj for obj in services.object_manager().get_all() if [role.use_object1 for role in
                    sc_Vars.roles if role.use_object1 in str(obj).lower() and role.use_object1 != "None" or
                    role.use_object1 in str(obj.definition.id)]]

        if sc_Vars.DEBUG:
            obj_list = ""
            role_objects = [role.use_object1 for role in sc_Vars.roles if [obj for obj in sc_Vars.routine_objects if role.use_object1 in str(obj).lower()]]
            role_object_list = []
            [role_object_list.append(obj) for obj in role_objects if obj not in role_object_list]
            for obj in role_object_list:
                obj_list = obj_list + "Custom Object: {}\n".format(obj)
            debugger(obj_list)

        dirty_objects = [obj for obj in services.object_manager().get_all() if "_clean" in
            str(obj._super_affordances).lower() and not obj.is_outside and [title for title in self.cleaning_job_list["object"] if title in
            str(obj).lower()]]
        random.shuffle(dirty_objects)
        sc_Vars.dirty_objects = [obj for i, obj in enumerate(dirty_objects) if i < 100 and obj]

        base_roles = sc_Vars.roles
        if routines:
            base_roles = [role for role in base_roles if [routine for routine in routines if role.title in routine]]

        base_roles = [role for role in base_roles if role.max_staff > 0]

        base_roles = [role for role in base_roles if role.use_object1 == "None" or [obj for obj in sc_Vars.routine_objects if
            role.use_object1 in str(obj).lower() and role.use_object1 != "None" or role.use_object1 in str(obj.definition.id)]]

        base_roles = [role for role in base_roles if not role.venue or [v for v in role.venue if v in venue]]
        base_roles = [role for role in base_roles if not role.zone or [z for z in role.zone if z in str(zone.id)]]

        if sc_Vars.DEBUG:
            allowed_roles = "Allowed Roles:\n"
            for role in base_roles:
                allowed_roles = allowed_roles + "Role: {}\n".format(role.title.title())
            debugger(allowed_roles)

        if base_roles:
            workforce_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.routine or
                (sim_info.career_tracker is not None and [career for career in sim_info.career_tracker if [role for role in base_roles if role.career in str(career)]])
                or [trait for trait in sim_info.trait_tracker if [role for role in base_roles if role.career in str(trait)]]]

            random.shuffle(workforce_sims)
            sc_Vars.routine_sims = workforce_sims
            for sim_info in workforce_sims:
                if sim_info.is_instanced() and sim_info.routine and "leave" not in sim_info.routine_info.title:
                    sim_info.routine = True
                    roles = [role for role in sc_Vars.roles if sim_info.routine_info.title in role.title]
                else:
                    sim_info.routine = False
                    career_name = get_career_name(sim_info)
                    career_level = get_career_level(sim_info)
                    if not career_name:
                        continue

                    roles = [role for role in base_roles if role.career in career_name and role.level == career_level
                            or role.career in career_name and role.level == -1 or [trait for trait in sim_info.trait_tracker
                            if role.career in str(trait)]]
                    if not roles:
                        continue

                for role in roles:
                    sim_info.routine_info = role
                    sim_info.use_object_index = 0
                    sim_info.choice = 0
                    if sim_info.routine_info.use_object1 and sim_info.routine_info.max_staff > 0:
                        objects = [obj for obj in sc_Vars.routine_objects if sim_info.routine_info.use_object1 in str(obj).lower()
                            and sim_info.routine_info.use_object1 != "None" or sim_info.routine_info.use_object1 in
                            str(obj.definition.id)]
                        if len(objects):
                            sim_info.routine_info.max_staff = min(sim_info.routine_info.max_staff, len(objects))
                sc_CareerCustom.sim_infos.append(sim_info)

            sc_Vars.routine_start_times = []
            if [sim_info for sim_info in sc_CareerCustom.sim_infos if "stripper" in sim_info.routine_info.title]:
                sc_Vars.routine_start_times = [17, 18, 19, 20, 21, 22, 23, 1, 3, 5, 7, 9, 11, 13, 15]
                if [start_time for start_time in sc_Vars.routine_start_times if start_time == now.hour()]:
                    sc_Vars.routine_start_times.remove(now.hour())
            else:
                for sim_info in sc_CareerCustom.sim_infos:
                    if not sc_Vars.routine_start_times and sim_info.routine_info.on_duty != now.hour() and sim_info.routine_info.on_duty > 0:
                        sc_Vars.routine_start_times.append(sim_info.routine_info.on_duty)
                        continue
                    if not [start_time for start_time in sc_Vars.routine_start_times if sim_info.routine_info.on_duty == start_time] \
                            and sim_info.routine_info.on_duty != now.hour() and sim_info.routine_info.on_duty > 0:
                        sc_Vars.routine_start_times.append(sim_info.routine_info.on_duty)

            if sc_Vars.DEBUG:
                debugger("Start Times: {}".format(sc_Vars.routine_start_times))

    def get_filter_routines_by_zone(self):
        zone = services.current_zone()
        zone_id = zone.id
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\zones.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section(str(zone_id)):
            if config.has_option(str(zone_id), "routines"):
                routines = ast.literal_eval(config.get(str(zone_id), "routines"))
                return routines
        return None

    def get_random_seed_by_zone(self):
        zone = services.current_zone()
        now = services.time_service().sim_now
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\zones.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        random_seed = int(zone.id)
        if config.has_section(str(zone.id)):
            if config.has_option(str(zone.id), "seed"):
                seeds = ast.literal_eval(config.get(str(zone.id), "seed"))
                if [seed for seed in seeds if "zone" in seed]:
                    random_seed = int(zone.id)
                if [seed for seed in seeds if "second" in seed]:
                    random_seed = random_seed + int(now.second())
                if [seed for seed in seeds if "minute" in seed]:
                    random_seed = random_seed + int(now.minute())
                if [seed for seed in seeds if "hour" in seed]:
                    random_seed = random_seed + int(now.hour())
                if [seed for seed in seeds if "day" in seed]:
                    random_seed = random_seed + int(now.hour())
        return random_seed

    def get_max_staff_by_zone(self):
        zone = services.current_zone()
        now = services.time_service().sim_now
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\zones.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        max_staff_routine = None
        max_staff = 0
        if config.has_section(str(zone.id)):
            if config.has_option(str(zone.id), "max_staff_routine"):
                max_staff_routine = config.get(str(zone.id), "max_staff_routine")
            if config.has_option(str(zone.id), "max_staff"):
                max_staff = config.getint(str(zone.id), "max_staff")
            if max_staff_routine and max_staff:
                return max_staff_routine, max_staff
        return None, 0

    def get_filter_sims_by_zone(self, routine: str):
        zone = services.current_zone()
        zone_id = zone.id
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\zones.ini"
        if not os.path.exists(filename):
            return None
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section(str(zone_id)):
            if config.has_option(str(zone_id), routine):
                sims = ast.literal_eval(config.get(str(zone_id), routine))
                return sims
        return None

    def load_sims(self):
        sc_CareerCustom.routine_sims = []
        zone_id = services.current_zone_id()

        if sc_Vars.DEBUG:
            sim_names = ""
            for sim_info in sc_CareerCustom.sim_infos:
                sim_names = sim_names + "Workforce Sim: {} {} - Title: {}\n".format(sim_info.first_name, sim_info.last_name, sim_info.routine_info.title)
            debugger(sim_names)

        for sim_info in list(sc_CareerCustom.sim_infos):
            sim_name = "{} {}".format(sim_info.first_name, sim_info.last_name)
            names = self.get_filter_sims_by_zone(sim_info.routine_info.title)
            if names:
                if not [name for name in names if sim_name in name]:
                    sim_info.routine = False
                    sc_CareerCustom.sim_infos.remove(sim_info)

        for sim_info in list(sc_CareerCustom.sim_infos):
            if max_sims(sim_info, sc_CareerCustom.sim_infos):
                sim_info.routine = False
                sc_CareerCustom.sim_infos.remove(sim_info)
                if sim_info.is_instanced() and not sim_info.is_selectable:
                    sim = init_sim(sim_info)
                    make_sim_leave(sim)
                continue
            if not get_work_hours(sim_info.routine_info.on_duty, sim_info.routine_info.off_duty):
                sim_info.routine = False
                sc_CareerCustom.sim_infos.remove(sim_info)
                if sim_info.is_instanced() and not sim_info.is_selectable:
                    sim = init_sim(sim_info)
                    make_sim_leave(sim)
                continue
            if not sim_info.is_instanced():
                self.sc_career_spawn.spawn_sim(sim_info)
            sim = init_sim(sim_info)
            if sim:
                self.assign_sim(sim_info)
                if len(sc_CareerCustom.routine_sims):
                    for routine_sim in sc_CareerCustom.routine_sims:
                        if routine_sim.first_name == sim_info.first_name and routine_sim.last_name == sim_info.last_name:
                            sc_CareerCustom.routine_sims.remove(routine_sim)
                sc_CareerCustom.routine_sims.append(sim_info)

        if sc_Vars.DEBUG:
            sim_names = ""
            for sim_info in sc_CareerCustom.routine_sims:
                sim_names = sim_names + "Routine Sim: {} {} - Title: {}\n".format(sim_info.first_name, sim_info.last_name, sim_info.routine_info.title)
            debugger(sim_names)
    
    def assign_sim(self, sim_info):
        clear_sim_instance(sim_info)
        if sim_info.routine_info.title != "none":
            assign_routine(sim_info, sim_info.routine_info.title)
        else:
            assign_routine(sim_info, sim_info.routine_info.title, True, False, False)

    def routine_handler(self, sim_info):
        try:
            if not sim_info.is_instanced() and get_work_hours(sim_info.routine_info.on_duty, sim_info.routine_info.off_duty):
                self.sc_career_spawn.spawn_sim(sim_info)
                self.assign_sim(sim_info)

            sim = init_sim(sim_info)
            if sim:
                if check_actions(sim, "wicked"):
                    return
                clear_queue_of_duplicates(sim)
                set_all_motives_by_sim(sim)
                assign_title(sim_info, sim_info.routine_info.title.title())
                assign_role(sim_info.routine_info.role, sim_info)
                if not sim_info.routine_info.routine:
                    sim_info.routine_info.routine.append(sim_info.routine_info.title + "_routine")

                if [buff for buff in sim_info.routine_info.buffs if buff == 145074]:
                    set_proper_sim_outfit(sim, False, sim_info.routine_info.title)

                if [buff for buff in sim_info.routine_info.buffs if buff == 35478] and not sc_Vars.dont_sleep_on_lot:
                    self.sleep_routine(sim_info)
                if [buff for buff in sim_info.routine_info.buffs if buff == 35478] and sc_Vars.dont_sleep_on_lot and not get_awake_hours(sim):
                    make_sim_leave(sim)
                if [buff for buff in sim_info.routine_info.buffs if buff == 115830]:
                    self.room_check_routine(sim_info)

                if not check_actions(sim, "sleep") and not check_actions(sim, "nap") and check_actions(sim, "gohere"):
                    clear_sim_instance(sim_info, "gohere", True)
                    return

                if not check_actions(sim, "sleep") and not check_actions(sim, "nap") and len(list(sim_info.routine_info.routine)):
                    now = services.time_service().sim_now
                    seed = int(sim.sim_id * 0.00000000000001) * int(now.second())
                    random.seed(seed)
                    chance = random.uniform(0, 100)
                    choice = sim_info.choice

                    if chance < sc_Vars.chance_switch_action:
                        choice = random.randint(0, len(list(sim_info.routine_info.routine)) - 1)
                        if choice >= len(list(sim_info.routine_info.routine)):
                            choice = 0


                    routine_choice = list(sim_info.routine_info.routine)[choice] if len(list(sim_info.routine_info.routine)) > choice else list(sim_info.routine_info.routine)[0]
                    if not function_options(sim_info, self, routine_choice):
                        choice = sim_info.choice
                        routine_choice = list(sim_info.routine_info.routine)[choice] if len(list(sim_info.routine_info.routine)) > choice else list(sim_info.routine_info.routine)[0]
                        if not function_options(sim_info, self, routine_choice):
                            choice = 0
                            routine_choice = list(sim_info.routine_info.routine)[choice]
                            function_options(sim_info, self, routine_choice)

                    sim_info.choice = choice
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - chance: {} seed: {} choice: {}. {}".format(sim_info.first_name, chance, seed,
                            sim_info.choice, list(sim_info.routine_info.routine)[sim_info.choice]))
        except BaseException as e:
            error_trap(e)
