import configparser
import os
from os.path import isfile, join

import build_buy
import objects
import services
import sims4
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.components.types import LIGHTING_COMPONENT
from sims4.localization import LocalizationHelperTuning
from sims4.resources import Types
from ui.ui_dialog_notification import UiDialogNotification
from weather.weather_enums import WeatherEffectType, WeatherElementTuple, PrecipitationType, CloudType, GroundCoverType, \
    Temperature

from module_editor.sc_editor_functions import point_object_at, random_orientation, get_similar_objects, \
    rotate_selected_objects, random_scale, scale_selected_objects, reset_scale_selected, reset_scale, \
    paint_selected_object, replace_selected_object, select_object, move_selected_objects
from scripts_core.sc_input import inputbox
from scripts_core.sc_jobs import compare_room
from scripts_core.sc_jobs import get_tag_name, get_sim_info, get_object_info
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_menu_class import ObjectMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_object_menu import ObjectMenuNoFile
from scripts_core.sc_script_vars import sc_Weather
from scripts_core.sc_util import error_trap, ld_file_loader, clean_string


class ModuleEditorMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None
    initial_value = ""

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_editor_menu_choices = ("<font color='#009900'>Get Info</font>",
                                        "Search Objects",
                                        "Find Objects",
                                        "Select Objects",
                                        "<font color='#000000'>Object Select Menu</font>",
                                        "<font color='#000000'>Object Delete Menu</font>",
                                        "<font color='#000000'>Object Rotate Menu</font>",
                                        "<font color='#000000'>Object Scale Menu</font>",
                                       "<font color='#000000'>Object Clone Menu</font>",
                                       "<font color='#000000'>Object Replace Menu</font>",
                                       "<font color='#000000'>Lights Menu</font>",
                                       "<font color='#000000'>Weather Menu</font>")

        self.sc_rotate_menu_choices = ("Point Object",
                              "Rotate This Object",
                              "Rotate Similar Objects",
                              "Rotate Selected Objects")

        self.sc_scale_menu_choices = ("Reset Scale",
                                    "Scale Similar Objects",
                                    "Less Scale Similar Objects",
                                    "Scale Selected Objects")

        self.sc_clone_menu_choices = ("Paint Selected Object",
                                      "Paint Selected Object Input")

        self.sc_replace_menu_choices = ("Replace Similar Objects",
                                        "Replace Selected Object")

        self.sc_select_menu_choices = ("Select Similar Objects",
                                       "Move Selected Objects")

        self.sc_lights_menu_choices = ("Dim Lights In Room",
                                       "Brighten Lights In Room")

        self.sc_weather_choices = ()
        self.sc_modify_weather_choices = ("Set Variable",
                                          "Set To Sunny",
                                          "Set To Cloudy",
                                          "Set To Partly Cloudy",
                                          "Set To Foggy",
                                          "Set To No Moisture",
                                          "Set To Rain",
                                          "Set To Snow")

        self.sc_editor_menu = MainMenu(*args, **kwargs)
        self.object_picker = ObjectMenu(*args, **kwargs)
        self.error_object_picker = ObjectMenuNoFile(*args, **kwargs)
        self.sc_editor_select_menu = MainMenu(*args, **kwargs)
        self.sc_editor_delete_menu = MainMenu(*args, **kwargs)
        self.sc_editor_rotate_menu = MainMenu(*args, **kwargs)
        self.sc_editor_scale_menu = MainMenu(*args, **kwargs)
        self.sc_editor_clone_menu = MainMenu(*args, **kwargs)
        self.sc_editor_replace_menu = MainMenu(*args, **kwargs)
        self.sc_editor_lights_menu = MainMenu(*args, **kwargs)
        self.sc_weather_menu = MainMenu(*args, **kwargs)
        self.sc_modify_weather_menu = MainMenu(*args, **kwargs)
        self.sc_weather = []
        self.script_choice = MainMenu(*args, **kwargs)
        self.weather_ini()

    def _run_interaction_gen(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Editor Menu is an extension of TOOL by TwistedMexi adding newer functionality to the mod. Editor Menu requires either TOOL or CAW installed.")

    def _menu(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Make a selection.")

    def object_select_menu(self, timeline):
        self.sc_editor_select_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_select_menu.commands = []
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_select_menu.show(timeline, self, 0, self.sc_select_menu_choices, "Object Select Menu", "Make a selection.")

    def object_delete_menu(self, timeline):
        self.sc_editor_delete_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_delete_menu.commands = []
        self.sc_editor_delete_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_delete_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_delete_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Make a selection.")

    def object_rotate_menu(self, timeline):
        self.sc_editor_rotate_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_rotate_menu.commands = []
        self.sc_editor_rotate_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_rotate_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_rotate_menu.show(timeline, self, 0, self.sc_rotate_menu_choices, "Object Rotate Menu", "Make a selection.")

    def object_scale_menu(self, timeline):
        self.sc_editor_scale_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_scale_menu.commands = []
        self.sc_editor_scale_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_scale_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_scale_menu.show(timeline, self, 0, self.sc_scale_menu_choices, "Object Scale Menu", "Make a selection.")

    def object_clone_menu(self, timeline):
        self.sc_editor_clone_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_clone_menu.commands = []
        self.sc_editor_clone_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_clone_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_clone_menu.show(timeline, self, 0, self.sc_clone_menu_choices, "Object Clone Menu", "Make a selection.")

    def object_replace_menu(self, timeline):
        self.sc_editor_replace_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_replace_menu.commands = []
        self.sc_editor_replace_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_replace_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_replace_menu.show(timeline, self, 0, self.sc_replace_menu_choices, "Object Replace Menu", "Make a selection.")

    def lights_menu(self, timeline):
        self.sc_editor_lights_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_lights_menu.commands = []
        self.sc_editor_lights_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_lights_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_lights_menu.show(timeline, self, 0, self.sc_lights_menu_choices, "Lights Menu", "Make a selection.")

    def weather_menu(self, timeline):
        self.sc_weather_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_weather_menu.commands = []
        self.sc_weather_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_weather_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_weather_menu.show(timeline, self, 0, self.sc_weather_choices, "Weather Menu", "Make a selection.")

    def modify_weather(self, timeline):
        self.sc_modify_weather_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_modify_weather_menu.commands = []
        self.sc_modify_weather_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_modify_weather_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_modify_weather_menu.show(timeline, self, 0, self.sc_modify_weather_choices, "Weather Menu", "Make a selection.")

    def dim_lights_in_room(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if not self.target.is_terrain:
            target = self.target

        lights = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                  if compare_room(obj, target)]
        for light in lights:
            if hasattr(light, "set_user_intensity_override"):
                intensity = light.get_user_intensity_overrides()
                intensity = intensity - 0.1
                if intensity < 0.1:
                    intensity = 0.1
                color = light.get_light_color()
                light.set_user_intensity_override(float(intensity))
                light.set_light_color(color)

    def brighten_lights_in_room(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if not self.target.is_terrain:
            target = self.target

        lights = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                  if compare_room(obj, target)]
        for light in lights:
            if hasattr(light, "set_user_intensity_override"):
                intensity = light.get_user_intensity_overrides()
                intensity = intensity + 0.1
                if intensity > 1.0:
                    intensity = 1.0
                color = light.get_light_color()
                light.set_user_intensity_override(float(intensity))
                light.set_light_color(color)

    def get_info(self, timeline):
        try:
            output = ""
            font_color = "000000"
            font_text = "<font color='#{}'>".format(font_color)
            end_font_text = "</font>"
            result = self.target
            for att in dir(result):
                if hasattr(result, att):
                    output = output + "\n(" + str(att) + "): " + clean_string(str(getattr(result, att)))

            if self.target.is_sim:
                info_string = get_sim_info(self.target)
                message_text = info_string
            else:
                info_string = get_object_info(self.target)
            message_text = info_string.replace("[", font_text).replace("]", end_font_text)

            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(message_text)
            localized_title = lambda **_: LocalizationHelperTuning.get_object_name(self.target)
            notification = UiDialogNotification.TunableFactory().default(None,
                                                                         text=localized_text,
                                                                         title=localized_title,
                                                                         icon=None,
                                                                         secondary_icon=None,
                                                                         urgency=urgency,
                                                                         information_level=information_level,
                                                                         visual_type=visual_type,
                                                                         expand_behavior=1)
            notification.show_dialog()

            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("object_info")
            if os.path.exists(filename):
                append_write = 'w'  # append if already exists
            else:
                append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            file.write("{}\n{}\n\nINFO:\n{}".format(self.target.__class__.__name__, info_string, output))
            file.close()

        except BaseException as e:
            error_trap(e)

    def move_selected_objects(self, timeline):
        inputbox("Move Selected Objects", "[x, z]", self.move_selected_objects_callback)

    def move_selected_objects_callback(self, move_string):
        try:
            value = move_string.split(",")
            move_selected_objects(float(value[0]), float(value[1]))
        except BaseException as e:
            error_trap(e)

    def replace_similar_objects(self, timeline):
        try:
            for obj in services.object_manager().get_all():
                if obj.definition.id == self.target.definition.id:
                    replace_selected_object(obj)

        except BaseException as e:
            error_trap(e)

    def paint_selected_object(self, info=None):
        amount = 5
        area = 2.5
        height = 0.25
        if isinstance(info, str):
            values = info.split(",")
            amount = int(values[0])
            area = float(values[1])
            height = float(values[2])
        paint_selected_object(self.target, amount, area, height)

    def paint_selected_object_input(self, timeline):
        inputbox("Paint Selected Object", "[amount, area, height]", self.paint_selected_object)

    def point_object(self, timeline):
        point_object_at(self.target)

    def rotate_this_object(self, timeline):
        if hasattr(self.target, "definition"):
            random_orientation(self.target)

    def rotate_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                random_orientation(obj)

    def rotate_selected_objects(self, timeline):
        rotate_selected_objects()

    def select_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for i, obj in enumerate(similar_objects):
                if i == 0:
                    select_object(obj, True)
                else:
                    select_object(obj, False)

    def reset_scale(self, timeline):
        if self.target.definition.id == 816:
            reset_scale_selected()
        else:
            if hasattr(self.target, "definition"):
                similar_objects = get_similar_objects(self.target.definition.id)
                for obj in similar_objects:
                    reset_scale(obj)

    def scale_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                random_scale(obj)

    def less_scale_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                random_scale(obj, 1.0, 0.25)

    def scale_selected_objects(self, timeline):
        scale_selected_objects()

    def select_objects(self, timeline):
        inputbox("Select Object On Lot", "Searches for object on active lot/zone. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags.",
                         self._select_objects_callback)

    def _select_objects_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            if search.isnumeric():
                obj = objects.system.find_object(int(search), include_props=True)
                if obj:
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)

                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    object_list.append(obj)
                #file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))
            else:
                for obj in services.object_manager().get_all():
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if found:
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                message_box(None, None, "Find Object", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.error_object_picker.show(object_list, 0, self.target, False, 1, False, select_object)
            else:
                message_box(None, None, "Find Object", "No objects found!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def find_objects(self, timeline):
        inputbox("Find Object On Lot", "Searches for object on active lot/zone. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags.",
                         self._find_objects_callback)

    def _find_objects_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            if search.isnumeric():
                obj = objects.system.find_object(int(search), include_props=True)
                if obj:
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)

                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    object_list.append(obj)
                #file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))
            else:
                for obj in services.object_manager().get_all():
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if found:
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                message_box(None, None, "Find Object", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.error_object_picker.show(object_list, 0, self.target, False, 1, True)
            else:
                message_box(None, None, "Find Object", "No objects found!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def search_objects(self, timeline):
        inputbox("Search For Object & Place", "Searches ALL game objects. Will take some time. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags. Only 512 items per search "
                                                      "will be shown.",
                         self._search_objects_callback)

    def _search_objects_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            for key in sorted(sims4.resources.list(type=(sims4.resources.Types.OBJECTDEFINITION))):
                if count < 512:
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(key.instance)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(key.instance))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if [x for x in search_value if x in str(key.instance)]:
                        found = True
                    if found:
                        try:
                            obj = objects.system.create_object(key.instance)
                        except:
                            obj = None
                            pass
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(key.instance, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                message_box(None, None, "Search Objects", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.error_object_picker.show(object_list, 0, self.target, False, 1)
            else:
                message_box(None, None, "Search Objects", "No objects found!", "GREEN")

        except BaseException as e:
            error_trap(e)

    def custom_function(self, option):
        if "weather" in option:
            weather_service = services.weather_service()
            season_service = services.season_service()
            street_service = services.street_service()
            now = services.time_service().sim_now
            selected_weather_list = [weather for weather in self.sc_weather if weather.title == option]
            if selected_weather_list:
                for weather in selected_weather_list:
                    # message_box(None, None, "{}".format(weather.title), "", "GREEN")
                    current_temp = Temperature(weather.temperature)
                    weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
                    weather_service.start_weather_event(weather_event_manager.get(186636), weather.duration)
                    weather_service._trans_info[int(WeatherEffectType.WIND)] = WeatherElementTuple(weather.wind_speed, now, weather.wind_speed, now)
                    weather_service._trans_info[int(WeatherEffectType.WATER_FROZEN)] = WeatherElementTuple(weather.water_frozen, now, weather.water_frozen, now)
                    weather_service._trans_info[int(WeatherEffectType.WINDOW_FROST)] = WeatherElementTuple(weather.window_frost, now, weather.window_frost, now)
                    weather_service._trans_info[int(WeatherEffectType.THUNDER)] = WeatherElementTuple(weather.thunder, now, weather.thunder, now)
                    weather_service._trans_info[int(WeatherEffectType.LIGHTNING)] = WeatherElementTuple(weather.lightning, now, weather.lightning, now)
                    weather_service._trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(weather.snow_amount, now, weather.snow_amount, now)
                    weather_service._trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(weather.rain_amount, now, weather.rain_amount, now)
                    weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(weather.light_clouds, now, weather.light_clouds, now)
                    weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(weather.dark_clouds, now, weather.dark_clouds, now)
                    weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(weather.light_clouds2, now, weather.light_clouds2, now)
                    weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(weather.dark_clouds2, now, weather.dark_clouds2, now)
                    weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(weather.cloudy, now, weather.cloudy, now)
                    weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(weather.heatwave, now, weather.heatwave, now)
                    weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(weather.partly_cloudy, now, weather.partly_cloudy, now)
                    weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(weather.clear, now, weather.clear, now)
                    weather_service._trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(weather.snow_depth, now, weather.snow_depth, now)
                    weather_service._trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(weather.rain_depth, now, weather.rain_depth, now)
                    weather_service._trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = WeatherElementTuple(weather.snow_depth, now, weather.snow_depth, now)
                    weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
                    weather_service._send_weather_event_op()

    def weather_ini(self):
        self.sc_weather_choices = ()
        self.sc_weather_choices = self.sc_weather_choices + ("Reset Weather",)
        self.sc_weather_choices = self.sc_weather_choices + ("Modify Weather",)
        self.sc_weather = []
        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\Data\weather.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        for each_section in config.sections():
            duration = config.getfloat(each_section, "duration")
            wind_speed = config.getfloat(each_section, "wind_speed")
            window_frost = config.getfloat(each_section, "window_frost")
            water_frozen = config.getfloat(each_section, "water_frozen")
            thunder = config.getfloat(each_section, "thunder")
            lightning = config.getfloat(each_section, "lightning")
            temperature = config.getint(each_section, "temperature")
            snow_amount = config.getfloat(each_section, "snow_amount")
            snow_depth = config.getfloat(each_section, "snow_depth")
            rain_amount = config.getfloat(each_section, "rain_amount")
            rain_depth = config.getfloat(each_section, "rain_depth")
            light_clouds = config.getfloat(each_section, "light_clouds")
            dark_clouds = config.getfloat(each_section, "dark_clouds")
            light_clouds2 = config.getfloat(each_section, "light_clouds2")
            dark_clouds2 = config.getfloat(each_section, "dark_clouds2")
            cloudy = config.getfloat(each_section, "cloudy")
            heatwave = config.getfloat(each_section, "heatwave")
            partly_cloudy = config.getfloat(each_section, "partly_cloudy")
            clear = config.getfloat(each_section, "clear")

            self.sc_weather_choices = self.sc_weather_choices + (each_section,)
            self.sc_weather.append(sc_Weather(each_section,
                                            duration,
                                            wind_speed,
                                            window_frost,
                                            water_frozen,
                                            thunder,
                                            lightning,
                                            temperature,
                                            snow_amount,
                                            snow_depth,
                                            rain_amount,
                                            rain_depth,
                                            light_clouds,
                                            dark_clouds,
                                            light_clouds2,
                                            dark_clouds2,
                                            cloudy,
                                            heatwave,
                                            partly_cloudy,
                                            clear))

    def reset_weather(self, timeline):
        services.weather_service().reset_forecasts()

    def set_variable(self, timeline):
        inputbox("Set Variable Weather", "Type in weather identifier and value separated by a comma", self.set_variable_callback, ModuleEditorMenu.initial_value)

    def set_variable_callback(self, variable):
        ModuleEditorMenu.initial_value = variable
        value = variable.split(",")
        duration = 1.0
        now = services.time_service().sim_now
        if len(value) > 2:
            duration = float(value[2])

        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), duration)

        if isinstance(value[0], str):
            trans_info = [info for info in WeatherEffectType if value[0] in str(info.name).lower()]
            trans_info = trans_info + [info for info in CloudType if value[0] in str(info.name).lower()]
            trans_info = trans_info + [info for info in PrecipitationType if value[0] in str(info.name).lower()]
            trans_info = trans_info + [info for info in GroundCoverType if value[0] in str(info.name).lower()]
            for info in trans_info:
                weather_service._trans_info[int(info)] = WeatherElementTuple(float(value[1]), now, float(value[1]), now)
                if "TEMPERATURE" in str(info.name):
                    current_temp = int(value[1])
        elif isinstance(value[0], int):
            weather_service._trans_info[int(value[0])] = WeatherElementTuple(float(value[1]), now, float(value[1]), now)
            if "1007" in str(value[0]):
                current_temp = int(value[1])

        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_sunny(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(1.0, now, 1.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_cloudy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(1.0, now, 1.0, now)
        weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_partly_cloudy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(1.0, now, 1.0, now)
        weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_foggy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(1.01, now, 1.01, now)
        weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.1, now, 0.1, now)
        weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_no_moisture(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now,
                                                                                              current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_rain(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(1.0, now, 1.0, now)
        weather_service._trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now,
                                                                                              current_temp, now)
        weather_service._send_weather_event_op()

    def set_to_snow(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_service.start_weather_event(weather_event_manager.get(186636), 1.0)
        weather_service._trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(0.0, now, 0.0, now)
        weather_service._trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(1.0, now, 1.0, now)
        weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, now)
        weather_service._send_weather_event_op()

    def _reload_scripts(self, timeline):
        inputbox("Reload Script", "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                ModuleEditorMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(ModuleEditorMenu.directory) if isfile(join(ModuleEditorMenu.directory, f))]
            else:
                ModuleEditorMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if ModuleEditorMenu.directory is None:
                ModuleEditorMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(ModuleEditorMenu.directory, filename)
        except BaseException as e:
            error_trap(e)
