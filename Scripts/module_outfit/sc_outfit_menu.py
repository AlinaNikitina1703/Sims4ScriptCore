import os
from os.path import isfile, join

import services
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow

from module_outfit.sc_outfit import OutfitCategoryMenu
from scripts_core.sc_input import inputbox
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_util import error_trap, ld_file_loader


class ModuleOutfitMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_outfit_choices = ("Option 1",
                                       "Set Title")

        self.outfit_category = OutfitCategoryMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        if self.target.is_sim:
            self.outfit_category._run_interaction_gen(timeline, self.target.sim_info, None)
        else:
            try:
                def modify_sim_outfit_callback(dialog):
                    if not dialog.accepted:
                        return
                    try:
                        result_tags = dialog.get_result_tags()
                        sims = []
                        for tags in result_tags:
                            sims.append(tags.sim_info)
                        self.outfit_category._run_interaction_gen(timeline, None, sims)
                    except BaseException as e:
                        error_trap(e)

                self.picker("Modify Outfit", "Pick up to 10 Sims", 50, modify_sim_outfit_callback)
            except BaseException as e:
                error_trap(e)

    def custom_function(self, option):
        return

    def picker(self, title: str, text: str, max: int = 50, callback=None, sims=None):
        try:
            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(text)
            dialog = UiSimPicker.TunableFactory().default(self.sim,
                                                          text=localized_text,
                                                          title=localized_title,
                                                          max_selectable=max,
                                                          min_selectable=1,
                                                          should_show_names=True,
                                                          hide_row_description=False)

            if not sims:
                sims = services.sim_info_manager().instanced_sims_gen()
            for sim in sims:
                dialog.add_row(SimPickerRow(sim.id, False, tag=sim))

            dialog.add_listener(callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

    def _reload_scripts(self, timeline):
        inputbox("Reload Script",
                         "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                ModuleOutfitMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(ModuleOutfitMenu.directory) if isfile(join(ModuleOutfitMenu.directory, f))]
            else:
                ModuleOutfitMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if ModuleOutfitMenu.directory is None:
                ModuleOutfitMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(ModuleOutfitMenu.directory, filename)
        except BaseException as e:
            error_trap(e)
