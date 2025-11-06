from contextlib import contextmanager
from enum import IntEnum
from html import escape as html_escape
from io import BytesIO
from typing import NamedTuple, Final

import pandas as pd
from nicegui import ui, Event, events, run, html as ui_html
from nicegui.element import Element

from grade_conversion_script.gui.base_components.inner_loading import InnerLoadingContainer
from grade_conversion_script.util.funcs import set_light_dark, wait_for_event, truncate_exception_to_html

import logging
logger = logging.getLogger(__name__)

class DataImportEntry(NamedTuple):
    name: str
    df: pd.DataFrame


class ImportDataSingleFile(Element):

    class Page(IntEnum):
        UPLOAD = InnerLoadingContainer.State.BEFORE
        LOADING = InnerLoadingContainer.State.LOADING
        SHOW_DATA = InnerLoadingContainer.State.AFTER
    @property
    def current_page(self) -> Page:
        return self.Page(self.page_manager.state)
    @current_page.setter
    def current_page(self, enum: Page):
        self.page_manager.state = self.page_manager.State(enum)

    @property
    def import_data(self) -> DataImportEntry | None:
        ''' State prop only--modifications do not affect UI. '''
        return self._import_data
    @import_data.setter
    def import_data(self, value: DataImportEntry | None):
        if (None == value == self.import_data) or (
            value is not None
            and self._import_data is not None
            and value.df.equals(self._import_data.df)
        ):
            return
        self._import_data = value
        self.on_import_data_changed.emit(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # State, event
        self._import_data: DataImportEntry | None = None
        self.on_import_data_changed: Final = Event[DataImportEntry | None]()

        with self:
            with InnerLoadingContainer(spinner_type='bars') as container:
                self.page_manager: Final = container
                self.upload_page: Final = container.before
                self.loading_overlay: Final = container.loading_overlay
                self.show_data_page: Final = container.after

        # Build initial element (uploader)

        with self.upload_page:
            with ui.column().classes('justify-end fit no-wrap') as stack:
                _ = stack.classes('gap-0')

                with ui.row().classes('justify-center w-full no-wrap'):
                    self.uploader_history_msg: Final = (
                        ui.label('History')
                        .classes('italic opacity-75')
                    )
                    self.uploader_history_msg.set_visibility(False)

                with ui.row().classes('justify-center w-full no-wrap'):
                    self.uploader: Final = (
                        ui.upload(
                            multiple=False,
                            on_begin_upload=self.uploading_callback,
                            on_rejected
                                = lambda: ui.notify(
                                    'File not accepted.'
                                    ' Double-check file'
                                    ' type and try again.',
                                    type='negative',
                                    closeable=True,
                                ),
                            label="Import CSV file",
                            auto_upload=True,
                        )
                        .props('accept="text/csv"')
                    )

        # Uploader style
        (
            self.uploader
            .props(add='flat square')
            .classes(add='column reverse')
            .style(add='width: min(100%, 320px);')
            .set_visibility(False)
        )
        set_light_dark(
            self.uploader,
            lambda uploader, tcolor: (
                uploader
                .props(add=f'color="transparent" text-color="{tcolor}"')
                .set_visibility(True)
            ),
            ('black',),
            ('white',)
        )

        # Display uploader
        self.current_page = self.Page.UPLOAD

    @contextmanager
    def show_file_processing_loading(self, filename: str):
        sanitized_filename = html_escape(filename, quote=True)
        with self.loading_overlay.show(msg=None):
            with self.loading_overlay:
                with ui.element().classes('q-mt-md justify-center text-center') as element:
                    temp_label = element
                    _ = ui.label('Processing file:').classes('text-bold')
                    _ = ui.label(sanitized_filename).classes('text-italic')
            yield
            temp_label.delete()
            temp_label = None

    async def uploading_callback(self, e_begin_uploading: events.UiEventArguments):

        with self.loading_overlay.show(msg="Loading file contents..."):
            e_uploaded, = await wait_for_event(self.uploader.on_upload)
            filename = e_uploaded.file.name
        with self.show_file_processing_loading(filename):

            # Get DataFrame
            df_label = filename
            csv_buffer = BytesIO(await e_uploaded.file.read())
            try:
                async def coroutine(csv_buffer: BytesIO):
                    return await run.cpu_bound(pd.read_csv, csv_buffer)
                df = await coroutine(csv_buffer)
            except Exception as exception:
                ui.notify(
                    f'Error reading {df_label}: {truncate_exception_to_html(exception)}', type='negative',
                    html=True,
                    closeable=True,
                    timeout=0,
                )
                logger.log(logging.ERROR, exception)
                logger.log(logging.ERROR, "CSV text follows:")
                logger.log(logging.ERROR, await e_uploaded.file.text())
                self.uploader.reset()
                return
            assert isinstance(df, pd.DataFrame)

            # Set import_data
            self.import_data = DataImportEntry(df_label, df)

            # Show new grid
            self.show_data_page.clear()
            with self.show_data_page.classes(add='q-pa-none', remove='q-pa-sm') as page:
                _ = page.classes('column no-wrap')
                _ = (
                    ui_html.h1(df_label)
                    .classes('ag-theme-params-2 mimic-ag-header')
                    .classes('w-full')
                )
                _ = (
                    ui.aggrid.from_pandas(
                        df,
                        theme='balham',
                        auto_size_columns=False,
                    )
                    .classes('no-border-ag grow w-full')
                )
            self.current_page = self.Page.SHOW_DATA

            # Clarify uploader history screen
            self.uploader_history_msg.set_visibility(True)

_ = ImportDataSingleFile.default_style(add='min-height: 16rem; min-width: 16rem;')
_ = ImportDataSingleFile.default_classes(add='fit')