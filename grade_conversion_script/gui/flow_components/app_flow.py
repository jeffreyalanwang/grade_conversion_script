from nicegui import ui
from nicegui.element import Element


ui.splitter.default_props(add='separator-class: "w-12 rounded-full opacity-75"')

class GradeConversionAppFlow(Element):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with self.classes('absolute-full'):
            v_splitter = ui.splitter().classes('fit')
            with v_splitter.before:
                h_splitter_0 = ui.splitter(horizontal = True, value = 70)
                with h_splitter_0.before:
                    h_splitter_1 = ui.splitter(horizontal = True)
                    with h_splitter_1.before:
                        ui.label('Left up')
                    with h_splitter_1.after:
                        ui.label('Left mid')
                with h_splitter_0.after:
                    ui.label('Left down')
            with v_splitter.after:
                h_splitter_0 = ui.splitter(horizontal=True, value=23)
                with h_splitter_0.before:
                    ui.label('Right up')
                with h_splitter_0.after:
                    h_splitter_1 = ui.splitter(horizontal = True)
                    with h_splitter_1.before:
                        ui.label('Right mid')
                    with h_splitter_1.after:
                        ui.label('Right down')


if __name__ in {"__main__", "__mp_main__"}:
    from nicegui import ui

    app_flow = GradeConversionAppFlow()

    ui.run(native=False)