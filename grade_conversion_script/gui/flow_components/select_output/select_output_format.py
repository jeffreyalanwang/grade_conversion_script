from typing import Any, Final

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_output.auto_canvas_rubric import \
    handler \
        as auto_canvas_rubric
from grade_conversion_script.gui.flow_components.select_output.canvas_gradebook import \
    handler \
        as canvas_gradebook
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputConstructorElement, PartialOutputConstructor
# TODO make sure no output constructor modifies AliasRecord
from grade_conversion_script.gui.state_components import UxFlow as UxFlow

# from grade_conversion_script.gui.flow_components.select_output.canvas_enhanced_rubric import handler \
#   as canvas_enhanced_rubric

handlers = (
    # canvas_enhanced_rubric,
    canvas_gradebook,
    auto_canvas_rubric,
)

class OutputFormatSelector(
    UxFlow.FlowStepDataElement[
        PartialOutputConstructor[Any]
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
            with ui.column(align_items='stretch'):

                self.format_selector: Final = ui.radio({
                    # name (unique ID) : text
                    handler_info.name_id: handler_info.title
                    for handler_info in handlers
                }).props('inline')

                with ui.tab_panels(keep_alive=False) as option_panels:
                    option_panels = option_panels.classes(add='fit grow')

                    self.handler_pages: Final = dict[str, OutputConstructorElement[Any]]()
                    for handler_info in handlers:
                        with ui.tab_panel(handler_info.name_id):
                            page = handler_info.options_page()
                            self.handler_pages[handler_info.name_id] = page


        # Connect radio buttons to tab panels
        _ = self.format_selector.on_value_change(
            lambda e: option_panels.set_value(e.value)
        )

        # Child generated new handler object
        for name, handler_page in self.handler_pages.items():
            handler_page.on_object_changed.subscribe(
                lambda new_data:
                self.new_child_data_callback(
                    name,
                    new_data
                )
            )

        # Tab switch -> trigger child page to re-calculate its handler object
        _ = self.format_selector.on_value_change(
            lambda e: self.tab_change_callback(e.value)
        )

    @property
    def curr_selected_name(self) -> str | None:
        ''' handler_info.name_id '''
        return self.format_selector.value

    def tab_change_callback(
        self,
        new_tab_name: str | None
    ):
        tab_data = self.handler_pages[new_tab_name].last_generated if new_tab_name else None
        self.handle_new_data(tab_data)

    def new_child_data_callback(
        self,
        child_page_name: str,
        child_output: PartialOutputConstructor[Any] | None
    ):
        if child_page_name != self.curr_selected_name:
            return
        self.handle_new_data(child_output)

    def handle_new_data(self, child_output: PartialOutputConstructor[Any] | None):
        self.data = child_output

if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row().style('min-width: 700px'):
        step_element = OutputFormatSelector(initial_state=UxFlow.State.START_READY)

    step_element.on_state_changed.subscribe(lambda state: ui.notify(f'New state: {state.name}'))

    ui.run(native=False)
