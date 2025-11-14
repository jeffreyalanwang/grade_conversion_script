from abc import ABC
from dataclasses import dataclass
from typing import Protocol

from grade_conversion_script.gui.state_components.constructor_element import \
    PartialObjectConstructingElement, \
    ConstructorDependencies, PartialObject
from grade_conversion_script.gui.util import StaticPanelInfo
from grade_conversion_script.input import InputHandler
from grade_conversion_script.util import AliasRecord


@dataclass(frozen=True)
class InputDependencies(ConstructorDependencies):
    ''' Class for holding output dependencies. '''
    student_aliases: AliasRecord

class PartialInputConstructor[T: InputHandler](
    PartialObject[
        T,
        InputDependencies
    ],
    Protocol
):
    pass

class InputConstructorElement[T: InputHandler](
    PartialObjectConstructingElement[
        T,
        InputDependencies
    ],
    ABC
):
    pass

class InputPanelInfo[T: InputHandler](
    StaticPanelInfo[InputConstructorElement[T]]
):
    pass