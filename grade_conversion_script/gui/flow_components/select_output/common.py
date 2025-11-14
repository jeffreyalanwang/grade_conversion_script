from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol, Sequence

from grade_conversion_script.gui.state_components.constructor_element import \
    PartialObject, PartialObjectConstructingElement, ConstructorDependencies
from grade_conversion_script.gui.util import StaticPanelInfo
from grade_conversion_script.output import OutputFormat
from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import Matcher, RubricMatcher


def file_safe_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

@dataclass(frozen=True)
class OutputDependencies(ConstructorDependencies):
    ''' Class for holding output dependencies. '''
    student_aliases: AliasRecord
    name_matcher: Matcher[str, str]
    rubric_criteria_matcher: RubricMatcher
    warning_handler: Callable[[Sequence[str]], None]

class PartialOutputConstructor[T: OutputFormat](
    PartialObject[
        T,
        OutputDependencies
    ],
    Protocol
):
    pass

class OutputConstructorElement[T: OutputFormat](
    PartialObjectConstructingElement[
        T,
        OutputDependencies
    ],
    ABC
):
    pass

@dataclass
class OutputPanelInfo[T: OutputFormat](
    StaticPanelInfo[OutputConstructorElement[T]]
):
    ''' Each tab panel exports its class, plus data about itself. '''
    make_filename: Callable[[], str]
    media_type: str