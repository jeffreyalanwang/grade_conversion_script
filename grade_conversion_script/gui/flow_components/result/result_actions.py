from pathlib import Path
from typing import Final, NamedTuple

from nicegui import ui

from grade_conversion_script.gui.state_components import UxFlow


class ResultActionsDepends(NamedTuple):
    file: Path
    filename: str
    media_type: str

class ResultActionsStep(
    UxFlow.FlowStepInputElement[
        ResultActionsDepends
    ]
):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        with self.classes('fit grid justify-center items-center'):
            self.button: Final = ui.button('Download file')

        _ = self.button.on_click(self.handle_button_click)

    def handle_button_click(self):
        assert self.inputs
        ui.download(
            src=self.inputs.file,
            filename=self.inputs.filename,
            media_type=self.inputs.media_type,)