#!/usr/bin/env python3
"""Generate deterministic Python and TypeScript clients from the pinned release."""

from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from common import LOCK_PATH, ROOT, SNAPSHOT_ROOT, canonical_json_bytes, load_json, sha256_bytes
from verify_contract_lock import verify


GENERATOR_VERSION = "planeon-contract-generator-v1"
PYTHON_GENERATED = ROOT / "python" / "src" / "planeon_harness" / "generated"
TYPESCRIPT_SOURCE = ROOT / "typescript" / "src"
TYPESCRIPT_DIST = ROOT / "typescript" / "dist"
GOLDEN_MANIFEST = ROOT / "tests" / "generated" / "golden-manifest.json"
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}


@dataclass(frozen=True, slots=True)
class Property:
    name: str
    required: bool
    schema: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Model:
    name: str
    source_path: str
    schema_pointer: str
    schema_id: str | None
    properties: tuple[Property, ...]


@dataclass(frozen=True, slots=True)
class Parameter:
    wire_name: str
    variable_name: str
    location: str
    required: bool
    value_type: str


@dataclass(frozen=True, slots=True)
class Operation:
    operation_id: str
    api: str
    method: str
    path: str
    parameters: tuple[Parameter, ...]
    request_body_required: bool
    request_schema_ref: str | None
    response_schema_ref: str | None


def _pascal(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    result = "".join(word[:1].upper() + word[1:] for word in words)
    if not result or result[0].isdigit():
        result = f"Generated{result}"
    return result


def _snake(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    if not value or value[0].isdigit():
        value = f"value_{value}"
    if keyword.iskeyword(value):
        value += "_"
    return value


def _camel(value: str) -> str:
    pascal = _pascal(value)
    return pascal[:1].lower() + pascal[1:]


def _object(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"expected object: {context}")
    return value


def _lock() -> dict[str, Any]:
    verify()
    return _object(load_json(LOCK_PATH), "contracts.lock.json")


def _schema_documents(lock: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []
    for entry in lock["files"]:
        path = entry["path"]
        if path.startswith("schemas/"):
            result.append((path, _object(load_json(SNAPSHOT_ROOT / path), path)))
    return result


def _properties(schema: Mapping[str, Any]) -> tuple[Property, ...]:
    raw_properties = schema.get("properties", {})
    if not isinstance(raw_properties, dict):
        return ()
    required = set(schema.get("required", [])) if isinstance(schema.get("required", []), list) else set()
    return tuple(
        Property(
            name=name,
            required=name in required,
            schema=_object(raw_schema, f"property {name}"),
        )
        for name, raw_schema in sorted(raw_properties.items())
    )


def _models(lock: Mapping[str, Any]) -> tuple[Model, ...]:
    models: dict[str, Model] = {}
    for path, document in _schema_documents(lock):
        title = document.get("title")
        if isinstance(title, str) and title and document.get("type") == "object":
            model = Model(
                name=_pascal(title),
                source_path=path,
                schema_pointer="",
                schema_id=document.get("$id") if isinstance(document.get("$id"), str) else None,
                properties=_properties(document),
            )
            if model.name in models:
                raise ValueError(f"duplicate generated model: {model.name}")
            models[model.name] = model
        definitions = document.get("$defs", {})
        if isinstance(definitions, dict):
            category = _pascal(Path(path).parent.name)
            owner = _pascal(title) if isinstance(title, str) and title else category + _pascal(Path(path).stem)
            for name, raw_schema in sorted(definitions.items()):
                schema = _object(raw_schema, f"{path}#/$defs/{name}")
                model_name = owner + _pascal(name)
                model = Model(
                    name=model_name,
                    source_path=path,
                    schema_pointer=f"/$defs/{name}",
                    schema_id=None,
                    properties=_properties(schema),
                )
                if model_name in models:
                    raise ValueError(f"duplicate generated model: {model_name}")
                models[model_name] = model

    for entry in lock["files"]:
        path = entry["path"]
        if not path.startswith("openapi/"):
            continue
        document = _object(load_json(SNAPSHOT_ROOT / path), path)
        components = _object(document.get("components", {}), f"{path}/components")
        schemas = _object(components.get("schemas", {}), f"{path}/components/schemas")
        for name, raw_schema in sorted(schemas.items()):
            schema = _object(raw_schema, f"{path}#/components/schemas/{name}")
            model_name = _pascal(name)
            if model_name in models:
                model_name = _pascal(Path(path).stem) + model_name
            models[model_name] = Model(
                name=model_name,
                source_path=path,
                schema_pointer=f"/components/schemas/{name}",
                schema_id=None,
                properties=_properties(schema),
            )
    return tuple(models[name] for name in sorted(models))


def _resolve_parameter(document: Mapping[str, Any], value: object, context: str) -> dict[str, Any]:
    parameter = _object(value, context)
    reference = parameter.get("$ref")
    if not isinstance(reference, str):
        return parameter
    prefix = "#/components/parameters/"
    if not reference.startswith(prefix):
        raise ValueError(f"unsupported parameter reference: {reference}")
    name = reference[len(prefix) :]
    components = _object(document.get("components", {}), "components")
    parameters = _object(components.get("parameters", {}), "components/parameters")
    return _object(parameters.get(name), f"components/parameters/{name}")


def _parameter_type(parameter: Mapping[str, Any]) -> str:
    schema = parameter.get("schema")
    if not isinstance(schema, dict):
        return "str"
    value_type = schema.get("type")
    if value_type == "integer":
        return "int"
    if value_type == "boolean":
        return "bool"
    return "str"


def _response_ref(operation: Mapping[str, Any]) -> str | None:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return None
    for status, response_value in sorted(responses.items()):
        if not str(status).startswith("2") or not isinstance(response_value, dict):
            continue
        content = response_value.get("content", {})
        if not isinstance(content, dict):
            continue
        for media in ("application/json", "application/problem+json"):
            media_value = content.get(media)
            if isinstance(media_value, dict) and isinstance(media_value.get("schema"), dict):
                reference = media_value["schema"].get("$ref")
                if isinstance(reference, str):
                    return reference
    return None


def _operations(lock: Mapping[str, Any]) -> tuple[Operation, ...]:
    result: list[Operation] = []
    seen: set[str] = set()
    for entry in lock["files"]:
        source_path = entry["path"]
        if not source_path.startswith("openapi/"):
            continue
        document = _object(load_json(SNAPSHOT_ROOT / source_path), source_path)
        raw_paths = _object(document.get("paths", {}), f"{source_path}/paths")
        for route, raw_path_item in sorted(raw_paths.items()):
            path_item = _object(raw_path_item, f"{source_path}/paths/{route}")
            inherited = path_item.get("parameters", [])
            if not isinstance(inherited, list):
                raise ValueError(f"path parameters must be an array: {source_path}/{route}")
            for method, raw_operation in sorted(path_item.items()):
                if method not in HTTP_METHODS:
                    continue
                operation = _object(raw_operation, f"{source_path}/{route}/{method}")
                operation_id = operation.get("operationId")
                if not isinstance(operation_id, str) or not operation_id:
                    raise ValueError(f"OpenAPI operation lacks operationId: {source_path}/{route}/{method}")
                if operation_id in seen:
                    raise ValueError(f"duplicate OpenAPI operationId: {operation_id}")
                seen.add(operation_id)
                raw_parameters = operation.get("parameters", [])
                if not isinstance(raw_parameters, list):
                    raise ValueError(f"operation parameters must be an array: {operation_id}")
                parameters: dict[tuple[str, str], Parameter] = {}
                for index, raw_parameter in enumerate([*inherited, *raw_parameters]):
                    parameter = _resolve_parameter(
                        document,
                        raw_parameter,
                        f"{source_path}/{operation_id}/parameters/{index}",
                    )
                    name = parameter.get("name")
                    location = parameter.get("in")
                    if not isinstance(name, str) or location not in {"header", "path", "query"}:
                        raise ValueError(f"operation parameter is invalid: {operation_id}/{index}")
                    parameters[(location, name)] = Parameter(
                        wire_name=name,
                        variable_name=_snake(name),
                        location=location,
                        required=bool(parameter.get("required")) or location == "path",
                        value_type=_parameter_type(parameter),
                    )
                request_body = operation.get("requestBody")
                body_required = False
                request_ref: str | None = None
                if isinstance(request_body, dict):
                    body_required = bool(request_body.get("required"))
                    content = request_body.get("content", {})
                    if isinstance(content, dict):
                        media = content.get("application/json")
                        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                            reference = media["schema"].get("$ref")
                            request_ref = reference if isinstance(reference, str) else None
                result.append(
                    Operation(
                        operation_id=operation_id,
                        api=Path(source_path).stem.replace(".openapi", ""),
                        method=method.upper(),
                        path=route,
                        parameters=tuple(
                            sorted(
                                parameters.values(),
                                key=lambda item: (not item.required, item.location, item.wire_name),
                            )
                        ),
                        request_body_required=body_required,
                        request_schema_ref=request_ref,
                        response_schema_ref=_response_ref(operation),
                    )
                )
    return tuple(sorted(result, key=lambda item: item.operation_id))


def _event_inventory(lock: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    async_paths = [entry["path"] for entry in lock["files"] if entry["path"].startswith("asyncapi/")]
    if async_paths != ["asyncapi/harness-events.asyncapi.json"]:
        raise ValueError("expected the single pinned Harness AsyncAPI contract")
    document = _object(load_json(SNAPSHOT_ROOT / async_paths[0]), async_paths[0])
    channels = _object(document.get("channels", {}), "AsyncAPI channels")
    components = _object(document.get("components", {}), "AsyncAPI components")
    messages = _object(components.get("messages", {}), "AsyncAPI messages")
    return tuple(sorted(channels)), tuple(sorted(messages))


def _python_type(schema: Mapping[str, Any]) -> str:
    enum = schema.get("enum")
    if isinstance(enum, list) and enum and all(isinstance(item, str) for item in enum):
        return "Literal[" + ", ".join(repr(item) for item in enum) + "]"
    constant = schema.get("const")
    if isinstance(constant, str):
        return f"Literal[{constant!r}]"
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        values = [_python_type({"type": item}) for item in raw_type]
        return " | ".join(dict.fromkeys(values))
    if raw_type == "string":
        return "str"
    if raw_type == "integer":
        return "int"
    if raw_type == "number":
        return "int | float"
    if raw_type == "boolean":
        return "bool"
    if raw_type == "null":
        return "None"
    if raw_type == "array":
        items = schema.get("items")
        item_type = _python_type(items) if isinstance(items, dict) else "JsonValue"
        return f"list[{item_type}]"
    if raw_type == "object":
        return "dict[str, JsonValue]"
    return "JsonValue"


def _typescript_type(schema: Mapping[str, Any]) -> str:
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return " | ".join(json.dumps(item, ensure_ascii=False) for item in enum)
    constant = schema.get("const")
    if constant is not None:
        return json.dumps(constant, ensure_ascii=False)
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        return " | ".join(dict.fromkeys(_typescript_type({"type": item}) for item in raw_type))
    if raw_type == "string":
        return "string"
    if raw_type in {"integer", "number"}:
        return "number"
    if raw_type == "boolean":
        return "boolean"
    if raw_type == "null":
        return "null"
    if raw_type == "array":
        items = schema.get("items")
        item_type = _typescript_type(items) if isinstance(items, dict) else "JsonValue"
        return f"Array<{item_type}>"
    if raw_type == "object":
        return "JsonObject"
    return "JsonValue"


def _python_models(models: Sequence[Model], release_digest: str) -> bytes:
    lines = [
        '"""Generated contract models. Do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Final, Literal, TypeAlias, TypedDict",
        "",
        "JsonScalar: TypeAlias = None | bool | int | float | str",
        "JsonValue: TypeAlias = JsonScalar | list['JsonValue'] | dict[str, 'JsonValue']",
        f"CONTRACT_RELEASE_DIGEST: Final = {release_digest!r}",
        "",
    ]
    registry: dict[str, dict[str, object]] = {}
    for model in models:
        required = [prop for prop in model.properties if prop.required]
        optional = [prop for prop in model.properties if not prop.required]
        if required and optional:
            lines.append(f"class _{model.name}Required(TypedDict):")
            for prop in required:
                annotation = _python_type(prop.schema)
                if not prop.name.isidentifier() or keyword.iskeyword(prop.name):
                    raise ValueError(f"Python-incompatible contract field: {model.name}.{prop.name}")
                lines.append(f"    {prop.name}: {annotation}")
            lines.append("")
            lines.append(f"class {model.name}(_{model.name}Required, total=False):")
            properties = optional
        else:
            total = "" if required else ", total=False"
            lines.append(f"class {model.name}(TypedDict{total}):")
            properties = required or optional
        if not properties:
            lines.append("    pass")
        for prop in properties:
            annotation = _python_type(prop.schema)
            if not prop.name.isidentifier() or keyword.iskeyword(prop.name):
                raise ValueError(f"Python-incompatible contract field: {model.name}.{prop.name}")
            lines.append(f"    {prop.name}: {annotation}")
        lines.append("")
        registry[model.name] = {
            "sourcePath": model.source_path,
            "schemaPointer": model.schema_pointer,
            "schemaId": model.schema_id,
            "requiredFields": [prop.name for prop in model.properties if prop.required],
        }
    lines.extend(
        [
            "MODEL_CONTRACTS: Final[dict[str, dict[str, object]]] = "
            + repr(registry),
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _operation_literal(operation: Operation) -> dict[str, object]:
    return {
        "api": operation.api,
        "method": operation.method,
        "path": operation.path,
        "parameters": [
            {
                "wireName": parameter.wire_name,
                "variableName": parameter.variable_name,
                "location": parameter.location,
                "required": parameter.required,
                "valueType": parameter.value_type,
            }
            for parameter in operation.parameters
        ],
        "requestBodyRequired": operation.request_body_required,
        "requestSchemaRef": operation.request_schema_ref,
        "responseSchemaRef": operation.response_schema_ref,
    }


def _python_client(operations: Sequence[Operation]) -> bytes:
    registry = {operation.operation_id: _operation_literal(operation) for operation in operations}
    lines = [
        '"""Generated transport-neutral request builders. Do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        "from collections.abc import Mapping",
        "from dataclasses import dataclass",
        "from typing import Final",
        "from urllib.parse import quote",
        "",
        "from .models import JsonValue",
        "",
        "@dataclass(frozen=True, slots=True)",
        "class Request:",
        "    operation_id: str",
        "    method: str",
        "    path: str",
        "    query: tuple[tuple[str, str], ...]",
        "    headers: tuple[tuple[str, str], ...]",
        "    body: Mapping[str, JsonValue] | None",
        "",
        "OPERATIONS: Final[dict[str, dict[str, object]]] = " + repr(registry),
        "",
        "def build_request(",
        "    operation_id: str,",
        "    parameters: Mapping[str, str | int | bool | None],",
        "    body: Mapping[str, JsonValue] | None = None,",
        ") -> Request:",
        "    try:",
        "        operation = OPERATIONS[operation_id]",
        "    except KeyError as exc:",
        "        raise ValueError(f'unknown operation: {operation_id}') from exc",
        "    specs = operation['parameters']",
        "    assert isinstance(specs, list)",
        "    admitted = {spec['variableName'] for spec in specs}",
        "    unknown = sorted(set(parameters) - admitted)",
        "    if unknown:",
        "        raise ValueError(f'unknown operation parameter: {unknown[0]}')",
        "    path = str(operation['path'])",
        "    query: list[tuple[str, str]] = []",
        "    headers: list[tuple[str, str]] = []",
        "    for spec in specs:",
        "        variable = str(spec['variableName'])",
        "        value = parameters.get(variable)",
        "        if value is None:",
        "            if spec['required']:",
        "                raise ValueError(f'missing operation parameter: {variable}')",
        "            continue",
        "        rendered = str(value).lower() if isinstance(value, bool) else str(value)",
        "        location = spec['location']",
        "        wire_name = str(spec['wireName'])",
        "        if location == 'path':",
        "            path = path.replace('{' + wire_name + '}', quote(rendered, safe=''))",
        "        elif location == 'query':",
        "            query.append((wire_name, rendered))",
        "        elif location == 'header':",
        "            headers.append((wire_name, rendered))",
        "    if '{' in path or '}' in path:",
        "        raise ValueError('not all path parameters were resolved')",
        "    if operation['requestBodyRequired'] and body is None:",
        "        raise ValueError('request body is required')",
        "    if body is not None:",
        "        headers.append(('Content-Type', 'application/json'))",
        "    return Request(",
        "        operation_id=operation_id,",
        "        method=str(operation['method']),",
        "        path=path,",
        "        query=tuple(query),",
        "        headers=tuple(headers),",
        "        body=body,",
        "    )",
        "",
        "class HarnessClient:",
        "    \"\"\"Build requests for a caller-supplied transport; performs no I/O.\"\"\"",
        "",
    ]
    for operation in operations:
        required = [parameter for parameter in operation.parameters if parameter.required]
        optional = [parameter for parameter in operation.parameters if not parameter.required]
        signature_parts = [
            f"{parameter.variable_name}: {parameter.value_type}" for parameter in required
        ]
        if operation.request_body_required:
            signature_parts.append("body: Mapping[str, JsonValue]")
        signature_parts.extend(
            f"{parameter.variable_name}: {parameter.value_type} | None = None"
            for parameter in optional
        )
        if operation.request_schema_ref is not None and not operation.request_body_required:
            signature_parts.append("body: Mapping[str, JsonValue] | None = None")
        signature = ", ".join(signature_parts)
        if signature:
            signature = "*, " + signature
        separator = ", " if signature else ""
        lines.append(
            f"    def {_snake(operation.operation_id)}(self{separator}{signature}) -> Request:"
        )
        pairs = [f"{parameter.variable_name!r}: {parameter.variable_name}" for parameter in operation.parameters]
        lines.append(f"        parameters = {{{', '.join(pairs)}}}")
        body_argument = ", body" if operation.request_schema_ref is not None else ""
        lines.append(
            f"        return build_request({operation.operation_id!r}, parameters{body_argument})"
        )
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _python_events(channels: Sequence[str], messages: Sequence[str]) -> bytes:
    return (
        '"""Generated AsyncAPI event inventory. Do not edit by hand."""\n\n'
        "from typing import Final\n\n"
        f"CHANNELS: Final = {tuple(channels)!r}\n"
        f"MESSAGE_NAMES: Final = {tuple(messages)!r}\n"
    ).encode("utf-8")


def _python_init(models: Sequence[Model]) -> bytes:
    model_names = [model.name for model in models]
    lines = [
        '"""Generated Planeon harness contract surface."""',
        "",
        "from .client import HarnessClient, OPERATIONS, Request, build_request",
        "from .events import CHANNELS, MESSAGE_NAMES",
        "from .models import CONTRACT_RELEASE_DIGEST, MODEL_CONTRACTS, JsonValue",
        "from .models import " + ", ".join(model_names),
        "",
        "__all__ = [",
    ]
    exports = [
        "CHANNELS",
        "CONTRACT_RELEASE_DIGEST",
        "HarnessClient",
        "JsonValue",
        "MESSAGE_NAMES",
        "MODEL_CONTRACTS",
        "OPERATIONS",
        "Request",
        "build_request",
        *model_names,
    ]
    lines.extend(f"    {name!r}," for name in exports)
    lines.extend(["]", ""])
    return "\n".join(lines).encode("utf-8")


def _ts_property_name(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name) else json.dumps(name)


def _typescript_models(models: Sequence[Model], release_digest: str) -> bytes:
    lines = [
        "// Generated contract models. Do not edit by hand.",
        "export type JsonScalar = null | boolean | number | string;",
        "export type JsonValue = JsonScalar | Array<JsonValue> | JsonObject;",
        "export interface JsonObject { [key: string]: JsonValue; }",
        f"export const CONTRACT_RELEASE_DIGEST = {json.dumps(release_digest)} as const;",
        "",
    ]
    registry: dict[str, dict[str, object]] = {}
    for model in models:
        lines.append(f"export interface {model.name} {{")
        for prop in model.properties:
            optional = "" if prop.required else "?"
            lines.append(
                f"  {_ts_property_name(prop.name)}{optional}: {_typescript_type(prop.schema)};"
            )
        lines.append("}")
        lines.append("")
        registry[model.name] = {
            "sourcePath": model.source_path,
            "schemaPointer": model.schema_pointer,
            "schemaId": model.schema_id,
            "requiredFields": [prop.name for prop in model.properties if prop.required],
        }
    lines.append(
        "export const MODEL_CONTRACTS = "
        + json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + " as const;"
    )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _typescript_client(operations: Sequence[Operation]) -> bytes:
    registry = {operation.operation_id: _operation_literal(operation) for operation in operations}
    lines = [
        "// Generated transport-neutral request builders. Do not edit by hand.",
        "import type { JsonObject, JsonValue } from './models.js';",
        "",
        "export interface RequestSpec {",
        "  readonly operationId: string;",
        "  readonly method: string;",
        "  readonly path: string;",
        "  readonly query: ReadonlyArray<readonly [string, string]>;",
        "  readonly headers: ReadonlyArray<readonly [string, string]>;",
        "  readonly body?: JsonObject;",
        "}",
        "",
        "export const OPERATIONS = "
        + json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + " as const;",
        "export type OperationId = keyof typeof OPERATIONS;",
        "",
        "export function buildRequest(",
        "  operationId: OperationId,",
        "  parameters: Readonly<Record<string, string | number | boolean | undefined>>,",
        "  body?: JsonObject,",
        "): RequestSpec {",
        "  const operation = OPERATIONS[operationId];",
        "  const admitted = new Set(operation.parameters.map((parameter) => parameter.variableName));",
        "  const unknown = Object.keys(parameters).filter((name) => !admitted.has(name));",
        "  if (unknown.length > 0) throw new Error(`unknown operation parameter: ${unknown.sort()[0]}`);",
        "  let path = operation.path;",
        "  const query: Array<readonly [string, string]> = [];",
        "  const headers: Array<readonly [string, string]> = [];",
        "  for (const parameter of operation.parameters) {",
        "    const value = parameters[parameter.variableName];",
        "    if (value === undefined) {",
        "      if (parameter.required) throw new Error(`missing operation parameter: ${parameter.variableName}`);",
        "      continue;",
        "    }",
        "    const rendered = String(value);",
        "    if (parameter.location === 'path') path = path.replace(`{${parameter.wireName}}`, encodeURIComponent(rendered));",
        "    if (parameter.location === 'query') query.push([parameter.wireName, rendered]);",
        "    if (parameter.location === 'header') headers.push([parameter.wireName, rendered]);",
        "  }",
        "  if (path.includes('{') || path.includes('}')) throw new Error('not all path parameters were resolved');",
        "  if (operation.requestBodyRequired && body === undefined) throw new Error('request body is required');",
        "  if (body !== undefined) headers.push(['Content-Type', 'application/json']);",
        "  return { operationId, method: operation.method, path, query, headers, ...(body === undefined ? {} : { body }) };",
        "}",
        "",
    ]
    for operation in operations:
        args: list[str] = []
        values: list[str] = []
        for parameter in operation.parameters:
            ts_type = {"str": "string", "int": "number", "bool": "boolean"}[parameter.value_type]
            optional = "" if parameter.required else "?"
            variable = _camel(parameter.wire_name)
            args.append(f"{variable}{optional}: {ts_type}")
            values.append(f"{json.dumps(parameter.variable_name)}: args.{variable}")
        if operation.request_schema_ref is not None:
            optional = "" if operation.request_body_required else "?"
            args.append(f"body{optional}: JsonObject")
        function_name = _camel(operation.operation_id)
        function_arguments = f"args: {{ {'; '.join(args)} }}" if args else ""
        lines.append(f"export function {function_name}({function_arguments}): RequestSpec {{")
        body_arg = ", args.body" if operation.request_schema_ref is not None else ""
        lines.append(
            f"  return buildRequest({json.dumps(operation.operation_id)}, "
            + "{ " + ", ".join(values) + " }" + body_arg + ");"
        )
        lines.append("}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _typescript_events(channels: Sequence[str], messages: Sequence[str]) -> bytes:
    return (
        "// Generated AsyncAPI event inventory. Do not edit by hand.\n"
        f"export const CHANNELS = {json.dumps(channels)} as const;\n"
        "export type ChannelName = typeof CHANNELS[number];\n"
        f"export const MESSAGE_NAMES = {json.dumps(messages)} as const;\n"
        "export type MessageName = typeof MESSAGE_NAMES[number];\n"
    ).encode("utf-8")


def _typescript_index() -> bytes:
    return (
        "// Generated public SDK surface. Do not edit by hand.\n"
        "export * from './models.js';\n"
        "export * from './client.js';\n"
        "export * from './events.js';\n"
        "export * from './runtime/index.js';\n"
    ).encode("utf-8")


def _javascript_client(operations: Sequence[Operation]) -> bytes:
    registry = {operation.operation_id: _operation_literal(operation) for operation in operations}
    lines = [
        "// Generated ESM request builders. Do not edit by hand.",
        "export const OPERATIONS = "
        + json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + ";",
        "export function buildRequest(operationId, parameters, body) {",
        "  const operation = OPERATIONS[operationId];",
        "  if (operation === undefined) throw new Error(`unknown operation: ${operationId}`);",
        "  const admitted = new Set(operation.parameters.map((parameter) => parameter.variableName));",
        "  const unknown = Object.keys(parameters).filter((name) => !admitted.has(name));",
        "  if (unknown.length > 0) throw new Error(`unknown operation parameter: ${unknown.sort()[0]}`);",
        "  let path = operation.path;",
        "  const query = [];",
        "  const headers = [];",
        "  for (const parameter of operation.parameters) {",
        "    const value = parameters[parameter.variableName];",
        "    if (value === undefined) {",
        "      if (parameter.required) throw new Error(`missing operation parameter: ${parameter.variableName}`);",
        "      continue;",
        "    }",
        "    const rendered = String(value);",
        "    if (parameter.location === 'path') path = path.replace(`{${parameter.wireName}}`, encodeURIComponent(rendered));",
        "    if (parameter.location === 'query') query.push([parameter.wireName, rendered]);",
        "    if (parameter.location === 'header') headers.push([parameter.wireName, rendered]);",
        "  }",
        "  if (path.includes('{') || path.includes('}')) throw new Error('not all path parameters were resolved');",
        "  if (operation.requestBodyRequired && body === undefined) throw new Error('request body is required');",
        "  if (body !== undefined) headers.push(['Content-Type', 'application/json']);",
        "  return { operationId, method: operation.method, path, query, headers, ...(body === undefined ? {} : { body }) };",
        "}",
    ]
    for operation in operations:
        function_name = _camel(operation.operation_id)
        values = [
            f"{json.dumps(parameter.variable_name)}: args.{_camel(parameter.wire_name)}"
            for parameter in operation.parameters
        ]
        body_arg = ", args.body" if operation.request_schema_ref is not None else ""
        function_arguments = "args" if operation.parameters or operation.request_schema_ref else ""
        lines.extend(
            [
                f"export function {function_name}({function_arguments}) {{",
                f"  return buildRequest({json.dumps(operation.operation_id)}, "
                + "{ " + ", ".join(values) + " }" + body_arg + ");",
                "}",
            ]
        )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _typescript_models_declaration(models: Sequence[Model], release_digest: str) -> bytes:
    lines = [
        "// Generated model declarations. Do not edit by hand.",
        "export type JsonScalar = null | boolean | number | string;",
        "export type JsonValue = JsonScalar | Array<JsonValue> | JsonObject;",
        "export interface JsonObject { [key: string]: JsonValue; }",
        f"export declare const CONTRACT_RELEASE_DIGEST: {json.dumps(release_digest)};",
        "",
    ]
    for model in models:
        lines.append(f"export interface {model.name} {{")
        for prop in model.properties:
            optional = "" if prop.required else "?"
            lines.append(
                f"  {_ts_property_name(prop.name)}{optional}: {_typescript_type(prop.schema)};"
            )
        lines.extend(["}", ""])
    lines.extend(
        [
            "export declare const MODEL_CONTRACTS: Readonly<Record<string, {",
            "  readonly sourcePath: string;",
            "  readonly schemaPointer: string;",
            "  readonly schemaId: string | null;",
            "  readonly requiredFields: ReadonlyArray<string>;",
            "}>>;",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _typescript_client_declaration(operations: Sequence[Operation]) -> bytes:
    lines = [
        "// Generated client declarations. Do not edit by hand.",
        "import type { JsonObject } from './models.js';",
        "",
        "export interface RequestSpec {",
        "  readonly operationId: string;",
        "  readonly method: string;",
        "  readonly path: string;",
        "  readonly query: ReadonlyArray<readonly [string, string]>;",
        "  readonly headers: ReadonlyArray<readonly [string, string]>;",
        "  readonly body?: JsonObject;",
        "}",
        "export declare const OPERATIONS: Readonly<Record<string, {",
        "  readonly api: string;",
        "  readonly method: string;",
        "  readonly path: string;",
        "  readonly parameters: ReadonlyArray<{",
        "    readonly wireName: string;",
        "    readonly variableName: string;",
        "    readonly location: 'header' | 'path' | 'query';",
        "    readonly required: boolean;",
        "    readonly valueType: 'str' | 'int' | 'bool';",
        "  }>;",
        "  readonly requestBodyRequired: boolean;",
        "  readonly requestSchemaRef: string | null;",
        "  readonly responseSchemaRef: string | null;",
        "}>>;",
        "export type OperationId = keyof typeof OPERATIONS;",
        "export declare function buildRequest(",
        "  operationId: OperationId,",
        "  parameters: Readonly<Record<string, string | number | boolean | undefined>>,",
        "  body?: JsonObject,",
        "): RequestSpec;",
        "",
    ]
    for operation in operations:
        args: list[str] = []
        for parameter in operation.parameters:
            ts_type = {"str": "string", "int": "number", "bool": "boolean"}[
                parameter.value_type
            ]
            optional = "" if parameter.required else "?"
            args.append(f"{_camel(parameter.wire_name)}{optional}: {ts_type}")
        if operation.request_schema_ref is not None:
            optional = "" if operation.request_body_required else "?"
            args.append(f"body{optional}: JsonObject")
        function_arguments = f"args: {{ {'; '.join(args)} }}" if args else ""
        lines.append(
            f"export declare function {_camel(operation.operation_id)}({function_arguments}): RequestSpec;"
        )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _typescript_events_declaration(channels: Sequence[str], messages: Sequence[str]) -> bytes:
    channel_union = " | ".join(json.dumps(item) for item in channels)
    message_union = " | ".join(json.dumps(item) for item in messages)
    return (
        "// Generated event declarations. Do not edit by hand.\n"
        f"export declare const CHANNELS: readonly [{', '.join(json.dumps(item) for item in channels)}];\n"
        f"export type ChannelName = {channel_union};\n"
        f"export declare const MESSAGE_NAMES: readonly [{', '.join(json.dumps(item) for item in messages)}];\n"
        f"export type MessageName = {message_union};\n"
    ).encode("utf-8")


def expected_outputs() -> dict[Path, bytes]:
    lock = _lock()
    models = _models(lock)
    operations = _operations(lock)
    channels, messages = _event_inventory(lock)
    release_digest = lock["release"]["manifestSha256"]
    outputs: dict[Path, bytes] = {
        Path("python/src/planeon_harness/generated/models.py"): _python_models(models, release_digest),
        Path("python/src/planeon_harness/generated/client.py"): _python_client(operations),
        Path("python/src/planeon_harness/generated/events.py"): _python_events(channels, messages),
        Path("python/src/planeon_harness/generated/__init__.py"): _python_init(models),
        Path("typescript/src/models.ts"): _typescript_models(models, release_digest),
        Path("typescript/src/client.ts"): _typescript_client(operations),
        Path("typescript/src/events.ts"): _typescript_events(channels, messages),
        Path("typescript/src/index.ts"): _typescript_index(),
        Path("typescript/dist/models.js"): (
            f"// Generated ESM model constants. Do not edit by hand.\nexport const CONTRACT_RELEASE_DIGEST = {json.dumps(release_digest)};\n"
        ).encode("utf-8"),
        Path("typescript/dist/client.js"): _javascript_client(operations),
        Path("typescript/dist/events.js"): (
            f"// Generated ESM event inventory. Do not edit by hand.\nexport const CHANNELS = {json.dumps(channels)};\nexport const MESSAGE_NAMES = {json.dumps(messages)};\n"
        ).encode("utf-8"),
        Path("typescript/dist/index.js"): _typescript_index(),
    }
    outputs[Path("typescript/dist/models.d.ts")] = _typescript_models_declaration(
        models, release_digest
    )
    outputs[Path("typescript/dist/client.d.ts")] = _typescript_client_declaration(operations)
    outputs[Path("typescript/dist/events.d.ts")] = _typescript_events_declaration(
        channels, messages
    )
    outputs[Path("typescript/dist/index.d.ts")] = outputs[Path("typescript/src/index.ts")]
    generated_digests = {
        path.as_posix(): sha256_bytes(content)
        for path, content in sorted(outputs.items(), key=lambda item: item[0].as_posix())
    }
    golden = {
        "schemaVersion": "harness.planeon.ai/generated-sdk-manifest/v1",
        "generatorVersion": GENERATOR_VERSION,
        "contractReleaseDigest": release_digest,
        "models": [
            {
                "name": model.name,
                "sourcePath": model.source_path,
                "schemaPointer": model.schema_pointer,
                "requiredFields": [prop.name for prop in model.properties if prop.required],
            }
            for model in models
        ],
        "operations": [
            {"operationId": operation.operation_id, **_operation_literal(operation)}
            for operation in operations
        ],
        "channels": list(channels),
        "messages": list(messages),
        "generatedFiles": generated_digests,
    }
    outputs[Path("tests/generated/golden-manifest.json")] = canonical_json_bytes(golden)
    return outputs


def _generated_sets(outputs: Mapping[Path, bytes]) -> dict[Path, set[Path]]:
    roots = {
        Path("python/src/planeon_harness/generated"),
        Path("typescript/src"),
        Path("typescript/dist"),
    }
    return {
        root: {path for path in outputs if path.is_relative_to(root)}
        for root in roots
    }


def _generated_candidates(root: Path) -> tuple[Path, ...]:
    """Return files owned by the generator under one generated root.

    TypeScript top-level source and distribution files are generated, while
    packet-owned extensions live in subdirectories such as
    ``typescript/src/telemetry`` and ``typescript/dist/telemetry``. Other
    generated roots remain recursively closed.
    """

    absolute_root = ROOT / root
    if not absolute_root.is_dir():
        return ()
    if root in {Path("typescript/src"), Path("typescript/dist")}:
        return tuple(absolute_root.iterdir())
    return tuple(absolute_root.rglob("*"))


def _reject_generated_links(root: Path) -> None:
    absolute_root = ROOT / root
    if absolute_root.is_symlink() or any(path.is_symlink() for path in absolute_root.rglob("*")):
        raise ValueError(f"generated directory contains a linked output: {root}")


def _check(outputs: Mapping[Path, bytes]) -> None:
    for path, expected in outputs.items():
        absolute = ROOT / path
        if not absolute.is_file() or absolute.is_symlink():
            raise ValueError(f"generated output is absent or linked: {path}")
        if absolute.read_bytes() != expected:
            raise ValueError(f"generated output is stale: {path}")
    for root, expected in _generated_sets(outputs).items():
        _reject_generated_links(root)
        actual = {
            path.relative_to(ROOT)
            for path in _generated_candidates(root)
            if path.is_file() and not path.is_symlink()
        }
        if actual != expected:
            raise ValueError(f"generated directory contains an undeclared output: {root}")


def _write(outputs: Mapping[Path, bytes]) -> None:
    for path, content in outputs.items():
        absolute = ROOT / path
        absolute.parent.mkdir(parents=True, exist_ok=True)
        if absolute.is_file() and not absolute.is_symlink() and absolute.read_bytes() == content:
            continue
        absolute.write_bytes(content)
    for root, expected in _generated_sets(outputs).items():
        _reject_generated_links(root)
        for path in sorted(_generated_candidates(root), reverse=True):
            relative = path.relative_to(ROOT)
            if path.is_file() and relative not in expected:
                path.unlink()
            elif root not in {Path("typescript/src"), Path("typescript/dist")} and path.is_dir() and not any(path.iterdir()):
                path.rmdir()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        outputs = expected_outputs()
        if arguments.check:
            _check(outputs)
        else:
            _write(outputs)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"SDK generation refused: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "accepted": True,
                "mode": "CHECK" if arguments.check else "WRITE",
                "outputs": len(outputs),
                "treeDigest": "sha256:"
                + hashlib.sha256(
                    canonical_json_bytes(
                        {
                            path.as_posix(): sha256_bytes(content)
                            for path, content in sorted(
                                outputs.items(), key=lambda item: item[0].as_posix()
                            )
                        }
                    )
                ).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
