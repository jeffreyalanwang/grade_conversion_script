from typing import Any, Callable, Final, NamedTuple

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_output.auto_canvas_rubric import \
    handler \
        as auto_canvas_rubric
from grade_conversion_script.gui.flow_components.select_output.canvas_enhanced_rubric import \
    handler \
        as canvas_enhanced_rubric
from grade_conversion_script.gui.flow_components.select_output.canvas_gradebook import \
    handler \
        as canvas_gradebook
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputConstructorElement, OutputPanelInfo, PartialOutputConstructor
from grade_conversion_script.gui.state_components import UxFlow as UxFlow

# TODO make sure no output constructor modifies AliasRecord

HANDLERS = (
    canvas_enhanced_rubric,
    canvas_gradebook,
    auto_canvas_rubric,
)

def get_child_info(name_id: str) -> OutputPanelInfo[Any]:
    for handler_info in HANDLERS:
        if handler_info.name_id == name_id:
            return handler_info
    raise ValueError(f'No handler found for name_id: {name_id}')

class OutputFormatData(NamedTuple):
    handler: PartialOutputConstructor[Any]
    make_filename: Callable[[], str]
    media_type: str

class OutputFormatSelectStep(
    UxFlow.FlowStepDataElement[OutputFormatData]
):
    def __init__(
        self,
        initial_state: UxFlow.State = UxFlow.State.NOT_START_READY,
        *args,
        **kwargs
    ):
        super().__init__(initial_state, *args, **kwargs)

        with self.classes('w-full'):
            with ui.column(align_items='stretch').classes('gap-0 absolute-full'):

                self.format_selector: Final = (
                    ui.radio({
                        # name (unique ID) : text
                        handler_info.name_id: handler_info.title
                        for handler_info in HANDLERS
                    })
                    .props('inline dense')
                    .classes('q-px-md q-py-sm'))

                with ui.tab_panels(keep_alive=False) as option_panels:
                    option_panels = (
                        option_panels
                        .classes(add='fit grow')
                        .props('transition-prev="fade" transition-next="fade"')
                    )

                    self.handler_pages: Final = dict[str, OutputConstructorElement[Any]]()
                    for handler_info in HANDLERS:
                        with ui.tab_panel(handler_info.name_id) as p:
                            _ = p.classes('py-0')
                            page = handler_info.options_page()
                            self.handler_pages[handler_info.name_id] = page


        # Connect radio buttons to tab panels
        _ = self.format_selector.on_value_change(
            lambda e: option_panels.set_value(e.value)
        )

        # Child generated new handler object
        for name, handler_page in self.handler_pages.items():
            handler_page.on_object_changed.subscribe(
                lambda new_data, page_name=name:
                self.new_child_data_callback(
                    page_name,
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
        child_info = get_child_info(name_id=new_tab_name) if new_tab_name else None
        self.handle_new_data(tab_data, child_info)

    def new_child_data_callback(
        self,
        child_page_name: str,
        child_output: PartialOutputConstructor[Any] | None
    ):
        if child_page_name != self.curr_selected_name:
            return
        child_info = get_child_info(name_id=child_page_name) if child_page_name else None
        self.handle_new_data(child_output, child_info)

    def handle_new_data(self, child_output: PartialOutputConstructor[Any] | None, child_info: OutputPanelInfo[Any] | None):
        if not child_output:
            self.data = None
            return

        assert child_info
        self.data = OutputFormatData(
            handler = child_output,
            make_filename = child_info.make_filename,
            media_type = child_info.media_type,
        )

if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row().style('min-width: 700px'):
        step_element = OutputFormatSelectStep(initial_state=UxFlow.State.START_READY)

    step_element.on_state_changed.subscribe(lambda state: ui.notify(f'New state: {state.name}'))

    ui.run(native=False)
