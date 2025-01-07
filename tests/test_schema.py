import pytest
from sqlglot import expressions as exp

from mysql_mimic.results import ensure_result_set
from mysql_mimic.schema import (
    Column,
    InfoSchema,
    mapping_to_columns,
    show_statement_to_info_schema_query,
)
from mysql_mimic.utils import aiterate


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
    input_columns = [
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
    schema = InfoSchema.from_columns(columns=input_columns)
    table_query = show_statement_to_info_schema_query(exp.Show(this="TABLES"), "my_db")
    result_set = await ensure_result_set(await schema.query(table_query))
    table_names = [row[0] async for row in aiterate(result_set.rows)]
    assert table_names == ["table_1", "table_2"]

    column_query = show_statement_to_info_schema_query(
        exp.Show(this="COLUMNS", full=True, target="table_1"), "my_db"
    )
    column_results = await ensure_result_set(await schema.query(column_query))
    columns = [row async for row in aiterate(column_results.rows)]
    assert columns == [
        (
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
    ]
