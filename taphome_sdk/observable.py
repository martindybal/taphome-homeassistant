"""Generic Event type and an ObservableValue."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, ParamSpec, Self, TypeVar

P = ParamSpec("P")


class Event(Generic[P]):
    """Publishes events carrying P arguments to registered handlers."""

    def __init__(self) -> None:
        """Initialize an empty set of event handlers."""
        self._handlers: set[Callable[P, None]] = set()
        self._last_args: tuple[Any, ...] | None = None
        self._last_kwargs: dict[str, Any] | None = None

    def __iadd__(self, handler: Callable[P, None]) -> Self:
        """Register a new event handler using '+=' operator."""
        return self.subscribe(handler)

    def __add__(self, handler: Callable[P, None]) -> Self:
        """Register a new event handler using '+' operator."""
        return self.subscribe(handler)

    def __isub__(self, handler: Callable[P, None]) -> Self:
        """Unregister an event handler using '-=' operator."""
        return self.unsubscribe(handler)

    def __sub__(self, handler: Callable[P, None]) -> Self:
        """Unregister an event handler using '-' operator."""
        return self.unsubscribe(handler)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        """Invoke all registered handlers with the given arguments."""
        self._last_args = args
        self._last_kwargs = kwargs
        for h in list(self._handlers):
            h(*args, **kwargs)

    def subscribe(self, handler: Callable[P, None]) -> Self:
        """Register a new event handler."""
        self._handlers.add(handler)
        if self._last_args is not None and self._last_kwargs is not None:
            handler(*self._last_args, **self._last_kwargs)
        return self

    def unsubscribe(self, handler: Callable[P, None]) -> Self:
        """Unregister an event handler."""
        self._handlers.discard(handler)
        return self


T = TypeVar("T")


class ObservableValue(Generic[T]):
    """Represents a value that notifies subscribers upon changes."""

    changed: Event[T, T]

    def __init__(self, initial: T) -> None:
        """Initialize with the given initial value and create the event."""
        self._value: T = initial
        self.changed = Event()
        self.changed(initial, initial)

    @property
    def value(self) -> T:
        """Get the current value."""
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set a new value and notify subscribers of the change."""
        old_value = self._value
        if old_value != new_value:
            self._value = new_value
            self.changed(old_value, new_value)
