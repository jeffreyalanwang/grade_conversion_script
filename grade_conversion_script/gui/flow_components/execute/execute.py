import logging
from collections.abc import Collection, Sequence
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Final, NamedTuple, cast

import pandas as pd
from nicegui import run, ui

from grade_conversion_script.gui.flow_components.execute.student_alias_match \
    import StudentAliasMatchElement
from grade_conversion_script.gui.flow_components.execute.rubric_match \
    import RubricCriteriaMatchElement
from grade_conversion_script.gui.flow_components.execute.warn_existings \
    import WarnExistings
from grade_conversion_script.gui.flow_components.select_input.common \
    import InputDependencies, PartialInputConstructor
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputDependencies, PartialOutputConstructor
from grade_conversion_script.gui.state_components import UxFlow
from grade_conversion_script.gui.util import wait_for_event, wrap_async
from grade_conversion_script.input import InputHandler
from grade_conversion_script.output import OutputFormat
from grade_conversion_script.util import AliasRecord


class PartialHandlerConstructors(NamedTuple):
    for_input: PartialInputConstructor[Any]
    for_output: PartialOutputConstructor[Any]

class ExecuteDepends(NamedTuple):
    input_csvs: pd.DataFrame | dict[str, pd.DataFrame]
    handler_constructors: PartialHandlerConstructors
    temp_dest_file: Path

class ExecuteStep(  # pyright: ignore[reportUnsafeMultipleInheritance]
    UxFlow.FlowStepInputElement[ExecuteDepends],
    UxFlow.FlowStepDataElement[Path]
):
    def __init__(self, add_step: Callable[[UxFlow.FlowStepElement], None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._birthed_siblings: Final = list[UxFlow.FlowStepElement]()
        self._add_step_callback: Final = add_step

        with self.classes('fit grid items-center justify-center'):
            self.button: Final = ui.button('Process data')

        _ = self.button.on_click(self.button_callback)

    def button_callback(self):
        assert self.inputs
        return self.execute(
            handler_constructors=self.inputs.handler_constructors,
            input_csvs=self.inputs.input_csvs,
            temp_output_file=self.inputs.temp_dest_file,)

    def _prompt_additional_step(self, step: UxFlow.FlowStepElement) -> None:
        self._birthed_siblings.append(step)
        with self:
            self._add_step_callback.__call__(step)
        self.set_state_immediately(UxFlow.State.CONTINUE_REQUIRED)  # ensure prompted step is allowed, and ensure this step does not reset

    def cleanup_children(self): # TODO take a callback from parent instead, to decrease FlowStepHolder birthed sibling count
        while self._birthed_siblings:
            self._birthed_siblings.pop().delete()

    async def execute(
        self,
        handler_constructors: PartialHandlerConstructors,
        input_csvs: pd.DataFrame | dict[str, pd.DataFrame],
        temp_output_file: Path,
    ):
        assert temp_output_file.parent.exists()

        _ = self.button.props(add='loading')
        self.button.disable()

        student_aliases = AliasRecord()
        student_name_match = wrap_async(self.prompt_student_alias_match)
        rubric_criteria_match = wrap_async(self.prompt_rubric_criteria_match)
        warning_printer = wrap_async(self.show_warnings)

        # Prepare objects
        input = cast(InputHandler,
            handler_constructors.for_input(
                InputDependencies(
                    student_aliases=student_aliases,
                ),
            ), )
        output = cast(OutputFormat,
            handler_constructors.for_output(
                OutputDependencies(
                    student_aliases=student_aliases,
                    name_matcher=student_name_match,
                    rubric_criteria_matcher=rubric_criteria_match,
                    warning_handler=warning_printer,
                ),
            ), )

        # Perform processing
        try:
            # We cannot use run.cpu_bound due to the constraint that
            # data must be serialized before transfer between processes.
            # We would not be able to run the callbacks passed to output_deps.
            # In addition, the mutable state of AliasRecord
            # would not be reflected in other processes.
            grades = await run.io_bound(
                input.get_scores,
                csv=input_csvs,
            )
            output_df = await run.io_bound(
                output.format,
                grades,
            )
            _ = await run.io_bound(
                output.write_file,
                self_output=output_df,
                filepath=temp_output_file,
            )
            self.data = temp_output_file
        except Exception as e:
            self.set_state_immediately(
                self.state.with_continue_required(False),)
            ui.notify(
                dedent(f'''
                    Error encountered. Double-check input data.
                    Details ({type(e)}):
                    {'\n'.join(str(a) for a in e.args)}
                ''').strip(),
                multi_line=True,
                close_button=True,
                type='negative',)
            logging.exception(e)
        finally:
            self.cleanup_children()
            if not self.state.requires_continue:
                self.button.enable()
            _ = self.button.props(remove='loading')

    async def prompt_student_alias_match(self,
        user: Collection[str],
        dest: Collection[str],
    ) -> dict[str, str]:
        with self: # temporarily place our new element here
            element = StudentAliasMatchElement(user, dest)
            # do not exit context (disabling all children) until new step is extracted to another place
            self._prompt_additional_step(element) # attach element in proper place
        while True:
            data = await wait_for_event(element.on_data_changed.subscribe)
            if data[0] is not None and element.state >= UxFlow.State.CONTINUE_REQUIRED:
                return data[0]

    async def prompt_rubric_criteria_match(self,
        given_labels: Collection[str],
        dest_labels: Collection[str],
    ) -> dict[str, str]:
        with self:  # temporarily place our new element here
            element = RubricCriteriaMatchElement(given_labels, dest_labels)
            # do not exit context (disabling all children) until new step is extracted to another place
            self._prompt_additional_step(element) # attach element in proper place
        while True:
            data = await wait_for_event(element.on_data_changed.subscribe)
            if data[0] is not None and element.state >= UxFlow.State.CONTINUE_REQUIRED:
                return data[0]

    async def show_warnings(self, messages: Sequence[str]):
        if not messages:
            return
        with self:  # temporarily place our new element here
            element = WarnExistings(messages)
            # do not exit context (disabling all children) until new step is extracted to another place
            self._prompt_additional_step(element) # attach element in proper place
