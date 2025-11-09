from collections.abc import Collection
from pathlib import Path
from typing import Any, NamedTuple, cast

import pandas as pd
from nicegui import run

from grade_conversion_script.gui.flow_components.execute.rubric_match import \
    RubricCriteriaMatchElement
from grade_conversion_script.gui.flow_components.execute.student_alias_match import \
    StudentAliasMatchElement
from grade_conversion_script.gui.flow_components.select_input.common \
    import InputDependencies, PartialInputConstructor
from grade_conversion_script.gui.flow_components.select_output.common \
    import OutputDependencies, PartialOutputConstructor
from grade_conversion_script.input import InputHandler
from grade_conversion_script.output import OutputFormat
from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.funcs import wait_for_event, wrap_async


class PartialHandlerConstructors(NamedTuple):
    for_input: PartialInputConstructor[Any]
    for_output: PartialOutputConstructor[Any]


async def begin_student_alias_match(
    user: Collection[str],
    dest: Collection[str],
) -> dict[str, str]:
    # TODO with ?? and don't forget card/border
    element = StudentAliasMatchElement(user, dest)
    while True:
        complete = await wait_for_event(element.on_complete_changed.subscribe)
        if complete:
            assert element.data is not None
            return element.data

async def begin_rubric_criteria_match(
    given_labels: Collection[str],
    dest_labels: Collection[str],
) -> dict[str, str]:
    # TODO with ?? and don't forget card/border
    element = RubricCriteriaMatchElement(given_labels, dest_labels)
    while True:
        complete = await wait_for_event(element.on_complete_changed.subscribe)
        if complete:
            assert element.data is not None
            return element.data

async def execute(
    handlers: PartialHandlerConstructors,
    input_csvs: pd.DataFrame | dict[str, pd.DataFrame],
    temp_output_file: Path,
):
    assert temp_output_file.exists()

    student_aliases = AliasRecord()
    student_name_match = wrap_async(begin_student_alias_match)
    rubric_criteria_match = wrap_async(begin_rubric_criteria_match)

    input = cast(
        InputHandler,
        handlers.for_input(
            InputDependencies(
                student_aliases = student_aliases,
            ),
        ),
    )
    output = cast(
        OutputFormat,
        handlers.for_output(
            OutputDependencies(
                student_aliases = student_aliases,
                name_matcher = student_name_match,
                rubric_criteria_matcher = rubric_criteria_match,
            ),
        ),
    )

    grades = await run.cpu_bound(
        input.get_scores,
        csv = input_csvs,
    )

    output_df = await run.io_bound(
        # CPU bound would not be able to run the callbacks we passed to output_deps
        output.format,
        grades,
    )

    _ = run.io_bound(
        output.write_file,
        self_output = output_df,
        filepath = temp_output_file,
    )

class ExecuteRubricElement(UxFlow.FlowStepElement):
    def __init__(self):
        with self:
