from typing import Final, override

from nicegui import ui

from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputConstructorElement, OutputPanelInfo, \
    PartialOutputConstructor, file_safe_timestamp
from grade_conversion_script.output import AcrOutputFormat


class AutoCanvasRubricFormatOptions(OutputConstructorElement[AcrOutputFormat]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with self:
            with ui.row(align_items='center').classes('justify-center'):
                _ = ui.label('No options').classes('italic')

        # Output cannot possibly change, create dummy now
        self.handle_options_changed()

    @override
    def generate_object(self) -> PartialOutputConstructor[AcrOutputFormat]:
        return lambda dependencies: AcrOutputFormat(
            student_aliases=dependencies.student_aliases
        )

handler: Final = OutputPanelInfo(
    title = 'Auto Canvas Rubric (browser extension)',
    options_page = AutoCanvasRubricFormatOptions,
    make_filename=lambda: f'acr_import_{file_safe_timestamp()}.csv',
    media_type='text/csv',
)

if __name__ in {"__main__", "__mp_main__"}:
    from grade_conversion_script.util import AliasRecord
    from grade_conversion_script.gui.flow_components.select_output.common \
        import OutputDependencies
    from grade_conversion_script.util.tui import interactive_alias_match, interactive_rubric_criteria_match
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row():
        element = AutoCanvasRubricFormatOptions()

    # def report_new_handler(new_handler):
    #     ui.notify(f'New handler generated: {new_handler}')
    #     logging.info(f'New handler generated: {new_handler.__dict__ if new_handler else None}')
    # element.on_object_changed.subscribe(report_new_handler)

    logging.info(str(element.last_generated))
    logging.info(str(
        element.last_generated(OutputDependencies(AliasRecord(), interactive_alias_match, interactive_rubric_criteria_match)))
        if element.last_generated else None
    )

    ui.run(native=False)
