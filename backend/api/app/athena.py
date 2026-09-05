import re
import time
from math import isfinite

import boto3
from flask import current_app

from .errors import ApiError


SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,254}$")


def _identifier(value):
    if not SAFE_IDENTIFIER.fullmatch(value or ""):
        raise ApiError("The dataset query metadata is invalid.", 500, "INVALID_QUERY_METADATA")
    return f'"{value}"'


def _string_literal(value):
    return "'" + value.replace("'", "''") + "'"


def build_query(table_name, athena_columns, selected_column, operator, value):
    table = _identifier(table_name)
    columns = [_identifier(item["name"]) for item in athena_columns]
    selected = _identifier(selected_column)

    if operator == "empty":
        condition = f"trim(COALESCE({selected}, '')) = ''"
    elif operator == "equals":
        condition = f"lower(COALESCE({selected}, '')) = lower({_string_literal(value)})"
    elif operator == "contains":
        condition = f"strpos(lower(COALESCE({selected}, '')), lower({_string_literal(value)})) > 0"
    else:
        try:
            numeric_value = float(value)
        except ValueError as error:
            raise ApiError("Enter a numeric value for this operator.", 400, "INVALID_QUERY_VALUE") from error
        if not isfinite(numeric_value):
            raise ApiError("Enter a finite numeric value for this operator.", 400, "INVALID_QUERY_VALUE")
        comparison = ">" if operator == "greater" else "<"
        condition = f"TRY_CAST({selected} AS DOUBLE) {comparison} {numeric_value!r}"

    projection = ", ".join(columns)
    return (
        f"SELECT {projection}, COUNT(*) OVER() AS \"__csv_insight_total\" "
        f"FROM {table} WHERE {condition} LIMIT 100"
    )


def run_query(table_name, athena_columns, selected_column, operator, value):
    query = build_query(table_name, athena_columns, selected_column, operator, value)
    client = boto3.client("athena", region_name=current_app.config["AWS_REGION"])
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": current_app.config["ATHENA_DATABASE"]},
        ResultConfiguration={"OutputLocation": current_app.config["ATHENA_OUTPUT_LOCATION"]},
        WorkGroup=current_app.config["ATHENA_WORKGROUP"],
    )
    execution_id = response["QueryExecutionId"]
    deadline = time.monotonic() + current_app.config["ATHENA_QUERY_TIMEOUT_SECONDS"]
    while time.monotonic() < deadline:
        execution = client.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            reason = execution["Status"].get("StateChangeReason", "Athena could not complete the query.")
            current_app.logger.error("Athena query %s failed: %s", execution_id, reason)
            raise ApiError("The dataset query could not be completed.", 502, "ATHENA_QUERY_FAILED")
        time.sleep(0.25)
    else:
        client.stop_query_execution(QueryExecutionId=execution_id)
        raise ApiError("The dataset query timed out.", 504, "ATHENA_QUERY_TIMEOUT")

    result = client.get_query_results(QueryExecutionId=execution_id, MaxResults=101)["ResultSet"]
    raw_rows = result.get("Rows", [])
    rows = []
    count = 0
    for raw_row in raw_rows[1:]:
        values = [cell.get("VarCharValue", "") for cell in raw_row.get("Data", [])]
        values.extend([""] * (len(athena_columns) + 1 - len(values)))
        if values[-1]:
            count = int(values[-1])
        rows.append(values[:-1])
    return rows, count
