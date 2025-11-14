import asyncio
import re
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass
from random import getrandbits
from typing import Any, Callable

from nicegui.element import Element


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

# region Async

async def wait_for_event[T0, *T, _, *U, __](
    callback_register_func: Callable[
        [
            Callable[[T0, *T], None],
        ],
        _
    ],
    error_register_func: Callable[
        [
            Callable[[*U], None]
        ],
        __
    ] | None = None
) -> tuple[T0, *T]:

    awaitable: asyncio.Future[tuple[T0, *T]]
    awaitable = asyncio.get_running_loop().create_future()
    event_done = False
    def event_callback(a: T0, *args: *T, **kwargs):
        nonlocal event_done, awaitable
        args_tuple = (a, *args, *kwargs.values())
        if not event_done:
            event_done = True
            awaitable.set_result(args_tuple)
    _ = callback_register_func(event_callback)

    if error_register_func is None:
        return await awaitable

    def event_error_callback(*args: *U, **kwargs):
        nonlocal event_done, awaitable
        if not event_done:
            event_done = True
            exception_data = (args, kwargs)
            awaitable.set_exception(
                Exception(exception_data)
            )
    _ = error_register_func(event_error_callback)

    return await awaitable

def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    '''
    Run in current event loop (i.e. nicegui)
    *or* a new one if none available.
    '''
    try:
        _ = asyncio.create_task(coro)
    except RuntimeError:
        with asyncio.Runner() as runner:
            runner.run(coro)

class DebouncedRunner:
    def __init__(self, min_interval: float):
        ''' min_interval: seconds, minimum delay before a task is run '''
        self.min_interval = min_interval
        self.current_task: asyncio.Task[None] | None = None

    def cancel_all(self):
        if self.current_task is not None:
            _ = self.current_task.cancel()

    def __call__(self, task: Callable[[], None] | Awaitable[None]):
        '''
        If `task` is awaitable, call as follows:
        `run_debounceable(foo_task())`
        '''

        if self.current_task is not None:
            _ = self.current_task.cancel() # if already done, does nothing

        async def debounce_task():
            await asyncio.sleep(self.min_interval)
            if isinstance(task, Awaitable):
                await task
            else:
                task()
        self.current_task = run_async(debounce_task())

def wrap_async[**P, RT](async_func: Callable[P, Coroutine[Any, Any, RT]]) -> Callable[P, RT]:
    '''
    Call this method in a function with an
    event loop.

    When the returned callback is called,
    it will execute `coro` in the same event
    loop as the original method caller.

    The callback blocks synchronously, so it
    must be called by a separate thread
    (e.g. nicegui.run.io_bound).

    Note that the original thread runs `coro`
    asynchronously, so it does not block.
    '''
    loop = asyncio.get_event_loop()
    def blocking_func(*args: P.args, **kwargs: P.kwargs):
        fut = asyncio.run_coroutine_threadsafe(
            async_func(*args, **kwargs),
            loop
        )
        return fut.result() # synchronous block occurs here
    return blocking_func

# endregion Async
# region HTML/GUI

def set_light_dark[*P](element: Element, on_resolve: Callable[[Element, *P], Any], if_light: tuple[*P], if_dark: tuple[*P]) -> None:
    async def async_by_light_dark(element: Element, on_resolve: Callable[[Element, *P], Any], if_light: tuple[*P], if_dark: tuple[*P]):
        dark_background = await element.get_computed_prop('dark')
        if dark_background:
            on_resolve(element, *if_dark)
        else:
            on_resolve(element, *if_light)

    run_async(async_by_light_dark(element, on_resolve, if_light, if_dark))

def unique_readable_html_safe(char_length: int = 5):
    # char_bit_size = 5
    # char_max_val + 1 = 32

    unique_bits = getrandbits(char_length * 5)

    result = list[str]()
    for _ in range(char_length):
        bit_chunk = unique_bits & ( (1 << 5) - 1 )
        unique_bits >>= 5

        if bit_chunk < 26:
            char = chr(bit_chunk + ord('a'))
            result.append(char)
        else:
            bit_chunk -= 26
            char = ('A', 'E', 'I', 'O', 'U', 'Y')[bit_chunk]
            result.append(char)

    return ''.join(result)

def truncate_exception_to_html(exception: Exception):
    lines = str(exception).splitlines()
    truncate_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if 'traceback' in line.lower()
        ),
        10
    )
    truncated_html = '<br>'.join(
        [
            line[:100] + ('...' if len(line) > 100 else '')
            for line in lines[:truncate_idx]
        ] + (
            ['...', ]
            if len(lines) > truncate_idx else []
        )
    )
    return truncated_html

def kebab_case(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

# endregion HTML/GUI