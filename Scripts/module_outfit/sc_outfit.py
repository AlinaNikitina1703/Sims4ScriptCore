import enum
import os
from os.path import isfile, join

import services
import sims4
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from scripts_core.sc_input import inputbox
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap, ld_file_loader, init_sim
from protocolbuffers import S4Common_pb2, Outfits_pb2
from sims.outfits.outfit_enums import OutfitCategory, BodyType
from sims.sim_info import SimInfo
from sims.sim_info_types import Age
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import OutfitPickerRow, UiOutfitPicker


class OutfitMenu(ImmediateSuperInteraction):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 9
        self.DELETE = 0
        self.ADD = 1
        self.CHANGE = 2

    def show(self, sim_info: SimInfo, outfit_action, filter=None, max=1):
        try:

            def get_picker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        return
                    result_tags = dialog.get_result_tags()
                    for outfit in result_tags:
                        if outfit_action == self.DELETE:
                            outfit_tracker = sim_info.get_outfits()
                            outfit_tracker.remove_outfit(outfit[0], outfit[1])
                        elif outfit_action == self.ADD:
                            outfit_tracker = sim_info.get_outfits()
                            outfit_data = outfit_tracker.get_outfit(outfit[0],
                                                                    outfit[1])
                            if outfit_data is None:
                                return
                            new_outfit = outfit_tracker.add_outfit(outfit[0], outfit_data)
                            if new_outfit is not None:
                                this_sim_info = outfit_tracker.get_sim_info()
                                this_sim_info.resend_outfits()
                                this_sim_info.set_current_outfit(new_outfit)
                        else:
                            sim_info._current_outfit = outfit
                except BaseException as e:
                    error_trap(e)

            obj_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Go Back]</b></p>")
            obj_label = LocalizationHelperTuning.get_raw_text("")

            if outfit_action == self.DELETE:
                localized_title = lambda **_: LocalizationHelperTuning.get_raw_text("Delete Sim Outfit")
                localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("")
            elif outfit_action == self.ADD:
                localized_title = lambda **_: LocalizationHelperTuning.get_raw_text("Duplicate Sim Outfit")
                localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("")
            else:
                localized_title = lambda **_: LocalizationHelperTuning.get_raw_text("Switch Sim Outfit")
                localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(str(filter))

            dialog = UiOutfitPicker.TunableFactory().default(sim_info.get_sim_instance(),
                                                             text=localized_text,
                                                             title=localized_title,
                                                             max_selectable=max,
                                                             min_selectable=1)
            for category in OutfitCategory:
                if category is not OutfitCategory.CURRENT_OUTFIT:
                    if filter is None or category is filter and filter is not None:
                        index = 0
                        while index < 5:
                            picked_outfit = (category, index)
                            if sim_info.has_outfit(picked_outfit):
                                dialog.add_row(OutfitPickerRow(outfit_sim_id=sim_info.get_sim_instance().id,
                                                               outfit_category=category,
                                                               outfit_index=index,
                                                               tag=picked_outfit))
                            index = index + 1

            dialog.add_listener(get_picker_results_callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)


class OutfitCategoryMenu(ImmediateSuperInteraction):
    outfit_data_clipboard = None
    outfit_data_array = []
    outfit_parts = None
    outfit_selected_sim = None
    outfit_selected_sim_list = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.outfit_menu_choices = ("Modify Career Outfit",
                                    "All",
                                    "Everyday",
                                    "Formal",
                                    "Athletic",
                                    "Sleep",
                                    "Party",
                                    "Bathing",
                                    "Career",
                                    "Situation",
                                    "Special",
                                    "Batuu",
                                    "Swimwear",
                                    "Hot Weather",
                                    "Cold Weather",
                                    "Copy Sim Outfit",
                                    "Paste Sim Outfit",
                                    "Paste Outfit Top",
                                    "Paste Outfit Bottom",
                                    "Paste Outfit Shoes",
                                    "Takeoff Top",
                                    "Takeoff Bottom",
                                    "Takeoff Shoes",
                                    "Takeoff Hat",
                                    "Remove Sim Outfit",
                                    "Duplicate Sim Outfit",
                                    "Save Sim Outfit",
                                    "Load Sim Outfit")

        self.menu = MainMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)
        self.outfit = OutfitMenu(*args, **kwargs)
        self.load_outfit = MainMenu(*args, **kwargs)
        self.datapath = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
        self.outfit_types = [1, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 36,
                             42]

    def convert_enum_to_dict(self, e: enum.Int):
        enum_dict = {}
        for datum in e:
            enum_dict[datum.name] = datum.value
        return enum_dict

    def _run_interaction_gen(self, timeline, sim_info=None, sims=None):
        try:
            if sim_info is not None:
                OutfitCategoryMenu.outfit_selected_sim_list = []
                OutfitCategoryMenu.outfit_selected_sim = sim_info
                OutfitCategoryMenu.outfit_selected_sim_list.append(sim_info)
            elif sims is not None:
                OutfitCategoryMenu.outfit_selected_sim = sims[0]
                OutfitCategoryMenu.outfit_selected_sim_list = sims
            else:
                client = services.client_manager().get_first_client()
                sim_info = client.active_sim.sim_info
                OutfitCategoryMenu.outfit_selected_sim = sim_info
            if OutfitCategoryMenu.outfit_parts is not None:
                OutfitCategoryMenu.outfit_parts.clear()
            self.menu.MAX_MENU_ITEMS_TO_LIST = 10
            self.menu.commands = []
            self.menu.commands.append("<font color='#990000'>[Menu]</font>")
            self.menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
            self.menu.show(timeline, self, 0, self.outfit_menu_choices, "Change Outfit", "Choose an Option")
            OutfitCategoryMenu.outfit_parts = self.convert_enum_to_dict(BodyType)
        except BaseException as e:
            error_trap(e)

    def _menu(self, timeline, sim_info: SimInfo, sims=None):
        self._run_interaction_gen(timeline, sim_info, sims)

    def modify_career_outfit(self, timeline):
        target = OutfitCategoryMenu.outfit_selected_sim
        sim = init_sim(target)
        client = services.client_manager().get_first_client()
        _connection = client.id
        sims4.commands.client_cheat('sims.exit2caswithhouseholdid {} {} career'.format(sim.id, sim.household_id),
                                    _connection)

    def all(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.EVERYDAY, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            if not OutfitCategoryMenu.outfit_selected_sim.has_outfit((OutfitCategory.CAREER, 0)):
                OutfitCategoryMenu.outfit_data_clipboard = (OutfitCategoryMenu.outfit_selected_sim, OutfitCategory.SITUATION, 0)
                self.paste_outfit(OutfitCategoryMenu.outfit_selected_sim, (OutfitCategory.CAREER, 0))
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE)

    def everyday(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.EVERYDAY, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.EVERYDAY)

    def formal(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.FORMAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.FORMAL)

    def athletic(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.ATHLETIC, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.ATHLETIC)

    def sleep(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SLEEP, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SLEEP)

    def party(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.PARTY, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.PARTY)

    def bathing(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.BATHING, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.BATHING)

    def career(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.CAREER, 0)
                if not sim_info.has_outfit(picked_outfit):
                    OutfitCategoryMenu.outfit_data_clipboard = (sim_info, OutfitCategory.SITUATION, 0)
                    self.paste_outfit(sim_info, picked_outfit)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            if not OutfitCategoryMenu.outfit_selected_sim.has_outfit((OutfitCategory.CAREER, 0)):
                OutfitCategoryMenu.outfit_data_clipboard = (OutfitCategoryMenu.outfit_selected_sim, OutfitCategory.SITUATION, 0)
                self.paste_outfit(OutfitCategoryMenu.outfit_selected_sim, (OutfitCategory.CAREER, 0))
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.CAREER)

    def situation(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SITUATION, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SITUATION)

    def special(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SPECIAL)

    def batuu(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.BATUU, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.BATUU)

    def swimwear(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SWIMWEAR, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SWIMWEAR)

    def hot_weather(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.HOTWEATHER, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.HOTWEATHER)

    def cold_weather(self, timeline):
        if len(OutfitCategoryMenu.outfit_selected_sim_list) > 1:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.COLDWEATHER, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.COLDWEATHER)

    def get_outfit_parts(self, sim_info: SimInfo, outfit_category_and_index):
        try:
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            if outfit_data is None:
                return {}
            return dict(zip(list(outfit_data.body_types), list(outfit_data.part_ids)))
        except BaseException as e:
            error_trap(e)

    def paste_outfit_by_part(self, sim_info: SimInfo, outfit_category_and_index, part_id):
        try:
            copied_sim = OutfitCategoryMenu.outfit_data_clipboard[0]
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            outfit_parts = self.get_outfit_parts(sim_info, outfit_category_and_index)
            new_outfit_parts = self.get_outfit_parts(copied_sim, (OutfitCategoryMenu.outfit_data_clipboard[1],
                                                                  OutfitCategoryMenu.outfit_data_clipboard[2]))

            if outfit_data is None:
                return
            outfit_body_types = []
            outfit_part_ids = []

            # if body_type is any of the copied outfit parts it gets added to the outfit
            # the actual outfit we want to copy
            for body_type, cas_id in new_outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    if body_type == part_id:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))
                        break

            # if body_type is NOT any of the original outfit parts it gets added to the outfit
            # everything else other than the copied outfit that remains the same
            for body_type, cas_id in outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    if body_type != part_id:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))

            outfits_msg = outfit_tracker.save_outfits()
            index = 0
            for outfit in outfits_msg.outfits:
                if int(outfit.category) == int(outfit_category_and_index[0]):
                    if index == outfit_category_and_index[1]:
                        outfit.parts = S4Common_pb2.IdList()
                        outfit.parts.ids.extend(outfit_part_ids)
                        outfit.body_types_list = Outfits_pb2.BodyTypesList()
                        outfit.body_types_list.body_types.extend(outfit_body_types)
                        break
                    index = index + 1

            outfit_tracker._base.outfits = outfits_msg.SerializeToString()
            sim_info = outfit_tracker.get_sim_info()
            sim_info.resend_outfits()
            sim_info.set_current_outfit(outfit_category_and_index)
        except BaseException as e:
            error_trap(e)

    def paste_outfit(self, sim_info: SimInfo, outfit_category_and_index, data=None):
        try:
            if data is None:
                copied_sim = OutfitCategoryMenu.outfit_data_clipboard[0]
            else:
                copied_sim = None
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            outfit_parts = self.get_outfit_parts(sim_info, outfit_category_and_index)

            if data is None:
                new_outfit_parts = self.get_outfit_parts(copied_sim, (OutfitCategoryMenu.outfit_data_clipboard[1],
                                                                      OutfitCategoryMenu.outfit_data_clipboard[2]))
            else:
                new_outfit_parts = data

            if outfit_data is None:
                return
            outfit_body_types = []
            outfit_part_ids = []

            # if body_type is any of the copied outfit parts it gets added to the outfit
            # the actual outfit we want to copy
            for body_type, cas_id in new_outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    for ot in self.outfit_types:
                        if body_type == ot:
                            outfit_body_types.append(int(body_type))
                            outfit_part_ids.append(int(cas_id))
                            continue

            # if body_type is NOT any of the original outfit parts it gets added to the outfit
            # everything else other than the copied outfit that remains the same
            for body_type, cas_id in outfit_parts.items():
                pass_types = True
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    for ot in self.outfit_types:
                        if body_type == ot:
                            pass_types = False
                    if pass_types:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))

            outfits_msg = outfit_tracker.save_outfits()
            index = 0
            for outfit in outfits_msg.outfits:
                if int(outfit.category) == int(outfit_category_and_index[0]):
                    if index == outfit_category_and_index[1]:
                        outfit.parts = S4Common_pb2.IdList()
                        outfit.parts.ids.extend(outfit_part_ids)
                        outfit.body_types_list = Outfits_pb2.BodyTypesList()
                        outfit.body_types_list.body_types.extend(outfit_body_types)
                        break
                    index = index + 1

            outfit_tracker._base.outfits = outfits_msg.SerializeToString()
            sim_info = outfit_tracker.get_sim_info()
            sim_info.resend_outfits()
            sim_info.set_current_outfit(outfit_category_and_index)
        except BaseException as e:
            error_trap(e)

    def remove_outfit(self, sim_info: SimInfo,
                      outfit_category: OutfitCategory,
                      outfit_index: int = 0):
        try:
            outfit_tracker = sim_info.get_outfits()
            if outfit_tracker is None:
                return
            outfit_tracker.remove_outfit(outfit_category, outfit_index)
        except BaseException as e:
            error_trap(e)

    def copy_outfit(self, sim_info: SimInfo,
                    source_outfit_category: OutfitCategory,
                    source_outfit_index: int):
        try:
            outfit_tracker = sim_info.get_outfits()
            if outfit_tracker is None:
                return
            if outfit_tracker.has_outfit((source_outfit_category, source_outfit_index)):
                OutfitCategoryMenu.outfit_data_clipboard = (sim_info, source_outfit_category, source_outfit_index)
            if OutfitCategoryMenu.outfit_data_clipboard is None:
                message_box(None, None, "Copy Error",
                          "Unable to copy outfit!", "ORANGE")
        except BaseException as e:
            error_trap(e)

    def paste_outfit_append(self, sim_info: SimInfo, outfit_category_and_index):
        try:
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            if outfit_data is None:
                return
            new_outfit = outfit_tracker.add_outfit(outfit_category_and_index[0], outfit_data)
            if new_outfit is not None:
                sim_info = outfit_tracker.get_sim_info()
                sim_info.resend_outfits()
                sim_info.set_current_outfit(new_outfit)

        except BaseException as e:
            error_trap(e)

    def copy_sim_outfit(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.is_sim:
                outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
                self.copy_outfit(OutfitCategoryMenu.outfit_selected_sim, outfit[0], outfit[1])
        except BaseException as e:
            error_trap(e)

    def paste_sim_outfit(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.is_sim:
                outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
                self.paste_outfit(OutfitCategoryMenu.outfit_selected_sim, (outfit[0], outfit[1]))
        except BaseException as e:
            error_trap(e)

    def paste_outfit_top(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.is_sim:
                outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
                self.paste_outfit_by_part(OutfitCategoryMenu.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.UPPER_BODY)
        except BaseException as e:
            error_trap(e)

    def paste_outfit_bottom(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.is_sim:
                outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
                self.paste_outfit_by_part(OutfitCategoryMenu.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.LOWER_BODY)
        except BaseException as e:
            error_trap(e)

    def paste_outfit_shoes(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.is_sim:
                outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
                self.paste_outfit_by_part(OutfitCategoryMenu.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.SHOES)
        except BaseException as e:
            error_trap(e)

    def takeoff_top(self, timeline):
        try:
            if OutfitCategoryMenu.outfit_selected_sim_list:
                for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                    outfit = sim_info.get_current_outfit()
                    self.copy_outfit(sim_info, outfit[0], outfit[1])
                    picked_outfit = (OutfitCategory.SPECIAL, 0)
                    if sim_info.has_outfit(picked_outfit):
                        sim_info._current_outfit = picked_outfit
                    outfit = sim_info.get_current_outfit()
                    self.paste_outfit(sim_info, (outfit[0], outfit[1]))
                    outfit = (OutfitCategory.BATHING, 0)
                    self.copy_outfit(sim_info, outfit[0], outfit[1])
                    outfit = (OutfitCategory.SPECIAL, 0)
                    self.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                              BodyType.UPPER_BODY)
            else:
                sim_info = OutfitCategoryMenu.outfit_selected_sim
                outfit = sim_info.get_current_outfit()
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.UPPER_BODY)

        except BaseException as e:
            error_trap(e)

    def takeoff_bottom(self, timeline):
        try:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.LOWER_BODY)
        except BaseException as e:
            error_trap(e)

    def takeoff_shoes(self, timeline):
        try:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.SHOES)
        except BaseException as e:
            error_trap(e)

    def takeoff_hat(self, timeline):
        try:
            for sim_info in OutfitCategoryMenu.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.HAT)
        except BaseException as e:
            error_trap(e)

    def remove_sim_outfit(self, timeline):
        self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.DELETE, None, 10)

    def duplicate_sim_outfit(self, timeline):
        self.outfit.show(OutfitCategoryMenu.outfit_selected_sim, self.outfit.ADD, None)

    def save_sim_outfit(self, timeline):
        try:
            inputbox("Save Sim Outfit", "Choose a filename no spaces", self.save_sim_outfit_callback)
        except BaseException as e:
            error_trap(e)

    def load_sim_outfit(self, timeline):
        try:
            files = [f for f in os.listdir(self.datapath) if isfile(join(self.datapath, f))]
            self.load_outfit.show(None, self, 0, files, "Load Outfit",
                                    "Choose an outfit to load", "load_sim_outfit_callback", True)
        except BaseException as e:
            error_trap(e)

    def write_sim_outfit(self, filename: str):
        try:
            if OutfitCategoryMenu.outfit_selected_sim.age == Age.BABY or OutfitCategoryMenu.outfit_selected_sim.age == Age.TODDLER:
                return
            file = open(filename, "w")
            outfit = OutfitCategoryMenu.outfit_selected_sim.get_current_outfit()
            parts = self.get_outfit_parts(OutfitCategoryMenu.outfit_selected_sim, (outfit[0], outfit[1]))

            file.write("{}:{}\n".format(int(OutfitCategoryMenu.outfit_selected_sim.age), int(OutfitCategoryMenu.outfit_selected_sim.gender)))
            for body_type, cas_id in parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    file.write("{}:{}\n".format(body_type, cas_id))
            file.close()
        except BaseException as e:
            error_trap(e)

    def read_sim_outfit(self, filename: str):
        try:
            file = open(filename, "r")
            body_types = []
            part_ids = []
            index = 0
            age = None
            gender = None
            for line in file.readlines():
                part = line.split(":")
                if len(part) < 2:
                    file.close()
                    return
                if index > 0:
                    body_types.append(int(part[0]))
                    part_ids.append(int(part[1]))
                else:
                    age = int(part[0])
                    gender = int(part[1])
                index = index + 1
            outfit_data = dict(zip(body_types, part_ids))
            file.close()
            for sim in OutfitCategoryMenu.outfit_selected_sim_list:
                outfit = sim.get_current_outfit()

                if sim.age == Age.ADULT and age != Age.CHILD and age != Age.TEEN or \
                        sim.age == Age.YOUNGADULT and age != Age.CHILD and age != Age.TEEN or \
                        sim.age == Age.ELDER and age != Age.CHILD and age != Age.TEEN:
                    self.paste_outfit(sim, outfit, outfit_data)
                elif sim.age == age and sim.age != Age.BABY and sim.age != Age.TODDLER:
                    self.paste_outfit(sim, outfit, outfit_data)
                else:
                    message_box(None, None, "Paste Error",
                              "Unable to paste outfit! Incorrect age group", "ORANGE")

        except BaseException as e:
            error_trap(e)

    def save_sim_outfit_callback(self, filename: str):
        self.write_sim_outfit(self.datapath + r"\{}.outfit".format(filename))

    def load_sim_outfit_callback(self, filename: str):
        self.read_sim_outfit(self.datapath + r"\{}".format(filename))
        
    def _reload_scripts(self, timeline):
        inputbox("Reload Script",
                         "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                OutfitCategoryMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(OutfitCategoryMenu.directory) if isfile(join(OutfitCategoryMenu.directory, f))]
            else:
                OutfitCategoryMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if OutfitCategoryMenu.directory is None:
                OutfitCategoryMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(OutfitCategoryMenu.directory, filename)
        except BaseException as e:
            error_trap(e)