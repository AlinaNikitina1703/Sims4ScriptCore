import math
import re

import objects
import services
from scripts_core.sc_dialog import display_choices
from scripts_core.sc_util import error_trap, ld_notice
from distributor.shared_messages import IconInfoData
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.game_object import GameObject
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import ObjectPickerRow, ObjectPickerType, UiObjectPicker

ICON_MORE = 14257953832746441564
ICON_NONE = 15219575448586220634
ICON_BACK = 11835544067185172333

def get_icon_info_data(obj: GameObject):
    if hasattr(obj, "definition"):
        id = obj.definition.id
    else:
        id = obj.sim_id
    if hasattr(obj, "geometry_state"):
        geometry_state = obj.geometry_state
    else:
        geometry_state = None
    if hasattr(obj, "material_hash"):
        material_hash = obj.material_hash
    else:
        material_hash = None

    if id is None:
        info = IconInfoData(obj_instance=obj, obj_name=(LocalizationHelperTuning.get_object_name(obj)))
    else:
        info = IconInfoData(obj_instance=obj, obj_def_id=id,
                        obj_geo_hash=(geometry_state),
                        obj_material_hash=(material_hash),
                        obj_name=(LocalizationHelperTuning.get_object_name(obj)))
    return info

class MainMenu(ImmediateSuperInteraction):

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.commands = []
        self.main_index = 0

    def files(self, timeline, className, funcName, filename: str):
        try:
            filename = filename.replace(".txt","")
            filename = filename.replace(".py", "")
            method = getattr(className, funcName)(filename)
            if method is not None:
                method(timeline)
        except BaseException as e:
            error_trap(e)

    def options(self, timeline, className, choice):
        try:
            result = choice.replace(" ", "_")
            clean = re.compile('<.*?>')
            result = re.sub(clean, '', result)
            result = result.replace("[", "_")
            result = result.replace("]", "")
            result = result.replace("*", "_")
            result = result.lower()
            result = re.sub(r'\W+', '', result)
            if not hasattr(className, result):
                result = "custom_function"
                method = getattr(className, result)
                if method is not None:
                    method(choice)
            else:
                method = getattr(className, result)
                if method is not None:
                    method(timeline)
        except BaseException as e:
            error_trap(e)

    def show(self, timeline, className, index: int, menu_choices, title=None, text=None, funcName=None, show_files=False, back_as_command=False):
        try:
            this_menu_items = []

            def handle_result(result):
                count = 0
                if result is None:
                    return
                elif "[More]" in result:
                    self.show(timeline, className, index + self.MAX_MENU_ITEMS_TO_LIST, menu_choices, title, text, funcName, show_files, back_as_command)
                    self.main_index = index + self.MAX_MENU_ITEMS_TO_LIST
                elif "[Back]" in result and index is not 0:
                    self.show(timeline, className, index - self.MAX_MENU_ITEMS_TO_LIST, menu_choices, title, text, funcName, show_files, back_as_command)
                    self.main_index = index - self.MAX_MENU_ITEMS_TO_LIST
                elif "[Back]" in result:
                    self.main_index = index
                    if back_as_command and show_files is True:
                        self.files(timeline, className, funcName, result)
                    else:
                        return
                else:
                    self.main_index = index
                    for choice in this_menu_items:
                        if result == choice and not show_files:
                            self.options(timeline, className, choice)
                        elif result == choice and show_files is True:
                            self.files(timeline, className, funcName, result)
                        count = count + 1
                        #if count is self.MAX_MENU_ITEMS_TO_LIST:
                        #    break

            count = 0
            if index > len(menu_choices) or index < 0:
                self.main_index = 0
                index = 0

            for item in menu_choices:

                if count >= index:
                    if show_files:
                        this_menu_items.append(item)
                    elif not show_files:
                        this_menu_items.append(item)
                count = count + 1
                if count is self.MAX_MENU_ITEMS_TO_LIST + index and count < len(menu_choices):
                    this_menu_items.append("<font color='#990000'>[More]</font>")
                    break

            this_menu_items.append("<font color='#990000'>[Back]</font>")
            for c in self.commands:
                this_menu_items.append(c)
            page = int((index+1)/self.MAX_MENU_ITEMS_TO_LIST+1)
            if len(menu_choices) > self.MAX_MENU_ITEMS_TO_LIST:
                max_pages = int(math.ceil(len(menu_choices) / self.MAX_MENU_ITEMS_TO_LIST))
            else:
                max_pages = 1
            display_choices(this_menu_items, handle_result, text=text + "\nPage {} of {}".format(page, max_pages), title=title)
        except BaseException as e:
            error_trap(e)

class ObjectMenu(ImmediateSuperInteraction):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.MENU_MORE = -1
        self.MENU_BACK = -2

    def show(self, path: str, filename: str, index: int, target: GameObject, delete=False, max=1):
        try:
            client = services.client_manager().get_first_client()

            def get_picker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        return
                    result_tags = dialog.get_result_tags()
                    deleted = 0
                    indexes = []
                    for tags in result_tags:
                        if tags is self.MENU_MORE:
                            self.show(path, filename, index + self.MAX_MENU_ITEMS_TO_LIST, target, delete, max)
                        elif tags is self.MENU_BACK and index is not 0:
                            self.show(path, filename, index - self.MAX_MENU_ITEMS_TO_LIST, target, delete, max)
                        elif tags is self.MENU_BACK:
                            return
                        elif delete:
                            deleted = deleted + 1
                            indexes.append(tags)

                            ld_notice(None, filename, "Object index: {}".format(tags), False,
                                  "GREEN")
                        elif tags is None:
                            return
                        else:
                            new_obj = objects.system.find_object(tags.definition.id)
                            if new_obj is None:
                                new_obj = objects.system.create_object(tags.definition.id)
                            if new_obj is not None:
                                new_obj.location = target.location
                            else:
                                ld_notice(None, filename, "Unable to place object {}".format(tags.definition.id), False,
                                          "GREEN")
                    if delete and deleted > 0:
                        #remove_object_from_file_by_index(path, filename, indexes)
                        ld_notice(None, filename, "Deleted {} objects".format(deleted), False,
                                  "GREEN")

                except BaseException as e:
                    error_trap(e)

            open_file = path + r"\{}.txt".format(filename)
            file = open(open_file, "r")
            all_lines = file.readlines()
            file.close()

            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(filename)
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("Page {} of {}".format(int((index+1)/self.MAX_MENU_ITEMS_TO_LIST+1),
                                                                                                      int((len(all_lines)+1)/self.MAX_MENU_ITEMS_TO_LIST+1)))

            dialog = UiObjectPicker.TunableFactory().default(client.active_sim,
                                                             text=localized_text,
                                                             title=localized_title,
                                                             max_selectable=max,
                                                             min_selectable=1,
                                                             picker_type=ObjectPickerType.OBJECT)

            count = 0
            file_index = 0
            for line in all_lines:
                if count >= index:
                    values = line.split(":")
                    obj_id = int(values[0])
                    obj = objects.system.create_object(obj_id)
                    if obj is not None:
                        obj_name = LocalizationHelperTuning.get_object_name(obj)
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, obj.definition.id))
                        obj_icon = get_icon_info_data(obj)
                    else:
                        obj_name = LocalizationHelperTuning.get_raw_text("No Object")
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, obj_id))
                        obj_icon = None
                    if not delete:
                        dialog.add_row(
                            ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                            tag=obj))
                    else:
                        dialog.add_row(
                            ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                            tag=file_index))

                count = count + 1
                file_index = file_index + 1
                if count >= self.MAX_MENU_ITEMS_TO_LIST + index:
                    obj_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Show More]</b></p>")
                    obj_label = LocalizationHelperTuning.get_raw_text("")
                    dialog.add_row(
                        ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=None,
                                        tag=self.MENU_MORE))
                    break

            obj_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Go Back]</b></p>")
            obj_label = LocalizationHelperTuning.get_raw_text("")
            dialog.add_row(
                ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=None,
                                tag=self.MENU_BACK))

            dialog.add_listener(get_picker_results_callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

