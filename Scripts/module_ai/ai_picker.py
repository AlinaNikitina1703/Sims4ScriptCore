import services
from module_ai.ai_util import error_trap
from sims.sim_info_types import Age, Gender, Species
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow

def default_picker(title: str, text: str, max: int=50, get_all=False, callback=None, sort=True):
    try:
        client = services.client_manager().get_first_client()
        sim_ids_a = []
        sim_ids_b = []
        sim_ids = []
        if get_all is not False:
            inst_sims = services.sim_info_manager().instanced_sims_gen()
            more_sims = services.sim_info_manager().get_all()
            for sim_info in inst_sims:
                is_household_sim = sim_info.is_selectable and sim_info.valid_for_distribution
                if sim_info.species == Species.HUMAN:
                    if is_household_sim:
                        sim_ids_a.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name, sim_info.age, sim_info.gender))
            for sim_info in more_sims:
                if sim_info.species == Species.HUMAN:
                    sim_ids_b.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name, sim_info.age, sim_info.gender))
            if sort:
                sim_ids_b.sort(reverse=True, key=(lambda s: (s[4], s[2], s[1])))
            else:
                sim_ids_b.sort(reverse=False, key=(lambda s: s[0]))
            sim_ids = sim_ids_a + sim_ids_b
        else:
            all_sims = services.sim_info_manager().instanced_sims_gen()
            for sim_info in all_sims:
                if sim_info.species == Species.HUMAN:
                    if sim_info.age != Age.BABY:
                        sim_ids.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name, sim_info.age, sim_info.gender))
            if sort:
                sim_ids.sort(reverse=True, key=(lambda s: (s[4], s[2], s[1])))
            else:
                sim_ids.sort(reverse=False, key=(lambda s: s[0]))



        localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(text)
        dialog = UiSimPicker.TunableFactory().default(client.active_sim,
                                                      text=localized_text,
                                                      title=localized_title,
                                                      max_selectable=max,
                                                      min_selectable=1,
                                                      should_show_names=True,
                                                      hide_row_description=False)
        for s in sim_ids:
            dialog.add_row(SimPickerRow((s[0]), False, tag=(s[0])))

        dialog.add_listener(callback)
        dialog.show_dialog()
    except BaseException as e:
        error_trap(e)

def default_picker_filter(title: str, text: str, max: int=50, all_sims = None, callback=None):
    try:
        client = services.client_manager().get_first_client()
        sim_ids = []
        if all_sims is None:
            return
        for sim_info in all_sims:
            sim_ids.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name))

        sim_ids.sort(key=(lambda s: s[2]))
        sim_ids.sort(key=(lambda s: s[1]))
        localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(text)
        dialog = UiSimPicker.TunableFactory().default(client.active_sim,
                                                      text=localized_text,
                                                      title=localized_title,
                                                      max_selectable=max,
                                                      min_selectable=1,
                                                      should_show_names=True,
                                                      hide_row_description=False)
        for s in sim_ids:
            dialog.add_row(SimPickerRow((s[0]), False, tag=(s[0])))

        dialog.add_listener(callback)
        dialog.show_dialog()
    except BaseException as e:
        error_trap(e)