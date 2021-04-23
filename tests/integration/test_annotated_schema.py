from dataclasses import dataclass, field

from graphql.utilities import print_schema

from apischema import schema, schema_ref
from apischema.graphql import graphql_schema
from apischema.json_schema import deserialization_schema, serialization_schema
from apischema.typing import Annotated


@dataclass
class A:
    a: Annotated[
        int,
        schema(max=10),
        schema(description="type description"),
        schema_ref("some_int"),
        schema(description="field description"),
    ] = field(metadata=schema(min=0))


def a() -> A:
    ...


def test_annotated_schema():
    assert (
        deserialization_schema(A)
        == serialization_schema(A)
        == {
            "$schema": "http://json-schema.org/draft/2019-09/schema#",
            "type": "object",
            "properties": {
                "a": {
                    "type": "integer",
                    "maximum": 10,
                    "minimum": 0,
                    "description": "field description",
                }
            },
            "required": ["a"],
            "additionalProperties": False,
        }
    )
    assert (
        deserialization_schema(A, all_refs=True)
        == serialization_schema(A, all_refs=True)
        == {
            "$schema": "http://json-schema.org/draft/2019-09/schema#",
            "$ref": "#/$defs/A",
            "$defs": {
                "A": {
                    "additionalProperties": False,
                    "properties": {
                        "a": {
                            "$ref": "#/$defs/some_int",
                            "description": "field description",
                            "minimum": 0,
                        }
                    },
                    "required": ["a"],
                    "type": "object",
                },
                "some_int": {
                    "description": "type description",
                    "maximum": 10,
                    "type": "integer",
                },
            },
        }
    )
    assert (
        print_schema(graphql_schema(query=[a]))
        == '''\
type Query {
  a: A!
}

type A {
  """field description"""
  a: some_int!
}

"""type description"""
scalar some_int
'''
    )