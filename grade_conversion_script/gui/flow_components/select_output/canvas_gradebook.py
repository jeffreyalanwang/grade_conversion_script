from typing import Final, override, cast

import pandas as pd
from nicegui import ui

from grade_conversion_script.gui.flow_components.import_data.single_file import \
    ImportDataSingleFile
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputConstructorElement, OutputPanelInfo, \
    PartialOutputConstructor, file_safe_timestamp
from grade_conversion_script.gui.state_components.constructor_element import \
    NotReadyException
from grade_conversion_script.output import CanvasGradebookOutputFormat

ReplaceBehavior = CanvasGradebookOutputFormat.ReplaceBehavior


class CanvasGradebookFormatOptions(OutputConstructorElement[CanvasGradebookOutputFormat]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gradebook_csv: pd.DataFrame | None = None
        self.assignment_header: str | None = None

        with self.classes('fit'):
            with ui.row(wrap=False).classes('fit'):
                with ui.column().classes('grow fit'):
                    self.import_data_element: Final = (
                        ImportDataSingleFile(
                            uploader_vertical_align='center'
                        )
                        .classes('grow fit'))
                with ui.column(align_items='stretch').classes('max-h-full overflow-auto'):

                    self.select_assignment_header_element: Final = (
                        ui.select(
                            options=[],
                            label='Assignment',
                            multiple=False,
                            with_input=True, )
                        .props('dense'))
                    self.select_assignment_header_element.disable()

                    self.sum_option_element: Final = (
                        ui.checkbox(
                            text='Sum scores per student',
                            value=True,)
                        .classes('dense'))

                    _ = ui.label('If students have existing grades:')
                    self.if_existing_element: Final = (
                        ui.radio(
                            {
                                ReplaceBehavior.PRESERVE.name: 'Keep them',
                                ReplaceBehavior.REPLACE.name: 'Replace them',
                                ReplaceBehavior.INCREMENT.name: 'Add to them',
                                ReplaceBehavior.ERROR.name: 'Show an error',
                            },
                            value = ReplaceBehavior.PRESERVE.name,)
                        .props('dense'))

                    self.warn_existing_element: Final = (
                        ui.checkbox(
                            text='Warn which students have an existing grade',
                            value=False,)
                        .classes('dense'))

        self.import_data_element.on_import_data_changed.subscribe(
            lambda data: self.handle_csv_change(data.df if data else None)
        )

        _ = self.select_assignment_header_element.on_value_change(
            lambda e: self.handle_assignment_header_selection(e.value)
        )

    def handle_csv_change(self, csv: pd.DataFrame | None):
        if csv is None:
            self.gradebook_csv = None
            self.select_assignment_header_element.set_options( # pyright: ignore[reportUnknownMemberType]
                [],
                value=None
            )
            self.select_assignment_header_element.disable()
            self.handle_options_changed()
            return

        try:
            assignment_header_options = csv.columns.tolist() # TODO replace with component of CanvasGradebook
        except:
            # TODO validation here and above
            raise

        self.select_assignment_header_element.enable()
        self.select_assignment_header_element.set_options( # pyright: ignore[reportUnknownMemberType]
            assignment_header_options,
            value=None
        )
        self.gradebook_csv = csv
        self.assignment_header = None
        self.handle_options_changed()

    def handle_assignment_header_selection(self, value: str | None):
        if not value: # include empty str
            value = None
        self.assignment_header = value
        self.handle_options_changed()

    @override
    def generate_object(self) -> PartialOutputConstructor[CanvasGradebookOutputFormat]:
        gradebook_csv = self.gradebook_csv
        assignment_header = self.assignment_header
        if (
            gradebook_csv is None
            or assignment_header is None
        ):
            raise NotReadyException
        return lambda dependencies: CanvasGradebookOutputFormat(
            gradebook_csv=gradebook_csv,
            assignment_header=assignment_header,
            student_aliases=dependencies.student_aliases,
            unrecognized_name_match=dependencies.name_matcher,
            warn_existing_handler=dependencies.warning_handler,
            sum=self.sum_option_element.value,
            if_existing=ReplaceBehavior[cast(str, self.if_existing_element.value)],
            warn_existing=cast(bool, self.warn_existing_element.value),
        )

handler: Final = OutputPanelInfo(
    title = 'Canvas Gradebook',
    options_page = CanvasGradebookFormatOptions,
    make_filename=lambda: f'gradebook_{file_safe_timestamp()}.csv',
    media_type='text/csv',
)

if __name__ in {"__main__", "__mp_main__"}:
    from grade_conversion_script.util import AliasRecord
    from grade_conversion_script.gui.flow_components.select_output.common \
        import OutputDependencies
    from grade_conversion_script.util.tui \
        import interactive_alias_match, interactive_rubric_criteria_match, default_warning_printer
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row():
        element = CanvasGradebookFormatOptions()

    def report_new_constructor(new_constructor):
        obj = new_constructor(OutputDependencies(AliasRecord(), interactive_alias_match, interactive_rubric_criteria_match, default_warning_printer))
        ui.notify(f'New constructor generated: {new_constructor}')
        logging.info(f'Generates object: {obj.__dict__ if obj else None}')
    element.on_object_changed.subscribe(report_new_constructor)

    ui.run(native=False)
