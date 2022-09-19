import copy
import random
from math import atan2

import objects
import services
import sims4
from objects.game_object import GameObject
from objects.object_enums import ResetReason
from routing import SurfaceIdentifier, SurfaceType
from sims4.localization import LocalizationHelperTuning
from sims4.math import Location, Transform, Vector3
from tag import Tag
from terrain import get_terrain_height

from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap, clean_string, get_icon_info_data

try:
    from Tmex_TOOL_InputInteraction import TMToolData
except:
    try:
        from tmex_CAW_Library import TMToolData
    except:
        pass
    pass
from ui.ui_dialog_picker import ObjectPickerRow, UiObjectPicker, ObjectPickerType



def get_selected_object():
    return TMToolData.SelectedObject

def reset_all_objects():
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        if obj.definition.tuning_file_id is not 0:
            count = count + 1
            obj.reset(ResetReason.NONE, None, 'Command')
    message_box(None, None, "Reset Objects", "{} Objects reset.".format(count), "GREEN")


def delete_all_objects(error_objects=False, elevation=120):
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        try:
            if error_objects:
                if obj.location.transform.translation.y < elevation and obj.slot_hash == 0:
                    count = count + 1
                    obj.destroy()
            elif obj.definition.id != 816:
                if not obj.is_sim:
                    if not obj.is_on_active_lot():
                        count = count + 1
                        obj.destroy()

        except BaseException as e:
            message_box(None, None, "Object Error", "Object ID {}".format(obj.definition.id), "ORANGE")
            error_trap(e)
    message_box(None, None, "Delete All Objects", "{} Objects deleted.".format(count), "GREEN")

def delete_similar_objects(object_id):
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        try:
            if obj.definition.id == object_id:
                if not obj.is_sim:
                    count = count + 1
                    obj.destroy()

        except BaseException as e:
            message_box(None, None, "Object Error", "Object ID {}".format(obj.definition.id), "ORANGE")
            error_trap(e)
    message_box(None, None, "Delete Similar Objects", "{} Objects deleted.".format(count), "GREEN")

def get_similar_objects(object_id):
    return [obj for obj in services.object_manager().get_all() if obj.definition.id == object_id]

def delete_objects_on_lot():
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        if not obj.is_sim:
            if obj.is_on_active_lot():
                count = count + 1
                obj.destroy()
    message_box(None, None, "Delete Objects On Lot", "{} Objects deleted.".format(count), "GREEN")


def delete_selected_objects():
    try:
        all_objects = TMToolData.GroupObjects
        count = 0
        for obj in list(all_objects):
            count = count + 1
            obj.destroy()
        TMToolData.GroupObjects.clear()
        message_box(None, None, "Delete Selected Objects", "{} Objects deleted.".format(count), "GREEN")
    except BaseException as e:
        error_trap(e)

def move_selected_objects(x=0.0, z=0.0, height=None):
    try:
        zone_id = services.current_zone_id()
        all_objects = TMToolData.GroupObjects
        for obj in list(all_objects):
            position = obj.position
            if height is None:
                position = Vector3(position.x + x,
                                   position.y,
                                   position.z + z)
            else:
                position = Vector3(position.x + x,
                                   position.y + height,
                                   position.z + z)

            level = obj.level
            orientation = obj.orientation
            routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
            obj.location = Location(Transform(position, orientation), routing_surface)

    except BaseException as e:
        error_trap(e)

def place_selected_objects(x=0.0, y = 0.0, z=0.0):
    try:
        zone_id = services.current_zone_id()
        all_objects = TMToolData.GroupObjects
        for obj in list(all_objects):
            position = Vector3(x, y, z)
            level = obj.level
            orientation = obj.orientation
            routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
            obj.location = Location(Transform(position, orientation), routing_surface)

    except BaseException as e:
        error_trap(e)

def get_angle(v1, v2):
    return atan2(v1.x - v2.x, v1.z - v2.z)

def select_object(target, clear=True):
    TMToolData.SelectedObject = target
    if clear:
        TMToolData.GroupObjects.clear()
    TMToolData.GroupObjects.append(TMToolData.SelectedObject)
    target.fade_opacity(0.5, 0.1)
    tint = sims4.color.from_rgba(0, 255, 0)
    target.tint = tint

def clone_selected_object(target):
    zone_id = services.current_zone_id()
    if TMToolData.SelectedObject is not None and not TMToolData.SelectedObject.is_sim:
        clone = create_game_object(TMToolData.SelectedObject.definition.id)
        level = clone.level
        orientation = clone.orientation
        routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
        position = Vector3(target.position.x,
                           target.position.y,
                           target.position.z)
        clone.location = sims4.math.Location(sims4.math.Transform(position, orientation), routing_surface)
        return clone
    return None

def random_position(obj, range=2.5, height=0.25):
    zone_id = services.current_zone_id()
    ground_obj = services.terrain_service.terrain_object()
    level = obj.level
    orientation = obj.orientation
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
    position = Vector3(obj.position.x + random.uniform(-range, range),
                           obj.position.y,
                           obj.position.z + random.uniform(-range, range))
    obj.location = sims4.math.Location(sims4.math.Transform(Vector3(position.x,
                                                                    ground_obj.get_height_at(position.x, position.z) - height,
                                                                    position.z),orientation), routing_surface)

def paint_selected_object(target, amount=10, area=2.5, height=0.25):
    for i in range(amount):
        obj = clone_selected_object(target)
        if obj:
            random_position(obj, area, height)
            random_orientation(obj)
            random_scale(obj, 1.0, 0.25)

def replace_selected_object(obj):
    level = obj.location.level
    scale = obj.scale
    translation = obj.location.transform.translation
    orientation = obj.location.transform.orientation
    obj.destroy()
    clone = create_game_object(TMToolData.SelectedObject.definition.id)
    zone_id = services.current_zone_id()
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
    clone.location = sims4.math.Location(sims4.math.Transform(translation, orientation), routing_surface)
    clone.scale = scale

def point_object_at(target):
    orig = TMToolData.SelectedObject.location.transform.translation
    point = target.location.transform.translation
    angle = get_angle(point, orig)
    level = TMToolData.SelectedObject.location.level
    orientation = sims4.math.angle_to_yaw_quaternion(angle)
    zone_id = services.current_zone_id()
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
    TMToolData.SelectedObject.location = sims4.math.Location(sims4.math.Transform(orig, orientation), routing_surface)

def rotate_selected_objects():
    for obj in TMToolData.GroupObjects:
        random_orientation(obj)

def random_orientation(obj):
    orig = obj.location.transform.translation
    level = obj.location.level
    orientation = sims4.math.angle_to_yaw_quaternion(random.uniform(0.0, sims4.math.TWO_PI))
    zone_id = services.current_zone_id()
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
    obj.location = sims4.math.Location(sims4.math.Transform(orig, orientation), routing_surface)

def random_scale(obj, scale=1.0, degree=0.0):
    obj.scale = scale * random.uniform((0.5 + degree), (1.5 - degree))

def reset_scale(obj):
    obj.scale = 1.0

def reset_scale_selected():
    for obj in TMToolData.GroupObjects:
        reset_scale(obj)

def scale_selected_objects():
    for obj in TMToolData.GroupObjects:
        random_scale(obj)

def swap_objects(obj, target):
    orig_loc = obj.location.transform.translation
    target_loc = target.location.transform.translation
    orig_or = obj.location.transform.orientation
    target_or = target.location.transform.orientation
    level = obj.location.level
    scale = target.scale
    zone_id = services.current_zone_id()
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
    obj.location = sims4.math.Location(sims4.math.Transform(target_loc, target_or), routing_surface)
    target.location = sims4.math.Location(sims4.math.Transform(orig_loc, orig_or), routing_surface)
    obj.scale = scale


def stack_object(obj, parent, hash, translation, orientation):
    if obj is None:
        return
    zone_id = services.current_zone_id()
    transform = sims4.math.Transform(translation, orientation)
    slot_hash = hash
    level = parent.location.level
    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_OBJECT)
    location = obj.create_parent_location(parent,
                                          transform=transform,
                                          joint_name_or_hash=None,
                                          slot_hash=slot_hash,
                                          routing_surface=routing_surface)
    obj.location = location


def get_stack_info(obj):
    if hasattr(obj, "slot_hash"):
        slot_hash = obj.slot_hash
    else:
        slot_hash = 0
    if hasattr(obj, "_location"):
        location_information = clean_string(str(obj._location.parent))
        try:
            value = location_information.split("0x")
            parent_id = int(value[1], 16)
        except:
            parent_id = 0
            pass
    else:
        parent_id = None
    return slot_hash, parent_id


def get_object_pos(obj: GameObject):
    if obj is None:
        return
    translation = obj.location.transform.translation
    return translation


def get_object_rotate(obj: GameObject):
    if obj is None:
        return
    orientation = obj.location.transform.orientation
    return orientation


def write_objects_to_file(filename: str, radius=0.0, save_lot=False, save_selected=False):
    try:
        file = open(filename, "w")
        if not save_selected:
            all_objects = services.object_manager().get_all()
        else:
            all_objects = TMToolData.GroupObjects
        write_entry = True
        for obj in all_objects:
            get_id = obj.definition.id
            if save_selected:
                write_entry = True;
            elif obj.is_on_active_lot() and save_lot is False:
                write_entry = False
            elif obj.is_on_active_lot() and save_lot is True:
                write_entry = True
            elif not obj.is_on_active_lot() and save_lot is True:
                write_entry = False
            else:
                write_entry = True
            if write_entry:
                if not obj.is_sim:
                    level = obj.location.level
                    scale = obj.scale
                    orientation = obj.location.transform.orientation
                    translation = obj.location.transform.translation
                    slot_hash, parent_id = get_stack_info(obj)
                    title = obj.__class__.__name__
                    world_id = obj.id
                    if parent_id > 0:
                        is_parent = 0
                    else:
                        is_parent = 1
                    if translation.x > radius > 1.0 and translation.z > radius or radius < 1.0:
                        file.write("{}:{}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:[{}]\n".
                                   format(get_id,
                                          level, scale, orientation.w, orientation.x, orientation.y,
                                          orientation.z, translation.x, translation.y, translation.z,
                                          title))
        file.close()
    except BaseException as e:
        error_trap(e)
        file.close()


def create_game_object(object_definition, init=None, post_add=None, location=None, household_id=-1, opacity=None):
    try:
        game_object = objects.system.create_object(object_definition, init=init, post_add=post_add)
    except:
        return None
        pass
    if game_object is not None:
        if location is not None:
            game_object.location = location
        if household_id != -1:
            game_object.set_household_owner_id(household_id)
        if opacity is not None:
            game_object.opacity = opacity
        return game_object


def add_object_to_file(path: str, filename: str, target: GameObject):
    try:
        file = open(path + r"\{}.txt".format(filename), "a")
        get_id = target.definition.id
        if not target.is_sim:
            level = target.location.level
            scale = target.scale
            orientation = target.location.transform.orientation
            translation = target.location.transform.translation
            slot_hash, parent_id = get_stack_info(target)
            file.write("{}:{}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:[{}]\n".format(get_id,
                                                                                                     level,
                                                                                                     scale,
                                                                                                     orientation.w,
                                                                                                     orientation.x,
                                                                                                     orientation.y,
                                                                                                     orientation.z,
                                                                                                     translation.x,
                                                                                                     translation.y,
                                                                                                     translation.z,
                                                                                                     target.__class__.__name__))
        file.close()
    except BaseException as e:
        error_trap(e)


def remove_object_from_file_by_index(path: str, filename: str, index: list):
    file = path + r"\{}.txt".format(filename)
    count = 0
    i = 0
    with open(file, "r+") as f:
        new_f = f.readlines()
        f.seek(0)
        for line in new_f:
            if count is not index[i]:
                f.write(line)
            else:
                i = i + 1
                if i is len(index):
                    i = len(index) - 1
            count = count + 1
        f.truncate()
    f.close()


def remove_object_from_file(filename, tags):
    pass


def list_objects_from_file(filename: str, target: GameObject, delete=False):
    try:
        client = services.client_manager().get_first_client()

        def get_picker_results_callback(dialog):
            try:
                if not dialog.accepted:
                    return
                result_tags = dialog.get_result_tags()
                count = 0
                for tags in result_tags:
                    if not delete:
                        new_obj = objects.system.find_object(tags.definition.id)
                        if new_obj is None:
                            new_obj = objects.system.create_object(tags.definition.id)
                        if new_obj is not None:
                            new_obj.location = target.location
                        else:
                            message_box(None, None, filename, "Unable to place object {}".format(tags.definition.id), "GREEN")
                    else:
                        count = count + 1
                        remove_object_from_file(filename, tags)
                if delete:
                    message_box(None, None, filename, "Deleted {} objects".format(count), "GREEN")

            except BaseException as e:
                error_trap(e)

        localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(filename)
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("")
        dialog = UiObjectPicker.TunableFactory().default(client.active_sim,
                                                         text=localized_text,
                                                         title=localized_title,
                                                         max_selectable=50,
                                                         min_selectable=1,
                                                         picker_type=ObjectPickerType.OBJECT)

        open_file = sc_Vars.config_data_location + r"\{}.txt".format(filename)
        file = open(open_file, "r")
        # EMPTY_ICON_INFO_DATA
        all_lines = file.readlines()
        file.close()
        for line in all_lines:
            values = line.split(":")
            obj_id = int(values[0])
            obj = create_game_object(obj_id)
            if obj is not None:
                obj_name = LocalizationHelperTuning.get_object_name(obj)
                obj_label = LocalizationHelperTuning.get_raw_text("Object ID: ({})".format(obj.definition.id))
                dialog.add_row(
                    ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=get_icon_info_data(obj),
                                    tag=obj))

        dialog.add_listener(get_picker_results_callback)
        dialog.show_dialog()
    except BaseException as e:
        error_trap(e)


def read_objects_from_file(target, filename: str, elevate: float = 0, x: float = 0, z: float = 0, selected=False,
                           move_shift=True):
    try:
        file = open(filename, "r")
        orientation = sims4.math.Quaternion(0, 0, 0, 0)
        translation = sims4.math.Vector3(0, 0, 0)
        count = 0
        diff_x = 0.0
        diff_z = 0.0
        for line in file.readlines():
            try:
                values = line.split(":")
                if len(values) < 10:
                    file.close()
                    return
                if count is 0:
                    diff_x = (x - float(values[7]))
                    diff_z = (z - float(values[9]))
                obj_id = int(values[0])
                level = int(values[1])
                scale = float(values[2])
                orientation.w = float(values[3])
                orientation.x = float(values[4])
                orientation.y = float(values[5])
                orientation.z = float(values[6])
                if x is not 0 and move_shift is True:
                    translation.x = float(values[7]) + diff_x
                else:
                    translation.x = float(values[7])
                if elevate == 0:
                    translation.y = float(values[8])
                else:
                    translation.y = float(elevate)
                if z is not 0 and move_shift is True:
                    translation.z = float(values[9]) + diff_z
                else:
                    translation.z = float(values[9])
                try:
                    slot_hash = int(values[10])
                    parent_id = int(values[11])
                except:
                    slot_hash = 0
                    parent_id = 0
                    pass
                obj = create_game_object(obj_id)
                if obj is not None:
                    count = count + 1
                    pos = sims4.math.Vector3(translation.x, translation.y, translation.z)
                    zone_id = services.current_zone_id()
                    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
                    obj.location = sims4.math.Location(sims4.math.Transform(pos, orientation), routing_surface)
                    obj.scale = scale
                    #if slot_hash > 0:
                    #    parent = objects.system.find_object(parent_id)
                    #    if parent is not None:
                    #        stack_object(obj, parent, slot_hash, translation, orientation)
                    #    else:
                    #        translation = sims4.math.Vector3(
                    #            target.location.transform.translation.x + random.uniform(-2, 2),
                    #            target.location.transform.translation.y,
                    #            target.location.transform.translation.z + random.uniform(-2, 2))
                    #        obj.location = sims4.math.Location(sims4.math.Transform(translation, orientation),
                    #                                           routing_surface)
                    #elif translation.y < 3:
                    #    translation = sims4.math.Vector3(
                    #        target.location.transform.translation.x + random.uniform(-2, 2),
                    #        target.location.transform.translation.y,
                    #        target.location.transform.translation.z + random.uniform(-2, 2))
                    #    obj.location = sims4.math.Location(sims4.math.Transform(translation, orientation),
                    #                                       routing_surface)
                    if selected:
                        obj.fade_opacity(0.5, 0.1)
                        tint = sims4.color.from_rgba(0, 255, 0)
                        obj.tint = tint
                        TMToolData.GroupObjects.append(obj)
                        TMToolData.SelectedObject = obj


            except:
                pass

        file.close()
        if selected:
            try:
                TMToolData.refreshGroupCenter()
            except:
                pass
        message_box(None, None, "Load Objects", "{} Objects loaded.".format(count), "GREEN")
    except BaseException as e:
        error_trap(e)


def find_between(s: str, first: str, last: str):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def covert_world_obj_data(filename: str):
    try:
        in_file = r"{}.txt".format(filename)
        out_file = r"{}.txt".format(filename + "_select")
        infile = open(in_file, "r")
        outfile = open(out_file, "w")
        orientation = sims4.math.Quaternion(0, 0, 0, 0)
        translation = sims4.math.Vector3(0, 0, 0)
        count = 0
        data = infile.read().replace("\n", " ")
        try:
            segs_locator = data.split('"Locator":')
            segs_objectdata = data.split('"ObjectData":')

            if len(segs_objectdata) > 0:
                for value in segs_objectdata[1:]:
                    trans_str = find_between(value, '"Position": "', '"')
                    orient_str = find_between(value, '"Rotation": "', '"')
                    if "Identity" in orient_str:
                        orient_str = "0.0,0.0,0.0,0.0"
                    scale_str = find_between(value, '"Scale": ', ',')
                    id_str = find_between(value, '"ObjectDefinitionGUID64": "', '"')
                    obj_id = int(id_str, 16)
                    name_str = find_between(value, '"DefinitionName": "', '"')
                    try:
                        count = count + 1
                        if count > 5000:
                            infile.close()
                            outfile.close()
                            return
                        v = trans_str.split(",")
                        translation.x = float("%0.3f" % (v[0]))
                        translation.y = float("%0.3f" % (v[1]))
                        translation.z = float("%0.3f" % (v[2]))
                        v = orient_str.split(",")
                        orientation.w = float("%0.3f" % (v[0]))
                        orientation.z = float("%0.3f" % (v[1]))
                        orientation.y = float("%0.3f" % (v[2]))
                        orientation.x = -float("%0.3f" % (v[3]))
                        level = 0;
                        outfile.write(
                            "{}:{}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:[{}]\n".format(obj_id, level,
                                                                                                          float(
                                                                                                              scale_str),
                                                                                                          orientation.w,
                                                                                                          orientation.x,
                                                                                                          orientation.y,
                                                                                                          orientation.z,
                                                                                                          translation.x,
                                                                                                          translation.y,
                                                                                                          translation.z,
                                                                                                          name_str))
                    except BaseException as e:
                        error_trap(e)

            if len(segs_locator) > 0:
                for value in segs_locator[1:]:
                    trans_str = find_between(value, '"Position": "', '"')
                    orient_str = find_between(value, '"Orientation": "', '"')
                    if "Identity" in orient_str:
                        orient_str = "0.0,0.0,0.0,0.0"
                    scale_str = find_between(value, '"Scale": ', ',')
                    id_str = find_between(value, '"DefinitionInstance": "', '"')
                    obj_id = int(id_str, 16)
                    name_str = find_between(value, '"DefinitionName": "', '"')
                    try:
                        count = count + 1
                        if count > 5000:
                            infile.close()
                            outfile.close()
                            return
                        v = trans_str.split(",")
                        translation.x = float("%0.3f" % (v[0]))
                        translation.y = float("%0.3f" % (v[1]))
                        translation.z = float("%0.3f" % (v[2]))
                        v = orient_str.split(",")
                        orientation.w = float("%0.3f" % (v[0]))
                        orientation.z = float("%0.3f" % (v[1]))
                        orientation.y = float("%0.3f" % (v[2]))
                        orientation.x = -float("%0.3f" % (v[3]))
                        level = 0;
                        outfile.write(
                            "{}:{}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:{:.4f}:[{}]\n".format(obj_id, level,
                                                                                                          float(
                                                                                                              scale_str),
                                                                                                          orientation.w,
                                                                                                          orientation.x,
                                                                                                          orientation.y,
                                                                                                          orientation.z,
                                                                                                          translation.x,
                                                                                                          translation.y,
                                                                                                          translation.z,
                                                                                                          name_str))
                    except BaseException as e:
                        error_trap(e)

        except BaseException as e:
            error_trap(e)

        infile.close()
        outfile.close()
    except BaseException as e:
        error_trap(e)


def get_world_height(x, z, world_surface, water_surface, object_surface, ignore_object=False):
    world_height = get_terrain_height(x, z, routing_surface=world_surface)
    water_height = get_terrain_height(x, z, routing_surface=water_surface)
    object_height = get_terrain_height(x, z, routing_surface=object_surface)
    if ignore_object:
        return max(world_height, water_height)
    return max(world_height, water_height, object_height)


def get_world_surface(obj: GameObject, snap_to_terrain=True):
    zone_id = services.current_zone().id
    world_surface = SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_WORLD)
    water_surface = SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_POOL)
    object_surface = SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_OBJECT)
    if snap_to_terrain:
        return get_world_height(obj.location.transform.translation.x, obj.location.transform.translation.z,
                                world_surface, water_surface, object_surface, True)
    return obj.location.transform.translation.y


def get_position(obj: GameObject):
    translation = obj.location.transform.translation
    pos = sims4.math.Vector3(translation.x, translation.y, translation.z)
    return pos


def get_tag_name(tag):
    if not isinstance(tag, Tag):
        tag = Tag(tag)
    return tag.name

def copy_lot():
    try:
        zone_manager = services.get_zone_manager()
        persistence_service = services.get_persistence_service()
        save_data = persistence_service.get_save_game_data_proto()
        current_zone = services.current_zone()
        lot_corners = services.current_zone().lot.corners
        neighborhood = persistence_service.get_neighborhood_proto_buff(current_zone.neighborhood_id)
        current_lot = services.active_lot()
        for zone in save_data.zones:
            if zone.neighborhood_id == current_zone.neighborhood_id:
                new_zone = copy.deepcopy(zone)
                new_zone.zone_id = random.getrandbits(32)
                for lot in neighborhood.lots:
                    if lot.zone_instance_id == zone.zone_id:
                        lot.zone_instance_id = new_zone.zone_id
                        lot.corners = sims4.math.Vector3(741, 150.05, 387)
                        lot.size_x = 24
                        lot.size_y = 24
                        del lot.lot_owner[:]

                save_data.zones.append(new_zone)
    except BaseException as e:
        error_trap(e)
