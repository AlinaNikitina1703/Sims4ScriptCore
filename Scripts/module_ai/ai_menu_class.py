import objects
import services
from module_ai.ai_debug import get_icon_info_data
from module_ai.ai_dialog import display_choices
from module_ai.ai_util import error_trap, ld_notice
from distributor.shared_messages import IconInfoData
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.context import InteractionContext, QueueInsertStrategy
from interactions.priority import Priority
from objects.game_object import GameObject
from sims4.localization import LocalizationHelperTuning
from sims4.resources import get_resource_key, Types
from ui.ui_dialog_picker import ObjectPickerRow, ObjectPickerType, UiObjectPicker, ObjectPickerStyle

ICON_MORE = 14257953832746441564
ICON_NONE = 15219575448586220634
ICON_BACK = 11835544067185172333

class MainMenu(ImmediateSuperInteraction):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10

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
            result = result.replace("*", "_")
            result = result.lower()
            method = getattr(className, result)
            if method is not None:
                method(timeline)
        except BaseException as e:
            error_trap(e)

    def show(self, timeline, className, index: int, menu_choices, title=None, text=None, funcName=None, show_files=False, show_main=False):
        try:
            this_menu_items = []

            def handle_result(result):
                count = 0
                if result is None:
                    return
                elif result == "Main Menu" and show_main is True:
                    self.options(timeline, className, result)
                elif result == "More":
                    self.show(timeline, className, index + self.MAX_MENU_ITEMS_TO_LIST, menu_choices, title, text, funcName, show_files, show_main)
                elif result == "Back" and index is not 0:
                    self.show(timeline, className, index - self.MAX_MENU_ITEMS_TO_LIST, menu_choices, title, text, funcName, show_files, show_main)
                elif result == "Back":
                    return
                else:
                    for choice in this_menu_items:
                        if result == choice and not show_files:
                            self.options(timeline, className, choice)
                        elif result == choice and show_files is True:
                            self.files(timeline, className, funcName, choice)
                        count = count + 1
                        if count is self.MAX_MENU_ITEMS_TO_LIST:
                            break

            count = 0
            for item in menu_choices:

                if count >= index:
                    if show_files:
                        this_menu_items.append(item)
                    elif not show_files:
                        this_menu_items.append(item)
                count = count + 1
                if count is self.MAX_MENU_ITEMS_TO_LIST + index:
                    this_menu_items.append("More")
                    break

            if show_main is True:
                this_menu_items.append("Main Menu")
            if index > 0:
                this_menu_items.append("Back")
            display_choices(this_menu_items, handle_result, text=text, title=title)
        except BaseException as e:
            error_trap(e)

class ObjectMenu(ImmediateSuperInteraction):
    picked_object = None
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.MENU_MORE = -1
        self.MENU_BACK = -2

    def show(self, obj_list, index: int, target: GameObject, delete=False, max=1):
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
                            self.show(obj_list, index + self.MAX_MENU_ITEMS_TO_LIST, target, delete, max)
                        elif tags is self.MENU_BACK and index is not 0:
                            self.show(obj_list, index - self.MAX_MENU_ITEMS_TO_LIST, target, delete, max)
                        elif tags is self.MENU_BACK:
                            return
                        elif delete:
                            deleted = deleted + 1
                            indexes.append(tags)

                            ld_notice(None, "Delete", "Object index: {}".format(tags), False,
                                  "GREEN")
                        elif tags is None:
                            return
                        else:
                            ObjectMenu.picked_object = tags
                            if ObjectMenu.picked_object is not None:
                                goto_interaction = 12677454845923784945
                                #goto_interaction = 15701567395891038891
                                if ObjectMenu.picked_object is not None:
                                    affordance_manager = services.affordance_manager()
                                    context = InteractionContext(target, (InteractionContext.SOURCE_SCRIPT),
                                                                 (Priority.High),
                                                                 insert_strategy=(QueueInsertStrategy.FIRST))
                                    target.push_super_affordance(affordance_manager.get(goto_interaction),
                                                                      ObjectMenu.picked_object, context)
                            else:
                                ld_notice(None, "Find", "Unable to find object {}".format(tags.definition.id), False,
                                          "GREEN")
                    if delete and deleted > 0:
                        #remove_object_from_file_by_index(path, filename, indexes)
                        ld_notice(None, "Delete", "Deleted {} objects".format(deleted), False,
                                  "GREEN")

                except BaseException as e:
                    error_trap(e)

            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text("Object List")
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("Page {} of {}".format(int((index+1)/self.MAX_MENU_ITEMS_TO_LIST+1),
                                                                                                      int((len(obj_list)+1)/self.MAX_MENU_ITEMS_TO_LIST+1)))

            dialog = UiObjectPicker.TunableFactory().default(client.active_sim,
                                                             text=localized_text,
                                                             title=localized_title,
                                                             max_selectable=max,
                                                             min_selectable=1,
                                                             picker_type=ObjectPickerType.OBJECT)

            count = 0
            file_index = 0
            for obj in list(obj_list):
                if count >= index:
                    obj_id = obj.definition.id
                    if obj is not None:
                        obj_name = LocalizationHelperTuning.get_object_name(obj)
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, obj.definition.id))
                        obj_icon = get_icon_info_data(obj)
                    else:
                        obj_name = LocalizationHelperTuning.get_raw_text("No Object")
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, obj_id))
                        obj_icon = IconInfoData(get_resource_key(ICON_NONE, Types.PNG))
                    if not delete:
                        dialog.add_row(
                            ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                            tag=obj, object_picker_style=ObjectPickerStyle.NUMBERED))
                    else:
                        dialog.add_row(
                            ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                            tag=obj.definition.id, object_picker_style=ObjectPickerStyle.NUMBERED))

                count = count + 1
                file_index = file_index + 1
                if count >= self.MAX_MENU_ITEMS_TO_LIST + index:
                    obj_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Show More]</b></p>")
                    obj_label = LocalizationHelperTuning.get_raw_text("")
                    obj_icon = IconInfoData(get_resource_key(ICON_MORE, Types.PNG))
                    dialog.add_row(
                        ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                                        tag=self.MENU_MORE))
                    break

            obj_name = LocalizationHelperTuning.get_raw_text("<p style='font-size:30px'><b>[Go Back]</b></p>")
            obj_label = LocalizationHelperTuning.get_raw_text("")
            obj_icon = IconInfoData(get_resource_key(ICON_BACK, Types.PNG))
            dialog.add_row(
                ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                                tag=self.MENU_BACK))

            dialog.add_listener(get_picker_results_callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

    def get_picked_object(self):
        return ObjectMenu.picked_object

