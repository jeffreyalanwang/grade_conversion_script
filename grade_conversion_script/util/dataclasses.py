from dataclasses import dataclass

from nicegui.element import Element

from grade_conversion_script.util.funcs import kebab_case


@dataclass(frozen=True)
class StaticPanelInfo[T: Element]:
    '''
    Data record to export a single
    Element making up a single tab panel.

    Useful for settings pages when the
    user may pick one of several sets
    of settings, each with their own page.
    '''
    title: str
    options_page: type[T] # class, not instance
    name_id: str = None # pyright: ignore[reportAssignmentType] see __post_init__

    def __post_init__(self):
        if self.name_id is None:  # pyright: ignore[reportUnnecessaryComparison]
            new_val = kebab_case(self.title)
            object.__setattr__(
                self,
                'name_id',
                new_val
            )
