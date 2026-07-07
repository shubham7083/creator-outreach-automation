from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, stop_after_attempt, wait_exponential

TCallable = TypeVar("TCallable", bound=Callable[..., object])


def retry_transient(max_attempts: int = 3) -> Callable[[TCallable], TCallable]:
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
