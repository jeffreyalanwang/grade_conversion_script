#!/usr/bin/env python3
import sys
sys.argv[0] = __file__
print('new argv: ' + str(sys.argv))
from nicegui import ui
from grade_conversion_script.gui.flow_components.app_flow \
    import GradeConversionAppFlow

DEBUG = any('debug' in x for x in sys.argv)

if DEBUG:
    print('Running in debug mode (you may see this message multiple times)')

def fix_path():
    '''
    If `pipx` created a proxy .exe,
    we need to replace it with the .py file
    for nicegui's server thread to find and
    begin execution at.
    '''
    sys.argv[0] = __file__
    print('new argv: ' + str(sys.argv))

def main():

    if any('grade-convert-app' in x for x in sys.argv):
        fix_path()

    with GradeConversionAppFlow():
        pass

    ui.run(
        title='Grade Conversion',
        favicon='📱',
        native=not DEBUG,
        dark=False,

        tailwind=True,
        reload=DEBUG,
        prod_js=DEBUG,
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()