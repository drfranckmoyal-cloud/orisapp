"""Appel des fournisseurs asynchrones depuis les routes synchrones (threadpool)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import anyio.from_thread


def run[T](function: Callable[[], Awaitable[T]]) -> T:
    async def call() -> T:
        return await function()

    try:
        return anyio.from_thread.run(call)
    except RuntimeError:  # hors d'un thread géré par anyio (scripts, tests unitaires)
        return asyncio.run(call())
