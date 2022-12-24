import camera
import objects
import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from routing import SurfaceIdentifier, SurfaceType
from sims4.math import Vector3, Quaternion, Location, Transform, vector_normalize
from terrain import get_terrain_height

from scripts_core.sc_debugger import debugger
from scripts_core.sc_gohere import go_here
from scripts_core.sc_jobs import check_actions, distance_to_pos
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap


class sc_GotoCamera(ImmediateSuperInteraction):

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.marker = None

    def _run_interaction_gen(self, timeline):
        goto_camera_target(self.sim)

    def show_camera_target(self):
        if not self.marker:
            self.marker = objects.system.create_object(317169)
        translation = camera._target_position
        orientation = Quaternion.ZERO()
        pos = Vector3(translation.x, translation.y, translation.z)
        routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
        self.marker.location = Location(Transform(pos, orientation), routing_surface)

    def hide_camera_target(self):
        if self.marker:
            self.marker.destroy()


def vector_magnify(v, m):
    return Vector3(v.x * m, v.y * m, v.z * m)

def camera_info(sim, distance=None, console=False):
    try:
        font_color = "000000"
        font_text = "<font color='#{}'>".format(font_color)
        end_font_text = "</font>"
        if not distance:
            distance = distance_to_pos(camera._camera_position, camera._target_position)
        directional_info = "[Camera Target]: {}\n".format(camera._target_position)
        directional_info = directional_info + "[Camera Position]: {}\n".format(camera._camera_position)
        directional_info = directional_info + "[Distance]: {}\n".format(distance)
        directional_info = directional_info + "[Sim Position]: {}\n".format(sim.position)
        directional_info = directional_info + "[Sim Forward]: {}\n".format(sim.position + sim.forward)
        directional_info = directional_info + "[Sim Distance]: {}\n".format(distance_to_pos(camera._target_position, sim.position))

        if console:
            debugger(directional_info)
            return
        directional_info = directional_info.replace("[", font_text).replace("]", end_font_text)
        message_box(sim, None, "Directional Controls", directional_info)
    except BaseException as e:
        error_trap(e)

def target_from_camera(distance):
    camera_direction = camera._camera_position - camera._target_position
    camera_direction = vector_normalize(camera_direction)
    camera_distance = distance_to_pos(camera._camera_position, camera._target_position)
    camera_move_vector = camera._camera_position - vector_magnify(camera_direction, distance * camera_distance)

    return camera_distance, Vector3(camera_move_vector.x,
                get_terrain_height(camera_move_vector.x, camera_move_vector.z),
                camera_move_vector.z)

def target_from_sim(sim, distance):
    sim_target = sim.position + sim.forward
    sim_direction = sim.position - sim_target
    sim_direction = vector_normalize(sim_direction)
    sim_distance = distance_to_pos(sim.position, sim_target)
    sim_move_vector = sim.position - vector_magnify(sim_direction, distance * sim_distance)

    return sim_distance, Vector3(sim_move_vector.x,
                get_terrain_height(sim_move_vector.x, sim_move_vector.z),
                sim_move_vector.z)

def update_camera(sim, distance=2.0, debug=False):
    if not check_actions(sim, "gohere"):
        camera_distance, camera_target = target_from_camera(distance)

        if distance_to_pos(sim.position, camera_target) > 1.5:
            if go_here(sim, camera_target) and debug:
                camera_info(sim, camera_distance)

def goto_camera_target(sim):
    if not check_actions(sim, "gohere"):
        go_here(sim, camera._target_position)

def set_camera_pos(sim):
    to_sim_direction = camera._camera_position - sim.position
    to_sim_direction = vector_normalize(to_sim_direction)
    to_sim_distance = distance_to_pos(camera._camera_position, sim.position)
    to_sim_move_vector = camera._camera_position - vector_magnify(to_sim_direction, to_sim_distance * 0.5)
    if to_sim_distance > 1:
        camera._camera_position = Vector3(to_sim_move_vector.x,
                                          camera._camera_position.y,
                                          to_sim_move_vector.z)
        camera._target_position = camera._camera_position - vector_magnify(to_sim_direction, to_sim_distance)
