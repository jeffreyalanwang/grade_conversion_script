from collections.abc import Collection

from nicegui import ui

from grade_conversion_script.gui.base_components.dual_list_match \
    import DualListMatch
from grade_conversion_script.gui.state_components import UxFlow


class RubricCriteriaMatchElement(
    UxFlow.FlowStepDataElement[
        dict[str, str]
    ]
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
            initial_state = UxFlow.State.START_READY,
            **kwargs,
        )

        with self:
            with ui.card_section():
                _ = ui.label('Match rubric criteria (cross-file)')
                _ = ui.space()
                done_button = (
                    ui.button(
                        icon = 'check',
                        text = 'Done',
                        color = 'accent',
                    )
                    .props('outline')
                )
                _ = ui.separator()
            content = DualListMatch(
                left = sorted(given_labels),
                right = sorted(dest_labels),
                discardable = False,
            )

        done_button.disable()

        content.on_any_changed.subscribe(
            lambda left_remaining, _, matches:
            self.handle_content_value_changed(
                bool(left_remaining),
                done_button
            ),
        )
        _ = done_button.on_click(
            lambda: self.handle_done_button(content),
        )

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
        self.data = dict(content.value)
        self.state = UxFlow.State.CONTINUE_REQUIRED
