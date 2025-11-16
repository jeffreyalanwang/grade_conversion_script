#!/usr/bin/env python3

import sys
import logging
from threading import current_thread
from dataclasses import dataclass

from nicegui import ui, app
from grade_conversion_script.gui.flow_components.app_flow \
    import GradeConversionAppFlow

logger = logging.getLogger(f'{__name__}.thread{current_thread().ident}')

VERBOSE = '-v' in sys.argv or any('verbose' in x for x in sys.argv)
if VERBOSE:
    logger.setLevel(logging.INFO)
    logger.info('Running in verbose mode')

DEBUG = any('debug' in x for x in sys.argv)
if DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.info('Running in debug mode (you may see this message multiple times)')

@dataclass
class _Options:
                        # TODO restore these options once we fix pywebview download
    native=False        #not DEBUG
    window_size=None    #(750, 775) if not DEBUG else None
    reload=DEBUG
    prod_js=DEBUG
OPTIONS=_Options()

# If using `pywebview`, downloads must be allowed.
# Note that this must not be run under a main guard.
logger.info('Setting downloads permission (in case GUI is run using pywebview).')
app.native.settings['ALLOW_DOWNLOADS'] = True

def main():

    if any('grade-convert-app' in x for x in sys.argv):
        # If `pipx` created a proxy .exe, we need to replace it
        # with the .py file for nicegui's server thread to find
        # and begin execution at.
        logger.info('Started using proxy executable. Modifying sys.argv.')
        sys.argv[0] = __file__

    with GradeConversionAppFlow():
        pass

    ui.run(
        title='Grade Conversion',
        favicon='📱',
        native=OPTIONS.native,
        window_size=OPTIONS.window_size,
        dark=False,

        tailwind=True,
        reload=OPTIONS.reload,
        prod_js=OPTIONS.prod_js,
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()