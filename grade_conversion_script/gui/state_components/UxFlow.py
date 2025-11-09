from contextlib import suppress
from enum import Enum, IntEnum
from itertools import chain
from string import Template
from typing import Final

from nicegui import ElementFilter, ui, Event
from nicegui.element import Element
from nicegui.elements.mixins.disableable_element import DisableableElement

from grade_conversion_script.util.funcs import DebouncedRunner

NO_VISUAL_DISABLE_CLASS = 'visual_state_no_disable'
'''
Set this HTML class to indicate that an element
should not be disabled with the rest of a
UxFlowStep element.
'''

class PropertyNotSetException(Exception):
    pass

class State(IntEnum):
    NOT_START_READY = 0
    START_READY = 1
    CONTINUE_READY = 2
    CONTINUE_REQUIRED = 3

class VisualState(Enum):
    NOT_READY = 'flow-step-not-ready'
    AVAILABLE = 'flow-step-ready'
    COMPLETE_INDICATED = 'flow-step-complete'

    ui.add_css(
        shared=True,
        content=Template(
            '''
            @layer components {
                .$not_ready {
                    opacity: 0.5;
                    transition: opacity 0.5s ease-in-out;
                }
                .$available {}
                .$complete_indicated {
                    opacity: 0.5;
                    transition: opacity 0.5s ease-in-out;
                }
            }
            ''').substitute(
                not_ready=NOT_READY,
                available=AVAILABLE,
                complete_indicated=COMPLETE_INDICATED
            )
    )

    @property
    def disables_elements(self) -> bool:
        match self:
            case self.NOT_READY:
                return True
            case self.AVAILABLE:
                return False
            case self.COMPLETE_INDICATED:
                return True

    @classmethod
    def disabled_sentinel_class_for(cls, element: ui.element) -> str:
        '''
        Allows the finding of disabled elements
        disabled by the VisualState of a specific element.
        '''
        return f'disabled-by-ux-flow-step-{element.id}'

    def set_on(self, element: ui.element):
        _ = element.classes(add=self.value)
        if self.disables_elements:
            to_disable = chain(
                (element,) if isinstance(element, DisableableElement) else (),
                ElementFilter(
                    kind=DisableableElement,
                    local_scope=True
                )
                .within(instance=element),
            )
            to_disable = filter(
                lambda e: NO_VISUAL_DISABLE_CLASS not in e.classes,
                to_disable
            )
            disable_sentinel = self.disabled_sentinel_class_for(element)
            for element in to_disable:
                _ = element.classes(add=disable_sentinel)
                element.disable()

    def clear_from(self, element: ui.element):
        if self.value not in element.classes:
            raise PropertyNotSetException()
        _ = element.classes(remove=self.value)
        if self.disables_elements:
            to_enable = chain(
                (element,) if isinstance(element, DisableableElement) else (),
                ElementFilter(
                    kind=DisableableElement,
                    local_scope=True
                ).within(instance=element),
            )
            disable_sentinel = self.disabled_sentinel_class_for(element)
            to_enable = filter(
                lambda e: disable_sentinel in e.classes,
                to_enable
            )
            for element in to_enable:
                _ = element.classes(remove=disable_sentinel)
                element.enable()

    @classmethod
    def clear_all_from(cls, element: ui.element):
        with suppress(PropertyNotSetException):
            for enum_member in cls:
                enum_member.clear_from(element)

    @classmethod
    def from_flow_state(cls, state: State):
        match state:
            case State.NOT_START_READY:
                return cls.NOT_READY
            case State.START_READY:
                return cls.AVAILABLE
            case State.CONTINUE_READY:
                return cls.AVAILABLE
            case State.CONTINUE_REQUIRED:
                return cls.COMPLETE_INDICATED

class FlowStepElement(Element):
    def __init__(self, initial_state: State = State.NOT_START_READY, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set HTML attributes
        _ = self.classes(add='flow-step')

        # Make events available
        self.on_state_changed: Final = Event[State]()
        self.on_complete_changed: Final = Event[bool]()

        # Initialize internal state
        self._state: State | None = None
        self._visual_state: VisualState | None = None
        self._complete: bool | None = None

        # Allow setting of state in a debounced manner
        self._state_debouncer = DebouncedRunner(2)

        # Set actual state, immediately triggering internal callbacks
        self.set_state_immediately(initial_state)

    def __exit__(self, *_):
        # apply visual state to any elements that may have been added
        super().__exit__(*_)
        self.visual_state.set_on(self)

    @property
    def state(self) -> State:
        assert self._state is not None
        return self._state
    @state.setter
    def state(self, value: State):
        if value == self._state:
            return
        self._state_debouncer(lambda: self.set_state_immediately(value))
    def set_state_immediately(self, value: State):
        self._state = value
        self.on_state_changed.emit(value)
        self.visual_state = VisualState.from_flow_state(value)
        self.complete = self.state >= State.CONTINUE_READY

    @property
    def visual_state(self) -> VisualState:
        assert self._visual_state is not None
        return self._visual_state
    @visual_state.setter
    def visual_state(self, value: VisualState):
        if value == self._visual_state:
            return
        if self._visual_state is not None:
            self._visual_state.clear_from(self)
        self._visual_state = value
        value.set_on(self)

    @property
    def ready(self) -> bool:
        ''' Whether the user is ready to begin to this step. '''
        return self.state >= State.START_READY and not self.complete

    @property
    def complete(self) -> bool:
        ''' Whether the user is done with this step. '''
        assert self._complete is not None
        return self._complete
    @complete.setter
    def complete(self, value: bool):
        if value == self._complete:
            return
        self._complete = value
        self.on_complete_changed.emit(value)

class FlowStepInputElement[T](FlowStepElement):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inputs: T | None = None
        self.on_inputs_changed: Final = Event[T]()

    @property
    def inputs(self) -> T:
        assert self._inputs is not None
        return self._inputs
    @inputs.setter
    def inputs(self, values: T):
        self._inputs = values
        self.on_inputs_changed.emit(values)

# TODO import_data should be instance of this
class FlowStepDataElement[T](FlowStepElement):
    ''' An element which generates data. '''

    def __init__(
        self,
        initial_state: State = State.NOT_START_READY,
        *args,
        **kwargs,
    ):
        super().__init__(*args, initial_state=initial_state, **kwargs)
        self._data: T | None = None
        self._on_data_changed: Final = Event[T | None]()

    @property
    def data(self) -> T | None:
        return self._data
    @data.setter
    def data(self, value: T | None):
        self._data = value
        self._on_data_changed.emit(value)

        if value is None:
            self.state = min(self.state, State.START_READY)
        else: # we have generated a value
            self.state = max(self.state, State.CONTINUE_READY)

    @property
    def on_data_changed(self) -> Event[T | None ]:
        return self._on_data_changed