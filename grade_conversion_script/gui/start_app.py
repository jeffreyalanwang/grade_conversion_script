#!/usr/bin/env python3

from nicegui import ui

from grade_conversion_script.gui.flow_components.app_flow import \
    GradeConversionAppFlow

DEBUG = False

if DEBUG:
    print('Running in debug mode')

def main():

    GradeConversionAppFlow()

    ui.run(
        title='Grade Conversion',
        favicon='📱',
        native=not DEBUG,
        dark=False,

        tailwind=True,
        reload=DEBUG,
        prod_js=DEBUG,
    )

if __name__ in ('__main__', '__mp_main__'):
    main()