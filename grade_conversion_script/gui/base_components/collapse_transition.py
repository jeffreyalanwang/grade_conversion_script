from typing import Literal, override
from nicegui import ui

class CollapseTransition(ui.element, component='CollapseTransition.vue'):
    def __init__(
        self,
        name: str = 'collapse',
        dimension: Literal['height'] | Literal['width'] = 'height',
        ms_duration: int = 300,
        easing: str = 'ease-in-out',
    ):
        ''' Starts closed. '''
        super().__init__()
        self.props(add=
            f'name={name}'
            f' dimension={dimension}'
            f' duration={ms_duration}'
            f' easing={easing}'
        )

        self.visible = False

    @override
    def _handle_visibility_change(
        self,
        visible: str # sic. nicegui Visibility class
    ) -> None:
        # runs when Visibility().visibility is set.
        # replaces the original behavior (setting "hidden" prop)
        self.run_method('setVisible', visible)
