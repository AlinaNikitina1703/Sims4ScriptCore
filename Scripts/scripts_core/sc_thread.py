import time
from threading import Thread

import services
from clock import ClockSpeedMode

from scripts_core.sc_jobs import debugger, update_lights
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_script_vars import sc_Vars


class sc_Watcher(Thread):

    def __init__(self, event, once=True, wait=0.0):
        Thread.__init__(self)
        self.sc_core = ScriptCoreMain()
        self.stopped = event
        self.once = once
        self.wait = wait

    def run(self):
        while not self.stopped.wait(self.wait):
            if self.once:
                self.sc_core.load()
                self.once = False
                debugger("Thread loaded!")
            else:
                time.sleep(sc_Vars.update_speed)
                current_zone = services.current_zone()
                is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
                if current_zone is not None:
                    if current_zone.is_zone_running and not is_paused:
                        self.sc_core.init()
                    elif current_zone.is_zone_running:
                        continue
                    else:
                        sc_Vars._running = False
                        sc_Vars._config_loaded = False

                    if current_zone.is_zone_shutting_down:
                        self.stopped.set()
                        debugger("Thread stopped!")
                        break
