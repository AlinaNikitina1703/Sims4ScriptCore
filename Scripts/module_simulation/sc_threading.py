import time
from threading import Thread

import services
from clock import ClockSpeedMode

from scripts_core.sc_script_vars import sc_Vars


class sc_Watcher(Thread):

    def __init__(self, event, function=None, once=True, wait=0.0):
        Thread.__init__(self)
        self.stopped = event
        self.once = once
        self.wait = wait
        self.function = function

    def run(self):
        while not self.stopped.wait(self.wait):
            if self.once:
                self.once = False
            else:
                time.sleep(sc_Vars.update_speed)
                current_zone = services.current_zone()
                is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
                if current_zone is not None:
                    if current_zone.is_zone_running and not is_paused:
                        self.function()
                        continue
                    elif current_zone.is_zone_running:
                        continue

                    if current_zone.is_zone_shutting_down:
                        self.stopped.set()
                        break
