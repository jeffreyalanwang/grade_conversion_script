from collections.abc import Collection, Sequence
from typing import Final, Literal, NamedTuple

from nicegui import ui, Event, ElementFilter
from nicegui.element import Element
from nicegui.elements.mixins.disableable_element import DisableableElement

from grade_conversion_script.util.funcs import index_where, tuple_pop

type _Side = Literal['left', 'right']

PLACEHOLDER_MARKER = 'placeholder'

class MatchResult(NamedTuple):
    left: str
    right: str
class DualListMatch(Element):
    def __init__(
        self,
        left: Sequence[str],
        right: Sequence[str],
        discardable = False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.discardable: Final = discardable
        self.left_all: Final[Sequence[str]] = tuple(left)
        self.right_all: Final[Sequence[str]] = tuple(right)

        self._left_discards: frozenset[str] = frozenset()
        self._right_discards: frozenset[str] = frozenset()
        self._pairs: tuple[MatchResult, ...] = tuple()

        self.on_value_changed: Final = Event[Sequence[MatchResult]]()
        self.on_any_changed: Final = Event[Sequence[str], Sequence[str], Sequence[MatchResult]]()
        ''' Emits left_remaining, right_remaining, pairs. '''

        with self:
            with ui.grid(rows='min-content auto', columns='1fr auto 1fr auto .75fr'):
                # Row 1
                with ui.select(
                        label='Match A',
                        options=list(self.left_all),
                        multiple=False,
                        with_input=True,
                        clearable=True,
                    ) as s:
                    self.left_select_element = s
                    with s.add_slot('after'):
                        self.left_discard_button = (
                            ui.button(
                                icon='do_not_disturb_on',
                                color='negative'
                            )
                            .props(add='title="Ignore selected"')
                            .props(add='flat round')
                        )
                _ = (
                    ui.label(text='+')
                    .classes(add='aspect-square')
                    .classes(add='justify-center items-center')
                )
                with ui.select(
                        label='Match B',
                        options=list(self.left_all),
                        multiple=False,
                        with_input=True,
                        clearable=True,
                    ) as s:
                    self.right_select_element = s
                    with s.add_slot('after'):
                        self.right_discard_button = (
                            ui.button(
                                icon='do_not_disturb_on',
                                color='negative'
                            )
                            .props(add='title="Ignore selected"')
                            .props(add='flat round')
                        )
                _ = (
                    ui.label(text='=')
                    .classes(add='aspect-square')
                    .classes(add='justify-center items-center')
                )
                with ui.button().classes(add='mx-1 my-auto') as b:
                    self.add_match_button = (
                        b.props('title="Add match from selected"')
                        .props(add='outline')
                    )
                    _ = ui.icon('add')
                    with ui.column().classes(add='w-full'):
                        self.add_match_label_left = ui.label()
                        self.add_match_label_right = ui.label()

                # Row 2
                with ui.list().classes(add='col-1') as l:
                    self.left_discards_element = l
                    _ = (
                        ui.item_label('Discarded')
                        .props('header')
                        .classes('text-bold')
                    )
                    _ = ui.separator()
                    _ = (
                        ui.label('No items')
                        .mark(PLACEHOLDER_MARKER)
                        .classes('italic opacity-75')
                    )
                with ui.list().classes(add='col-3') as l:
                    self.right_discards_element = l
                    _ = (
                        ui.item_label('Discarded')
                        .props('header')
                        .classes('text-bold')
                    )
                    _ = ui.separator()
                    _ = (
                        ui.label('No items')
                        .mark(PLACEHOLDER_MARKER)
                        .classes('italic opacity-75')
                    )
                with ui.list().classes(add='col-5') as l:
                    self.matches_element = l
                    _ = (
                        ui.item_label('Matches')
                        .props('header')
                        .classes('text-bold')
                    )
                    _ = ui.separator()
                    _ = (
                        ui.label('No items')
                        .mark(PLACEHOLDER_MARKER)
                        .classes('italic opacity-75')
                    )

        self.left_discard_button.disable()
        self.right_discard_button.disable()
        self.add_match_button.disable()
        if self.discardable:
            self.left_discard_button.delete()
            self.right_discard_button.delete()
            self.left_discards_element.delete()
            self.right_discards_element.delete()

        _ = self.left_select_element.on_value_change(
            lambda e:
            self.handle_selector_value_change(
                self.left_select_element,
                e.value
            )
        )
        _ = self.right_select_element.on_value_change(
            lambda e:
            self.handle_selector_value_change(
                self.right_select_element,
                e.value
            )
        )
        _ = self.left_discard_button.on_click(
            lambda: self.handle_discard_button('left')
        )
        _ = self.right_discard_button.on_click(
            lambda: self.handle_discard_button('right')
        )
        _ = self.add_match_button.on_click(
            lambda: self.handle_add_match_button()
        )

    def add_match_item(self, value: MatchResult, match_list: ui.list):
        with match_list:
            with ui.item():
                with ui.item_section():
                    _ = ui.item_label(value.left)
                    _ = ui.item_label(value.right)
                with ui.item_section().props('side'):
                    undo_button = (
                        ui.button(
                            icon='undo',
                            color='grey'
                        )
                        .props('title="Remove matched pair"')
                        .props(add='flat round')
                    )

        _ = undo_button.on_click(
            lambda:
            self.handle_match_undo(
                list_item=ui.item(),
                value=value,
            )
        )

    def add_discard_item(self, value: str, discard_list: ui.list, side: _Side):
        with discard_list:
            with ui.item() as i:
                item = i
                _ = (
                    ui.item_label(value)
                    .props('caption')
                )
                with ui.item_section().props('side'):
                    undo_button = (
                        ui.button(
                            icon='undo',
                            color='grey'
                        )
                        .props('title="Unmark as discarded"')
                        .props(add='flat round')
                    )

        _ = undo_button.on_click(
            lambda:
            self.handle_discard_undo(
                list_item=item,
                value=value,
                side=side,
            )
        )

    def handle_add_match_button(self):
        left_value = self.left_select_element.value
        assert isinstance(left_value, str)
        self.left_select_element.set_value(None)

        right_value = self.right_select_element.value
        assert isinstance(right_value, str)
        self.right_select_element.set_value(None)

        pair = MatchResult(left_value, right_value)

        self.add_match_item(pair, self.matches_element)
        self.ensure_list_placeholder(self.matches_element)

        self.pairs += (pair,)

    def handle_match_undo(self, list_item: ui.item, value: MatchResult):
        pair_index = index_where(
            lambda x: x.left == value.left,
            self.pairs
        )
        assert self.pairs[pair_index].right == value.right

        _, self.pairs = tuple_pop(pair_index, self.pairs)
        
        list_item.delete()
        self.ensure_list_placeholder(self.matches_element)

    def handle_discard_button(self, side: _Side):
        selector = self.left_select_element if side == 'left' else self.right_select_element
        discards_list = self.left_discards_element if side == 'left' else self.right_discards_element

        value = selector.value
        assert isinstance(value, str)
        selector.set_value(None)

        self.add_discard_item(value, discards_list, side)

        if side == 'left':
            self.left_discards = self.left_discards.union({value})
        else:
            self.right_discards = self.right_discards.union({value})
        self.ensure_list_placeholder(discards_list)

    def handle_discard_undo(self, list_item: ui.item, value: str, side: _Side):
        discards_list = self.left_discards_element if side == 'left' else self.right_discards_element

        if side == 'left':
            self.left_discards = self.left_discards.difference((value,))
        else:
            self.right_discards = self.right_discards.difference((value,))

        list_item.delete()
        self.ensure_list_placeholder(discards_list)

    def ensure_list_placeholder(self, list: ui.list):
        is_element_empty = not any(
            ElementFilter(
                kind=ui.item,
                local_scope=True
            )
            .within(instance=list)
            .__iter__()
        )
        placeholder_element = next(
            ElementFilter(
                marker=PLACEHOLDER_MARKER,
                local_scope=True
            )
            .within(instance=list)
            .__iter__()
        )
        placeholder_element.set_visibility(is_element_empty)

    def handle_selector_value_change(self, selector: ui.select, value: str | None):

        is_value_present = bool(value)
        if is_value_present:
            # we assume validation will prevent
            # a value change event,
            # but double check here
            assert value in selector.options

        for element in selector.slots['after']:
            assert isinstance(element, DisableableElement)
            element.set_enabled(is_value_present)
        self.add_match_button.set_enabled(is_value_present)

    @property
    def left_discards(self) -> frozenset[str]:
        return self._left_discards
    @left_discards.setter
    def left_discards(self, value: frozenset[str]):
        self._left_discards = value
        self.left_select_element.options = list(self.left_remaining)
        self.on_any_changed.emit(self.left_remaining, self.right_remaining, self.pairs)

    @property
    def right_discards(self) -> frozenset[str]:
        return self._right_discards
    @right_discards.setter
    def right_discards(self, value: frozenset[str]):
        self._right_discards = value
        self.right_select_element.options = list(self.right_remaining)
        self.on_any_changed.emit(self.left_remaining, self.right_remaining, self.pairs)

    @property
    def pairs(self) -> tuple[MatchResult, ...]:
        return self._pairs
    @pairs.setter
    def pairs(self, value: tuple[MatchResult, ...]):
        self._pairs = value
        self.left_select_element.options = list(self.left_remaining)
        self.right_select_element.options = list(self.right_remaining)
        self.on_value_changed.emit(value)
        self.on_any_changed.emit(self.left_remaining, self.right_remaining, self.pairs)

    @property
    def left_remaining(self) -> Sequence[str]:
        done_items = self.left_discards.union(x.left for x in self.pairs)
        return [
            x for x in self.left_all
            if x not in done_items
        ]
    @property
    def right_remaining(self) -> Sequence[str]:
        done_items = self.right_discards.union(x.right for x in self.pairs)
        return [
            x for x in self.right_all
            if x not in done_items
        ]

    @property
    def value(self) -> Collection[MatchResult]:
        return self.pairs
