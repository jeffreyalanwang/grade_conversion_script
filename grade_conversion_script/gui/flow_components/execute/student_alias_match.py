from collections.abc import Collection, Iterable
from typing import Final

from nicegui import ui

from grade_conversion_script.gui.base_components.dual_list_match \
    import DualListMatch
from grade_conversion_script.gui.state_components import UxFlow


class StudentAliasMatchElement(
    UxFlow.FlowStepDataElement[
        dict[str, str]
    ]
):
    def __init__(
        self,
        user: Collection[str],
        dest: Collection[str],
        *args,
        **kwargs,
    ):
        super().__init__(*args, initial_state=UxFlow.State.START_READY, **kwargs)
        self.flip: Final[bool] = len(user) > len(dest)

        with self:
            with ui.card_section():
                _ = ui.label('Match students (cross-file)')
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
                left = sorted(user if not self.flip else dest),
                right = sorted(dest if not self.flip else user),
                discardable = True,
            )

        done_button.disable()

        content.on_value_changed.subscribe(
            lambda value:
            self.handle_content_value_changed(value, done_button),
        )
        _ = done_button.on_click(
            lambda: self.handle_done_button(content),
        )

    def handle_content_value_changed(
        self,
        value: Collection[tuple[str, str]],
        done_button: ui.button,
    ):
        done_button.set_enabled(len(value) > 0)

    def handle_done_button(
        self,
        content: DualListMatch,
    ):
        self.data = self._pairs_to_dict(content.value, self.flip)
        self.state = UxFlow.State.CONTINUE_REQUIRED

    def _pairs_to_dict[T1, T2](
        self,
        pairs: Collection[tuple[T1, T2]],
        flip: bool,
    ):
        new_pairs = Iterable[tuple[T1, T2]]
        if flip:
            new_pairs = ((b, a) for (a, b) in pairs)
            d = dict(new_pairs)
        else:
            new_pairs = pairs
            d = dict(new_pairs)
        return d
