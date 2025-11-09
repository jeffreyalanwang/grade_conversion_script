from collections.abc import Sequence
from types import NoneType
from typing import Callable, NamedTuple, Final, cast

from nicegui import html as ui_html, ui, Event, events
from nicegui.elements.tabs import TabPanel

from grade_conversion_script.gui.base_components.collapse_transition import \
    CollapseTransition
from grade_conversion_script.gui.flow_components.import_data.single_file import \
    DataImportEntry, ImportDataSingleFile
from grade_conversion_script.gui.flow_components.import_data.tab_util import \
    TabOptionButton
from grade_conversion_script.gui.state_components import UxFlow as UxFlow
from grade_conversion_script.util.custom_types import NoChange
from grade_conversion_script.util.funcs import set_light_dark, index_where, \
    tuple_insert, tuple_pop, tuple_replace, unique_readable_html_safe

# Default line-height is slightly higher
# than text, causes misalignment in y-position
_ = ui.add_css(
    shared=True,
    content='''
    .q-btn {
        line-height: unset !important;
    }
''')

def tab_buttons_visibility_updater(
    toggle_view_button: ui.button,
    toggle_view_collapser: CollapseTransition,
    delete_tab_button: ui.button,
    delete_button_collapser: CollapseTransition,
):
    def tab_buttons_update_visibility(
            this_tab_focused: bool,
            this_tab_data_loaded: bool,
            other_tabs_exist: bool
    ):
        if not this_tab_focused:
            toggle_view_collapser.visible = delete_button_collapser.visible = False
        else:
            toggle_view_collapser.visible = this_tab_data_loaded
            delete_button_collapser.visible = other_tabs_exist

        half_round_style_class = (
            (toggle_view_button,
             'rounded-r-none'),
            (delete_tab_button,
             'rounded-l-none'),
        )
        for element, html_class in half_round_style_class:
            if toggle_view_collapser.visible and delete_button_collapser.visible:
                _ = element.classes(add=html_class)
            else:
                _ = element.classes(remove=html_class)

    return tab_buttons_update_visibility

class TabRecord(NamedTuple):
    '''
    Guaranteed order:
    no item comes before its parent element.
    '''
    tab: ui.tab
    tab_panel: ui.tab_panel
    import_data_element: ImportDataSingleFile
    on_change_tab_focused: Callable[[bool], None]

class ImportDataFlowStep(
    UxFlow.FlowStepDataElement[
        Sequence[DataImportEntry | None]
    ]
):

    def __init__(
        self,
        initial_state: UxFlow.State = UxFlow.State.NOT_START_READY,
        multi_file: bool = True,
        *args,
        **kwargs
    ):
        super().__init__(initial_state, *args, **kwargs)

        # Python props (do not exist in any Vue component)
        self._multi_file: bool = multi_file

        # Initialize internal state
        self._import_data: tuple[DataImportEntry | None, ...] = tuple()
        self._current_tab_index: int | None = None

        # Make events available
        self.on_import_data_changed: Final = Event[Sequence[DataImportEntry | None]]()

        # Build element
        with self:
            _ = self.classes('column no-wrap h-full')

            with ui.tab_panels(keep_alive=True) as tab_panels:
                self.tab_panel_view: Final = (
                    tab_panels
                    .classes(add='fit grow')
                )
            with ui.element('q-toolbar') as toolbar:
                _ = (
                    toolbar
                    .classes('q-pa-none')
                    .style(add='min-height: 0')
                    .style(add='border-top: 1px solid rgba(0,0,0,0.12);')
                )
                self.tabs_bar: Final = (
                    ui.tabs(
                        on_change=self._handle_tab_change
                    )

                    .props(add='inline-label no-caps') # view by filename; allow adding delete button
                    .props(add='shrink dense align="left" ') # compact tabs

                    # Bind with tab panels
                    .bind_value(self.tab_panel_view, 'value')
                    .props(add='switch-indicator')  # indicator adjacent to above tab_panel_view
                )
                self.tabs_bar.set_visibility(self.multi_file)
                set_light_dark(
                    self.tabs_bar,
                    lambda tab_selector, bcolor: (
                        tab_selector.props(add=f'active-bg-color="{bcolor}"')
                    ),
                    ('grey-3',),
                    ('grey-7',)
                )

                _ = ui.space()
                self.button_new_tab: Final = (
                    ui.button(
                        icon='add',
                        color=None,
                        on_click=lambda: self.new_tab(),
                    )
                    .props('title="New tab"')
                    .props(add='flat square')
                )

            with ui.dialog() as dialog:
                with ui.card().classes(add='p-8 min-h-24'):
                    _ = ui.label('Are you sure you want to delete this tab?')
                    dialog_filename_msg = ui_html.span()
                    _ = ui.space()
                    with ui.row().classes(add='w-full justify-end'):
                        _ = (
                            ui.button(
                                'Cancel',
                                color='grey',
                                on_click=lambda: dialog.close()
                            )
                            .props(add='outline')
                        )
                        _ = (
                            ui.button(
                                'Delete',
                                color='negative',
                                on_click=lambda: dialog.close()
                            )
                            .on_click(lambda: self.delete_tab())
                        )

                def open_delete_dialog():
                    tab_data = self.import_data[self.current_tab_index]
                    dialog_filename_msg._text = (
                        f"This will cancel importing data"
                        f" from the file:<br/><b>{tab_data.name}</b>"
                        if tab_data else ""
                    )
                    dialog.open()
                self.delete_dialog_open: Final = open_delete_dialog

            # Initialize with first tab
            self.tabs: list[TabRecord] = []
            self.new_tab()


    @property
    def multi_file(self) -> bool:
        return self._multi_file

    @property
    def current_tab_index(self) -> int:
        assert self._current_tab_index is not None
        return self._current_tab_index

    @property
    def import_data(self) -> Sequence[DataImportEntry | None]:
        return self._import_data
    @import_data.setter
    def import_data(self, value: Sequence[DataImportEntry | None]):
        if (
            len(value) == len(self._import_data)
            and all(
                None == data1 == data2
                or (
                    data1 is not None and data2 is not None
                    and data1.df.equals(data2.df)
                )
                for data1, data2 in zip(value, self._import_data)
            )
        ):
            return
        value = tuple(value)
        if not self.multi_file:
            assert len(value) <= 1

        self._import_data = value
        self.on_import_data_changed.emit(value)

        match (len(value) != 0 and None not in value):
            case True:
                state_val = UxFlow.State.CONTINUE_READY
            case False if (self.state >= UxFlow.State.CONTINUE_READY):
                state_val = UxFlow.State.START_READY
            case _:
                state_val = NoChange
        if state_val is not NoChange:
            cast(UxFlow.FlowStepElement, self).state = state_val

    new_tab_label: Final = "Upload"
    tab_name_prefix: Final = "import-tab-"
    def new_tab(self):
        assert self.multi_file or len(self.tabs) == 0

        # Build elements

        with (self.tabs_bar):
            with ui.tab(
                self.tab_name_prefix + unique_readable_html_safe(5),
                label=self.new_tab_label
            ) as tab:
                tab_element = (
                    tab.classes('q-px-sm')
                )

                with ui.element().classes('row') as buttons_holder:
                    _ = buttons_holder.classes(add='items-center q-pl-xs')

                    toggle_view_collapser, toggle_view_button = TabOptionButton(
                        icon='swap_horiz',
                        color='grey',
                    )
                    _ = toggle_view_button.style('position: relative; left: 1px;')
                    _ = toggle_view_button.props('title="Toggle view: upload file / preview data"')

                    delete_button_collapser, delete_tab_button = TabOptionButton(
                        icon='delete',
                        color='negative',  # red
                    )
                    _ = delete_tab_button.props('title="Delete tab and remove file import"')

        with self.tab_panel_view:
            with ui.tab_panel(tab_element).classes(add='fit q-pa-none') as panel:
                tab_panel = panel

                import_data_element = ImportDataSingleFile(
                    internal_flip_button=False,
                    uploader_vertical_align='end',
                ) # TODO allow multi upload somewhere

        # bind state
        tab_buttons_adjust_visibility = tab_buttons_visibility_updater(
            toggle_view_button=toggle_view_button,
            toggle_view_collapser=toggle_view_collapser,
            delete_tab_button=delete_tab_button,
            delete_button_collapser=delete_button_collapser,
        )
        self._listen_single_data_state(
            element=import_data_element,
            index=len(self.tabs),
        )
        import_data_element.on_import_data_changed.subscribe(
            lambda new_data_val:
                tab_buttons_adjust_visibility(
                    this_tab_focused=(
                        self._current_tab_index == index_where(
                            lambda x: x.import_data_element is import_data_element,
                            self.tabs
                        )
                    ),
                    this_tab_data_loaded=(
                        new_data_val is not None
                    ),
                    other_tabs_exist=(
                        len(self.tabs) > 1
                    ),
                )
        )
        _ = toggle_view_button.on_click(
            lambda: import_data_element.tab_view_toggle()
        )
        _ = delete_tab_button.on_click(
            lambda: self.delete_dialog_open()
        )

        # Register elements
        self.tabs.append(TabRecord(
            tab = tab_element,
            tab_panel = tab_panel,
            import_data_element = import_data_element,
            on_change_tab_focused = lambda this_tab_focused:
                tab_buttons_adjust_visibility(
                    this_tab_focused=this_tab_focused,
                    this_tab_data_loaded=(
                        import_data_element.import_data is not None
                    ),
                    other_tabs_exist=(
                        len(self.tabs) > 1
                    ),
                ),
        ))

        # Triggers callbacks in this element
        self.tab_panel_view.value = tab_panel

    def delete_tab(self, index: int | None = None):
        assert self.multi_file and len(self.tabs) > 1

        if index is None:
            index = self.current_tab_index
        tab_record = self.tabs[index]

        switch_to_index = index + (-1 if index > 0 else 1)
        switch_to_tab = self.tabs[switch_to_index]

        self._unregister_single_data_state(tab_record.import_data_element, index)
        for element in reversed(tab_record): # delete children first
            if isinstance(element, ui.element):
                element.delete()
        del self.tabs[index]

        self.tab_panel_view.value = switch_to_tab.tab_panel

    def _handle_tab_change(self, event: events.ValueChangeEventArguments):
        assert self.multi_file or len(self.tabs) == 1
        assert isinstance(event.previous_value, (str, NoneType)), type(event.previous_value)
        assert isinstance(event.value, (str, TabPanel)), type(event.value)

        def extract_tab_name(tab_info: str) -> str:
            tab_info = tab_info.splitlines()[0]
            if (
                tab_info.startswith(self.tab_name_prefix)
                and len(tab_info) == len(self.tab_name_prefix) + 5
            ):
                return tab_info
            else:
                i = tab_info.index(self.tab_name_prefix)
                return tab_info[
                    i
                    :
                    i + len(self.tab_name_prefix) + 5
                ]
        new_selected_name = extract_tab_name(str(event.value))

        old_tab_index, old_tab_record = (
            self._current_tab_index,
            self.tabs[self._current_tab_index]
                if self._current_tab_index is not None # first-time open tab
                    and self._current_tab_index != len(self.tabs) # delete last tab in the list
                else None
        )
        new_tab_index, new_tab_record = next(
            (i, tab_record) for i, tab_record
            in enumerate(self.tabs)
            if tab_record.tab._props['name'] == new_selected_name
        )

        if old_tab_index == new_tab_index:
            return

        self._current_tab_index = new_tab_index
        if old_tab_record:
            old_tab_record.on_change_tab_focused(False)
        new_tab_record.on_change_tab_focused(True)

    def _listen_single_data_state(self, element: ImportDataSingleFile, index: int):
        ''' Element must be present in `self.tabs` at `index`. '''

        # expand parent import_data collection
        append_value = None
        self.import_data = tuple_insert(index, append_value, self.import_data)

        # register callback
        def set_parent_data(data: DataImportEntry | None):
            # find location in parent import_data
            parent_data_loc = index_where(
                lambda tab_record:
                    element is tab_record.import_data_element,
                self.tabs
            )
            self.import_data = tuple_replace(parent_data_loc, data, self.import_data)

            tab = self.tabs[parent_data_loc].tab
            _ = tab.props(remove='title')
            if data:
                tab.label = data.name if len(data.name) < 15 else f'{data.name[:15]}...'
                _ = tab.props(f'title="{data.name}"')
            else:
                tab.label = self.new_tab_label
        element.on_import_data_changed.subscribe(set_parent_data)

    def _unregister_single_data_state(self, element: ImportDataSingleFile, index: int):
        ''' Element must be present in `self.tabs` at `index`. '''

        # shrink parent import_data collection
        _, self.import_data = tuple_pop(index, self.import_data)

        # callback is not unregistered;
        # if somehow called, its call to
        # parent_data_loc will raise error.

_ = ImportDataFlowStep.default_style(add="min-width: 20rem; min-height: 20rem;")

if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.row():
        step_element = ImportDataFlowStep(multi_file=True, initial_state=UxFlow.State.START_READY)

    step_element.on_state_changed.subscribe(lambda state: ui.notify(f'New state: {state.name}'))

    ui.run()
