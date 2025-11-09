from typing import Final, override, cast

import pandas as pd
from nicegui import ui

from grade_conversion_script.gui.flow_components.import_data.single_file import \
    ImportDataSingleFile
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputConstructorElement, OutputConstructorInfo, \
    PartialOutputConstructor
from grade_conversion_script.gui.state_components.constructor_element import \
    NotReadyException
from grade_conversion_script.output import CanvasEnhancedRubricOutputFormat


class CanvasEnhancedRubricFormatOptions(OutputConstructorElement[CanvasEnhancedRubricOutputFormat]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gradebook_csv: pd.DataFrame | None = None

        with self:
            with ui.row():
                self.import_data_element: Final = (
                    ImportDataSingleFile(
                        uploader_vertical_align='center'
                    )
                    .classes('grow')
                )
                with ui.column(align_items='stretch'):

                    self.replace_existing_element: Final = (
                        ui.checkbox(
                            text='Replace existing scores',
                            value=False
                        )
                    )

                    self.warn_existing_element: Final = (
                        ui.checkbox(
                            text='Warn which students have an existing grade',
                            value=False
                        )
                    )

        _ = self.replace_existing_element.on_value_change(
            lambda e: self.handle_options_changed()
        )

        _ = self.warn_existing_element.on_value_change(
            lambda e: self.handle_options_changed()
        )

        self.import_data_element.on_import_data_changed.subscribe(
            lambda data: self.handle_csv_change(data.df if data else None)
        )

    def handle_csv_change(self, csv: pd.DataFrame | None):
        self.gradebook_csv = csv
        self.handle_options_changed()

    @override
    def generate_object(self) -> PartialOutputConstructor[CanvasEnhancedRubricOutputFormat]:
        rubric_csv = self.gradebook_csv
        if rubric_csv is None:
            raise NotReadyException
        return lambda dependencies: CanvasEnhancedRubricOutputFormat(
            rubric_csv = rubric_csv,
            student_aliases = dependencies.student_aliases,
            unrecognized_name_match = dependencies.name_matcher,
            rubric_criteria_match = dependencies.rubric_criteria_matcher,
            replace_existing = cast(bool, self.replace_existing_element.value),
            warn_existing = cast(bool, self.warn_existing_element.value),
        )

handler: Final = OutputConstructorInfo(
    title = 'Canvas Enhanced Rubric',
    options_page = CanvasEnhancedRubricFormatOptions
)

if __name__ in {"__main__", "__mp_main__"}:
    from grade_conversion_script.util import AliasRecord
    from grade_conversion_script.gui.flow_components.select_output.common \
        import OutputDependencies
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row():
        element = CanvasEnhancedRubricFormatOptions()

    def report_new_constructor(new_constructor):
        obj = new_constructor(OutputDependencies(AliasRecord()))
        ui.notify(f'New constructor generated: {new_constructor}')
        logging.info(f'Generates object: {obj.__dict__ if obj else None}')
    element.on_object_changed.subscribe(report_new_constructor)

    ui.run(native=False)
