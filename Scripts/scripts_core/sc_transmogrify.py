import objects
import routing
import services
from objects.object_enums import ResetReason
from objects.system import create_script_object
from sims4.color import from_rgba_as_int, to_rgba_as_int
from sims4.math import Location, Transform, Vector3

from scripts_core.sc_file import set_config, get_config
from scripts_core.sc_script_vars import sc_Vars

# New transmog code
def swap_objects(obj, target):
    orig_loc = obj.position
    target_loc = target.position
    orig_or = obj.orientation
    target_or = target.orientation
    orig_level = obj.level
    target_level = target.level
    zone_id = services.current_zone_id()
    routing_surface = routing.SurfaceIdentifier(zone_id, target_level, routing.SurfaceType.SURFACETYPE_WORLD)
    obj.location = Location(Transform(target_loc, target_or), routing_surface)
    routing_surface = routing.SurfaceIdentifier(zone_id, orig_level, routing.SurfaceType.SURFACETYPE_WORLD)
    target.location = Location(Transform(orig_loc, orig_or), routing_surface)

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

def clone_selected_object(source, target):
    zone_id = services.current_zone_id()
    clone = create_game_object(source.definition.id)
    level = source.level
    scale = source.scale
    orientation = source.orientation
    routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
    position = Vector3(target.position.x,
                       target.position.y,
                       target.position.z)
    clone.location = Location(Transform(position, orientation), routing_surface)
    clone.scale = scale
    return clone

def load_material(target):
    if set_material(target,
                 get_config("Mats/{}.mat".format(target.id), "material", "model"),
                 get_config("Mats/{}.mat".format(target.id), "material", "tex"),
                 get_config("Mats/{}.mat".format(target.id), "material", "tint")):
        return True
    return False

def save_material(target):
    set_config("Mats/{}.mat".format(target.id), "material", "model", target.definition.id)
    set_config("Mats/{}.mat".format(target.id), "material", "tex", target._material_variant)
    if target.tint:
        set_config("Mats/{}.mat".format(target.id), "material", "tint", to_rgba_as_int(target.tint))

def transmogrify(source, target):
    target.reset(ResetReason.NONE, None, 'Command')
    source = clone_selected_object(source, target)
    swap_objects(source, target)
    source._model = target._model
    source.model = target.model
    source.model_with_material_variant = (target.model, target._material_variant)
    source._material_variant = target._material_variant
    save_material(source)
    set_config("Mats/{}.mat".format(source.id), "material", "model", target.definition.id)
    sc_Vars.transmog_objects.append(source) if source not in sc_Vars.transmog_objects else None
    target.destroy()

def set_material(target, model, tex, tint=None):
    if not model and not tex and not tint:
        return False
    if model and tex:
        if type(model) is int:
            script = objects.system.create_script_object(model)
            model = script.model
        target._model = model
        target.model = model
        target.model_with_material_variant = (target.model, tex)
        target._material_variant = tex
    if tint:
        r, g, b, a = tint
    else:
        r, g, b, a = (255, 255, 255, 1)
    target.tint = from_rgba_as_int(r, g, b)
    return True
