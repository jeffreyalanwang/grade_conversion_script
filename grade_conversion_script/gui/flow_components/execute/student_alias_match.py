from collections.abc import Collection, Iterable
from typing import Final

from nicegui import ui

from grade_conversion_script.gui.base_components.dual_list_match \
    import DualListMatch
from grade_conversion_script.gui.flow_components.pane_header import \
    ClientSideHeaderElement
from grade_conversion_script.gui.state_components import UxFlow


class StudentAliasMatchElement(  # pyright: ignore[reportUnsafeMultipleInheritance]
    UxFlow.FlowStepDataElement[
        dict[str, str]
    ],
    ClientSideHeaderElement,
):
    def __init__(
        self,
        user: Collection[str],
        dest: Collection[str],
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            header_text='Match student names (cross-file)',
            initial_state=UxFlow.State.START_READY,
            **kwargs,)
        self.flip: Final[bool] = len(user) > len(dest) # show shorter list on left

        _ = self.content.classes('q-pa-md')

        with self.header_bar:
            _ = ui.space()
            done_button = (
                ui.button(
                    text = 'Done',
                    color = 'accent',
                )
                .props('outline icon-right="check"'))
        with self:
            content = DualListMatch(
                left = sorted(user if not self.flip else dest),
                right = sorted(dest if not self.flip else user),
                discardable = True,)

        _ = done_button.on_click(
            lambda: self.handle_done_button(content),)

    def handle_done_button(
        self,
        content: DualListMatch,
    ):
        self.data = self._pairs_to_dict(content.value, self.flip)
        self.set_state_immediately(UxFlow.State.CONTINUE_REQUIRED)

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
