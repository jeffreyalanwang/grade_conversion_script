from collections.abc import Collection

from nicegui import ui

from grade_conversion_script.gui.base_components.dual_list_match \
    import DualListMatch
from grade_conversion_script.gui.flow_components.pane_header import \
    ClientSideHeaderElement
from grade_conversion_script.gui.state_components import UxFlow


class RubricCriteriaMatchElement(  # pyright: ignore[reportUnsafeMultipleInheritance]
    UxFlow.FlowStepDataElement[
        dict[str, str]
    ],
    ClientSideHeaderElement,
):
    def __init__(
        self,
        given_labels: Collection[str],
        dest_labels: Collection[str],
        *args,
        **kwargs,
    ):
        ''' `given_labels` are matched injectively to `dest_labels`. '''
        super().__init__(
            *args,
            header_text='Match rubric criteria (cross-file)',
            initial_state=UxFlow.State.START_READY,
            **kwargs, )
        _ = self.content.classes('q-px-md')

        with self.header_bar:
            _ = ui.space()
            done_button = (
                ui.button(
                    text = 'Done',
                    color = 'accent',
                )
                .props('outline icon-right="check"'))
        with self:
            _ = (
                self.content # see parent class
                .classes('overflow-y-auto overflow-x-hidden q-py-sm'))
            content = DualListMatch(
                left = sorted(given_labels),
                right = sorted(dest_labels),
                discardable = False,)

        done_button.disable()

        content.on_any_changed.subscribe(
            lambda left_remaining, right_remaining, matches:
            self.handle_content_value_changed(
                bool(left_remaining),
                done_button
            ),)
        _ = done_button.on_click(
            lambda: self.handle_done_button(content),)

    def handle_content_value_changed(
        self,
        given_labels_remaining: bool,
        done_button: ui.button,
    ):
        done_button.set_enabled(not given_labels_remaining)

    def handle_done_button(
        self,
        content: DualListMatch,
    ):
        self.set_state_immediately(UxFlow.State.CONTINUE_REQUIRED)
        self.data = dict(content.value)
