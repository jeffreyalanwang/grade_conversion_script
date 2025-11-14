from typing import Any, Final

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_input.attendance_poll_ev import \
    handler as attendance_poll_ev
from grade_conversion_script.gui.flow_components.select_input.attendance_true_false import \
    handler as attendance_true_false
from grade_conversion_script.gui.flow_components.select_input.common import \
    InputConstructorElement, PartialInputConstructor
from grade_conversion_script.gui.state_components import UxFlow

HANDLERS = (
    attendance_poll_ev,
    attendance_true_false,
)

class InputHandlerSelectStep(
    UxFlow.FlowStepDataElement[
        PartialInputConstructor[Any]
    ]
):
    def __init__(
        self,
        initial_state: UxFlow.State = UxFlow.State.NOT_START_READY,
        *args,
        **kwargs
    ):
        super().__init__(initial_state, *args, **kwargs)

        with self.classes('w-full'):
            with ui.column(align_items='stretch').classes('gap-0'):

                self.input_handler_selector: Final = ui.radio({
                    # name (unique ID) : text
                    handler_info.name_id: handler_info.title
                    for handler_info in HANDLERS
                }).props('inline')

                with ui.tab_panels(keep_alive=False) as option_panels:
                    _ = (
                        option_panels
                        .classes(add='fit grow')
                        .props('transition-prev="fade" transition-next="fade"')
                    )

                    self.handler_pages: Final = dict[str, InputConstructorElement[Any]]()
                    for input_handler_info in HANDLERS:
                        with ui.tab_panel(input_handler_info.name_id):
                            page = input_handler_info.options_page()
                            self.handler_pages[input_handler_info.name_id] = page

        # Connect radio buttons to tab panels
        _ = self.input_handler_selector.on_value_change(
            lambda e: option_panels.set_value(e.value)
        )

        # Child generated new handler object
        for name, handler_page in self.handler_pages.items():
            handler_page.on_object_changed.subscribe(
                lambda new_data, page_name=name:
                self.new_child_data_callback(
                    page_name, new_data
                ),
            )

        # Tab switch -> trigger child page to re-calculate its handler object
        _ = self.input_handler_selector.on_value_change(
            lambda e: self.tab_change_callback(e.value)
        )

    @property
    def curr_selected_name(self) -> str | None:
        ''' handler_info.name_id '''
        return self.input_handler_selector.value

    def tab_change_callback(
        self,
        new_tab_name: str | None
    ):
        tab_data = self.handler_pages[new_tab_name].last_generated if new_tab_name else None
        self.handle_new_data(tab_data)

    def new_child_data_callback(
        self,
        child_page_name: str,
        child_output: PartialInputConstructor[Any] | None
    ):
        if child_page_name != self.curr_selected_name:
            return
        self.handle_new_data(child_output)

    def handle_new_data(self, child_output: PartialInputConstructor[Any] | None):
        self.data = child_output


if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row().style('min-width: 700px'):
        step_element = InputHandlerSelectStep(initial_state=UxFlow.State.START_READY)

    step_element.on_state_changed.subscribe(lambda state: ui.notify(f'New state: {state.name}'))

    ui.run()
