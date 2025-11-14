from typing import Literal

from nicegui import ui
from nicegui.events import Handler, ClickEventArguments

from grade_conversion_script.gui.base_components.click_stop import ClickStop
from grade_conversion_script.gui.base_components.collapse_transition import \
    CollapseTransition

_ = ui.button.default_props(add=f'ripple={ {'early': True} }')


def TabOptionButton(
    icon: str,
    color: str | None = None,
    on_click: Handler[ClickEventArguments] | None = None,
    size: Literal['xs', 'sm', 'md'] = 'sm',
):
    '''
    Create a button in a `ui.tab`.
    Can be collapsed by setting `visible` on collapser.
    '''
    with ClickStop():

        with CollapseTransition(dimension='width') as collapser:
            _ = collapser.style('line-height: 0 !important;')
                # button inside is inline, would not fill larger line-height

            with ui.button(icon=icon, color=color, on_click=on_click) as button:
                _ = (
                   button
                    .classes(add='aspect-square')
                    .classes(add='q-pa-none q-ma-none')
                    .props(add=f'size="{size}" outline dense')
                )
                return collapser, button
