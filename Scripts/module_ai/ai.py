import inspect
import os
import random
import re
import time
from inspect import getframeinfo, currentframe

import sims4

import services
from sims4.resources import Types, get_resource_key

from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai_functions import push_sim_function
from module_ai.ai_socials import Behavior
from module_ai.ai_util import error_trap, ld_notice, clean_string, distance_to
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from scripts_core.sc_jobs import distance_to_by_room, clear_queue_of_duplicates, clear_sim_instance, add_sim_buff
from scripts_core.sc_message_box import message_box


class AIMain(ImmediateSuperInteraction):

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

        self.mean_socials = [27704, 25674, 26151, 26544, 35132, 25888, 26543, 25885, 25886, 25577, 98192, 35124]
        self.do_socials = []

    def pick_on_sim_count(self, sim):
        try:
            count = 0
            for queue in AI_Autonomy.behavior_queue:
                if queue.sim == sim:
                    count += 1
            return count
        except BaseException as e:
            error_trap(e)

    def get_sim_count_in_social_group(self, sim, target):
        try:
            # EA only counts sims in the active social group that are with a queue.
            # This counts all sims in the target groups that have social ties to each other active or not.
            this_count = 0
            for group in sim.get_groups_for_sim_gen():
                count = sum((1 for sim in group))
                if this_count < count:
                    this_count = count
            if target.is_sim:
                for that_group in target.get_groups_for_sim_gen():
                    if that_group is not None:
                        if that_group != group:
                            that_count = sum((1 for sim in that_group))
                            if that_count > this_count:
                                this_count = that_count
            return this_count
        except BaseException as e:
            error_trap(e)

    def debugger(self, debug_text):
        try:
            # 0 is root function info, 1 is function info from where its running and 2 is parent calling function
            frame = 1
            now = services.time_service().sim_now
            total_stack = inspect.stack()  # total complete stack
            total_depth = len(total_stack)  # length of total stack
            frameinfo = total_stack[frame][0]  # info on rel frame

            func_name = frameinfo.f_code.co_name
            filename = os.path.basename(frameinfo.f_code.co_filename)
            line_number = frameinfo.f_lineno  # of the call
            func_firstlineno = frameinfo.f_code.co_firstlineno

            debug_text = "\n{}\n".format(now) + debug_text + "\n@{}\n{}\n{}".format(line_number, filename, func_name)
            client = services.client_manager().get_first_client()
            sims4.commands.cheat_output(debug_text, client.id)
        except BaseException as e:
            error_trap(e)

    def is_sim_in_group(self, sim, target):
        for group in sim.get_groups_for_sim_gen():
            for s in group:
                if s == target:
                    return True
        return False

    def init_socials(self):
        disallowed_actions = ["fight", "enemy", "feud"]
        self.do_socials = []
        socials_manager = services.get_instance_manager(Types.INTERACTION)
        for key in sims4.resources.list():
            interaction = socials_manager.get(key.instance)
            action = str(interaction).lower()
            if "mixer_social" in action and not [a for a in disallowed_actions if a in action]:
                self.do_socials.append(interaction)

    def get_social(self, type="mean"):
        do_socials = []
        do_social_names = []
        for social in self.do_socials:
            action = str(social).lower()
            if type in action:
                do_socials.append(social.guid64)
                do_social_names.append(action)

        random.seed(int(time.process_time()))
        index = random.randint(0, len(do_socials) - 1)
        if len(do_socials):
            return do_socials[index]
        return self.mean_socials[index]

    def pick_on_sim(self):
        try:
            allowed_interactions = "sit|violence|gohere|frontdesk|grab|consume|drink|smoke|sim_chat|social"
            for queue in AI_Autonomy.behavior_queue:
                if queue.behavior == Behavior.MEAN:
                    self.set_sim_mood(queue.sim)
                    self.set_sim_mood(queue.target)
                    clear_queue_of_duplicates(queue.sim)
                    social = self.get_social("mean")
                    if queue.sim != queue.target and distance_to_by_room(queue.sim, queue.target) < 8:
                        clear_sim_instance(queue.sim.sim_info, allowed_interactions, True)
                        clear_sim_instance(queue.target.sim_info, allowed_interactions, True)
                        push_sim_function(queue.sim, queue.target, social)
                    elif distance_to(queue.sim, queue.target) > 8:
                        clear_sim_instance(queue.sim.sim_info, "sit", True)
                        clear_sim_instance(queue.target.sim_info, "sit", True)
                        AI_Autonomy.behavior_queue = []
        except BaseException as e:
            error_trap(e)

    def set_sim_mood(self, sim):
        buff_manager = services.get_instance_manager(Types.BUFF)
        buff_component = sim.sim_info.Buffs
        mood = buff_component._active_mood
        buff = buff_manager.get(27207)
        if buff and mood:
            mood_type = str(mood.__name__).replace("Mood_", "")
            visible_buffs = [b for b in buff_manager.types.values() if "feud" not in str(buff.__name__).lower() and sim.sim_info.has_buff(b)]
            if mood_type.lower() not in str(buff.__name__).lower():
                if visible_buffs:
                    for b in visible_buffs:
                        sim.sim_info.remove_buff_by_type(buff_manager.get(get_resource_key(b.guid64, Types.BUFF)))
        if buff:
            add_sim_buff(27207, sim.sim_info)
