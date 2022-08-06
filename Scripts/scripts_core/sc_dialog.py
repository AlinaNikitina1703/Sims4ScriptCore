import services
import traceback
from scripts_core.sc_io import inject_to
from ui.ui_dialog_notification import UiDialogNotification
from sims.sim_info_types import Age
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog import ButtonType, UiDialog, UiDialogResponse
import ui.ui_dialog_service
from ui.ui_dialog_picker import SimPickerRow, UiSimPicker

class UiDialogChoicesInput(UiDialog):
	__qualname__ = 'UiDialogChoicesInput'
	CHOICES_LOWEST_ID = 20000

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._choice_responses = list()

	def _get_responses_gen(self):
		# yield old values:
		super_results = list(super()._get_responses_gen())
		for result in super_results:
			yield result
		# yield our choices:
		for response in self._choice_responses:
			yield response

shown_choices_dlg = None

@inject_to(ui.ui_dialog_service.UiDialogService, "dialog_respond")
def display_choices_dialog_respond_hook(original, self, *args, **kwargs):
	try:
		dialog = self._active_dialogs.get(\
			args[0], None)

		global shown_choices_dlg
		if shown_choices_dlg != None:
			dlg = shown_choices_dlg
			shown_choices_dlg = None
			dlg.respond(args[1])
			return True

		# regular handling of other dialogs:
		result = original(self, *args, **kwargs)
		return result
	except Exception as e:
		print("INTERNAL ERROR ON RESPOND: " + str(e))
		print(traceback.format_exc())

def display_choices(choices, choice_callback, title="Choose...", text="Please make a choice"):
	global shown_choices_dlg

	# create dialog:
	client = services.client_manager().get_first_client()
	sim_info = client.active_sim.sim_info
	urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
	information_level = UiDialogNotification.UiDialogNotificationLevel.SIM
	visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
	dlg = UiDialogChoicesInput.TunableFactory().\
		default(
		client.active_sim,
		text=lambda **_: LocalizationHelperTuning.get_raw_text(text),
		title=lambda **_: LocalizationHelperTuning.get_raw_text(title)
		)

	# add choices:
	choice_id = dlg.CHOICES_LOWEST_ID
	i = 0
	while i < len(choices):  # NOT a for loop to require indexing to work
		choice = choices[i]
		dlg._choice_responses.append(\
			UiDialogResponse(dialog_response_id=choice_id,
				text=lambda _txt=choice, **_: \
					LocalizationHelperTuning.get_raw_text(\
					_txt),\
				ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST))
		choice_id += 1
		i += 1
	# default cancel choice:
	dlg._choice_responses.append(\
		UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CANCEL,\
			text=lambda **_: LocalizationHelperTuning.get_raw_text(\
				"Cancel"),\
			ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST))

	# response handler calling the choice_callback of the user:
	def response_func(dialog):
		try:
			if dialog.accepted:
				try:
					choice_callback(choices[dialog.response - \
						dlg.CHOICES_LOWEST_ID])
				except IndexError:
					choice_callback(None)
			else:
				choice_callback(None)
		except Exception as e:
			print("[maybecats choices] error in choice_callback: " + str(e))
			print(traceback.format_exc())
			raise e  # propagate error

	# show dialog:
	dlg.add_listener(response_func)
	shown_choices_dlg = dlg
	dlg.show_dialog()

