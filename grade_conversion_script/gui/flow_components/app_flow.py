import tempfile
from pathlib import Path
from typing import override

from nicegui.element import Element

from grade_conversion_script.gui.base_components.split_panes_layout \
    import SplitPanesLayout
from grade_conversion_script.gui.flow_components.execute.execute \
    import ExecuteDepends, ExecuteStep, PartialHandlerConstructors
from grade_conversion_script.gui.flow_components.import_data \
    import ImportDataFlowStep
from grade_conversion_script.gui.flow_components.pane_header \
    import decorate as decorate_generic
from grade_conversion_script.gui.flow_components.result.result_actions import \
    ResultActionsDepends, ResultActionsStep
from grade_conversion_script.gui.flow_components.select_input \
    import InputHandlerSelectStep
from grade_conversion_script.gui.flow_components.select_output \
    import OutputFormatSelectStep
from grade_conversion_script.gui.state_components import UxFlow
from grade_conversion_script.gui.state_components.FlowStepHolder \
    import FlowStepHolder
from grade_conversion_script.util.funcs import all_truthy

TITLES: dict[type[UxFlow.FlowStepElement], str] = {
    ImportDataFlowStep    : 'Import Data',
    InputHandlerSelectStep: 'Input Options',
    OutputFormatSelectStep: 'Output Options',
    ExecuteStep           : 'Process Data',
    ResultActionsStep     : 'Result',
}

def decorate_step(step: UxFlow.FlowStepElement) -> Element:

    header_text = TITLES.get(type(step), None)
    decorated = decorate_generic(step, header_text)

    def set_state_on_parent(state: UxFlow.State):
        visual_state = UxFlow.VisualState.from_flow_state(state)
        UxFlow.VisualState.clear_all_from(decorated)
        visual_state.set_on(decorated)
    set_state_on_parent(step.state)
    step.on_state_changed.subscribe(set_state_on_parent)

    return decorated


def generate_execute_depends(
    tmp_dir: Path,
    input_data: ImportDataFlowStep,
    input_select: InputHandlerSelectStep,
    output_select: OutputFormatSelectStep,
) -> ExecuteDepends | None:
    assert tmp_dir.exists()
    # TODO pandas can read file buffers, switch to a non-named tempfile
    tmpfile = tempfile.NamedTemporaryFile(
        delete_on_close=False,
        dir=tmp_dir,)
    tmpfile.close()

    if not (input_csvs := input_data.data) or not all_truthy(input_csvs):
        return None
    if not (input_handler := input_select.data):
        return None
    if not (output_data := output_select.data):
        return None

    value = ExecuteDepends(
        input_csvs={
            df_entry.name: df_entry.df
            for df_entry in input_csvs },
        handler_constructors=
            PartialHandlerConstructors(
                for_input=input_handler,
                for_output=output_data.handler, ),
        temp_dest_file=
            Path(tmpfile.name), )
    return value

def generate_result_actions_depends(
    output_select: OutputFormatSelectStep,
    execute: ExecuteStep,
) -> ResultActionsDepends | None:
    if not (output_data := output_select.data):
        return None
    if not (execute_data := execute.data):
        return None

    value = ResultActionsDepends(
        file=execute_data,
        filename=output_data.make_filename(),
        media_type=output_data.media_type,)

class GradeConversionAppFlow(FlowStepHolder, SplitPanesLayout):  # pyright: ignore[reportUnsafeMultipleInheritance]
    '''
    Responsible for combining functionalities of
    FlowStepHolder (manages state of children) and
    SplitPanesLayout (manages visual positioning).
    '''
    def __init__(self, *args, **kwargs):
        self._tmp_dir_obj = TemporaryDirectory()
        self.tmp_dir = Path(self._tmp_dir_obj.name)

        steps: tuple[UxFlow.FlowStepElement, ...] = (
            ImportDataFlowStep(
                multi_file=True,),
            InputHandlerSelectStep(),
            OutputFormatSelectStep(),
            ExecuteStep(
                add_step =
                    lambda sibling:
                    self.add_child_sibling(
                        new_sibling=sibling,
                        for_child=self.get_step(ExecuteStep),
                    ),),
            ResultActionsStep(),
        )

        top_level_elements = [
            decorate_step(step)
            for step in steps]
        super().__init__(
            *args,
            children=top_level_elements,
            steps=steps,
            **kwargs,)

        self.bind_element_inputs(steps)

    def __del__(self):
        self._tmp_dir_obj.cleanup()

    def bind_element_inputs(self, steps: tuple[UxFlow.FlowStepElement, ...]):

        for step in steps:
            if not isinstance(step, UxFlow.FlowStepInputElement):
                continue
            match step:
                case ExecuteStep():
                    input_data = self.get_step(ImportDataFlowStep)
                    input_select = self.get_step(InputHandlerSelectStep)
                    output_select = self.get_step(OutputFormatSelectStep)

                    execute = step
                    def update_execute_inputs():
                        new_inputs = generate_execute_depends(
                            self.tmp_dir, input_data, input_select, output_select, )
                        execute.inputs = new_inputs
                    input_data.on_data_changed.subscribe(update_execute_inputs)
                    input_select.on_data_changed.subscribe(update_execute_inputs)
                    output_select.on_data_changed.subscribe(update_execute_inputs)
                case ResultActionsStep():
                    output_select = self.get_step(OutputFormatSelectStep)
                    execute = self.get_step(ExecuteStep)

                    result_actions = step
                    def update_result_inputs():
                        new_inputs = generate_result_actions_depends(
                            output_select, execute,)
                        result_actions.inputs = new_inputs
                    execute.on_data_changed.subscribe(update_result_inputs)
                case _:
                    raise ValueError(f"Unrecognized flow step takes input data: {step}")

    @override
    def distribute_items(self, count: int) -> tuple[int, ...]:
        # We would specifically like
        # InputDataFlowStep, InputHandlerSelectStep, and OutputFormatSelectStep
        # to be in the first column.
        if count >= 5:
            return (3, count - 3)
        else:
            return super().distribute_items(count)

    @override
    def add_flow_step(self, element: UxFlow.FlowStepElement, position: int) -> None:
        '''
        Use this method to add a flow step;
        performs placement in UI layout.

        Also modifies FlowStepHolder's methods which rely on self.add_flow_step
        (e.g. `add_child_sibling`).
        '''
        print(f'2.3.1 {element.state}')
        decorated_element = decorate_step(element)
        print(f'2.3.2 {element.state}')
        super().add_child(decorated_element, position)
        print(f'2.3.3 {element.state}')
        super().add_flow_step(element, position)
        print(f'2.3.4 {element.state}')

if __name__ in {"__main__", "__mp_main__"}:
    from nicegui import ui
    from tempfile import TemporaryDirectory

    app_flow = GradeConversionAppFlow()
    ui.run(native=False, reload=False)
