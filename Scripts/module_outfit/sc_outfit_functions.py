import os

import enum
from protocolbuffers import S4Common_pb2, Outfits_pb2
from sims.outfits.outfit_enums import OutfitCategory
from sims.sim_info import SimInfo
from sims.sim_info_types import Age

from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap, init_sim


class OutfitFunctions:
    outfit_data_clipboard = None
    outfit_data_array = []
    outfit_parts = None
    outfit_selected_sim = None
    outfit_selected_sim_list = None

    def __init__(self):
        (super().__init__)()
        self.datapath = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
        self.outfit_types = [1, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 36,
                             42]

    def convert_enum_to_dict(self, e: enum.Int):
        enum_dict = {}
        for datum in e:
            enum_dict[datum.name] = datum.value
        return enum_dict

    def get_outfit_parts(self, sim_info: SimInfo, outfit_category_and_index):
        try:
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            if outfit_data is None:
                return {}
            return dict(zip(list(outfit_data.body_types), list(outfit_data.part_ids)))
        except BaseException as e:
            error_trap(e)

    def paste_outfit_by_part(self, sim_info: SimInfo, outfit_category_and_index, part_id):
        try:
            copied_sim = OutfitFunctions.outfit_data_clipboard[0]
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            outfit_parts = self.get_outfit_parts(sim_info, outfit_category_and_index)
            new_outfit_parts = self.get_outfit_parts(copied_sim, (OutfitFunctions.outfit_data_clipboard[1],
                                                                  OutfitFunctions.outfit_data_clipboard[2]))

            if outfit_data is None:
                return
            outfit_body_types = []
            outfit_part_ids = []

            # if body_type is any of the copied outfit parts it gets added to the outfit
            # the actual outfit we want to copy
            for body_type, cas_id in new_outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    if body_type == part_id:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))
                        break

            # if body_type is NOT any of the original outfit parts it gets added to the outfit
            # everything else other than the copied outfit that remains the same
            for body_type, cas_id in outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    if body_type != part_id:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))

            outfits_msg = outfit_tracker.save_outfits()
            index = 0
            for outfit in outfits_msg.outfits:
                if int(outfit.category) == int(outfit_category_and_index[0]):
                    if index == outfit_category_and_index[1]:
                        outfit.parts = S4Common_pb2.IdList()
                        outfit.parts.ids.extend(outfit_part_ids)
                        outfit.body_types_list = Outfits_pb2.BodyTypesList()
                        outfit.body_types_list.body_types.extend(outfit_body_types)
                        break
                    index = index + 1

            outfit_tracker._base.outfits = outfits_msg.SerializeToString()
            sim_info = outfit_tracker.get_sim_info()
            sim_info.resend_outfits()
            sim_info.set_current_outfit(outfit_category_and_index)
        except BaseException as e:
            error_trap(e)

    def paste_outfit(self, sim_info: SimInfo, outfit_category_and_index, data=None):
        try:
            if data is None:
                copied_sim = OutfitFunctions.outfit_data_clipboard[0]
            else:
                copied_sim = None
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            outfit_parts = self.get_outfit_parts(sim_info, outfit_category_and_index)

            if data is None:
                new_outfit_parts = self.get_outfit_parts(copied_sim, (OutfitFunctions.outfit_data_clipboard[1],
                                                                      OutfitFunctions.outfit_data_clipboard[2]))
            else:
                new_outfit_parts = data

            if outfit_data is None:
                return
            outfit_body_types = []
            outfit_part_ids = []

            # if body_type is any of the copied outfit parts it gets added to the outfit
            # the actual outfit we want to copy
            for body_type, cas_id in new_outfit_parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    for ot in self.outfit_types:
                        if body_type == ot:
                            outfit_body_types.append(int(body_type))
                            outfit_part_ids.append(int(cas_id))
                            continue

            # if body_type is NOT any of the original outfit parts it gets added to the outfit
            # everything else other than the copied outfit that remains the same
            for body_type, cas_id in outfit_parts.items():
                pass_types = True
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    for ot in self.outfit_types:
                        if body_type == ot:
                            pass_types = False
                    if pass_types:
                        outfit_body_types.append(int(body_type))
                        outfit_part_ids.append(int(cas_id))

            outfits_msg = outfit_tracker.save_outfits()
            index = 0
            for outfit in outfits_msg.outfits:
                if int(outfit.category) == int(outfit_category_and_index[0]):
                    if index == outfit_category_and_index[1]:
                        outfit.parts = S4Common_pb2.IdList()
                        outfit.parts.ids.extend(outfit_part_ids)
                        outfit.body_types_list = Outfits_pb2.BodyTypesList()
                        outfit.body_types_list.body_types.extend(outfit_body_types)
                        break
                    index = index + 1

            outfit_tracker._base.outfits = outfits_msg.SerializeToString()
            sim_info = outfit_tracker.get_sim_info()
            sim_info.resend_outfits()
            sim_info.set_current_outfit(outfit_category_and_index)
        except BaseException as e:
            error_trap(e)

    def remove_outfit(self, sim_info: SimInfo,
                      outfit_category: OutfitCategory,
                      outfit_index: int = 0):
        try:
            outfit_tracker = sim_info.get_outfits()
            if outfit_tracker is None:
                return
            outfit_tracker.remove_outfit(outfit_category, outfit_index)
        except BaseException as e:
            error_trap(e)

    def copy_outfit(self, sim_info: SimInfo,
                    source_outfit_category: OutfitCategory,
                    source_outfit_index: int):
        try:
            outfit_tracker = sim_info.get_outfits()
            if outfit_tracker is None:
                return
            if outfit_tracker.has_outfit((source_outfit_category, source_outfit_index)):
                OutfitFunctions.outfit_data_clipboard = (sim_info, source_outfit_category, source_outfit_index)
            if OutfitFunctions.outfit_data_clipboard is None:
                message_box(None, None, "Copy Error",
                          "Unable to copy outfit!", "ORANGE")
        except BaseException as e:
            error_trap(e)

    def paste_outfit_append(self, sim_info: SimInfo, outfit_category_and_index):
        try:
            outfit_tracker = sim_info.get_outfits()
            outfit_data = outfit_tracker.get_outfit(outfit_category_and_index[0], outfit_category_and_index[1])
            if outfit_data is None:
                return
            new_outfit = outfit_tracker.add_outfit(outfit_category_and_index[0], outfit_data)
            if new_outfit is not None:
                sim_info = outfit_tracker.get_sim_info()
                sim_info.resend_outfits()
                sim_info.set_current_outfit(new_outfit)

        except BaseException as e:
            error_trap(e)

    def copy_sim_outfit(self):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.copy_outfit(OutfitFunctions.outfit_selected_sim, outfit[0], outfit[1])
        except BaseException as e:
            error_trap(e)

    def paste_sim_outfit(self):
        try:
            if OutfitFunctions.outfit_selected_sim.is_sim:
                outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
                self.paste_outfit(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]))
        except BaseException as e:
            error_trap(e)

    def write_sim_outfit(self, filename: str):
        try:
            if OutfitFunctions.outfit_selected_sim.age == Age.BABY or OutfitFunctions.outfit_selected_sim.age == Age.TODDLER:
                return
            file = open(filename, "w")
            outfit = OutfitFunctions.outfit_selected_sim.get_current_outfit()
            parts = self.get_outfit_parts(OutfitFunctions.outfit_selected_sim, (outfit[0], outfit[1]))

            file.write("{}:{}\n".format(int(OutfitFunctions.outfit_selected_sim.age), int(OutfitFunctions.outfit_selected_sim.gender)))
            for body_type, cas_id in parts.items():
                if not body_type == -1:
                    if cas_id == -1:
                        continue
                    file.write("{}:{}\n".format(body_type, cas_id))
            file.close()
        except BaseException as e:
            error_trap(e)

    def read_sim_outfit(self, filename: str):
        try:
            file = open(filename, "r")
            body_types = []
            part_ids = []
            index = 0
            age = None
            gender = None
            for line in file.readlines():
                part = line.split(":")
                if len(part) < 2:
                    file.close()
                    return
                if index > 0:
                    body_types.append(int(part[0]))
                    part_ids.append(int(part[1]))
                else:
                    age = int(part[0])
                    gender = int(part[1])
                index = index + 1
            outfit_data = dict(zip(body_types, part_ids))
            file.close()
            for sim in OutfitFunctions.outfit_selected_sim_list:
                outfit = sim.get_current_outfit()

                if sim.age == Age.ADULT and age != Age.CHILD and age != Age.TEEN or \
                        sim.age == Age.YOUNGADULT and age != Age.CHILD and age != Age.TEEN or \
                        sim.age == Age.ELDER and age != Age.CHILD and age != Age.TEEN:
                    self.paste_outfit(sim, outfit, outfit_data)
                elif sim.age == age and sim.age != Age.BABY and sim.age != Age.TODDLER:
                    self.paste_outfit(sim, outfit, outfit_data)
                else:
                    message_box(None, None, "Paste Error",
                              "Unable to paste outfit! Incorrect age group", "ORANGE")

        except BaseException as e:
            error_trap(e)

def generate_outfit(self, outfit_category, outfit_index):
    return
    datapath = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
    filename = "orderly.outfit"
    picked_outfit = (outfit_category, outfit_index)
    if self.has_outfit(picked_outfit):
        self._current_outfit = picked_outfit
    outfit_functions = OutfitFunctions()
    OutfitFunctions.outfit_selected_sim_list = []
    OutfitFunctions.outfit_selected_sim_list.append(self)
    outfit_functions.read_sim_outfit(datapath + r"\{}".format(filename))
    self.on_outfit_generated(outfit_category, outfit_index)
    self.resend_outfits()
    self.set_outfit_dirty(outfit_category)
