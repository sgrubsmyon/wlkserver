"""Generate docs/API_REFERENCE.md from the app's OpenAPI schema.

Run from anywhere:

    python/venv/bin/python docs/generate_api_reference.py

The output is committed so the reference is readable without a running server.
Regenerate it whenever endpoints, parameters or schemas change; `docs/API.md`
stays hand-written and links here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from python.main import app  # noqa: E402

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
GROUP_TITLES = {
    "abrechnung_tag": "Abrechnung Tag (daily settlement)",
    "abrechnung_monat": "Abrechnung Monat (monthly settlement)",
    "abrechnung_jahr": "Abrechnung Jahr (yearly settlement)",
    "import_export": "Import / export (CSV, DSFinV-K)",
    "tse": "TSE (technical security device)",
    "warenkorb": "Warenkorb (stateless cart preview)",
}


def leaf_routes(routes, inherited=()):
    """Yield (APIRoute, dependency names) including router-level dependencies."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route, inherited
        elif hasattr(route, "original_router"):
            context = route.include_context
            names = tuple(
                getattr(dep.dependency, "__name__", "") for dep in context.dependencies
            )
            yield from leaf_routes(route.original_router.routes, inherited + names)


def dependency_names(dependant):
    """All dependency callable names below a route's dependant."""
    for dep in dependant.dependencies:
        name = getattr(dep.call, "__name__", "")
        if name:
            yield name
        yield from dependency_names(dep)


def auth_level(route, inherited):
    names = set(inherited) | set(dependency_names(route.dependant))
    if "require_admin" in names:
        return "admin"
    if "require_user" in names:
        return "user"
    return "public"


AUTH_LABEL = {"public": "public", "user": "logged-in user", "admin": "admin"}


def resolve(schema, node):
    """Follow $ref and unwrap anyOf/oneOf with a single non-null branch."""
    while isinstance(node, dict):
        if "$ref" in node:
            node = schema["components"]["schemas"][node["$ref"].rsplit("/", 1)[-1]]
            continue
        branches = node.get("anyOf") or node.get("oneOf")
        if branches:
            real = [b for b in branches if b.get("type") != "null"]
            if len(real) == 1:
                node = real[0]
                continue
        break
    return node or {}


def type_name(schema, node):
    node = resolve(schema, node)
    kind = node.get("type", "object")
    if kind == "array":
        return f"array of {type_name(schema, node.get('items', {}))}"
    if "enum" in node:
        return "one of " + ", ".join(f"`{value}`" for value in node["enum"])
    if kind == "object" and "properties" in node:
        return "object"
    return kind


def schema_label(schema, node):
    """Ref/array-aware label: `VerkaufPublic`, `array of VerkaufDetailsCreate`."""
    if isinstance(node, dict) and "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    resolved = resolve(schema, node)
    if resolved.get("type") == "array":
        return f"array of {schema_label(schema, resolved.get('items', {}))}"
    return type_name(schema, node)


def constraints(node):
    parts = []
    for key, label in (
        ("minimum", "min"), ("maximum", "max"),
        ("exclusiveMinimum", ">"), ("exclusiveMaximum", "<"),
        ("minLength", "min length"), ("maxLength", "max length"),
        ("pattern", "pattern"), ("default", "default"),
    ):
        if key in node and node[key] is not None:
            parts.append(f"{label} {node[key]}".strip())
    return ", ".join(parts)


def field_rows(schema, node, prefix=""):
    """Rows of a request/response object, one level deep."""
    node = resolve(schema, node)
    properties = node.get("properties")
    if not properties:
        return [("(free form)", type_name(schema, node), "", "")]
    required = set(node.get("required", []))
    rows = []
    for name, prop in properties.items():
        resolved = resolve(schema, prop)
        rows.append((
            f"{prefix}{name}",
            type_name(schema, prop),
            "yes" if name in required else "no",
            constraints(resolved),
        ))
    return rows


def parameter_rows(schema, operation):
    rows = []
    for param in operation.get("parameters", []):
        if param.get("in") not in ("path", "query", "header"):
            continue
        content = resolve(schema, param.get("schema", {}))
        rows.append((
            param["name"],
            param["in"],
            type_name(schema, param.get("schema", {})),
            "yes" if param.get("required") else "no",
            constraints(content),
        ))
    return rows


def body_schema(schema, operation):
    body = operation.get("requestBody")
    if not body:
        return None, None
    for media_type, content in body.get("content", {}).items():
        return media_type, content.get("schema", {})
    return None, None


def first_line(text):
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def render_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return lines


def main() -> None:
    schema = app.openapi()
    operations = []
    for route, inherited in leaf_routes(app.routes):
        if route.path not in schema["paths"]:
            continue  # e.g. /favicon.ico, excluded from the schema
        for method in sorted(route.methods & set(m.upper() for m in HTTP_METHODS)):
            operations.append((route, method, auth_level(route, inherited)))
    operations.sort(key=lambda item: (item[0].endpoint.__module__, item[0].path, item[1]))

    out = [
        "# API reference",
        "",
        "Generated from the OpenAPI schema by `docs/generate_api_reference.py` - do not",
        "edit by hand. Regenerate after changing endpoints, parameters or schemas:",
        "",
        "```",
        "python/venv/bin/python docs/generate_api_reference.py",
        "```",
        "",
        "The hand-written overview (base URL, authentication, error format, endpoint",
        "groups) is in [`API.md`](API.md); settlement details with examples are in",
        "[`KASSENSTAND_UND_ABRECHNUNG.md`](KASSENSTAND_UND_ABRECHNUNG.md).",
        "",
        "## Authentication",
        "",
        "Every endpoint except `POST /auth/login` requires",
        "`Authorization: Bearer <token>` from `POST /auth/login`. \"admin\" below means",
        "the token belongs to an active user with role `admin`; such requests also",
        "need a logged-in user. A missing or invalid token is `401`, an insufficient",
        "role is `403`.",
        "",
        "## Index",
        "",
    ]

    index_auth = []
    for route, method, auth in operations:
        summary = first_line(route.description) or route.name.replace("_", " ")
        index_auth.append((
            f"`{method}`", f"`{route.path}`", AUTH_LABEL[auth], summary,
        ))
    out += render_table(["Method", "Path", "Access", "Summary"], index_auth)

    current_group = None
    for route, method, auth in operations:
        group = route.endpoint.__module__.rsplit(".", 1)[-1]
        if group != current_group:
            current_group = group
            out += ["", f"## {GROUP_TITLES.get(group, group)}", ""]
        operation = schema["paths"][route.path][method.lower()]
        summary = first_line(route.description) or route.name.replace("_", " ")
        out += [f"### `{method} {route.path}`", "", summary, ""]
        description = (route.description or "").strip()
        extra = "\n".join(description.splitlines()[1:]).strip()
        if extra:
            out += [extra, ""]
        out += [f"**Access:** {AUTH_LABEL[auth]}", ""]

        params = parameter_rows(schema, operation)
        if params:
            out += ["**Parameters**", ""]
            out += render_table(["Name", "In", "Type", "Required", "Constraints"], params)
            out += [""]

        media_type, body = body_schema(schema, operation)
        if body:
            label = schema_label(schema, body)
            suffix = f" - `{label}`" if label not in ("object", "free form") else ""
            out += [f"**Request body** (`{media_type}`){suffix}", ""]
            out += render_table(["Field", "Type", "Required", "Constraints"],
                                field_rows(schema, body))
            out += [""]

        responses = operation.get("responses", {})
        rows = []
        for status, response in responses.items():
            content = response.get("content", {})
            if content:
                schema_node = next(iter(content.values())).get("schema", {})
                target = schema_label(schema, schema_node)
            else:
                target = response.get("description", "")
            rows.append((status, target))
        out += ["**Responses**", ""]
        out += render_table(["Status", "Body"], rows)
        out += [""]

    target = ROOT / "docs" / "API_REFERENCE.md"
    target.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({len(operations)} operations)")


if __name__ == "__main__":
    main()
