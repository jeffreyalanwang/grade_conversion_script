from abc import ABC
from dataclasses import dataclass
from typing import Protocol

from grade_conversion_script.gui.state_components.constructor_element import \
    PartialObject, PartialObjectConstructingElement, ConstructorDependencies
from grade_conversion_script.output import OutputFormat
from grade_conversion_script.util import StaticPanelInfo, AliasRecord
from grade_conversion_script.util.custom_types import Matcher, RubricMatcher


@dataclass(frozen=True)
class OutputDependencies(ConstructorDependencies):
    ''' Class for holding output dependencies. '''
    student_aliases: AliasRecord
    name_matcher: Matcher[str, str]
    rubric_criteria_matcher: RubricMatcher

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

class OutputConstructorInfo[T: OutputFormat](
    StaticPanelInfo[OutputConstructorElement[T]]
):
    pass