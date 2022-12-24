import heapq
import inspect
import time

import sims4
from animation.arb_accumulator import ArbSequenceElement
from scheduling import MAX_ELEMENTS, HardStopError, ACCEPTABLE_GARBAGE, MAX_GARBAGE_FACTOR

logger = sims4.log.Logger('Scheduling')
vanilla_run_gen = ArbSequenceElement._run_gen

class sc_Simulate:

    def __init__(self):
        super().__init__()

    def simulate(self, until, max_elements=MAX_ELEMENTS, max_time_ms=None):
        if until < self.future:
            logger.error('Simulating past time. until: {}, future: {}', until, self.future)
            return True
        else:
            count = 0
            self.future = until
            self.per_simulate_callbacks()
            if max_time_ms is not None:
                start_time = time.monotonic()
                end_time = start_time + max_time_ms / 1000
            else:
                end_time = None
        early_exit = False
        while self.heap and self.heap[0].when <= until:
            count += 1
            handle = heapq.heappop(self.heap)
            if handle.element is None:
                self._garbage -= 1
                continue
            when, _, _t, _s, e = handle
            if self.now != when:
                self.now = when
                self.on_time_advanced()
            calling = True
            result = None
            try:
                while e is not None:
                    handle._set_when(None)
                    handle._set_scheduled(False)
                    self._active = (
                     e, handle)
                    try:
                        if calling:
                            result = e._run(self)
                        else:
                            result = e._resume(self, result)
                        if self._pending_hard_stop:
                            raise HardStopError('Hard stop exception was consumed by {}'.format(e))
                    except BaseException as exc:
                        try:
                            self._pending_hard_stop = False
                            self._active = None
                            try:
                                if not isinstance(exc, HardStopError):
                                    self._report_exception(e, exc, 'Exception {} Element'.format('running' if calling else 'resuming'))
                            finally:
                                if e._parent_handle is not None:
                                    self.hard_stop(e._parent_handle)

                        finally:
                            exc = None
                            del exc

                    if inspect.isgenerator(result):
                        raise RuntimeError('Element {} returned a generator {}'.format(e, result))
                    if self._active is None:
                        break
                    if self._child is not None:
                        handle = self._child
                        self._child = None
                        e = handle.element
                        calling = True
                        count += 1
                        continue
                    if handle.is_scheduled:
                        break
                    e._element_handle = None
                    handle = e._parent_handle
                    e._parent_handle = None
                    if handle is None:
                        e._teardown()
                        break
                    child = e
                    e = handle.element
                    will_reschedule = e._child_returned(child)
                    if not will_reschedule:
                        child._teardown()
                    del child
                    calling = False

            finally:
                self._active = None
                self._child = None

            if count >= max_elements:
                early_exit = True
                break
            if end_time is not None and time.monotonic() > end_time:
                early_exit = True
                break

        if self._garbage > ACCEPTABLE_GARBAGE:
            if self._garbage > len(self.heap) * MAX_GARBAGE_FACTOR:
                self._clear_garbage()
        if not early_exit:
            if self.now != until:
                self.now = until
                self.on_time_advanced()
            return True
        return False


#Timeline.simulate = sc_Simulate.simulate
