import alarms
import scheduling
import services

from scripts_core.sc_debugger import debugger
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap, clean_string


class sc_Timeline:

    def __init__(self):
        super().__init__()
        self.timeline = services.time_service().sim_timeline
        self.timeline_values = {}
        self.inverse = False
        self.filter = []

    def get_sim_name_from_timeline(self, handle) -> str:
        sim_info = self.get_sim_from_timeline(handle)
        if sim_info:
            return sim_info.first_name + " " + sim_info.last_name
        return "None"

    def get_sim_from_timeline(self, handle):
        sim_info = None
        try:
            element_str = clean_string(str(handle.element))
            sim = None
            sim_info = None
            v1 = element_str.split("of sim")
            v2 = ["", ""]
            if len(v1):
                v2 = v1[1].split(", interaction")
                if len(v2):
                    sim_id = int(v2[0], 16)
                    sim_info = services.sim_info_manager().get(sim_id)
                    sim = sim_info.get_sim_instance()
        except:
            pass
        return sim_info

    def get_values(self):
        self.timeline_values = {}
        for handle_id, scheduled_at, parent_handle, short_name in self.get_timeline_element_gen():
            self.timeline_values[handle_id] = [scheduled_at, parent_handle, short_name]

    def dump_values(self):
        output_list = ""
        for handle_id, value_list in self.timeline_values.items():
            output_list = output_list + "[{}] {}\n".format(handle_id, str(value_list))
        debugger(output_list)

    def dump_attributes(self):
        output_list = ""
        for handle_id, handle, att, attribute in self.get_timeline_attr_gen():
            output_list = output_list + "[{}] Sim:{} {} {}\n".format(handle_id, self.get_sim_name_from_timeline(handle), att, str(attribute))
        debugger(output_list)

    def dump_element_attributes(self):
        output_list = ""
        for handle_id, att, attribute in self.get_timeline_element_attr_gen():
            output_list = output_list + "[{}] {} {}\n".format(handle_id, att, str(attribute))
        debugger(output_list)

    def get_timeline_element_gen(self):
        for handle in sorted(self.timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                parent_handle = handle
                scheduled_at = handle.when
                handle_id = handle.ix
                child_name = None
                while parent_handle is not None:
                    name = str(parent_handle.element)
                    if child_name is not None:
                        name = name.replace(child_name, '$child')
                    short_name = clean_string(name)
                    short_name = short_name.lower()
                    if not self.inverse and [filter for filter in self.filter if filter in short_name] and len(self.filter) or not len(self.filter):
                        yield handle_id, scheduled_at, parent_handle, short_name
                    elif self.inverse and not [filter for filter in self.filter if filter in short_name] and len(self.filter) or not len(self.filter):
                        yield handle_id, scheduled_at, parent_handle, short_name
                    parent_handle = parent_handle.element._parent_handle
                    child_name = name

    def get_timeline_gen(self):
        for handle in sorted(self.timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                yield handle.ix, handle.when, handle, handle.element.__class__.__name__

    def get_timeline_attr_gen(self):
        for handle in sorted(self.timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                for att in dir(handle):
                    if hasattr(handle, att):
                        yield handle.ix, handle, att, getattr(handle, att)

    def get_timeline_element_attr_gen(self):
        for handle in sorted(self.timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                for att in dir(handle.element):
                    if hasattr(handle.element, att):
                        yield handle.ix, att, getattr(handle.element, att)

    def reset_timeline(self):
        before_len = len(self.timeline.heap)
        for handle in sorted(self.timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                if handle.ix in self.timeline_values.items():
                    self.timeline.hard_stop(handle)
        after_len = len(self.timeline.heap)
        message_box(None, None, "Timeline Reset", "{} elements stopped.".format(before_len - after_len))

    def reset_timeline_by_filter(self):
        before_len = len(self.timeline.heap)
        for handle_id, value_list in self.timeline_values.items():
            self.timeline.hard_stop(value_list[1])
        after_len = len(self.timeline.heap)
        message_box(None, None, "Timeline Reset", "{} elements stopped.".format(abs(before_len - after_len)))

    def get_element_gen(self, filter="running"):
        try:
            names = []
            for handle in sorted(self.timeline.heap):
                if handle.element is not None:
                    if isinstance(handle.element, alarms.AlarmElement):
                        continue
                    parent_handle = handle
                    scheduled_at = handle.when
                    handle_id = handle.ix
                    child_name = None
                    while parent_handle is not None:
                        name = str(parent_handle.element)
                        if child_name is not None:
                            short_name = name.replace(child_name, '$child')
                        else:
                            short_name = name
                        if short_name.find(filter) is not -1 and len(filter) or not len(filter):
                            names.append(short_name)
                        parent_handle = parent_handle.element._parent_handle
                        child_name = name

                    for i, name in enumerate(reversed(names), 1):
                        yield handle_id, scheduled_at, name
        except BaseException as e:
            error_trap(e)
