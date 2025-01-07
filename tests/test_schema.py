import pytest
from sqlglot import Expression
from sqlglot import expressions as exp
import sqlglot

from mysql_mimic.schema import (
    Column,
    InfoSchema,
    mapping_to_columns,
    show_statement_to_info_schema_query,
)


@pytest.mark.asyncio
def test_mapping_to_columns() -> None:
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


@pytest.mark.asyncio
async def test_info_schema_from_columns() -> None:
    columns = [
        Column(
            name="col_1",
            type="TEXT",
            table="table_1",
            schema="my_db",
            catalog="def",
            comment="This is a comment",
        ),
        Column(
            name="col_1", type="TEXT", table="table_2", schema="my_db", catalog="def"
        ),
    ]
    schema = InfoSchema.from_columns(columns=columns)
    table_query = show_statement_to_info_schema_query(exp.Show(this="TABLES"), "my_db")
    tables, _ = await schema.query(table_query)
    assert tables[0][0] == "table_1"
    assert tables[1][0] == "table_2"

    column_query = show_statement_to_info_schema_query(
        exp.Show(this="COLUMNS", full=True, target="table_1"), "my_db"
    )
    columns, _ = await schema.query(column_query)
    assert columns[0] == (
        "col_1",
        "TEXT",
        "YES",
        None,
        None,
        None,
        "NULL",
        None,
        "This is a comment",
    )
