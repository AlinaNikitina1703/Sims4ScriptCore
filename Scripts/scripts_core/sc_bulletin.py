import services

from scripts_core.sc_message_box import message_box
from scripts_core.sc_routine_menu import sc_RoutineMenu
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


class sc_Bulletin(sc_RoutineMenu):

    def __init__(self):
        super().__init__()

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
            sim_list = [sim for sim in sims if sim.is_human]

            if len(sim_list):
                self.show("Sims On Lot", sim_list, 0, services.get_active_sim(), 1, callback)
            else:
                message_box(None, None, "Sims On Lot", "No one is on this lot which is impossible.", False, "GREEN")
        except BaseException as e:
            error_trap(e)
