# -*- coding: utf-8 -*-
"""
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import auto
from typing import (
    TypeVar,
    Generic,
    Any,
    Optional,
    Self,
    Mapping,
    Sequence,
    Iterable,
)

T = TypeVar("T")
"""Item type returned from a loader."""
Q = TypeVar("Q")
"""Query type internally used by a loader."""


class SortDirection:
    """Specify direction of sorting."""

    ASC = auto()
    """From the lowest to the highest value."""
    DESC = auto()
    """From the highest to the lowest value."""
    UNSPECIFIED = auto()
    """No direction modifier specified."""


class LoaderSpecPiece:
    """Represent piece of loader spec. Each loader piece have list of its requirement."""

    def __init__(self, required_extensions: Optional[Iterable[str]] = None):
        self._required_extensions = list(required_extensions or [])

    @property
    def required_extensions(self) -> Sequence[str]:
        return self._required_extensions


class LoaderExtension(LoaderSpecPiece, ABC, Generic[Q]):
    """Represent loader extension (e.g. joins etc)."""

    @abstractmethod
    def apply_extension(self, query: Q) -> Q:
        """Apply the extension to the `query`."""
        pass


class QueryFilter(LoaderSpecPiece, ABC, Generic[Q]):
    """Apply filtration condition(s) to a query."""

    @abstractmethod
    def apply_filter(self, query: Q, reference_value: Optional[Any]) -> Q:
        """Apply the filtration condition specified by instance to the `query`."""
        pass


class QuerySort(LoaderSpecPiece, ABC, Generic[Q]):
    """Apply sorting to a query."""

    @abstractmethod
    def apply_sorting(self, query: Q, direction: SortDirection) -> Q:
        """Apply sorting to the `query`."""
        pass


@dataclass()
class DefaultSort:
    sort: str
    """Name of the sort field in the spec."""

    direction: SortDirection = SortDirection.UNSPECIFIED
    """Direction of sort."""

    @classmethod
    def from_string(cls, sort: str) -> Self:
        """Create instance from name of the sort field."""
        return cls(sort)


@dataclass()
class LoaderSpec(Generic[Q]):
    """Specification of available filters and sorts for loader."""

    sortable_fields: Mapping[str, QuerySort[Q]]
    """The key is field name and value is sort definition."""

    default_sort_by: Sequence[DefaultSort]
    """List of sorts used if no other sorts are specified."""

    filterable_fields: Mapping[str, Mapping[str, QueryFilter[Q]]]
    """Contain two nested mappings:
    
    The top level mapping is mapping from the field name (key) to lookup of operators (values).
    The second level mapping is operator lookup - the key is operator name (e.g. "eq", "lt", "like", ...) and value is
    instance of the `QueryFilter`.
    """

    extensions: Sequence[str, LoaderExtension[Q]]
    """The key is extension name and value is extension itself."""

    def clone(self) -> LoaderSpec[Q]:
        return LoaderSpec(
            sortable_fields=dict(self.sortable_fields),
            default_sort_by=list(self.default_sort_by),
            filterable_fields={
                field: dict(filters)
                for field, filters in self.filterable_fields.items()
            },
            extensions=list(self.extensions),
        )


class Loader(ABC, Generic[T]):
    """Base class for all loaders."""

    @abstractmethod
    def __next__(self) -> T:
        """Iterate over"""

    @abstractmethod
    def __len__(self) -> int:
        """Get total count of items available in the loader"""


class LoaderBuilder(ABC, Generic[T]):
    """Create instances of data loaders."""

    @abstractmethod
    def build(self) -> Loader[T]:
        """Build new `Loader` instance."""
        pass


class ConfigurableLoaderBuilder(LoaderBuilder, ABC, Generic[T]):
    """Extend the `LoaderBuilder` by build configuration methods."""

    @abstractmethod
    def apply_extension(self, extension_name: str) -> None:
        """Manually apply extension to the query.

        Raises:
            ExtensionNotFound: There is no extension of given name
        """
        pass

    @abstractmethod
    def add_sort(
        self, field: str, direction: SortDirection, options: Optional[Any] = None
    ):
        """Add sort requirement to the configuration.

        Raises:
            ExtensionNotFound: There is no sort definition for the field of given name
        """
        pass

    @abstractmethod
    def add_filter(
        self, field: str, operator: str, reference_value: Optional[Any] = None
    ) -> None:
        """Add filter requirement to the configuration.

        Raises:
            ExtensionNotFound: There is no filter definition for the field of given name supporting given operator.
        """
        pass

    @abstractmethod
    def set_offset(self, offset: int) -> None:
        """Set offset in row set where to start."""
        pass

    @abstractmethod
    def set_limit(self, limit: int) -> None:
        """Set max number of items to be returned."""
        pass

    def set_page(self, page: int, items_per_page: int) -> None:
        """Shorthand for calling `set_offset` and `set_limit` method when using pagination."""
        self.set_limit(items_per_page)
        self.set_offset(page * items_per_page)