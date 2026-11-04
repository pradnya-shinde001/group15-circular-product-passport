"""The building blocks of the pipeline."""
from abc import ABC, abstractmethod
from datetime import date


def get_event_date(event):
    """The day the event happened, or None if the date is not valid."""
    text = event.get_details().get("date", event.get_timestamp())
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


# CONCEPT: iterator. __iter__ and __next__ make `for event in stream` work.
class EventStream:
    def __init__(self, events):
        self.events = events
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.position >= len(self.events):
            raise StopIteration
        event = self.events[self.position]
        self.position += 1
        return event


# CONCEPT: abstract base class. Every step must have its own process().
class StreamProcessor(ABC):
    @abstractmethod
    def process(self, record):
        """Return the record to pass it on, or None to drop it."""

    # CONCEPT: operator overloading. step_a | step_b makes a Pipeline.
    def __or__(self, other):
        return Pipeline(self, other)


# CONCEPT: inheritance. A filter is a kind of step.
class FilterProcessor(StreamProcessor):
    reason = "not allowed"

    @abstractmethod
    def keep(self, record):
        """Return True to keep the record, or False to drop it."""

    def process(self, record):
        if self.keep(record):
            return record
        print(f"   Dropped {record['event'].get_event_type()}: {self.reason}")
        return None


# CONCEPT: inheritance. A transform is also a kind of step.
class TransformProcessor(StreamProcessor):
    @abstractmethod
    def transform(self, record):
        """Add new values to the record."""

    def process(self, record):
        self.transform(record)
        return record


class Pipeline(StreamProcessor):
    def __init__(self, *steps):
        self.steps = steps

    def __or__(self, other):
        return Pipeline(*self.steps, other)

    def process(self, record):
        for step in self.steps:
            record = step.process(record)    # CONCEPT: polymorphism. Same call for every step.
            if record is None:
                return None
        return record

    # CONCEPT: generator. yield gives back one result, then waits.
    def run(self, stream):
        for event in stream:
            record = {"event": event, "date": get_event_date(event)}
            result = self.process(record)
            if result is not None:
                yield result
