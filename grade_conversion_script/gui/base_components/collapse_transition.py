from typing import Literal, override
from nicegui.element import Element

class CollapseTransition(Element, component='CollapseTransition.vue'):
    def __init__(
        self,
        name: str = 'collapse',
        dimension: Literal['height'] | Literal['width'] = 'height',
        ms_duration: int = 300,
        easing: str = 'ease-in-out',
    ):
        ''' Starts closed. '''
        super().__init__()
        _ = self.props(add=
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
        _ = self.run_method('setVisible', visible)
