from typing import Final, Optional, override

from nicegui import ui
from nicegui.elements.button import Button
from nicegui.elements.icon import Icon
from nicegui.events import Handler, ClickEventArguments

SPACE=' '

def button_label(text: str = '') -> ui.label:
    return ui.label(text)

def placeholder_label(text: str = SPACE) -> ui.label:
    return button_label(text).classes('italic opacity-75')

class ButtonDualLabel(Button):
    def __init__(
        self,
        placeholders: Optional[tuple[str | None, str | None]] = None,
        icon: Optional[str] = None,
        on_click: Optional[Handler[ClickEventArguments]] = None,
        color: Optional[str] = 'primary',
        *args,
        **kwargs
    ):
        super().__init__(on_click=on_click, color=color, *args, **kwargs)

        placeholders = placeholders or (None, None)
        placeholders = (placeholders[0] or SPACE, placeholders[1] or SPACE)

        with self:
            with ui.row(align_items = 'center', wrap = False).classes('w-full'):
                self.icon_element: Icon | None = ui.icon(icon) if icon else None
                with ui.column().classes(add = 'w-full gap-0'):
                    with ui.row():
                        self.top_label: Final = button_label()
                        self.top_placeholder: Final = placeholder_label(placeholders[0])
                    with ui.row().style('margin-top: -0.5em;'):
                        self.bottom_label: Final = button_label()
                        self.bottom_placeholder: Final = placeholder_label(placeholders[1])

        for label in (self.top_label, self.bottom_label):
            label.set_visibility(False)

    @property
    def text_top(self) -> str | None:
        return self.top_label.text
    @property
    def text_bottom(self) -> str | None:
        return self.bottom_label.text
    @text_top.setter
    def text_top(self, value: str | None):
        self.top_label.set_text(value.strip() if value else '')
        self.top_label.set_visibility( bool(self.top_label.text) )
        self.top_placeholder.set_visibility(not self.top_label.visible)
    @text_bottom.setter
    def text_bottom(self, value: str | None):
        self.bottom_label.set_text(value.strip() if value else '')
        self.bottom_label.set_visibility( bool(self.bottom_label.text) )
        self.bottom_placeholder.set_visibility(not self.bottom_label.visible)

    @override
    def _handle_icon_change(self, icon: Optional[str]) -> None:
        if new_icon_value := icon:
            if self.icon_element:
                self.icon_element.name = new_icon_value
            else:
                self.icon_element = ui.icon(new_icon_value)
        else:
            if self.icon_element:
                self.icon_element.delete()
