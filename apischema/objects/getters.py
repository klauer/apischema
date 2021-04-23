from dataclasses import Field
from typing import (
    Any,
    Iterable,
    Mapping,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from apischema.cache import cache
from apischema.objects.fields import ObjectField
from apischema.objects.visitor import ObjectVisitor
from apischema.types import AnyType, OrderedDict
from apischema.typing import _GenericAlias
from apischema.visitor import Unsupported


class GetFields(ObjectVisitor[Sequence[ObjectField]]):
    def __init__(self, serialization: bool):
        super().__init__()
        self.serialization = serialization

    def _fields(
        self,
        fields: Sequence[Field],
        init_vars: Sequence[Field],
    ) -> Iterable[Field]:
        return fields if self.serialization else (*fields, *init_vars)

    def object(self, cls: Type, fields: Sequence[ObjectField]) -> Sequence[ObjectField]:
        return fields


@cache
def object_fields(
    tp: AnyType, *, serialization: bool = False
) -> Mapping[str, ObjectField]:
    try:
        return OrderedDict((f.name, f) for f in GetFields(serialization).visit(tp))
    except Unsupported:
        raise TypeError(f"{tp} doesn't have fields")


def object_fields2(obj: Any, serialization: bool = False) -> Mapping[str, ObjectField]:
    return object_fields(
        obj if isinstance(obj, (type, _GenericAlias)) else obj.__class__,
        serialization=serialization,
    )


T = TypeVar("T")


class FieldGetter:
    def __init__(self, obj: Any):
        self.fields = object_fields2(obj)

    def __getattribute__(self, name: str) -> ObjectField:
        try:
            return object.__getattribute__(self, "fields")[name]
        except KeyError:
            raise AttributeError(name)


@overload
def get_field(obj: Type[T]) -> T:
    ...


@overload
def get_field(obj: T) -> T:
    ...


# Overload because of Mypy issue
# https://github.com/python/mypy/issues/9003#issuecomment-667418520
def get_field(obj: Union[Type[T], T]) -> T:
    return cast(T, FieldGetter(obj))


class AliasGetter:
    def __init__(self, obj: Any):
        self.fields = object_fields2(obj)

    def __getattribute__(self, name: str) -> str:
        try:
            return object.__getattribute__(self, "fields")[name].alias
        except KeyError:
            raise AttributeError(name)


@overload
def get_alias(obj: Type[T]) -> T:
    ...


@overload
def get_alias(obj: T) -> T:
    ...


def get_alias(obj: Union[Type[T], T]) -> T:
    return cast(T, AliasGetter(obj))