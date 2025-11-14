from asyncio import Lock
from collections.abc import Sequence
from math import ceil, floor
from typing import Final, Literal

from nicegui import ui
from nicegui.element import Element

from grade_conversion_script.gui.base_components.split_panes \
    import SplitPane, SplitPanes
from grade_conversion_script.util.funcs import index_where, tuple_insert

ui.add_head_html('''
    <script>
    function emitSize() {
        emitEvent('resize', {
            width: document.body.offsetWidth,
            height: document.body.offsetHeight,
        });
    }
    window.onload = emitSize;
    window.onresize = emitSize;
    </script>
''')
# To catch event:
# ui.on('resize',
#     lambda e:
#     print(f'resize: {e.args['width'], e.args['height']}'),)

ui.add_css(
    shared=True,
    content='''
    .splitpanes__pane > .flow-step {
        overflow: auto;
    }
    '''
)

ui.add_css(
    shared=True,
    content='''
    .splitpanes__pane {
        position: relative;
    }
    '''
)

ui.add_css(
    shared=True,
    # TODO add this rule, which relies on CSS variables currently buried further deep
    # .splitpanes.fullscreen-paneview.v-scroll-paneview::before {
    #     width: 100%;
    #     height: var(--total-thickness);
    #     inset: calc(-1 * var(--inverted-corner-radius)) 0;
    #     clip-path: shape( evenodd from 0 0, line to 0 100%, arc by var(--c-r) var(--c-nr) of var(--c-r) cw, line by calc(100% - var(--c-2r)) 0, arc by var(--c-r) var(--c-r) of var(--c-r) cw, line to 100% 0, arc by var(--c-nr) var(--c-r) of var(--c-r) cw, line to var(--c-r) var(--c-r), arc to 0 0 of var(--c-r) cw, close, move to calc(50% - var(--p-12l)) calc(50% - var(--p-12w)), line by var(--p-l) 0, arc by 0 var(--p-w) of var(--p-12w) cw, line by var(--p-nl) 0, arc by 0 var(--p-nw) of var(--p-12w) cw, close );
    #     content: '';
    #     position: relative;
    #     background-color: #444444;
    # }
    content='''
    @layer utility {    
        *:not(.fullscreen-paneview) > :not(.splitpanes__pane):has(> .splitpanes.fullscreen-paneview) {
            position: absolute;
            inset: 0;
            
            &:not(:has(> .v-scroll-paneview)) {
                border-radius: 20px;
                border-color: #444444;
                border-width: 10px;
                border-style: solid;
                box-sizing: border-box;
                box-shadow: 0px 0px 0px 10px #444444;
            }
        }
        .splitpanes.fullscreen-paneview {
            --pane-corner-radius: 10px;
            
            & > .splitpanes__pane {
                background-color: transparent;
                box-sizing: border-box;
                border-radius: var(--pane-corner-radius);
                margin: 0;
                padding: 0;
                
                & > * {
                    width: 100%;
                    height: 100%;
                }
            }
            
            & > .splitpanes__splitter {
                background-color: transparent;
                border-style: none;
                &::before {
                    display: none;
                }
                &::after {
                    --inverted-corner-radius: var(--pane-corner-radius);
                    --pill-length: 3rem;
                    --pill-thickness: 6px;
                    --pill-padding: 2px;
                    --total-thickness: calc(var(--pill-thickness) + var(--pill-padding) + 2 * var(--inverted-corner-radius));
                    background-color: #444444;
                    
                    margin: 0;
                    position: absolute;
                    transform: unset;
                    
                    --c-r    : var(--inverted-corner-radius);
                    --c-nr   : calc(-1 * var(--c-r));
                    --c-2r   : calc(2 * var(--c-r));
                    --p-l    : calc(var(--pill-length) - var(--pill-thickness)); /* round corners add length */
                    --p-nl   : calc(-1 * var(--p-l));
                    --p-12l  : calc(var(--p-l) / 2);
                    --p-w    : var(--pill-thickness);
                    --p-nw   : calc(-1 * var(--p-w));
                    --p-12w  : calc(var(--p-w) / 2);
                }
            }
            &.splitpanes--vertical > .splitpanes__splitter {
                width: 8px;
            }
            &.splitpanes--horizontal > .splitpanes__splitter {
                height: 8px;
            }
            &.splitpanes--vertical > .splitpanes__splitter::after {
                height: 100%;
                width: var(--total-thickness);
                inset: 0 calc(-1 * var(--inverted-corner-radius));
                clip-path: shape(
                    evenodd
                    
                    from 0 0,
                    line to 100% 0,
                    arc by var(--c-nr) var(--c-r) of var(--c-r) ccw,
                    line by 0 calc(100% - var(--c-2r)),
                    arc by var(--c-r) var(--c-r) of var(--c-r) ccw,
                    line to 0 100%,
                    arc by var(--c-r) var(--c-nr) of var(--c-r) ccw,
                    line to var(--c-r) var(--c-r),
                    arc to 0 0 of var(--c-r) ccw,
                    close,
                    
                    move to calc(50% - var(--p-12w)) calc(50% - var(--p-12l)),
                    arc by var(--p-w) 0 of var(--p-12w) cw,
                    line by 0 var(--p-l),
                    arc by var(--p-nw) 0 of var(--p-12w) cw,
                    line by 0 var(--p-nl),
                    close
                );
            }
            &.splitpanes--horizontal > .splitpanes__splitter::after {
                width: 100%;
                height: var(--total-thickness);
                inset: calc(-1 * var(--inverted-corner-radius)) 0;
                clip-path: shape(
                    evenodd
                    
                    from 0 0,
                    line to 0 100%,
                    arc by var(--c-r) var(--c-nr) of var(--c-r) cw,
                    line by calc(100% - var(--c-2r)) 0,
                    arc by var(--c-r) var(--c-r) of var(--c-r) cw,
                    line to 100% 0,
                    arc by var(--c-nr) var(--c-r) of var(--c-r) cw,
                    line to var(--c-r) var(--c-r),
                    arc to 0 0 of var(--c-r) cw,
                    close,
                    
                    move to calc(50% - var(--p-12l)) calc(50% - var(--p-12w)),
                    line by var(--p-l) 0,
                    arc by 0 var(--p-w) of var(--p-12w) cw,
                    line by var(--p-nl) 0,
                    arc by 0 var(--p-nw) of var(--p-12w) cw,
                    close
                );
            }            
        }
    }
''')

class SplitPanesLayout(Element):
    def __init__(self, children: Sequence[Element], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._redoing_layout_mutex: Final = Lock()
        self._children: tuple[Element, ...] = tuple(children)
        self._panes: tuple[SplitPane, ...] = ()
        self.current_layout_type: Literal['vertical', 'panes'] | None = None

        # Resize layout once now, and on future viewport resizes
        self._redo_layout_immediately(None)
        assert self.current_layout_type is not None
        ui.on('resize',
            lambda e: self.redo_layout(
                (e.args['width'], e.args['height']),),)

    def distribute_items(self, count: int) -> tuple[int, ...]:
        return (
            floor(count / 2),
            ceil(count / 2),
        )
    
    def add_child(self, child: Element, index: int = -1) -> None:
        if index < 0:
            index = len(self._children) + index

        place_after = self._panes[index - 1] if index > 0 else self._panes[0]
        target_panes_container = place_after.parent_slot.parent if place_after.parent_slot else None
        assert target_panes_container
        place_after_index = index_where(
            lambda child: child is place_after,
            target_panes_container,)

        with target_panes_container:
            child_pane = SplitPane()
            child.move(child_pane)
            child_pane.move(target_panes_container, place_after_index + 1)

        self._panes = tuple_insert(index, child_pane, self._panes)
        self._children = tuple_insert(index, child, self._children)

    async def redo_layout(self, viewport_size_px: tuple[float, float]) -> None:
        async with self._redoing_layout_mutex:
            self._redo_layout_immediately(viewport_size_px)

    def _redo_layout_immediately(self,
        viewport_size_px: tuple[float, float] | None
    ) -> None:
        ''' If viewport_size_px is None, it is not considered. '''

        match viewport_size_px:
            case (width, height) if (width <= height) or (width < 550):
                layout_type = 'vertical'
            case None | _:
                layout_type = 'panes'

        if self.current_layout_type == layout_type:
            return
        count = len(self._children)
        old_content = self._make_children_orphans()
        match layout_type:
            case 'vertical':
                new_panes = self._layout_single_col(count)
            case 'panes':
                new_panes = self._layout_panes(count)

        for step, pane in zip(old_content, new_panes):
            step.move(pane)

    def _layout_single_col(self, count: int) -> tuple[SplitPane, ...]:
        assert self._children
        assert not self._panes
        panes: list[SplitPane] = []
        item_height = 300

        with self:
            with SplitPanes(orientation='horizontal') as container:
                _ = (
                    container
                    .classes('fullscreen-paneview')
                    .classes(f'v-scroll-paneview min-h-[{count * item_height}px]')
                )
                panes.extend(
                    SplitPane()
                    for _ in range(count))

        self.current_layout_type = 'vertical'
        self._panes = tuple(panes)
        return self._panes

    def _layout_panes(self, count: int) -> tuple[SplitPane, ...]:
        if count < 2:
            return self._layout_single_col(count)
        assert self._children
        assert not self._panes

        # main axis: the axis we stay aligned on until wrap
        main_axis: Literal['vertical', 'horizontal'] = 'vertical'
        main_axis_counts = self.distribute_items(count)

        panes: list[SplitPane] = []

        with self:
            with SplitPanes(orientation=main_axis).classes('fullscreen-paneview'):
                segment_containers = list[SplitPanes]()
                child_axis = 'horizontal' if main_axis == 'vertical' else 'vertical'
                for segment in main_axis_counts:
                    with SplitPane():
                        segment_containers.append(SplitPanes(orientation=child_axis))

        for curr_count, curr_container in zip(main_axis_counts, segment_containers):
            with curr_container as c:
                _ = c.classes('fullscreen-paneview')
                panes.extend(
                    SplitPane()
                    for _ in range(curr_count))

        self.current_layout_type = 'panes'
        self._panes = tuple(panes)
        return self._panes

    def _make_children_orphans(self):
        '''
        Result: self._panes is cleared
        and items in self._children are top-level
        in self.
        '''
        for orphan in self._children:
            orphan.move(self)
        for orphan_holder in self._panes:
            orphan_holder.delete()
        for element in self.default_slot.children:
            if isinstance(element, SplitPanes):
                element.delete()
        self._panes = ()
        return self._children
