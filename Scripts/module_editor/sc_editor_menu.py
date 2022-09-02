import os
from os.path import isfile, join

import build_buy
import objects
import services
import sims4
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification

from module_editor.sc_editor_functions import point_object_at, random_orientation, get_similar_objects, \
    rotate_selected_objects, random_scale, scale_selected_objects, reset_scale_selected, reset_scale, \
    paint_selected_object, create_game_object, replace_selected_object
from scripts_core.sc_input import inputbox
from scripts_core.sc_jobs import get_tag_name, get_object_info, get_sim_info
from scripts_core.sc_menu_class import MainMenu, ObjectMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_object_menu import ObjectMenuNoFile
from scripts_core.sc_util import error_trap, ld_file_loader, clean_string


class ModuleEditorMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_editor_menu_choices = ("<font color='#009900'>Get Info</font>",
                                        "Search Objects",
                                        "Find Objects",
                                        "<font color='#000000'>Object Select Menu</font>",
                                        "<font color='#000000'>Object Delete Menu</font>",
                                        "<font color='#000000'>Object Rotate Menu</font>",
                                        "<font color='#000000'>Object Scale Menu</font>",
                                       "<font color='#000000'>Object Clone Menu</font>",
                                       "<font color='#000000'>Object Replace Menu</font>")

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

        self.sc_editor_menu = MainMenu(*args, **kwargs)
        self.object_picker = ObjectMenu(*args, **kwargs)
        self.error_object_picker = ObjectMenuNoFile(*args, **kwargs)
        self.sc_editor_select_menu = MainMenu(*args, **kwargs)
        self.sc_editor_delete_menu = MainMenu(*args, **kwargs)
        self.sc_editor_rotate_menu = MainMenu(*args, **kwargs)
        self.sc_editor_scale_menu = MainMenu(*args, **kwargs)
        self.sc_editor_clone_menu = MainMenu(*args, **kwargs)
        self.sc_editor_replace_menu = MainMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Editor Menu is an extension of TOOL by TwistedMexi adding newer functionality to the mod. Editor Menu requires either TOOL or CAW installed.")

    def _menu(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Make a selection.")

    def object_select_menu(self, timeline):
        self.sc_editor_select_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_select_menu.commands = []
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_select_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Make a selection.")

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
