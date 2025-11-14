from collections.abc import Collection
from typing import Sequence

from nicegui import ui

from grade_conversion_script.gui.base_components.dual_list_match \
    import DualListMatch
from grade_conversion_script.gui.flow_components.pane_header import \
    ClientSideHeaderElement
from grade_conversion_script.gui.state_components import UxFlow


class WarnExistings(  # pyright: ignore[reportUnsafeMultipleInheritance]
    UxFlow.FlowStepElement,
    ClientSideHeaderElement,
):
    def __init__(
        self,
        messages: Sequence[str],
        *args,
        **kwargs,
    ):
        ''' `given_labels` are matched injectively to `dest_labels`. '''
        super().__init__(
            *args,
            header_text='Existing grades',
            initial_state=UxFlow.State.START_READY,
            **kwargs, )
        _ = self.content.classes('q-px-md')

        with self.header_bar:
            _ = ui.space()
            done_button = (
                ui.button(
                    text = 'Done',
                    color = 'accent',)
                .props('outline icon-right="check"'))
        with self:
            _ = (
                self.content  # see parent class
                .classes('q-py-sm'))
            with ui.list().props('dense'):
                _ = ui.item_label(messages[0]).props('header').classes('text-bold')
                _ = ui.separator()
                for message in messages[1:]:
                    _ = ui.item(message)

        _ = done_button.on_click(self.handle_done_button)

    def handle_done_button(self):
        self.set_state_immediately(UxFlow.State.CONTINUE_READY)
