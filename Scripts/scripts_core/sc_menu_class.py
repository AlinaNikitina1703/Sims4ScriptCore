import math
import re

from distributor.shared_messages import IconInfoData
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.game_object import GameObject
from sims4.localization import LocalizationHelperTuning

from scripts_core.sc_dialog import display_choices
from scripts_core.sc_util import error_trap

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
        self.callback = None
        self.main_index = 0

    def files(self, timeline, className, funcName, filename: str):
        try:
            filename = filename.replace(".txt","")
            filename = filename.replace(".dat","")
            filename = filename.replace(".py", "")
            method = getattr(className, funcName)(filename)
            if method is not None:
                method(timeline)
        except BaseException as e:
            error_trap(e)

    def options(self, timeline, className, choice):
        try:
            if self.callback:
                result = self.callback
            else:
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
            elif self.callback:
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
                            self.options(timeline, className, result)
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

