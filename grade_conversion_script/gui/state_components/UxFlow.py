import logging
from contextlib import suppress
from enum import Enum, IntEnum
from string import Template
from textwrap import indent
from typing import Final

from nicegui import ElementFilter, ui, Event
from nicegui.element import Element

from grade_conversion_script.gui.util import DebouncedRunner

logger = logging.getLogger(__name__)

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

    @property
    def allows_start(self) -> bool:
        assert self < State.CONTINUE_REQUIRED, "Ambiguous case"
        return self >= State.START_READY

    @property
    def allows_continue(self) -> bool:
        return self >= State.CONTINUE_READY

    @property
    def requires_continue(self) -> bool:
        return self == State.CONTINUE_REQUIRED

    def with_start_allowed(self, allowed: bool):
        if allowed:
            return max(self, State.START_READY)
        else:
            return State.NOT_START_READY

    def with_continue_allowed(self, allowed: bool):
        if allowed:
            return max(self, State.CONTINUE_READY)
        else:
            return min(self, State.START_READY)

    def with_continue_required(self, required: bool):
        if required:
            return State.CONTINUE_REQUIRED
        else:
            return min(self, State.CONTINUE_READY)

class VisualState(Enum):
    NOT_READY = 'flow-step-not-ready'
    AVAILABLE = 'flow-step-ready'
    COMPLETE_INDICATED = 'flow-step-complete'

    ui.add_css(
        shared=True,
        content=Template(
            '''
            @layer components {
                .$not_ready, .$complete_indicated {
                    opacity: 0.5;
                    transition: opacity 0.5s ease-in-out;
                    cursor: not-allowed;                  
                    pointer-events: none;
                }
                .$available {}
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

    def set_on_container(self, container: Element):
        ''' Use if a container needs visual decoration to match its child. '''
        _ = container.classes(add=self.value)

    def remove_from_container(self, container: Element):
        ''' See `set_on_container`. '''
        _ = container.classes(remove=self.value)

    def set_on(self, element: Element):
        _ = element.classes(add=self.value)

    def clear_from(self, element: ui.element):
        if self.value not in element.classes:
            raise PropertyNotSetException(
                f'Error removing {self} from element of type {type(element)}.'
                f' Element classes: {list(element.classes)}')
        _ = element.classes(remove=self.value)

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
        self._elements_on_enter: Final = list[set[Element]]()

        # Set HTML attributes
        _ = self.classes(add='flow-step')

        # Make events available
        self.on_state_changed: Final = Event[State]()

        # Initialize internal state
        self._state: State | None = None
        self._visual_state: VisualState | None = None
        self._complete: bool | None = None

        # Allow setting of state in a debounced manner
        self._state_debouncer = DebouncedRunner(.5)

        # Set actual state, immediately triggering internal callbacks
        self.set_state_immediately(initial_state)

    def __enter__(self):
        self_obj = super().__enter__()
        self._elements_on_enter.append(set(
            ElementFilter(kind=Element).within(instance=self)
        ))
        return self_obj

    def __exit__(self, *_):
        elements_on_enter = self._elements_on_enter.pop()
        elements_on_exit = set(
            ElementFilter(kind=Element).within(instance=self)
        )
        super().__exit__(*_)

        # apply visual state to any elements that may have been added
        if elements_on_enter != elements_on_exit:
            self.visual_state.set_on(self)

    @property
    def state(self) -> State:
        assert self._state is not None
        return self._state

    def set_state_immediately(self, value: State):
        self.log_changing_state(value)
        self._state_debouncer.cancel_all()
        self._state = value
        self.on_state_changed.emit(value)
        self.visual_state = VisualState.from_flow_state(value)

    def set_state_debounced(self, value: State):
        '''
        Debounce period cancels any recursion,
        and prevents update if user makes
        several consecutive changes in a row.
        '''
        if value == self._state:
            return
        self._state_debouncer(lambda: self.set_state_immediately(value))

    def log_changing_state(self, value: State):
        ''' Call *before* state is modified. '''
        logger.info(
            f'Flow step {str(self).splitlines()[0]} changing ({self._state} to {value})'
            + ('\n' + indent(self.parent.__str__(), '+ ')) if self.parent else '')

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
    def parent(self):
        ancestor_slot = self.parent_slot
        while ancestor_slot is not None:
            ancestor_element = ancestor_slot.parent
            if hasattr(ancestor_element, 'steps') and self in ancestor_element.steps:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
                return ancestor_element  # pyright: ignore[reportReturnType]
            ancestor_slot = ancestor_element.parent_slot
        return None

class FlowStepInputElement[T](FlowStepElement):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inputs: T | None = None
        self.on_inputs_changed: Final = Event[T | None]()

    @property
    def inputs(self) -> T | None:
        return self._inputs
    @inputs.setter
    def inputs(self, values: T | None):
        if values == self._inputs:
            return
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
            self.set_state_debounced(
                self.state.with_continue_allowed(False),)
        else: # we have generated a value
            self.set_state_debounced(
                self.state.with_continue_allowed(True),)

    @property
    def on_data_changed(self) -> Event[T | None ]:
        return self._on_data_changed