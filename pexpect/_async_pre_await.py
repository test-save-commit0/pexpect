"""Implementation of coroutines without using ``async def``/``await`` keywords.

``@asyncio.coroutine`` and ``yield from`` are  used here instead.
"""
import asyncio
import errno
import signal
from pexpect import EOF


class PatternWaiter(asyncio.Protocol):
    transport = None
