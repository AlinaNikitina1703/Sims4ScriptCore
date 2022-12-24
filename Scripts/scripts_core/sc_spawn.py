import math
import random

import camera
import objects
import routing
import services
from objects.object_enums import ResetReason
from server_commands.visualization_commands import _create_layer, _spawn_point_visualizers
from sims.sim_spawner import SimSpawner
from sims4.math import Location, Transform, Quaternion, Vector3
from visualization.spawn_point_visualizer import SpawnPointVisualizer
from world.spawn_point import SpawnPointOption

from scripts_core.sc_debugger import debugger
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import init_sim, error_trap, clean_string


class sc_Spawn:
    spawn_points = []

    def __init__(self):
        super().__init__()

    def spawn_sim(self, sim_info, spawn_point=None, level=0, use_radius=False, use_reset=True):
        try:
            zone_id = services.current_zone_id()
            lot = services.active_lot()

            if use_radius:
                lot_x_size = int(lot.size_x)
                lot_z_size = int(lot.size_z)
                lot_size = (lot_x_size + lot_z_size) * 0.5
                x = (lot_size * random.uniform(0.1, 0.5)) * math.cos(math.radians(random.uniform(0, 360)))
                z = (lot_size * random.uniform(0.1, 0.5)) * math.sin(math.radians(random.uniform(0, 360)))
                translation = Vector3(lot.position.x + x,
                                      lot.position.y,
                                      lot.position.z + z)
                orientation = Quaternion.ZERO()
            else:
                if not spawn_point:
                    spawn_point = self.lot_spawn_point()
                    if spawn_point:
                        translation = Vector3(spawn_point._center.x, spawn_point._center.y,spawn_point._center.z)
                        orientation = Quaternion(spawn_point._rotation.x, spawn_point._rotation.y, spawn_point._rotation.z,
                                                 spawn_point._rotation.w)
                    else:
                        translation = lot.position
                        orientation = Quaternion.ZERO()
                elif hasattr(spawn_point, "_center"):
                    translation = spawn_point._center
                    orientation = Quaternion.ZERO()
                elif hasattr(spawn_point, "position"):
                    translation = spawn_point.position
                    orientation = Quaternion.ZERO()
                else:
                    translation = spawn_point.transform.translation
                    orientation = Quaternion.ZERO()


            routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)

            sim_location = Location(Transform(translation, orientation), routing_surface)
            if sim_info.is_instanced():
                sim = sim_info.get_sim_instance()
                if use_reset:
                    sim.reset(ResetReason.NONE, None, 'Command')
                sim.location = sim_location
            else:
                sim = sim_info.get_sim_instance(allow_hidden_flags=objects.ALL_HIDDEN_REASONS)
                try:
                    sim.destroy()
                except:
                    pass
                sim_info.set_zone_on_spawn()
                SimSpawner.spawn_sim(sim_info, sim_location=sim_location, from_load=True,
                                     spawn_point_option=(SpawnPointOption.SPAWN_SAME_POINT))
                sim = init_sim(sim_info)
                if sim.has_hidden_flags(objects.HiddenReasonFlag.RABBIT_HOLE):
                    sim.show(objects.HiddenReasonFlag.RABBIT_HOLE)
                    if use_reset:
                        sim.reset(ResetReason.NONE, None, 'Command')
                    sim.location = sim_location
                else:
                    sim.location = sim_location

            if sc_Vars.ai_function:
                sc_Vars.ai_function.load_sim_ai(sim_info)
                sc_Vars.ai_function.update_sim_ai_info(sim_info)

            if sc_Vars.DEBUG:
                debugger("Spawn Sim: {}".format(sim_info.first_name))

        except BaseException as e:
            error_trap(e)
            
    def validate_spawn_points(self):
        zone = services.current_zone()
        if zone is not None:
            zone.validate_spawn_points()
            for spawn_point in zone.spawn_points_gen():
                valid_positions, _ = spawn_point.get_valid_and_invalid_positions()
                auto_out = ''
                for t in str(spawn_point).split():
                    t = t.replace(',', ' ')
                    if t.find(':') < 0:
                        auto_out += t.replace(',', ' ')
                    else:
                        auto_out += ', ' + t

                valid_positions, _ = spawn_point.get_valid_and_invalid_positions()


    def show_spawn_points(self):
        self.validate_spawn_points()
        vis_name = 'spawn_points'
        handle = 0
        layer = _create_layer(vis_name, handle)
        visualizer = SpawnPointVisualizer(layer)
        for spawn_point_str in visualizer.get_spawn_point_string_gen():
            message_box(None, None, "Spawn Point", "{}".format(clean_string(str(spawn_point_str))), "GREEN")
        if handle in _spawn_point_visualizers:
            return False
        _spawn_point_visualizers[handle] = visualizer

    def focus_on_spawn_points(self, timeline):
        self.get_all_spawn_points()
        points = []
        for point in sc_Spawn.spawn_points:
            try:
                point_string = str(point._center).replace("Vector3Immutable(", "")
                point_string = point_string.replace(")", "")
                points.append(point_string)
            except:
                pass
        #self.spawn_menu.show(timeline, self, 0, points, "Spawn Points", "Focus on a spawn point.", "focus_on_point", True)

    def focus_on_point(self, point):
        pos = Vector3(float(point.split(',')[0]), float(point.split(',')[1]), float(point.split(',')[2]))
        camera.focus_on_position(pos)

    def get_all_spawn_points(self):
        sc_Spawn.spawn_points = []
        zone = services.current_zone()
        for spawn_point in zone.spawn_points_gen():
            sc_Spawn.spawn_points.append(spawn_point)

    def lot_spawn_point(self):
        zone = services.current_zone()
        for spawn_point in zone.spawn_points_gen():
            if spawn_point.lot_id == zone.lot.lot_id:
                return spawn_point

    def world_spawn_point(self, index=0):
        zone = services.current_zone()
        for i, spawn_point in enumerate(zone._world_spawn_points.values()):
            if index == i:
                return spawn_point
