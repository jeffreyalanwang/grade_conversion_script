from typing import Final

from nicegui import ui
from nicegui.element import Element


def decorate(element: Element, header_text: str | None) -> Element:
    '''
    Add any decoration content we would like around the FlowStepElement.
    '''

    if isinstance(element, ClientSideHeaderElement):
        if header_text is not None and header_text != element.header_text:
            element.header_text = header_text
        return element
    else:
        decorated_element = ClientSideHeaderElement(header_text=header_text)
        element.move(decorated_element.content)
        return decorated_element

class ClientSideHeaderElement(ui.column):
    '''
    An Element which may be given a title bar,
    but needs to create and manage the bar
    itself.
    '''
    def __init__(self, header_text: str | None = None, *args, **kwargs) -> None:
        super().__init__(wrap=False, align_items='stretch', *args, **kwargs)
        _ = self.classes('gap-0 items-stretch')

        super().__enter__()

        self.header_bar: Final = ui.element('q-toolbar')
        with self.header_bar:
            self._header_label: ui.label | None
            if not header_text:
                self._header_label = None
            else:
                self._header_label = ui.label(text=header_text).classes('text-bold')

        _ = ui.separator()

        self.content: Final = ui.element().classes('grow relative')

        super().__exit__()

    def __enter__(self):
        super().__enter__()
        return self.content.__enter__()
    def __exit__(self, *_):
        self.content.__exit__(*_)
        return super().__exit__(*_)

    @property
    def header_text(self) -> str | None:
        return self._header_label.text if self._header_label else None
    @header_text.setter
    def header_text(self, header_text: str | None) -> None:
        match header_text, self._header_label:
            case None, None:
                return
            case _, None:
                with self.header_bar:
                    self._header_label = ui.label(header_text).classes('text-bold')
                    self._header_label.move(self.header_bar, 0)
            case None, _:
                self._header_label.delete()
                self._header_label = None
            case _, _:
                self._header_label.text = header_text
