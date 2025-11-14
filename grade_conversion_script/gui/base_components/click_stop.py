from contextlib import contextmanager

from nicegui import ui


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
            .on('pointerdown.stop', js_handler=js_null_f).on('keydown.stop', js_handler=js_null_f).on('mousedown.stop', js_handler=js_null_f)
            .on('pointerup.stop', js_handler=js_null_f).on('click.stop', js_handler=js_null_f).on('keyup.stop', js_handler=js_null_f).on('mouseup.stop', js_handler=js_null_f)
            .on('mouseenter', js_handler=js_null_f)
            .on('mouseleave', js_handler=js_null_f)
        )
        yield click_event_no_propogate
