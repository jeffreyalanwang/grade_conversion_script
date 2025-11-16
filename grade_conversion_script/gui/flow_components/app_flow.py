from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
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
    ''' Wraps decorate method to bind decorator element to step's visual state. '''

    header_text = TITLES.get(type(step), None)
    decorated = decorate_generic(step, header_text)

    def set_state_on_parent(state: UxFlow.State):
        UxFlow.VisualState.clear_all_from(decorated)
        UxFlow.VisualState.from_flow_state(state).set_on_container(decorated)
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
    tmpfile = NamedTemporaryFile(
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

    return value

class GradeConversionAppFlow(FlowStepHolder, SplitPanesLayout):  # pyright: ignore[reportUnsafeMultipleInheritance]
    '''
    Responsible for combining functionalities of
    FlowStepHolder (manages state of children) and
    SplitPanesLayout (manages visual positioning).
    '''
    def __init__(self, *args, **kwargs):
        self._tmp_dir_obj = TemporaryDirectory() # TemporaryDirectory will clean itself up when no more references are held.
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
    def _bind_element_inputs(self, step: UxFlow.FlowStepElement):
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
                output_select.on_data_changed.subscribe(update_result_inputs)
                execute.on_data_changed.subscribe(update_result_inputs)
            case _:
                super()._bind_element_inputs(step)

    @override
    def add_flow_step(self, element: UxFlow.FlowStepElement, position: int) -> None:
        '''
        Use this method to add a flow step;
        performs placement in UI layout.

        Also modifies FlowStepHolder's methods which rely on self.add_flow_step
        (e.g. `add_child_sibling`).
        '''
        super().add_child(decorate_step(element), position)
        super().add_flow_step(element, position)

if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    from nicegui import ui
    app_flow = GradeConversionAppFlow()
    ui.run(native=False, reload=False)
