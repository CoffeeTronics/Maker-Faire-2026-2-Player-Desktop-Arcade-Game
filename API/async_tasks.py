"""
async_tasks.py — Asyncio Task Runner
=======================================
Board: Dev Board

Provides a lightweight wrapper around CircuitPython's asyncio module for
running multiple concurrent tasks.  Simplifies the common pattern of
creating several tasks and gathering them.

Software Dependencies
---------------------
  asyncio — must be copied into /lib on the CIRCUITPY drive

Use this module for:
  - Running multiple hardware animations or sensor reads concurrently
  - Periodic background tasks alongside a main loop
  - Any situation where you need cooperative multitasking
"""

import asyncio


class AsyncRunner:
    """Collect and run async tasks concurrently.

    Example — Blink five NeoPixels at different rates
    --------------------------------------------------
import pykit_explorer
import random
from neopixels import NeoPixels, OFF
from async_tasks import AsyncRunner
pixels = NeoPixels()

async def blink(pixel, interval, count, color):
    for _ in range(count):
        pixels.set(pixel,color, True)
        await AsyncRunner.sleep(interval)
        pixels.set(pixel, OFF)
        await AsyncRunner.sleep(interval)

runner = AsyncRunner()
runner.add(blink(0, 0.30, 15, (random.randrange(255), random.randrange(255), random.randrange(255))))
runner.add(blink(1, 0.75, 10, (0, 255, 0)))
runner.add(blink(2, 1.00, 10, (255, 0, 0)))
runner.add(blink(3, 0.50, 10, (255, 150, 0)))
runner.add(blink(4, 0.25, 15, (0, 0, 255)))
runner.run()

    """

    def __init__(self):
        self._coros = []

    def add(self, coro):
        """Add a coroutine to be run concurrently.

        Parameters
        ----------
        coro : an awaitable coroutine (the result of calling an async function)
        """
        self._coros.append(coro)

    @staticmethod
    async def sleep(seconds: float):
        """Async sleep — use this instead of time.sleep() inside coroutines.

        Parameters
        ----------
        seconds : float
            Number of seconds to sleep.
        """
        await asyncio.sleep(seconds)

    def run(self):
        """Run all added coroutines concurrently and block until they complete."""
        async def _main():
            tasks = [asyncio.create_task(c) for c in self._coros]
            await asyncio.gather(*tasks)
        asyncio.run(_main())
        self._coros.clear()
