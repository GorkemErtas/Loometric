"""Bounded, strict JSON without passing planning numbers through binary floats."""

import json
from decimal import Decimal
from typing import Any

from loometric.api.errors import ApiError, complexity_error
from loometric.api.settings import Limits
from loometric.planning.loading import parse_json
from loometric.planning.validation import PlanningError


def decode_body(source: str, limits: Limits) -> Any:
    # Count nesting before the recursive stdlib decoder; strings/escapes are opaque.
    depth, quoted, escaped = 0, False, False
    for char in source:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > limits.max_depth:
                raise complexity_error()
        elif char in "]}":
            depth -= 1
    try:
        value = parse_json(source)
    except (PlanningError, ValueError, RecursionError):
        raise ApiError(
            400, "INVALID_JSON", "Expected strict UTF-8 JSON with unique keys."
        ) from None
    pending, nodes = [value], 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > limits.max_nodes:
            raise complexity_error()
        if isinstance(item, dict):
            if len(item) > limits.max_collection_items:
                raise complexity_error()
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            if len(item) > limits.max_collection_items:
                raise complexity_error()
            pending.extend(item)
        elif isinstance(item, str):
            if len(item) > limits.max_string_length:
                raise complexity_error()
        elif type(item) is int:
            if len(str(item)) > limits.max_number_length:
                raise complexity_error()
        elif isinstance(item, Decimal):
            if (
                not item.is_finite()
                or len(item.as_tuple().digits) > limits.max_number_length
                or abs(item.as_tuple().exponent) > limits.max_decimal_exponent
            ):
                raise complexity_error()
    return value


def input_json(value: Any) -> str:
    """Re-encode decoded input for existing parsers, retaining exact number tokens."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite input number.")
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + ":" + input_json(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(input_json(v) for v in value) + "]"
    if isinstance(value, float):
        raise ValueError("Binary floats are not planning input values.")
    return json.dumps(value, allow_nan=False)
