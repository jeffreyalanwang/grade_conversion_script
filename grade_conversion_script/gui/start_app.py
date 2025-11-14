#!/usr/bin/env python3

from nicegui import ui

# app.on_exception()

def app():
    ui.run(native=True)

if __name__ in ('__main__', '__mp_main__'):
    app()