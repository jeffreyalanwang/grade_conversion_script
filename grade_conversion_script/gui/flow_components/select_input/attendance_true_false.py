import numbers as num
from typing import Final, override

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_input.common \
    import InputPanelInfo, InputConstructorElement, InputDependencies
from grade_conversion_script.gui.state_components.constructor_element import \
    NotReadyException
from grade_conversion_script.input import AttendanceTrueFalse


class AttendanceTrueFalseHandlerOptions(InputConstructorElement[AttendanceTrueFalse]):

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
            return AttendanceTrueFalse(
                pts_per_day=pts_per_day,
                student_aliases=dependencies.student_aliases,
            )
        return generate_handler

handler: Final = InputPanelInfo(
    title = 'Attendance (true/false)',
    options_page = AttendanceTrueFalseHandlerOptions
)

if __name__ in {"__main__", "__mp_main__"}:
    from grade_conversion_script.util import AliasRecord

    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row():
        step_element = AttendanceTrueFalseHandlerOptions()

    def report_new_state(new_callable):
        generated = new_callable(InputDependencies(AliasRecord())) if new_callable else None
        ui.notify(f'New constructor generates: {generated}')
        logging.info(f'New constructor generates: {generated.__dict__ if generated else None}')
    step_element.on_object_changed.subscribe(report_new_state)

    ui.run(native=False)
