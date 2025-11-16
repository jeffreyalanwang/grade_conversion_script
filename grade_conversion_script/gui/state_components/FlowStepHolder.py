from collections import Counter
from collections.abc import Sequence
from typing import Callable, Final, NamedTuple

from grade_conversion_script.gui.state_components import UxFlow
from grade_conversion_script.util.funcs import tuple_insert


class LinkingCallbacks(NamedTuple):
    modifying_prev_step: Callable[[UxFlow.State], None]
    modifying_next_step: Callable[[UxFlow.State], None]

class FlowStepHolder:
    '''
    Manage a sequence of FlowStepElements,
    triggering each on the completion of its previous.
    '''
    def __init__(self, steps: Sequence[UxFlow.FlowStepElement], *args, **kwargs):
        super().__init__(*args, **kwargs)

        # support for add_sibling
        self._birthed_sibling_count: Final = Counter[UxFlow.FlowStepElement]()

        self.steps: tuple[UxFlow.FlowStepElement, ...] = tuple(steps)

        self.steps[0].set_state_immediately(UxFlow.State.START_READY)
        for step in self.steps[1:]:
            step.set_state_immediately(UxFlow.State.NOT_START_READY)

        # Link steps' states
        self.step_state_callbacks: Final = dict[UxFlow.FlowStepElement, LinkingCallbacks]()
        for i, step in enumerate(self.steps):
            callbacks = self._generate_state_change_callbacks(
                prev_step= self.steps[i - 1] if i > 0 else None,
                next_step= self.steps[i + 1] if i + 1 < len(self.steps) else None,)
            self._set_state_change_callbacks(step, *callbacks)

        # Setup state changes for FlowStepInputElement.
        for step in self.steps:
            if isinstance(step, UxFlow.FlowStepInputElement):
                self._bind_element_inputs(step)

    def _bind_element_inputs(self, step: UxFlow.FlowStepElement) -> None:
        ''' Input binding only occurs once, at __init__ time. '''
        assert isinstance(step, UxFlow.FlowStepInputElement)
        raise NotImplementedError(f"Unrecognized flow step takes input data: {step}")

    def _generate_state_change_callbacks(self,
        prev_step: UxFlow.FlowStepElement | None,
        next_step: UxFlow.FlowStepElement | None,
    ) -> LinkingCallbacks:
        # Note: Python uses late binding; however,
        # function scope does not change values of
        # prev_step or next_step, so `prev_step` and
        # `next_step` may be considered early-bound.
        def callback_modifying_prev_step(new_state: UxFlow.State):
            if not prev_step:
                return
            if new_state.requires_continue:
                prev_step.set_state_immediately(
                    prev_step.state.with_continue_required(True),)
            elif new_state.allows_start:
                prev_step.set_state_debounced(
                    prev_step.state.with_continue_required(False), )
            else: pass
        def callback_modifying_next_step(new_state: UxFlow.State):
            if not next_step:
                return
            if new_state.allows_continue:
                next_step.set_state_debounced(
                    next_step.state.with_start_allowed(True),)
            else:
                next_step.set_state_immediately(
                    next_step.state.with_start_allowed(False),)
        return LinkingCallbacks(
            callback_modifying_prev_step,
            callback_modifying_next_step, )

    def _set_state_change_callbacks(self,
        step: UxFlow.FlowStepElement,
        modifying_prev_step: Callable[[UxFlow.State], None] | None,
        modifying_next_step: Callable[[UxFlow.State], None] | None,
    ):
        '''
        Updates one backward- and one forwarding-linking callback
        on `step` and also registers them (so they can be replaced later).
        If arg is None, that callback is not modified.
        '''
        old_callbacks = self.step_state_callbacks.get(step, None)
        final_prev_step_modifier = old_callbacks.modifying_prev_step if old_callbacks else None
        final_next_step_modifier = old_callbacks.modifying_next_step if old_callbacks else None

        if modifying_prev_step:
            final_prev_step_modifier = modifying_prev_step
            if old_callbacks:
                step.on_state_changed.unsubscribe(old_callbacks.modifying_prev_step)
            step.on_state_changed.subscribe(modifying_prev_step)
        if modifying_next_step:
            final_next_step_modifier = modifying_next_step
            if old_callbacks:
                step.on_state_changed.unsubscribe(old_callbacks.modifying_next_step)
            step.on_state_changed.subscribe(modifying_next_step)

        assert final_prev_step_modifier and final_next_step_modifier
        self.step_state_callbacks[step] = LinkingCallbacks(
            final_prev_step_modifier,
            final_next_step_modifier,)

    def add_child_sibling(self, new_sibling: UxFlow.FlowStepElement, for_child: UxFlow.FlowStepElement) -> None:
        assert for_child in self.steps
        self._birthed_sibling_count[for_child] += 1
        index = self.steps.index(for_child) + self._birthed_sibling_count[for_child]
        self.add_flow_step(new_sibling, index)

    def get_step[T: UxFlow.FlowStepElement](self, cls: type[T]) -> T:
        for item in self.steps:
            if isinstance(item, cls):
                return item
        raise ValueError(f"No member was instance of {cls} in iterable: {iter}")

    def add_flow_step(self, element: UxFlow.FlowStepElement, position: int) -> None:
        self.steps = tuple_insert(position, element, self.steps)

        if isinstance(element, UxFlow.FlowStepInputElement):
            self._bind_element_inputs(element)

        prev_element = self.steps[position - 1] if position > 0 else None
        curr_element = element
        next_element = self.steps[position + 1] if position + 1 < len(self.steps) else None

        # Link the three steps' states

        if prev_element: # only change the callback modifying the next element
            generated_callbacks = self._generate_state_change_callbacks(
                prev_step=None,
                next_step=curr_element,)
            self._set_state_change_callbacks(
                step = prev_element,
                modifying_prev_step = None,
                modifying_next_step = generated_callbacks.modifying_next_step,)

        generated_callbacks = self._generate_state_change_callbacks(prev_element, next_element)
        self._set_state_change_callbacks(element, *generated_callbacks)

        if next_element: # only change the callback modifying the prev element
            generated_callbacks = self._generate_state_change_callbacks(
                prev_step=curr_element,
                next_step=None,)
            self._set_state_change_callbacks(
                step = next_element,
                modifying_prev_step = generated_callbacks.modifying_prev_step,
                modifying_next_step = None,)

        # Manually trigger state changes once now

        if not prev_element:
            element.set_state_immediately(element.state.with_start_allowed(True))
        else:
            prev_element_callback = self.step_state_callbacks[prev_element].modifying_prev_step
            prev_element_callback(prev_element.state)

    def __str__(self):
        header = type(self).__name__
        steps_info = list[dict[str, str]]()
        for step in self.steps:
            step_info = dict[str, str]()
            step_info['name'] = type(step).__name__
            step_info['state'] = step.state.name
            if isinstance(step, UxFlow.FlowStepInputElement):
                step_info['input value'] = str(step.inputs is not None)
            if isinstance(step, UxFlow.FlowStepDataElement):
                step_info['data produced'] = type(step.data).__name__ if step.data else str(step.data)
            steps_info.append(step_info)
        item_state_descriptions = (f"{i}: {d.pop('name')} {d}"
                                    for i, d in enumerate(steps_info))
        return '\n'.join([header, *item_state_descriptions])