import camera
import objects
import services
import sims4
from distributor.shared_messages import IconInfoData
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.game_object import GameObject
from routing import SurfaceIdentifier, SurfaceType
from sims4.localization import LocalizationHelperTuning
from sims4.resources import get_resource_key, Types
from ui.ui_dialog_picker import UiObjectPicker, ObjectPickerType, ObjectPickerRow

from scripts_core.sc_jobs import get_tags_from_id
from scripts_core.sc_menu_class import ICON_NONE, ICON_MORE, ICON_BACK
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap, get_icon_info_data


class sc_Object:
    def __init__(self, id=0, position=None, orientation=None, location=None, level=0, name=None, icon=None):
        super().__init__()
        self.id = id
        self.position = position
        self.orientation = orientation
        self.location = location
        self.level = level
        self.name = name
        self.icon = icon


class ObjectMenu(ImmediateSuperInteraction):
    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.MAX_MENU_ITEMS_TO_LIST = 10
        self.MENU_MORE = -1
        self.MENU_BACK = -2
        self.title = "Object List"

    def show(self, obj_list, index: int, target: GameObject, max=1, focus=False, callback=None, selection=None, label_override=None):
        try:
            client = services.client_manager().get_first_client()

            def get_picker_results_callback(dialog):
                if not dialog.accepted:
                    return
                result_tags = dialog.get_result_tags()
                for tags in result_tags:
                    if tags is self.MENU_MORE:
                        self.show(obj_list, index + self.MAX_MENU_ITEMS_TO_LIST, target, max, focus, callback, selection)
                    elif tags is self.MENU_BACK and index is not 0:
                        self.show(obj_list, index - self.MAX_MENU_ITEMS_TO_LIST, target, max, focus, callback, selection)
                    elif tags is self.MENU_BACK:
                        return
                    elif focus:
                        camera.focus_on_object(tags)
                    elif callback:
                        callback(tags)

                    elif not focus and not callback:
                        new_obj = objects.system.create_object(tags.definition.id)
                        level = target.level
                        translation = target.position
                        orientation = target.orientation
                        pos = sims4.math.Vector3(translation.x, translation.y, translation.z)
                        zone_id = services.current_zone_id()
                        routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
                        new_obj.location = sims4.math.Location(sims4.math.Transform(pos, orientation),
                                                           routing_surface)

                    elif tags is None:
                        return
                    else:
                        message_box(None, None, "Find", "Unable to find object {}".format(tags), "GREEN")

            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(self.title)
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
            for i, obj in enumerate(list(obj_list)):
                if count >= index:
                    if obj is not None:
                        target_object_tags = get_tags_from_id(obj.definition.id)
                        obj_name = LocalizationHelperTuning.get_object_name(obj)
                        if not label_override:
                            obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})\n{}\n{}".format(file_index, obj.definition.id, obj.__class__.__name__, target_object_tags))
                        else:
                            obj_label = LocalizationHelperTuning.get_raw_text(label_override[i])
                        if selection:
                            if selection(obj):
                                obj_label = LocalizationHelperTuning.get_raw_text("[DIRTY] Index: ({}) Object ID: ({})\n{}\n".format(file_index, obj.definition.id, obj.__class__.__name__, target_object_tags))
                        obj_icon = get_icon_info_data(obj)
                    else:
                        obj_name = LocalizationHelperTuning.get_raw_text("No Object")
                        if not label_override:
                            obj_label = LocalizationHelperTuning.get_raw_text("Index: ({}) Object ID: ({})".format(file_index, 0))
                        else:
                            obj_label = LocalizationHelperTuning.get_raw_text(label_override[i])
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
