import math

import services
from scripts_core.sc_jobs import get_sim_role, set_exam_info
from scripts_core.sc_menu_class import get_icon_info_data, ICON_MORE, ICON_BACK
from scripts_core.sc_util import error_trap
from distributor.shared_messages import IconInfoData
from sims4.localization import LocalizationHelperTuning
from sims4.resources import Types, get_resource_key
from ui.ui_dialog_picker import ObjectPickerRow, UiObjectPicker, ObjectPickerType


class sc_RoutineMenu:
    def __init__(self):
        super().__init__()
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.MENU_MORE = -1
        self.MENU_BACK = -2

    def show(self, title, option_list, index, target, max=1, callback=None):
        try:
            client = services.client_manager().get_first_client()

            def get_picker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        return
                    for option in dialog.get_result_tags():
                        if option is self.MENU_MORE:
                            self.show(title, option_list, index + self.MAX_MENU_ITEMS_TO_LIST, target, max, callback)
                            return
                        elif option is self.MENU_BACK and index is not 0:
                            self.show(title, option_list, index - self.MAX_MENU_ITEMS_TO_LIST, target, max, callback)
                            return
                        elif option is self.MENU_BACK:
                            return
                        elif callback:
                            callback(option)
                        elif option is None:
                            return
                except BaseException as e:
                    error_trap(e)

            if isinstance(index, int):
                page = int((index + 1) / self.MAX_MENU_ITEMS_TO_LIST + 1)
                if len(option_list) > self.MAX_MENU_ITEMS_TO_LIST:
                    max_pages = int(math.ceil(len(option_list) / self.MAX_MENU_ITEMS_TO_LIST))
                else:
                    max_pages = 1
            else:
                page = 0
                max_pages = 0

            sims = services.sim_info_manager().instanced_sims_gen()
            sim_list = [sim for sim in sims if sim.sim_info.routine]
            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(
                "{} sim(s) in work pool\n{} {}\nPage {} of {}".
                format(len(sim_list), len(option_list), title.lower(), page, max_pages))

            dialog = UiObjectPicker.TunableFactory().default(client.active_sim,
                                                             text=localized_text,
                                                             title=localized_title,
                                                             max_selectable=max,
                                                             min_selectable=1,
                                                             picker_type=ObjectPickerType.OBJECT)

            count = 0
            for sim in option_list:
                if count >= index:
                    if hasattr(sim, "autonomy"):
                        autonomy = sim.sim_info.autonomy
                    else:
                        autonomy = None
                    currently = ""
                    if hasattr(sim.sim_info, "exam_info"):
                        set_exam_info(sim.sim_info)
                        if sim.sim_info.exam_info.doctor:
                            currently = currently + "Waiting on Exam: ({}) - Doctor: {}\n" \
                                .format(sim.sim_info.exam_info.exam, sim.sim_info.exam_info.doctor.first_name)
                    if hasattr(sim, "get_all_running_and_queued_interactions"):
                        for i, interaction in enumerate(sim.get_all_running_and_queued_interactions()):
                            currently = currently + "({})\n".format(interaction.guid64) + interaction.__class__.__name__
                    sim_name = LocalizationHelperTuning.get_object_name(sim)
                    if sim.routine:
                        sim_label = LocalizationHelperTuning.get_raw_text("Job: {}\nAutonomy: {}\nCurrently:\n{}".format(
                            sim.sim_info.routine_info.title.title(), autonomy, currently))
                    else:
                        sim.job = get_sim_role(sim)
                        sim_label = LocalizationHelperTuning.get_raw_text("Job: {}\nAutonomy: {}\nCurrently:\n{}".format(
                            sim.job.title(), autonomy, currently))
                    if hasattr(sim, "icon_info"):
                        sim_icon = get_icon_info_data(sim)
                    else:
                        sim_icon = None

                    dialog.add_row(ObjectPickerRow(name=sim_name, row_description=sim_label, icon_info=sim_icon,
                                                   tag=sim))

                count = count + 1
                if count >= self.MAX_MENU_ITEMS_TO_LIST + index:
                    sim_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Show More]</b></p>")
                    sim_label = LocalizationHelperTuning.get_raw_text("")
                    sim_icon = IconInfoData(get_resource_key(ICON_MORE, Types.PNG))
                    dialog.add_row(ObjectPickerRow(name=sim_name, row_description=sim_label, icon_info=sim_icon,
                                                   tag=self.MENU_MORE))
                    break

            sim_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Go Back]</b></p>")
            sim_label = LocalizationHelperTuning.get_raw_text("")
            sim_icon = IconInfoData(get_resource_key(ICON_BACK, Types.PNG))
            dialog.add_row(ObjectPickerRow(name=sim_name, row_description=sim_label, icon_info=sim_icon,
                                           tag=self.MENU_BACK))

            dialog.add_listener(get_picker_results_callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)
