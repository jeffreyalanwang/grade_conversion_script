#!/usr/bin/env python3
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from nicegui import ui

app.on_exception()

def app():
    ui.run(native=True)

if __name__ in ('__main__', '__mp_main__'):
    app()