from contextlib import contextmanager
from enum import IntEnum
from typing import Final, overload

from nicegui import ui
from nicegui.element import Element
from nicegui.elements.spinner import SpinnerTypes

from grade_conversion_script.util.custom_types import NoChange, NoChangeFlag


class QInnerLoading(Element):
    def __init__(
        self,
        loading_msg: str | None = None,
        spinner_type: SpinnerTypes | None = 'default',
        *args,
         spinner_size: str = '1em',
        spinner_color: str | None = 'primary',
        tag: str = 'q-inner-loading',
    **kwargs) -> None:
        super().__init__(tag=tag, *args, **kwargs)

        self.spinner = None
        self.label = None
        with self:
            self.spinner = ui.spinner(spinner_type, size=spinner_size, color=spinner_color)
            if loading_msg:
                self.label = ui.label(loading_msg)

        self.visible = True

    def _handle_visibility_change(self, visible: str) -> None:
        # `visible` param's type: sic. parent class implementation
        if visible:
            self.props(add='showing')
        else:
            self.props(remove='showing')

    @contextmanager
    def show(self, msg: str | None | NoChangeFlag = NoChange):
        no_modify_label = any((
            msg is NoChange,
            None == msg == self.label,
            self.label and (msg == self.label.text),
        ))

        if not no_modify_label:
            old_label = self.label.text if self.label else None
            if self.label:
                self.label.delete()
                self.label = None
            if msg:
                assert msg is not NoChange
                with self:
                    self.label = ui.label(msg)

        self.visible = True
        yield self
        self.visible = False

        if not no_modify_label:
            if self.label:
                self.label.delete()
                self.label = None
            if old_label: # pyright: ignore[reportPossiblyUnboundVariable]
                with self:
                    self.label = ui.label(old_label)

_ = QInnerLoading.default_style(add='backdrop-filter: blur(5px);')
_ = QInnerLoading.default_style(add='padding: 1em;')

class InnerLoadingContainer(Element):
    '''
    A container element that displays a loading indicator,
    plus content before and after showing the indicator.

    Note that `InnerLoading.before_slot` remains
    visible behind `InnerLoading.after_slot`.

    Clear `InnerLoading.loading_element` and then
    fill it with a new `ui.spinner` and `ui.label`
    to modify the loading indicator.
    '''

    def __init__(
        self,
        loading_msg: str | None = 'Loading...',
        spinner_type: SpinnerTypes | None = 'default',
        *args,
        spinner_size: str = '4em',
        spinner_color: str | None = 'primary',
         **kwargs
    ) -> None:
        super().__init__()

        with self:
            self.before: Final = ui.element().classes(add='before-slot-holder')
            ''' Holds element(s) to be displayed before the loading indicator. '''

            self.after: Final = ui.element().classes(add='after-slot-holder')
            ''' Holds element(s) to be displayed after the loading indicator. '''

            # must appear last (see Quasar documentation for QInnerLoading).
            self.loading_overlay: Final = QInnerLoading(loading_msg, spinner_type,
                                                        spinner_size=spinner_size,
                                                        spinner_color=spinner_color)
        _ = self.before.classes('absolute-full q-pa-sm')
        _ = self.after.classes('absolute-full q-pa-sm')

        self._state: InnerLoadingContainer.State
        self.state = self.State.BEFORE

    class State(IntEnum):
        BEFORE = -1
        LOADING = 0
        AFTER = 1
    @property
    def state(self) -> State:
        return self._state
    @state.setter
    def state(self, value: State):
        self._state = value
        match value:
            case self.State.BEFORE:
                self._set_parts_visibility(True, False, False)
            case self.State.LOADING:
                self._set_parts_visibility(loading=True)
            case self.State.AFTER:
                self._set_parts_visibility(False, False, True)

    @overload
    def _set_parts_visibility(self, before: bool, loading: bool, after: bool, /) -> None:
        ...
    @overload
    def _set_parts_visibility(self, *, before: bool | None = None, loading: bool | None = None, after: bool | None = None) -> None:
        ...
    def _set_parts_visibility(self, before: bool | None = None, loading: bool | None = None, after: bool | None = None):
        if before is not None:
            self.before.set_visibility(before)
        if loading is not None:
            self.loading_overlay.set_visibility(loading)
        if after is not None:
            self.after.set_visibility(after)

_ = InnerLoadingContainer.default_style(add='min-width: 100px; min-height: 100px;')
_ = InnerLoadingContainer.default_classes(add='block absolute-full')

if __name__ in {"__main__", "__mp_main__"}:
    ''' Simple demo of InnerLoadingContainer. '''
    from nicegui import ui
    with ui.row():
        il = InnerLoadingContainer()
        with il.before:
            _ = ui.label('before')
        with il.after:
            _ = ui.label('after')

        def increment_state(increment: int = 1):
            new_value = il.state + increment
            if new_value not in InnerLoadingContainer.State:
                return
            il.state = InnerLoadingContainer.State(value=new_value)
        _ = ui.button('state ++', on_click=increment_state)
        _ = ui.button('state --', on_click=lambda: increment_state(-1))

    ui.run(native=False)