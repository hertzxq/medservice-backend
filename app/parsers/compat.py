"""
Helper to run Playwright (async) code on Windows.

Uvicorn on Windows uses SelectorEventLoop which does NOT support
subprocess creation (asyncio.create_subprocess_exec).  Playwright
needs subprocesses.  This module provides a helper that runs an
async coroutine in a *new* ProactorEventLoop inside a separate thread.
"""

import asyncio
import sys
import threading
from typing import Any, Coroutine


def _thread_runner(coro: Coroutine, result_holder: list, exc_holder: list) -> None:
    """Target for the background thread — creates a new event loop
    with subprocess support and runs the coroutine there."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()          # supports subprocesses
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        result_holder.append(loop.run_until_complete(coro))
    except Exception as exc:          # noqa: BLE001
        exc_holder.append(exc)
    finally:
        loop.close()


async def run_in_playwright_loop(coro: Coroutine) -> Any:
    """Await *coro* that uses Playwright by running it in a dedicated thread
    with a Proactor event loop (Windows-safe).

    Usage::

        result = await run_in_playwright_loop(some_parser.parse_by_url(url))
    """
    result: list = []
    exception: list = []

    thread = threading.Thread(
        target=_thread_runner,
        args=(coro, result, exception),
        daemon=True,
    )
    thread.start()

    # Wait for the thread without blocking uvicorn's event loop
    await asyncio.get_event_loop().run_in_executor(None, thread.join)

    if exception:
        raise exception[0]
    return result[0] if result else None
