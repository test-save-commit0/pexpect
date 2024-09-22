"""Implementation of coroutines using ``async def``/``await`` keywords.

These keywords replaced ``@asyncio.coroutine`` and ``yield from`` from
Python 3.5 onwards.
"""
import asyncio
import errno
import signal
from sys import version_info as py_version_info
from pexpect import EOF
if py_version_info >= (3, 7):
    _loop_getter = asyncio.get_running_loop
else:
    _loop_getter = asyncio.get_event_loop


class PatternWaiter(asyncio.Protocol):
    transport = None
