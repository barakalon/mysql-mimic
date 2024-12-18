from mysql_mimic.schema import Column, mapping_to_columns
import pytest


@pytest.mark.asyncio
def test_schema_type_only() -> None:
    schema = {
        "table_1": {
            "col_1": "TEXT",
            "col_2": "INT",
        }
    }

    columns = mapping_to_columns(schema=schema)

    assert columns[0] == Column(
        name="col_1", type="TEXT", table="table_1", schema="", catalog="def"
    )
    assert columns[1] == Column(
        name="col_2", type="INT", table="table_1", schema="", catalog="def"
    )


def test_schema_with_col_metadata() -> None:
    schema = {
        "table_1": {
            "col_1": {"type": "TEXT", "comment": "this is a comment", "default": "default"},
            "col_2": {"type": "INT", "comment": "this is another comment"},
            "col_3": {"type": "DOUBLE", "comment": "comment", "is_nullable": False}
        }
    }

    columns = mapping_to_columns(schema=schema)

    assert columns[0] == Column(
        name="col_1",
        type="TEXT",
        table="table_1",
        schema="",
        catalog="def",
        comment="this is a comment",
        default="default"
    )
    assert columns[1] == Column(
        name="col_2",
        type="INT",
        table="table_1",
        schema="",
        catalog="def",
        comment="this is another comment",
    )

    assert columns[2] == Column(
        name="col_3",
        type="DOUBLE",
        table="table_1",
        schema="",
        catalog="def",
        comment="comment",
        is_nullable=False,
    )
