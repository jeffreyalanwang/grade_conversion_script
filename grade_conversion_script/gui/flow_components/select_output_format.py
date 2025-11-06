import grade_conversion_script.gui.flow_components.UxFlow as UxFlow

class OutputFormatSelector(UxFlow.FlowStepElement):
    def __init__(
        self,
        initial_state: UxFlow.State = UxFlow.State.NOT_START_READY,
        tag: str = 'select-output-format',
        *args,
        **kwargs
    ):
        super().__init__(initial_state, tag,*args, **kwargs)