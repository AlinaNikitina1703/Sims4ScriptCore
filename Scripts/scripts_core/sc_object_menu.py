import math

import camera
import services
import sims4
from routing import SurfaceIdentifier, SurfaceType
from scripts_core.sc_menu_class import ICON_NONE, ICON_MORE, ICON_BACK
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap, get_icon_info_data
from distributor.shared_messages import IconInfoData
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.game_object import GameObject
from sims4.localization import LocalizationHelperTuning
from sims4.resources import get_resource_key, Types
from ui.ui_dialog_picker import UiObjectPicker, ObjectPickerType, ObjectPickerRow


class ObjectMenuNoFile(ImmediateSuperInteraction):
    picked_object = None
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.MENU_MORE = -1
        self.MENU_BACK = -2

    def show(self, obj_list, index: int, target: GameObject, delete=False, max=1, focus=False):
        try:
            client = services.client_manager().get_first_client()

            def get_picker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        if not delete and not focus:
                            for obj in list(obj_list):
                                obj.destroy()
                        return
                    result_tags = dialog.get_result_tags()
                    deleted = 0
                    indexes = []
                    for tags in result_tags:
                        if tags is self.MENU_MORE:
                            self.show(obj_list, index + self.MAX_MENU_ITEMS_TO_LIST, target, delete, max, focus)
                        elif tags is self.MENU_BACK and index is not 0:
                            self.show(obj_list, index - self.MAX_MENU_ITEMS_TO_LIST, target, delete, max, focus)
                        elif tags is self.MENU_BACK:
                            return
                        elif focus:
                            camera.focus_on_object(tags)
                        elif delete:
                            deleted = deleted + 1
                            indexes.append(tags)

                            message_box(None, None, "Delete", "Object index: {}".format(tags), "GREEN")
                        elif not delete and not focus:
                            for obj in list(obj_list):
                                if obj != tags:
                                    obj.destroy()
                                else:
                                    level = target.location.level
                                    translation = target.location.transform.translation
                                    orientation = target.location.transform.orientation
                                    pos = sims4.math.Vector3(translation.x, translation.y, translation.z)
                                    zone_id = services.current_zone_id()
                                    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
                                    obj.location = sims4.math.Location(sims4.math.Transform(pos, orientation),
                                                                       routing_surface)

                        elif tags is None:
                            return
                        else:
                            message_box(None, None, "Find", "Unable to find object {}".format(tags.definition.id), "GREEN")
                    if delete and deleted > 0:
                        for obj in indexes:
                            obj.destroy()

                        message_box(None, None, "Delete", "Deleted {} objects".format(deleted), "GREEN")

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
                    if obj is not None:
                        obj_id = obj.definition.id
                        obj_name = LocalizationHelperTuning.get_object_name(obj)
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})\n{}".format(file_index, obj.definition.id, obj.__class__.__name__))
                        obj_icon = get_icon_info_data(obj)
                    else:
                        obj_id = 0
                        obj_name = LocalizationHelperTuning.get_raw_text("No Object")
                        obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, obj_id))
                        obj_icon = IconInfoData(get_resource_key(ICON_NONE, Types.PNG))

                    dialog.add_row(
                        ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=obj_icon,
                        tag=obj))

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
        return ObjectMenuNoFile.picked_object
