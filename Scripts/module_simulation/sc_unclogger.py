import inspect
from functools import wraps

from module_simulation.sc_unclogger_util import simulation_timeout
from reset import ResettableElement
from scheduling import Timeline


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


_last_heap_handle_date = 0
_last_heap_handle_count = 0
SIMULATION_TIMEOUT = 120

def set_simulation_timeout(timeout):
    global SIMULATION_TIMEOUT
    SIMULATION_TIMEOUT = timeout

@safe_inject(Timeline, 'simulate')
def _reset_stuck_element(original, self, *args, **kwargs):
    global _last_heap_handle_count
    global _last_heap_handle_date
    global SIMULATION_TIMEOUT
    result = original(self, *args, **kwargs)
    try:
        if not result:
            handle = self.heap[0]
            element = handle.element
            if element is not None:
                if isinstance(element, ResettableElement):
                    date = int(handle[0])
                    if _last_heap_handle_date != date:
                        _last_heap_handle_date = date
                        _last_heap_handle_count = 0
                    else:
                        _last_heap_handle_count += 1
                        if _last_heap_handle_count > SIMULATION_TIMEOUT:
                            _last_heap_handle_count = 0
                            simulation_timeout(self, handle)
    except:
        pass

    return result