import os
from os.path import isfile, join

import services
import sims4
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims.outfits.outfit_enums import OutfitCategory, BodyType
from sims.sim_info import SimInfo
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import OutfitPickerRow, UiOutfitPicker

from module_outfit.sc_outfit_functions import OutfitFunctions
from scripts_core.sc_input import inputbox
from scripts_core.sc_jobs import get_career_name
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_util import error_trap, ld_file_loader, init_sim


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

            sim = sim_info.get_sim_instance()
            outfit_tracker = sim_info.get_outfits()
            outfits_msg = outfit_tracker.save_outfits()
            outfit_categories = []
            thumbnail_type = UiOutfitPicker._OutftiPickerThumbnailType=UiOutfitPicker._OutftiPickerThumbnailType.SIM_INFO
            for outfit in outfits_msg.outfits:
                if outfit.category not in outfit_categories and outfit.category != OutfitCategory.BATHING and \
                        outfit.category != OutfitCategory.SITUATION and outfit.category != OutfitCategory.BATUU and \
                        outfit.category != OutfitCategory.CAREER and outfit.category != OutfitCategory.SPECIAL:
                    outfit_categories.append(outfit.category)

            dialog = UiOutfitPicker.TunableFactory().default(sim,
                                        text=localized_text,
                                        title=localized_title,
                                        outfit_categories=set(outfit_categories),
                                        thumbnail_type=thumbnail_type,
                                        show_filter=True,
                                        max_selectable=max,
                                        min_selectable=1)

            for category in OutfitCategory:
                if category is not OutfitCategory.CURRENT_OUTFIT:
                    if filter is None or category is filter and filter is not None:
                        index = 0
                        while index < 5:
                            picked_outfit = (category, index)
                            if sim_info.has_outfit(picked_outfit):
                                dialog.add_row(OutfitPickerRow(outfit_sim_id=sim.id,
                                                               outfit_category=category,
                                                               outfit_index=index,
                                                               is_enable=(sim_info.get_current_outfit() != (category, index)),
                                                               tag=picked_outfit))
                            index = index + 1

            dialog.outfit_category_filters = outfit_categories
            dialog.add_listener(get_picker_results_callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)


class OutfitCategoryMenu(ImmediateSuperInteraction):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.outfit_functions = OutfitFunctions()
        self.outfit_menu_choices = ("<font color='#000000'>Modify Menu</font>",
                                    "<font color='#000000'>File Menu</font>",
                                    "<font color='#990000'>All</font>",
                                    "Bathing",
                                    "Career",
                                    "Situation",
                                    "Special",
                                    "Batuu")

        self.outfit_modify_choices = ("<font color='#990000'>Edit Career Outfit</font>",
                                        "Copy Sim Outfit",
                                        "Paste Sim Outfit",
                                        "Paste Sim Outfit To All",
                                        "Paste Makeup And Hair To All",
                                        "Paste Skin Details To All",
                                        "Paste Outfit Top",
                                        "Paste Outfit Bottom",
                                        "Paste Outfit Shoes",
                                        "Paste Outfit Hair",
                                        "Paste Part",
                                        "Takeoff Top",
                                        "Takeoff Bottom",
                                        "Takeoff Shoes",
                                        "Takeoff Hat",
                                        "Takeoff Part",
                                        "Remove Sim Outfit",
                                        "Duplicate Sim Outfit")

        self.outfit_file_choices = ("Save Sim Outfit",
                                    "Save All",
                                    "Load Sim Outfit",
                                    "Load Career Outfit",
                                    "Load Hair And Makeup",
                                    "Load Skin Details",
                                    "Load All")

        self.menu = MainMenu(*args, **kwargs)
        self.outfit_modify_menu = MainMenu(*args, **kwargs)
        self.outfit_file_menu = MainMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)
        self.outfit = OutfitMenu(*args, **kwargs)
        self.load_outfit = MainMenu(*args, **kwargs)
        self.datapath = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
        self.outfit_types = [1, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 36,
                             42]

    def _run_interaction_gen(self, timeline, sim_info=None, sims=None):
        try:
            if sim_info is not None:
                OutfitFunctions.outfit_selected_sim_list = []
                OutfitFunctions.outfit_selected_sim = sim_info
                OutfitFunctions.outfit_selected_sim_list.append(sim_info)
            elif sims is not None:
                OutfitFunctions.outfit_selected_sim = sims[0]
                OutfitFunctions.outfit_selected_sim_list = sims
            else:
                client = services.client_manager().get_first_client()
                sim_info = client.active_sim.sim_info
                OutfitFunctions.outfit_selected_sim = sim_info
            if OutfitFunctions.outfit_parts is not None:
                OutfitFunctions.outfit_parts.clear()
            self.menu.MAX_MENU_ITEMS_TO_LIST = 10
            self.menu.commands = []
            self.menu.commands.append("<font color='#990000'>[Menu]</font>")
            self.menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
            self.menu.show(timeline, self, 0, self.outfit_menu_choices, "Change Outfit", "Choose an Option")
            OutfitFunctions.outfit_parts = self.outfit_functions.convert_enum_to_dict(BodyType)
        except BaseException as e:
            error_trap(e)

    def _menu(self, timeline):
        self._run_interaction_gen(timeline, OutfitFunctions.outfit_selected_sim, OutfitFunctions.outfit_selected_sim_list)

    def modify_menu(self, timeline):
        self.outfit_modify_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.outfit_modify_menu.commands = []
        self.outfit_modify_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.outfit_modify_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.outfit_modify_menu.show(timeline, self, 0, self.outfit_modify_choices, "Modify Outfit", "Choose an Option")

    def file_menu(self, timeline):
        self.outfit_file_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.outfit_file_menu.commands = []
        self.outfit_file_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.outfit_file_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.outfit_file_menu.show(timeline, self, 0, self.outfit_file_choices, "File Menu", "Choose an Option")

    def edit_career_outfit(self, timeline):
        target = OutfitFunctions.outfit_selected_sim
        sim = init_sim(target)
        client = services.client_manager().get_first_client()
        _connection = client.id
        sims4.commands.client_cheat('sims.exit2caswithhouseholdid {} {} career'.format(sim.id, sim.household_id),
                                    _connection)

    def all(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.EVERYDAY, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE)

    def bathing(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.BATHING, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.BATHING)

    def career(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.CAREER, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.CAREER)

    def situation(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SITUATION, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SITUATION)

    def special(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.SPECIAL)

    def batuu(self, timeline):
        if len(OutfitFunctions.outfit_selected_sim_list) > 1:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                picked_outfit = (OutfitCategory.BATUU, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
        else:
            self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.CHANGE, OutfitCategory.BATUU)

    def copy_sim_outfit(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.copy_outfit(OutfitFunctions.outfit_selected_sim, outfit[0], outfit[1])
        except BaseException as e:
            error_trap(e)

    def paste_sim_outfit(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.paste_outfit(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]))
        except BaseException as e:
            error_trap(e)

    def paste_sim_outfit_to_all(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit_tracker = OutfitFunctions.outfit_selected_sim.get_outfits()
                outfits_msg = outfit_tracker.save_outfits()
                picked_outfit = OutfitFunctions.outfit_selected_sim._current_outfit
                for outfit in outfits_msg.outfits:
                    if outfit.category != OutfitCategory.BATHING and outfit.category != OutfitCategory.SLEEP and outfit.category != OutfitCategory.SWIMWEAR:
                        for index in range(5):
                            if outfit_tracker.has_outfit((outfit.category, index)):
                                self.outfit_functions.paste_outfit(OutfitFunctions.outfit_selected_sim, (outfit.category, index))
                OutfitFunctions.outfit_selected_sim._current_outfit = picked_outfit
        except BaseException as e:
            error_trap(e)

    def paste_makeup_and_hair_to_all(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit_tracker = OutfitFunctions.outfit_selected_sim.get_outfits()
                outfits_msg = outfit_tracker.save_outfits()
                picked_outfit = OutfitFunctions.outfit_selected_sim._current_outfit
                for outfit in outfits_msg.outfits:
                    for index in range(5):
                        if outfit_tracker.has_outfit((outfit.category, index)):
                            self.outfit_functions.paste_outfit(OutfitFunctions.outfit_selected_sim, (outfit.category, index), None, self.outfit_functions.outfit_hair_and_makeup)
                OutfitFunctions.outfit_selected_sim._current_outfit = picked_outfit
        except BaseException as e:
            error_trap(e)

    def paste_skin_details_to_all(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit_tracker = OutfitFunctions.outfit_selected_sim.get_outfits()
                outfits_msg = outfit_tracker.save_outfits()
                picked_outfit = OutfitFunctions.outfit_selected_sim._current_outfit
                for outfit in outfits_msg.outfits:
                    for index in range(5):
                        if outfit_tracker.has_outfit((outfit.category, index)):
                            self.outfit_functions.paste_outfit(OutfitFunctions.outfit_selected_sim, (outfit.category, index), None, self.outfit_functions.outfit_skin_details)
                OutfitFunctions.outfit_selected_sim._current_outfit = picked_outfit
        except BaseException as e:
            error_trap(e)

    def paste_outfit_top(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.paste_outfit_by_part(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.UPPER_BODY)
        except BaseException as e:
            error_trap(e)

    def paste_outfit_bottom(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.paste_outfit_by_part(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.LOWER_BODY)
        except BaseException as e:
            error_trap(e)

    def paste_outfit_shoes(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.paste_outfit_by_part(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.SHOES)
        except BaseException as e:
            error_trap(e)

    def paste_outfit_hair(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.outfit_functions.paste_outfit_by_part(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]),
                                          BodyType.HAIR)
        except BaseException as e:
            error_trap(e)

    def paste_part(self, timeline):
        inputbox("Paste Part", "Choose a part", self.paste_part_callback)

    def paste_part_callback(self, part: str):
        try:
            body_type = [info for info in BodyType if part.lower() in str(info.name).lower()]
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                for info in body_type:
                    self.outfit_functions.paste_outfit_by_part(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]),
                                          info)
        except BaseException as e:
            error_trap(e)

    def takeoff_top(self, timeline):
        try:
            if OutfitFunctions.outfit_selected_sim_list:
                for sim_info in OutfitFunctions.outfit_selected_sim_list:
                    outfit = sim_info.get_current_outfit()
                    self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                    picked_outfit = (OutfitCategory.SPECIAL, 0)
                    if sim_info.has_outfit(picked_outfit):
                        sim_info._current_outfit = picked_outfit
                    outfit = sim_info.get_current_outfit()
                    self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                    outfit = (OutfitCategory.BATHING, 0)
                    self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                    outfit = (OutfitCategory.SPECIAL, 0)
                    self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                              BodyType.UPPER_BODY)
            else:
                sim_info = OutfitFunctions.outfit_selected_sim
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.UPPER_BODY)

        except BaseException as e:
            error_trap(e)

    def takeoff_bottom(self, timeline):
        try:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.LOWER_BODY)
        except BaseException as e:
            error_trap(e)

    def takeoff_shoes(self, timeline):
        try:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.SHOES)
        except BaseException as e:
            error_trap(e)

    def takeoff_hat(self, timeline):
        try:
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          BodyType.HAT)
        except BaseException as e:
            error_trap(e)

    def takeoff_part(self, timeline):
        inputbox("Takeoff Part", "Choose a part", self.takeoff_part_callback)

    def takeoff_part_callback(self, part: str):
        try:
            body_type = [info for info in BodyType if part.lower() in str(info.name).lower()]
            for sim_info in OutfitFunctions.outfit_selected_sim_list:
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                picked_outfit = (OutfitCategory.SPECIAL, 0)
                if sim_info.has_outfit(picked_outfit):
                    sim_info._current_outfit = picked_outfit
                outfit = sim_info.get_current_outfit()
                self.outfit_functions.paste_outfit(sim_info, (outfit[0], outfit[1]))
                outfit = (OutfitCategory.BATHING, 0)
                self.outfit_functions.copy_outfit(sim_info, outfit[0], outfit[1])
                outfit = (OutfitCategory.SPECIAL, 0)
                for info in body_type:
                    self.outfit_functions.paste_outfit_by_part(sim_info, (outfit[0], outfit[1]),
                                          info)
        except BaseException as e:
            error_trap(e)

    def remove_sim_outfit(self, timeline):
        self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.DELETE, None, 10)

    def duplicate_sim_outfit(self, timeline):
        self.outfit.show(OutfitFunctions.outfit_selected_sim, self.outfit.ADD, None)

    def save_sim_outfit(self, timeline):
        try:
            name = ""
            if self.target.is_sim:
                outfit = self.target.sim_info.get_current_outfit()
                outfit_category = str(OutfitCategory(outfit[0]).name).lower()
                if "career" not in outfit_category and "situation" not in outfit_category:
                    name = "{}_{}_{}".format(self.target.first_name.lower(), self.target.last_name.lower(), outfit_category)
                elif "career" not in outfit_category:
                    name = "{}".format(str(get_career_name(self.target.sim_info)).lower())
                else:
                    name = "{}_situation".format(str(get_career_name(self.target.sim_info)).lower())
            inputbox("Save Sim Outfit", "Choose a filename no spaces", self.save_sim_outfit_callback, name)
        except BaseException as e:
            error_trap(e)

    def save_all(self, timeline):
        try:
            if self.target.is_sim:
                outfit_tracker = self.target.sim_info.get_outfits()
                outfits_msg = outfit_tracker.save_outfits()
                for outfit in outfits_msg.outfits:
                    outfit_category = str(OutfitCategory(outfit.category).name).lower()
                    for index in range(5):
                        if outfit_tracker.has_outfit((outfit.category, index)):
                            name = "{}_{}_{}{}".format(self.target.first_name.lower(), self.target.last_name.lower(), outfit_category, index)
                            self.outfit_functions.write_sim_outfit(self.datapath + r"\{}.outfit".format(name), (outfit.category, index))
        except BaseException as e:
            error_trap(e)

    def load_all(self, timeline):
        try:
            if self.target.is_sim:
                outfit_tracker = self.target.sim_info.get_outfits()
                outfits_msg = outfit_tracker.save_outfits()
                for outfit in outfits_msg.outfits:
                    outfit_category = str(OutfitCategory(outfit.category).name).lower()
                    for index in range(5):
                        name = "{}_{}_{}{}".format(self.target.first_name.lower(), self.target.last_name.lower(), outfit_category, index)
                        filename = self.datapath + r"\{}.outfit".format(name)
                        if os.path.exists(filename):
                            self.outfit_functions.read_sim_outfit(filename, None, (outfit.category, index))
                            self.outfit_functions.read_sim_outfit(filename, self.outfit_functions.outfit_hair_and_makeup, (outfit.category, index))
                            self.outfit_functions.read_sim_outfit(filename, self.outfit_functions.outfit_skin_details, (outfit.category, index))

        except BaseException as e:
            error_trap(e)

    def load_sim_outfit(self, timeline):
        try:
            files = [f for f in os.listdir(self.datapath) if isfile(join(self.datapath, f))]
            self.load_outfit.show(None, self, 0, files, "Load Outfit",
                                    "Choose an outfit to load", "load_sim_outfit_callback", True)
        except BaseException as e:
            error_trap(e)

    def load_career_outfit(self, timeline):
        try:
            files = [f for f in os.listdir(self.datapath) if isfile(join(self.datapath, f))]
            self.load_outfit.show(None, self, 0, files, "Load Career Outfit",
                                    "Choose an outfit to load", "load_career_outfit_callback", True)
        except BaseException as e:
            error_trap(e)

    def load_hair_and_makeup(self, timeline):
        try:
            files = [f for f in os.listdir(self.datapath) if isfile(join(self.datapath, f))]
            self.load_outfit.show(None, self, 0, files, "Load Hair And Makeup",
                                    "Choose an outfit to load", "load_sim_makeup_callback", True)
        except BaseException as e:
            error_trap(e)

    def load_skin_details(self, timeline):
        try:
            files = [f for f in os.listdir(self.datapath) if isfile(join(self.datapath, f))]
            self.load_outfit.show(None, self, 0, files, "Load Skin Details",
                                    "Choose an outfit to load", "load_sim_details_callback", True)
        except BaseException as e:
            error_trap(e)

    def save_sim_outfit_callback(self, filename: str):
        self.outfit_functions.write_sim_outfit(self.datapath + r"\{}.outfit".format(filename))

    def load_sim_outfit_callback(self, filename: str):
        self.outfit_functions.read_sim_outfit(self.datapath + r"\{}".format(filename))

    def load_career_outfit_callback(self, filename: str):
        self.outfit_functions.read_sim_outfit(self.datapath + r"\{}".format(filename), None, (OutfitCategory.CAREER, 0))

    def load_sim_makeup_callback(self, filename: str):
        self.outfit_functions.read_sim_outfit(self.datapath + r"\{}".format(filename), self.outfit_functions.outfit_hair_and_makeup)

    def load_sim_details_callback(self, filename: str):
        self.outfit_functions.read_sim_outfit(self.datapath + r"\{}".format(filename), self.outfit_functions.outfit_skin_details)

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
