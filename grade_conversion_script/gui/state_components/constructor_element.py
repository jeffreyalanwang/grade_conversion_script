from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final, Protocol

from nicegui import Event
from nicegui.element import Element
from nicegui.events import EventArguments


class NotReadyException(Exception):
    pass

class ObjectConstructingElement[T](Element, ABC):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_generated: T | None = None
        self.on_object_changed: Final = Event[T | None]()
        ''' Emits `None` if no longer ready to proceed. '''

    @property
    def last_generated(self) -> T | None:
        return self._last_generated

    def handle_options_changed(
        self,
        _: EventArguments | None = None
    ) -> None:

        try:
            val = self.generate_object()
        except NotReadyException:
            val = None

        self._last_generated = val
        self.on_object_changed.emit(val)

    @abstractmethod
    def generate_object(self) -> T:
        '''
        Create instance of T based
        on UI-prompted constructor options.

        Raises NotReadyException if
        handler could not be generated.
        '''
        ...


@dataclass(frozen=True)
class ConstructorDependencies:
    ''' Further input required from a parent element. '''
    pass

class PartialObject[
    TObject,
    TDependencies: ConstructorDependencies
](
    Protocol
):
    def __call__(self, dependencies: TDependencies) -> TObject:
        ...

class PartialObjectConstructingElement[
    TConstructed,
    TDependencies: ConstructorDependencies
](
    ObjectConstructingElement[
        PartialObject[TConstructed, TDependencies]
    ],
    ABC
):
    pass