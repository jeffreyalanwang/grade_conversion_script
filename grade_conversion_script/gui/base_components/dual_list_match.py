from collections.abc import Collection, Sequence
from typing import Any, Final, Literal, NamedTuple

from nicegui import ui, Event, ElementFilter
from nicegui.element import Element

from grade_conversion_script.gui.base_components.button_dual_label import \
    ButtonDualLabel
from grade_conversion_script.util.funcs import index_where, tuple_pop

type _Side = Literal['left', 'right']

class MatchResult(NamedTuple):
    left: str
    right: str

def header_icon(icon: str) -> ui.icon:
    return (
        ui.icon(icon, size = 'md')
        .classes(add = 'place-self-center opacity-60')
    )

def select_discardables(*args, **kwargs) -> ui.select:
    '''
    Listen to item discarded event
    using .on('discardItem', lambda e: callback(e.args)),
    (args={'value': Any, 'label', str}).
    '''
    element = ui.select(*args, **kwargs).props('dense')
    with element:
        _ = element.add_slot('option', '''
            <q-item v-bind="props.itemProps">
                <q-item-section>
                    <q-item-label v-html="props.opt.label" />
                </q-item-section>
                <q-item-section side>
                    <q-btn
                    icon="do_not_disturb_on" title="Ignore this option"
                    color="negative" flat round
                    @click.stop="$parent.$parent.$parent.$parent.$emit('discardItem', props.opt)" />
                </q-item-section>
            </q-item>
        ''')
        with element.add_slot('no-option'):
            with ui.item().classes('row items-center'):
                _ = ui.item_label('No items').classes('italic opacity-50')
    return element

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

        select_element = select_discardables if discardable else ui.select

        with self:
            with ui.grid(
                rows='min-content auto',
                columns='minmax(4rem, 4fr)'
                        ' auto minmax(4rem, 4fr)'
                        ' auto minmax(10rem, 3fr)'
            ) as g:
                _ = g.classes('gap-y-0')
                # Row 1
                self.left_select_element: Final = (
                    select_element(
                        label='Match A',
                        options=list(self.left_all),
                        multiple=False,
                        with_input=True,
                        clearable=True,
                    ))
                _ = header_icon('add')
                self.right_select_element: Final = (
                    select_element(
                        label='Match B',
                        options=list(self.right_all),
                        multiple=False,
                        with_input=True,
                        clearable=True,
                    ))
                _ = header_icon('forward')
                self.add_match_button: Final = (
                    ButtonDualLabel(
                        icon='add',
                        placeholders=('Match A', 'Match B'),
                    )
                    .classes(add='mx-1 my-auto')
                    .classes(add='text-ellipsis')
                    .props(add='outline no-caps')
                    .props('title="Add match from selected"'))

                # Row 2
                with ui.list().props('dense').classes(add='col-1') as l:
                    self.left_discards_element: Final = l
                    _ = (
                        ui.item_label('Discarded')
                        .props('header')
                        .classes('text-bold'))
                    self.left_discards_placeholder: Final = (
                        ui.item('No items')
                        .classes('italic opacity-50'))
                with ui.list().props('dense').classes(add='col-3') as l:
                    self.right_discards_element: Final = l
                    _ = (
                        ui.item_label('Discarded')
                        .props('header')
                        .classes('text-bold'))
                    self.right_discards_placeholder: Final = (
                        ui.item('No items')
                        .classes('italic opacity-50'))
                with ui.list().props('dense').classes(add='col-5') as l:
                    self.matches_element: Final = l
                    _ = (
                        ui.item_label('Matches')
                        .props('header')
                        .classes('text-bold'))
                    self.matches_placeholder: Final = (
                        ui.item('No items')
                        .classes('italic opacity-50'))

        self.add_match_button.disable()
        if not self.discardable:
            self.left_discards_element.delete()
            self.right_discards_element.delete()

        _ = self.left_select_element.on('input-value',
            lambda e: self.handle_text_box_changed(
                self.left_select_element, e.args, 'left',),)
        _ = self.right_select_element.on('input-value',
            lambda e: self.handle_text_box_changed(
                self.right_select_element, e.args, 'left',),)

        _ = self.left_select_element.on_value_change(
            lambda e: self.handle_selected_changed(
                self.left_select_element, e.value, 'left',),)
        _ = self.right_select_element.on_value_change(
            lambda e: self.handle_selected_changed(
                self.right_select_element, e.value, 'right',),)

        _ = self.left_select_element.on('discardItem',
            lambda e: self.handle_child_discard_button(
                e.args['label'], 'left'),)
        _ = self.right_select_element.on('discardItem',
            lambda e: self.handle_child_discard_button(
                e.args['label'], 'right'),)

        _ = self.left_select_element.on('keyup',
            lambda e: self.handle_focused_keypress(e.args),)
        _ = self.right_select_element.on('keyup',
            lambda e: self.handle_focused_keypress(e.args),)
        _ = self.add_match_button.on_click(
            lambda: self.handle_add_match_button(
                ),)

    def add_match_item(self, value: MatchResult, match_list: ui.list):
        with match_list:
            with ui.item() as i:
                element = i
                with ui.item_section():
                    _ = (
                        ui.item_label(value.left)
                        .props(f'title="{value.left}"')
                        .classes('leading-none truncate'))
                    _ = (
                        ui.item_label(value.right)
                        .props(f'title="{value.right}"')
                        .classes('leading-none truncate'))
                with ui.item_section().props('side'):
                    undo_button = (
                        ui.button(
                            icon='undo',
                            color='grey',)
                        .props('title="Remove matched pair"')
                        .props(add='flat round')
                        .props(add='size="xs"'))

        _ = undo_button.on_click(
            lambda:
            self.handle_match_undo(
                list_item=element,
                value=value,
            ),)

    def add_discard_item(self, value: str, discard_list: ui.list, side: _Side):
        with discard_list:
            with ui.item() as i:
                element = i
                with ui.item_section():
                    _ = ui.item_label(value)
                with ui.item_section().props('side'):
                    undo_button = (
                        ui.button(
                            icon='undo',
                            color='grey',)
                        .props('title="Unmark as discarded"')
                        .props(add='flat round')
                        .props(add='size="xs"'))

        _ = undo_button.on_click(
            lambda:
            self.handle_discard_undo(
                list_item=element,
                value=value,
                side=side,
            ),)

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

    def handle_child_discard_button(self, value: str, side: _Side):
        discards_list = self.left_discards_element if side == 'left' else self.right_discards_element
        selector = self.left_select_element if side == 'left' else self.right_select_element

        selector.set_value(None)
        self.add_discard_item(value, discards_list, side)

        match side:
            case 'left': # refreshes selector
                self.left_discards = self.left_discards.union({value})
            case 'right':
                self.right_discards = self.right_discards.union({value})
        self.ensure_list_placeholder(discards_list)

    def handle_discard_undo(self, list_item: ui.item, value: str, side: _Side):
        discards_list = self.left_discards_element if side == 'left' else self.right_discards_element

        match side:
            case 'left':
                self.left_discards = self.left_discards.difference((value,))
            case 'right':
                self.right_discards = self.right_discards.difference((value,))

        list_item.delete()
        self.ensure_list_placeholder(discards_list)

    def ensure_list_placeholder(self, list: ui.list):
        placeholders = {
            self.left_discards_placeholder,
            self.right_discards_placeholder,
            self.matches_placeholder,
        }
        list_items = ElementFilter(kind=ui.item).within(instance=list)
        non_placeholders = filter(
            lambda x: x not in placeholders,
            iter(list_items),)
        is_list_empty = not any(non_placeholders)

        placeholder = next(iter(
            placeholders.intersection( list_items.__iter__() )
        ))
        placeholder.set_visibility(is_list_empty)

    async def handle_text_box_changed(
        self,
        selector: ui.select,
        value: (str | None),
        side: _Side
    ):
        if value and any(x.startswith(value) for x in selector.options):
            if await selector.run_method('getOptionIndex') == -1:
                # True -> do not set model value
                _ = selector.run_method('moveOptionSelection', 1, True)
        else:
            _ = selector.run_method('setOptionIndex', -1)
            _ = selector.value = None

    def handle_selected_changed(self, selector: ui.select, value: str | None, side: _Side):

        is_value_present = bool(value)

        match side:
            case 'left':
                self.add_match_button.text_top = value
            case 'right':
                self.add_match_button.text_bottom = value

        other_selector = self.left_select_element if side == 'right' else self.right_select_element
        is_other_value_present = bool(other_selector.value)
        self.add_match_button.set_enabled(is_value_present and is_other_value_present)

    def handle_focused_keypress(self, key_event: dict[str, Any]):
        if key_event['metaKey'] and not key_event['ctrlKey']:
            # allow macOS cmd key equivalent
            key_event = {
                **key_event,
                'ctrlKey': True,
                'metaKey': False,
            }
        required_vals = {
            'key'     : 'Enter',
            'ctrlKey' : True,
            'shiftKey': False,
            'altKey'  : False,
            'metaKey' : False,
        }
        if (
            self.add_match_button.enabled
            and all(key_event[required_key] == required_val
                for required_key, required_val in required_vals.items())
        ):
            self.handle_add_match_button()

    @property
    def left_discards(self) -> frozenset[str]:
        return self._left_discards
    @left_discards.setter
    def left_discards(self, value: frozenset[str]):
        self._left_discards = value
        self.left_select_element.set_options( list(self.left_remaining) )
        self.on_any_changed.emit(self.left_remaining, self.right_remaining, self.pairs)

    @property
    def right_discards(self) -> frozenset[str]:
        return self._right_discards
    @right_discards.setter
    def right_discards(self, value: frozenset[str]):
        self._right_discards = value
        self.right_select_element.set_options( list(self.right_remaining) )
        self.on_any_changed.emit(self.left_remaining, self.right_remaining, self.pairs)

    @property
    def pairs(self) -> tuple[MatchResult, ...]:
        return self._pairs
    @pairs.setter
    def pairs(self, value: tuple[MatchResult, ...]):
        self._pairs = value
        self.left_select_element.set_options(list(self.left_remaining))
        self.right_select_element.set_options( list(self.right_remaining) )
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

if __name__ in {"__main__", "__mp_main__"}:
    from nicegui import ui

    element = DualListMatch(
        left = ['apple', 'banana', 'canteloupe',],
        right = ['dry grape', 'e', 'dry apple',],
        discardable = True,
    ).classes('fit absolute-full q-pa-lg')

    ui.run(native=False)