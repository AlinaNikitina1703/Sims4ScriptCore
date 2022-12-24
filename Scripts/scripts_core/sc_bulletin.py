import services
from objects import ALL_HIDDEN_REASONS

from scripts_core.sc_jobs import doing_nothing, get_sims_using_object
from scripts_core.sc_message_box import message_box
from scripts_core.sc_routine_menu import sc_RoutineMenu
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


class sc_Bulletin(sc_RoutineMenu):

    def __init__(self):
        super().__init__()

    def show_indexed_sims(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            non_routine_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if not sim.sim_info.routine]
            routine_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]
            sim_list = []
            if sc_Vars.sim_index < len(non_routine_sims):
                sim_list.append(non_routine_sims[sc_Vars.sim_index])
            if sc_Vars.routine_sim_index < len(routine_sims):
                sim_list.append(routine_sims[sc_Vars.routine_sim_index])

            if len(sim_list):
                self.show("Non Routine & Routine Sims", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Non Routine and Routine Sims", "No one is currently indexed. Reload the routine.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_scheduled_sims(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            if len(sc_Vars.routine_sims):
                self.show("Scheduled Sims", sc_Vars.routine_sims, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Scheduled Sims", "No one is currently scheduled for this lot.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_autonomy_sims(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            if len(sc_Vars.sorted_autonomy_sims):
                self.show("Autonomy Sims", sc_Vars.sorted_autonomy_sims, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Autonomy Sims", "No autonomy sims in range of active sims.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_idle_sims(self, callback=None):
        try:
            sim_list = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine and doing_nothing(sim)]
            if len(sim_list):
                self.show("Idle Sims", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Idle Sims", "No routine sims are currently idle.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_routine_staff(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            sims = services.sim_info_manager().instanced_sims_gen()
            sim_list = [sim for sim in sims if sim.sim_info.routine]

            if len(sim_list):
                self.show("Sims On Duty", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Sims On Duty", "No one is on duty. Make sure you have the careers module "
                    "installed. Careers module coming soon.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_exams(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            sims = services.sim_info_manager().instanced_sims_gen()
            sim_list = [sim for sim in sims if [exam for exam in sc_Vars.exam_list if exam.patient == sim]]

            if len(sim_list):
                self.show("Medical Exams", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Medical Exams", "No exams!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def sims_on_lot(self, callback=None):
        try:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            sims = services.sim_info_manager().instanced_sims_gen()
            non_routine_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS) if not sim.sim_info.routine]
            routine_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]
            sim_list = non_routine_sims + routine_sims

            if len(sim_list):
                self.show("Sims On Lot", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Sims On Lot", "No one is on this lot which is impossible.", "GREEN")
        except BaseException as e:
            error_trap(e)

    def show_sims_using_object(self, target, callback=None):
        if not target.is_sim and target.definition.id != 816:
            self.MAX_MENU_ITEMS_TO_LIST = 20
            sim_list = get_sims_using_object(target)
            if len(sim_list):
                self.show("Sims Using Object", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(target, None, "Sims Using Object", "No one is using this object.", "GREEN")


