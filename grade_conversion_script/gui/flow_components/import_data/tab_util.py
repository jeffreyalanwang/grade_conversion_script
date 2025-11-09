from contextlib import contextmanager
from typing import Literal

from nicegui import ui
from nicegui.events import Handler, ClickEventArguments

from grade_conversion_script.gui.base_components.collapse_transition import \
    CollapseTransition

_ = ui.button.default_props(add=f'ripple={ {'early': True} }')

@contextmanager
def ClickStop():
    '''
    Prevents click-events from propagating to parent elements
    (useful to stop ripple effects from duplicating).
    '''

    js_null_f = '() => {}'

    with ui.element() as click_event_no_propogate:
        _ = (
            click_event_no_propogate

            # prevent propogation of ripple to tab button
            .on('pointerdown.stop', js_handler=js_null_f).on(
                'keydown.stop', js_handler=js_null_f).on('mousedown.stop', js_handler=js_null_f)
            .on('pointerup.stop', js_handler=js_null_f).on('click.stop', js_handler=js_null_f).on(
                'keyup.stop', js_handler=js_null_f).on('mouseup.stop', js_handler=js_null_f)
            .on('mouseenter', js_handler=js_null_f)
            .on('mouseleave', js_handler=js_null_f)
        )
        yield click_event_no_propogate

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
