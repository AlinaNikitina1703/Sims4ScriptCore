import camera
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.math import Vector3, vector_normalize
from terrain import get_terrain_height

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import check_actions, distance_to_pos, go_here
from scripts_core.sc_message_box import message_box


class sc_GotoCamera(ImmediateSuperInteraction):

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        goto_camera_target(self.sim)


def vector_magnify(v, m):
    return Vector3(v.x * m, v.y * m, v.z * m)

def camera_info(sim, distance=None, console=False):
    font_color = "000000"
    font_text = "<font color='#{}'>".format(font_color)
    end_font_text = "</font>"
    if not distance:
        distance = distance_to_pos(camera._camera_position, camera._target_position)
    directional_info = "[Camera Target]: {}\n".format(camera._target_position)
    directional_info = directional_info + "[Camera Position]: {}\n".format(camera._camera_position)
    directional_info = directional_info + "[Distance]: {}\n".format(distance)
    directional_info = directional_info + "[Sim Position]: {}\n".format(sim.position)


    if console:
        debugger(directional_info)
        return
    directional_info = directional_info.replace("[", font_text).replace("]", end_font_text)
    message_box(sim, None, "Directional Controls", directional_info)

def target_from_camera(distance):
    camera_direction = camera._camera_position - camera._target_position
    camera_direction = vector_normalize(camera_direction)
    camera_distance = distance_to_pos(camera._camera_position, camera._target_position)
    camera_move_vector = camera._camera_position - vector_magnify(camera_direction, distance * camera_distance)

    return camera_distance, Vector3(camera_move_vector.x,
                get_terrain_height(camera_move_vector.x, camera_move_vector.z),
                camera_move_vector.z)

def target_from_sim(sim, distance):
    camera_direction = sim.position - camera._target_position
    camera_direction = vector_normalize(camera_direction)
    camera_distance = distance_to_pos(sim.position, camera._target_position)
    camera_move_vector = sim.position - vector_magnify(camera_direction, distance * camera_distance)

    return camera_distance, Vector3(camera_move_vector.x,
                get_terrain_height(camera_move_vector.x, camera_move_vector.z),
                camera_move_vector.z)

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
