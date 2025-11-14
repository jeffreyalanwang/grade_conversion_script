import numbers as num
from typing import Final, override

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_input.common \
    import InputPanelInfo, InputConstructorElement, InputDependencies
from grade_conversion_script.gui.state_components.constructor_element import \
    NotReadyException
from grade_conversion_script.input import AttendancePollEv


class AttendancePollEvHandlerOptions(InputConstructorElement[AttendancePollEv]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with self:
            with ui.row(align_items='start'):
                self.pts_per_day: Final = (
                    ui.number(
                        label='Points per day',
                        placeholder='0.0',
                        min=0,
                        on_change=self.handle_options_changed,
                    )
                )

    @override
    def generate_object(self):
        assert isinstance(self.pts_per_day.value, num.Real | None)
        if self.pts_per_day.value is None:  # pyright: ignore[reportUnnecessaryComparison] sic. nicegui
            raise NotReadyException

        pts_per_day = self.pts_per_day.value
        def generate_handler(dependencies: InputDependencies):
            return AttendancePollEv(
                pts_per_day=pts_per_day,
                student_aliases=dependencies.student_aliases,
            )
        return generate_handler


handler: Final = InputPanelInfo(
    title = 'Attendance (PollEverywhere export CSV)',
    options_page = AttendancePollEvHandlerOptions,
)
