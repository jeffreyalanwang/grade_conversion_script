from nicegui import Event

from gui.flow_components import UxFlow as UxFlow


class InputHandlerSelector(UxFlow.FlowStepElement):
    def __init__(
        self,
        initial_state: UxFlow.State = UxFlow.State.NOT_START_READY,
        *args,
        **kwargs
    ):
        super().__init__(initial_state, tag,*args, **kwargs)
        self.input_handlers = input_handlers
        self.ready_state_changed = Event[bool]()
