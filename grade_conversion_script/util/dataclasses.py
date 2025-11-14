from dataclasses import dataclass

from nicegui.element import Element

from grade_conversion_script.util.funcs import kebab_case


@dataclass
class StaticPanelInfo[T: Element]:
    '''
    Data record to export a single
    Element making up a single tab panel,
    while providing metadata to display with it.

    Useful for settings pages when the
    user may pick one of several sets
    of settings, each with their own page.
    '''
    title: str
    options_page: type[T] # class, not instance

    @property
    def name_id(self):
        return kebab_case(self.title)
