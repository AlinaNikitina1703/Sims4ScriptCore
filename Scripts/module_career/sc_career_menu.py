import os
from os.path import isfile, join

import camera
import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow

from module_career.sc_career_custom import sc_CareerCustom
from module_career.sc_career_functions import get_routine_objects_by_title
from module_career.sc_career_routines import sc_CareerRoutine
from scripts_core.sc_bulletin import sc_Bulletin
from scripts_core.sc_debugger import debugger
from scripts_core.sc_gohere import go_here
from scripts_core.sc_input import inputbox
from scripts_core.sc_jobs import clear_sim_instance, push_sim_function, distance_to, assign_situation, assign_title, \
    set_exam_info, assign_routine, is_object_in_use, remove_sim_role, doing_nothing, check_actions
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_routine_info import sc_RoutineInfo
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap, ld_file_loader


class ModuleCareerMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None
    last_initial_value = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_career_menu_choices = ("Set Vendor Menu",
                                       "Show Exams",
                                       "Set Exam To Patient",
                                       "Add Routine To Sim",
                                       "Add Situation To Sim",
                                       "Remove Role From Sim")

        self.sc_vendor_choices = ("Mexican",
                                  "American",
                                  "Chinese",
                                  "Cafeteria Sunday",
                                  "Cafeteria Monday",
                                  "Cafeteria Tuesday",
                                  "Cafeteria Wednesday",
                                  "Cafeteria Thursday",
                                  "Cafeteria Friday",
                                  "Cafeteria Saturday")

        self.sc_career_menu = MainMenu(*args, **kwargs)
        self.sc_vendor_menu = MainMenu(*args, **kwargs)
        self.sc_bulletin = sc_Bulletin()
        self.script_choice = MainMenu(*args, **kwargs)
        self.sc_career_routine = sc_CareerRoutine()

    def _run_interaction_gen(self, timeline):
        self.sc_career_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_career_menu.commands = []
        self.sc_career_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_career_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_career_menu.show(timeline, self, 0, self.sc_career_menu_choices, "Career Menu", "Make a selection.")

    def _menu(self, timeline):
        self.sc_career_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_career_menu.commands = []
        self.sc_career_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_career_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_career_menu.show(timeline, self, 0, self.sc_career_menu_choices, "Career Menu", "Make a selection.")

    def set_vendor_menu(self, timeline):
        self.sc_vendor_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_vendor_menu.commands = []
        self.sc_vendor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_vendor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_vendor_menu.show(timeline, self, 0, self.sc_vendor_choices, "Vendor Menu", "Make a selection.")

    def show_exams(self, timeline):
        self.sc_bulletin.show_exams(camera.focus_on_object)
        if len(sc_Vars.exam_list):
            for exam in sc_Vars.exam_list:
                currently = "Waiting on Exam: ({}) - Doctor: {}\n".format(exam.exam, exam.doctor.first_name)
                for interaction in exam.patient.get_all_running_and_queued_interactions():
                    currently = currently + "({}) {}\n".format(interaction.guid64, interaction.__class__.__name__)
                message_box(exam.patient, exam.doctor, "Exam {}".format(exam.exam), "{}".format(currently), "GREEN")

    def set_exam_to_patient(self, timeline):
        inputbox("Add Exam To Patient", "Enter the exam ID.", self._add_exam_to_patient_callback, ModuleCareerMenu.last_initial_value)

    def _add_exam_to_patient_callback(self, exam_id: str):
        try:
            patient = None
            ModuleCareerMenu.last_initial_value = exam_id
            if exam_id == "" or exam_id is None:
                return

            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return

                def get_doctorpicker_results_callback(dialog):
                    if not dialog.accepted:
                        return

                    for sim in dialog.get_result_tags():
                        for exam in sc_Vars.exam_list:
                            if exam.patient == patient:
                                exam.doctor = sim
                                assign_routine(patient.sim_info, "patient")
                                set_exam_info(patient.sim_info)
                                message_box(patient, sim, "{}".format(exam_id), "Exam assigned to patient!", "GREEN")

                doctors = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine and "doctor" in sim.sim_info.routine_info.title or sim.sim_info.routine and "radiologist" in sim.sim_info.routine_info.title]
                if not doctors:
                    message_box(None, None, "Doctors", "No doctors on lot!", "GREEN")
                    return

                for sim in dialog.get_result_tags():
                    for exam in sc_Vars.exam_list:
                        if exam.patient == sim:
                            patient = sim
                            exam.exam = exam_id
                            self.picker("Add Doctor to Exam {}".format(exam_id), "Pick up to 1 Sim", 1, get_doctorpicker_results_callback, doctors)

            sims = services.sim_info_manager().instanced_sims_gen()
            sim_list = [sim for sim in sims if [r for r in sim.autonomy_component.active_roles() if "patient" in str(r).lower()]]
            self.picker("Add Exam {} To Sim".format(exam_id), "Pick up to 1 Sim", 1, get_simpicker_results_callback, sim_list)
        except BaseException as e:
            error_trap(e)

    def add_situation_to_sim(self, timeline):
        inputbox("Add Situation To Sim", "Enter the situation ID.", self._add_situation_to_sim_callback)

    def _add_situation_to_sim_callback(self, situation_id: str):
        full_duty = False
        if situation_id == "" or situation_id is None:
            return

        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            for sim in dialog.get_result_tags():
                assign_situation(int(situation_id), sim.sim_info)
                message_box(sim, None, "{}".format(situation_id), "Situation assigned to sim!", "GREEN")


        self.picker("Add Situation {} To Sim".format(situation_id), "Pick up to 50 Sims", 50, get_simpicker_results_callback)

    def remove_role_from_sim(self, timeline):
        inputbox("Remove Role From Sim", "Enter the role title.", self._remove_role_from_sim_callback)

    def _remove_role_from_sim_callback(self, role_title: str):
        if role_title == "" or role_title is None:
            return

        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            for sim in dialog.get_result_tags():
                remove_sim_role(sim, role_title)
                message_box(sim, None, "{}".format(role_title.title()), "Role removed from sim!", "GREEN")


        self.picker("Remove Role {} From Sim".format(role_title.title()), "Pick up to 50 Sims", 50, get_simpicker_results_callback)

    def add_routine_to_sim(self, timeline):
        inputbox("Add Routine To Sim", "Enter the routine title. Add a + to the beginning for 24 hour duty.", self._add_routine_to_sim_callback)

    def _add_routine_to_sim_callback(self, role_title: str):
        full_duty = False
        if role_title == "" or role_title is None:
            role_title = "none"
        if "+" in role_title:
            full_duty = True
            role_title = role_title.replace("+", "")

        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            if not role_title:
                message_box(None, None, "{}".format(role_title.title()), "Routine unassigned!", "GREEN")
                for sim in dialog.get_result_tags():
                    sim.sim_info.routine = False
                    assign_title(sim.sim_info, "")
                return
            roles = [role for role in sc_Vars.roles if role_title in role.title]
            if not roles:
                message_box(None, None, "{}".format(role_title.title()), "No routine found!", "GREEN")
                return
            for sim in dialog.get_result_tags():
                sim.sim_info.routine_info = roles[0]
                if full_duty:
                    sim.sim_info.routine_info.on_duty = 0
                    sim.sim_info.routine_info.off_duty = 0
                routine_objects = [obj for obj in services.object_manager().get_all() if roles[0].use_object1
                                            in str(obj).lower() and roles[0].use_object1 != "None" or
                                            roles[0].use_object1 in str(obj.definition.id)]
                if len(routine_objects):
                    sc_Vars.routine_objects = list(set(list(sc_Vars.routine_objects) + list(routine_objects)))
                sc_CareerCustom.assign_sim(self, sim.sim_info)
                message_box(sim, None, "{}".format(roles[0].title.title()), "Routine assigned to sim! On Duty: {}"
                    " Off Duty: {}".format(sim.sim_info.routine_info.on_duty, sim.sim_info.routine_info.off_duty), "GREEN")


        self.picker("Add Routine {} To Sim".format(role_title.title()), "Pick up to 50 Sims", 50, get_simpicker_results_callback)


    def picker(self, title: str, text: str, max: int = 50, callback=None, sims=None):
        try:
            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(text)
            dialog = UiSimPicker.TunableFactory().default(self.sim,
                                                          text=localized_text,
                                                          title=localized_title,
                                                          max_selectable=max,
                                                          min_selectable=1,
                                                          should_show_names=True,
                                                          hide_row_description=False)

            if not sims:
                sims = services.sim_info_manager().instanced_sims_gen()
            for sim in sims:
                dialog.add_row(SimPickerRow(sim.id, False, tag=sim))

            dialog.add_listener(callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

    def mexican(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 139285

    def american(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 132722

    def chinese(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 139454

    def cafeteria_monday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217850, False)

    def cafeteria_tuesday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217853, False)

    def cafeteria_wednesday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217854, False)

    def cafeteria_thursday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217855, False)

    def cafeteria_friday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217856, False)

    def cafeteria_saturday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217857, False)

    def cafeteria_sunday(self, timeline):
        if self.target.is_sim:
            clear_sim_instance(self.target.sim_info)
            self.target.sim_info.routine_info.object_action1 = 217884
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(self.target.sim_info.routine_info.use_object1, sc_Vars.routine_objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if self.target.sim_info.use_object_index >= len(objs):
                    self.target.sim_info.use_object_index = 0
                obj = objs[self.target.sim_info.use_object_index]
                if is_object_in_use(obj) and not obj.in_use_by(self.target):
                    self.target.sim_info.use_object_index += 1
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Obj Index: {}".format(self.target.sim_info.first_name, self.target.sim_info.use_object_index))
                    return
                if obj:
                    push_sim_function(self.target, obj, 217858, False)

    def routine_info(self, timeline):
        font_color1 = "aa88ff"
        font_text1 = "<font color='#{}'>".format(font_color1)
        end_font_text = "</font>"
        routine_info = ""
        routine_info = routine_info + "[Start Times:] {}\n".format(sc_Vars.routine_start_times)
        routine_info = routine_info.replace("[", font_text1).replace("]", end_font_text)
        message_box(None, None, "Routine Info", "{}".format(routine_info), "PURPLE")

    def custom_function(self, option):
        font_color1 = "aa88ff"
        font_text1 = "<font color='#{}'>".format(font_color1)
        end_font_text = "</font>"
        routine_info = ""
        routine_info = routine_info + "[Title:] {}\n".format(self.target.sim_info.routine_info.title)
        routine_info = routine_info + "[Autonomy:] {}\n".format(self.target.sim_info.routine_info.autonomy)
        routine_info = routine_info + "[Career:] {}\n".format(self.target.sim_info.routine_info.career)
        routine_info = routine_info + "[Max_staff:] {}\n".format(self.target.sim_info.routine_info.max_staff)
        routine_info = routine_info + "[Buffs:] {}\n".format(self.target.sim_info.routine_info.buffs)
        routine_info = routine_info + "[Off_lot:] {}\n".format(self.target.sim_info.routine_info.off_lot)
        routine_info = routine_info + "[Zone:] {}\n".format(self.target.sim_info.routine_info.zone)
        routine_info = routine_info + "[Venue:] {}\n".format(self.target.sim_info.routine_info.venue)
        routine_info = routine_info + "[On_duty:] {}\n".format(self.target.sim_info.routine_info.on_duty)
        routine_info = routine_info + "[Off_duty:] {}\n".format(self.target.sim_info.routine_info.off_duty)
        routine_info = routine_info + "[Use_object1:] {}\n".format(self.target.sim_info.routine_info.use_object1)
        routine_info = routine_info + "[Use_object2:] {}\n".format(self.target.sim_info.routine_info.use_object2)
        routine_info = routine_info + "[Use_object3:] {}\n".format(self.target.sim_info.routine_info.use_object3)
        routine_info = routine_info + "[Use_object_index:] {}\n".format(self.target.sim_info.use_object_index)
        routine_info = routine_info.replace("[", font_text1).replace("]", end_font_text)

        message_box(None, None, "Routine Info for {} {}".format(self.target.first_name, self.target.last_name), "{}".format(routine_info), "PURPLE")

    def set_title(self, timeline):
        inputbox("Set Title", "This sims title", self.set_title_callback)

    def set_title_callback(self, title: str):
        self.target.sim_info.routine_info = sc_RoutineInfo(title=title)

    def _reload_scripts(self, timeline):
        inputbox("Reload Script",
                         "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                ModuleCareerMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(ModuleCareerMenu.directory) if isfile(join(ModuleCareerMenu.directory, f))]
            else:
                ModuleCareerMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if ModuleCareerMenu.directory is None:
                ModuleCareerMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(ModuleCareerMenu.directory, filename)
        except BaseException as e:
            error_trap(e)
