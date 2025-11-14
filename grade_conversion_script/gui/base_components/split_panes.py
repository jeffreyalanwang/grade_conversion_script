from typing import Final, Literal

from nicegui import ui
from nicegui.element import Element

# https://antoniandre.github.io/splitpanes/

# nicegui imports Vue's 'global' version,
#   not its ES Module version. (11/10/25; may change soon, see https://github.com/zauberzeug/nicegui/discussions/5328)
#
# As a result, custom Vue components which import Vue as a
#   module instead of referencing Vue as a global variable
#   (including the Splitpanes ES module from npm) will fail to initialize.
#
# Current workaround:
#
# We use the version of Splitpanes from a CDN (unpkg).
# This version assumes that Vue was also imported from a CDN
#   (the typical scenario requiring the 'global' build of Vue),
#   so it references Vue compatibly with how nicegui sets it up.
# This version makes the Splitpanes components available as globals:
#   `splitpanes.Splitpanes` and `splitpanes.Pane`.
#
# nicegui imports components from '.js' files (as opposed to '.vue')
#   by loading each as an ES module and registering
#   their default export as a single Vue component.
# So, we define each component in nicegui from a shim file
#   that exports one of the above globals.


ui.add_body_html(
    shared=True,
    code='''
    <script defer src="https://unpkg.com/splitpanes@4"></script>
''')
ui.add_css(
    shared=True,
    content='''
    @import "https://unpkg.com/splitpanes@4/dist/splitpanes.css" layer(base);
''')

class SplitPanes(Element, component='splitpanes.js'):
    def __init__(self,
        orientation: Literal[
            'h', 'v',
            'horizontal', 'vertical',],
        push: bool = True,
        dbl_click: bool = True,
        rtl: bool = False,
        first_splitter: bool = False,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        _ = self.classes('default-theme')

        if horizontal := (
            'h' == orientation[:1].lower()
        ):
            _ = self.props(add='horizontal')
        self._horizontal: Final = horizontal

        if not push:
            _ = self.props(remove='push-other-panes')
        if not dbl_click:
            _ = self.props(remove='maximize-panes')
        if rtl:
            _ = self.props(add='rtl')
        if first_splitter:
            _ = self.props(add='first-splitter')

    @property
    def horizontal(self) -> bool:
        return self._horizontal

class SplitPane(Element, component='splitpane.js'):
    def __init__(
        self,
        default_size: int | None = None,
        min_size: int = 0,
        max_size: int = 100,
        *args,
        **kwargs):
        '''
        Sizes in percentages.
        '''
        super().__init__(*args, **kwargs)
        if default_size is not None:
            _ = self.props(add=f'size="{default_size}"')
        _ = self.props(add=f'min-size={min_size} max-size={max_size}')

if __name__ in {"__main__", "__mp_main__"}:
    import logging, sys
    logging.basicConfig(level=logging.INFO,stream=sys.stdout)

    with ui.element().classes('absolute-full'):
        with SplitPanes('h') as panes:
            with SplitPane():
                with SplitPanes('v', push=False):
                    with SplitPane():
                        _ = ui.label('Pane 1')
                    with SplitPane():
                        _ = ui.label('Pane 2')
                    with SplitPane():
                        _ = ui.label('Pane 3')
            with SplitPane():
                _ = ui.label('Pane 4')

    ui.run()