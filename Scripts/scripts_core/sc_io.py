import inspect
from functools import wraps

import services
import sims4.commands
from clock import ClockSpeedMode
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap
from sims4.resources import Types
from sims4.tuning.instance_manager import InstanceManager
from zone import Zone

c_button_ids = (10025896225466403349, 228298059881543707, 6255962372122061904, 8953588018542590974)

def safe_inject(target_object, target_function_name, safe=False):
    if safe is True:
        if not hasattr(target_object, target_function_name):

            def _self_wrap(wrap_function):
                return wrap_function

            return _self_wrap

    def _wrap_original_function(original_function, new_function):

        @wraps(original_function)
        def _wrapped_function(*args, **kwargs):
            return new_function(original_function, *args, **kwargs)

        if not inspect.ismethod(original_function):
            return _wrapped_function
        return classmethod(_wrapped_function)

    def _injected(wrap_function):
        original_function = getattr(target_object, target_function_name)
        setattr(target_object, target_function_name, _wrap_original_function(original_function, wrap_function))
        return wrap_function

    return _injected

# method calling injection
def inject(target_function, new_function):
    @wraps(target_function)
    def _inject(*args, **kwargs):
        return new_function(target_function, *args, **kwargs)

    return _inject


# decarator injection.
def inject_to(target_object, target_function_name):
    def _inject_to(new_function):
        target_function = getattr(target_object, target_function_name)
        setattr(target_object, target_function_name, inject(target_function, new_function))
        return new_function

    return _inject_to


def is_injectable(target_function, new_function):
    target_argspec = inspect.getargspec(target_function)
    new_argspec = inspect.getargspec(new_function)
    return len(target_argspec.args) == len(new_argspec.args) - 1


@inject_to(InstanceManager, 'load_data_into_class_instances')
def load_sc_buttons(original, self):
    original(self)
    global c_button_ids
    try:
        if self.TYPE == Types.OBJECT:
            affordance_manager = services.affordance_manager()
            sa_list = []
            for sa_id in c_button_ids:
                key = sims4.resources.get_resource_key(sa_id, Types.INTERACTION)
                sa_tuning = affordance_manager.get(key)
                if not sa_tuning is None:
                    sa_list.append(sa_tuning)
            for (key, cls) in self._tuned_classes.items():
                if hasattr(cls, '_super_affordances'):
                    cls._super_affordances += tuple(sa_list)
    except BaseException as e:
        error_trap(e)

