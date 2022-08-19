import time
from threading import Thread

import services

from scripts_core.sc_jobs import debugger
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_script_vars import sc_Vars


class sc_Watcher(Thread):

    def __init__(self, event, once=False, wait=0.0):
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
                if current_zone is not None:
                    if current_zone.is_zone_running:
                        self.sc_core.init()
                    elif current_zone.is_zone_shutting_down:
                        self.stopped.set()
                        debugger("Thread stopped!")
                        break
