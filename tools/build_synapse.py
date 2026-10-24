#!/usr/bin/env python3
"""Build Synapse Git artifacts (pipeline, linked services, datasets) from specs + SQL.

Copilot writes readable SQL in sql/<layer>/*.sql. This script turns it into the JSON
files Synapse Studio reads from Git (synapse/), so nobody hand-edits pipeline JSON.

Usage:
    python3 tools/build_synapse.py validate   # check specs + SQL conventions
    python3 tools/build_synapse.py build      # (re)write synapse/**/*.json
    python3 tools/build_synapse.py check      # CI: fail if synapse/ is out of date

Pipeline produced (pl_<use_case>):
    copy_<table>_landing_to_raw   (one per source spec, run in parallel)
      -> one Script activity per SQL file, in order: 00_setup, bronze, silver, gold

SQL conventions handled here:
    GO on its own line         -> splits the file into separate script blocks
    -- target_db: master       -> first-line directive; run the file against master
    {{run_id}}                 -> @{pipeline().RunId}
    {{ingest_date}}            -> @{formatDateTime(pipeline().TriggerTime,'yyyy-MM-dd')}
    {{storage_account}} {{landing_container}} {{raw_container}} {{curated_container}} {{database}}
                               -> literal values from config/environment.yaml
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "environment.yaml"
SOURCES_DIR = ROOT / "specs" / "sources"
MODELS_DIR = ROOT / "specs" / "models"
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "synapse"

LAYERS = ["00_setup", "bronze", "silver", "gold"]
ALLOWED_TYPES = re.compile(r"^(INT|BIGINT|SMALLINT|BIT|DATE|DATETIME2|VARCHAR\(\d+\)|DECIMAL\(\d+,\d+\))$")
ALLOWED_CHECKS = {"not_null", "regex", "valid_type", "max_length", "min_value",
                  "allowed_values", "references", "unique"}
GO_LINE = re.compile(r"^\s*GO\s*;?\s*$", re.IGNORECASE | re.MULTILINE)
TARGET_DB = re.compile(r"^\s*--\s*target_db:\s*(\w+)", re.IGNORECASE)
FORBIDDEN_SQL = [
    (re.compile(r"\bMERGE\b", re.I), "MERGE is not supported on serverless SQL"),
    (re.compile(r"\bUPDATE\s+\w", re.I), "UPDATE is not supported on serverless SQL"),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), "DELETE is not supported on serverless SQL"),
    (re.compile(r"\bINSERT\s+INTO\b", re.I), "INSERT is not supported on serverless SQL; use CETAS"),
    (re.compile(r"\bSECRET\s*=", re.I), "secrets must not appear in SQL; use managed identity"),
]
RUNTIME_TOKENS = {
    "{{run_id}}": "@{pipeline().RunId}",
    "{{ingest_date}}": "@{formatDateTime(pipeline().TriggerTime,'yyyy-MM-dd')}",
}
IR_REF = {"referenceName": "AutoResolveIntegrationRuntime", "type": "IntegrationRuntimeReference"}


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all():
    config = load_yaml(CONFIG_FILE)
    sources = [load_yaml(p) for p in sorted(SOURCES_DIR.glob("*.yaml"))]
    models = [load_yaml(p) for p in sorted(MODELS_DIR.glob("*.yaml"))]
    return config, sources, models


def sql_files():
    files = []
    for layer in LAYERS:
        files.extend(sorted((SQL_DIR / layer).glob("*.sql")))
    return files


# ---------------------------------------------------------------- validation

def validate(config, sources, models):
    errors = []
    tables = set()
    for spec in sources:
        name = spec.get("table", "<missing table>")
        for key in ("table", "description", "source_file", "business_key", "columns"):
            if not spec.get(key):
                errors.append("specs/sources/{}: missing '{}'".format(name, key))
        if not str(spec.get("source_file", "")).endswith(".csv"):
            errors.append("specs/sources/{}: source_file must be a .csv".format(name))
        cols = {}
        for col in spec.get("columns") or []:
            cname = col.get("name", "")
            if not re.match(r"^[a-z][a-z0-9_]*$", cname):
                errors.append("{}.{}: column names must be snake_case".format(name, cname))
            if not ALLOWED_TYPES.match(str(col.get("type", ""))):
                errors.append("{}.{}: unsupported type '{}'".format(name, cname, col.get("type")))
            if not col.get("description"):
                errors.append("{}.{}: missing description".format(name, cname))
            cols[cname] = col
        for key in spec.get("business_key") or []:
            if key not in cols:
                errors.append("{}: business_key '{}' is not a column".format(name, key))
        for rule in spec.get("dq_rules") or []:
            if rule.get("check") not in ALLOWED_CHECKS:
                errors.append("{}: rule '{}' has unknown check '{}'".format(name, rule.get("name"), rule.get("check")))
            if rule.get("column") not in cols:
                errors.append("{}: rule '{}' column '{}' not found".format(name, rule.get("name"), rule.get("column")))
            if rule.get("action") not in ("reject", "warn"):
                errors.append("{}: rule '{}' action must be reject or warn".format(name, rule.get("name")))
        tables.add(name)

    for model in models:
        mname = model.get("model", "<missing model>")
        for src in model.get("sources") or []:
            schema, _, table = src.partition(".")
            if schema != "silver" or table not in tables:
                errors.append("specs/models/{}: source '{}' is not a silver table from specs/sources".format(mname, src))

    for path in sql_files():
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            errors.append("{}: file is empty".format(rel))
        stripped = re.sub(r"--[^\n]*", "", text)  # ignore comments
        for pattern, message in FORBIDDEN_SQL:
            if pattern.search(stripped):
                errors.append("{}: {}".format(rel, message))
        leftover = re.findall(r"\{\{(\w+)\}\}", text)
        known = {t.strip("{}") for t in RUNTIME_TOKENS} | {"storage_account", "landing_container",
                                                           "raw_container", "curated_container", "database"}
        for token in leftover:
            if token not in known:
                errors.append("{}: unknown placeholder {{{{{}}}}}".format(rel, token))
        if "@{" in text:
            errors.append("{}: '@{{' is reserved for pipeline expressions; use a {{{{placeholder}}}}".format(rel))
    return errors


# ------------------------------------------------------------------ builders

def expr(value):
    return {"value": value, "type": "Expression"}


def render_sql_block(block, config):
    storage = config["storage"]
    literals = {
        "{{storage_account}}": storage["account"],
        "{{landing_container}}": storage["containers"]["landing"],
        "{{raw_container}}": storage["containers"]["raw"],
        "{{curated_container}}": storage["containers"]["curated"],
        "{{database}}": config["synapse"]["database"],
    }
    for token, value in literals.items():
        block = block.replace(token, value)
    if not any(token in block for token in RUNTIME_TOKENS):
        return block
    for token, value in RUNTIME_TOKENS.items():
        block = block.replace(token, value)
    if block.startswith("@"):
        block = "@" + block  # a leading @ must be escaped in pipeline expressions
    return expr(block)


def linked_services(config):
    endpoint = config["synapse"]["serverless_endpoint"]
    adls = {
        "name": "ls_adls",
        "type": "Microsoft.Synapse/workspaces/linkedservices",
        "properties": {
            "description": "ADLS Gen2 via workspace managed identity. Generated by tools/build_synapse.py.",
            "annotations": ["copilot-generated"],
            "type": "AzureBlobFS",
            "typeProperties": {"url": "https://{}.dfs.core.windows.net/".format(config["storage"]["account"])},
            "connectVia": IR_REF,
        },
    }
    sql = {
        "name": "ls_serverless_sql",
        "type": "Microsoft.Synapse/workspaces/linkedservices",
        "properties": {
            "description": "Serverless SQL (Built-in) via workspace managed identity. Generated by tools/build_synapse.py.",
            "parameters": {"DBName": {"type": "String"}},
            "annotations": ["copilot-generated"],
            "type": "AzureSqlDW",
            "typeProperties": {
                "connectionString": "Integrated Security=False;Encrypt=True;Connection Timeout=30;"
                                    "Data Source={};Initial Catalog=@{{linkedService().DBName}}".format(endpoint)
            },
            "connectVia": IR_REF,
        },
    }
    return {"ls_adls": adls, "ls_serverless_sql": sql}


def datasets():
    binary = {
        "name": "ds_adls_binary",
        "type": "Microsoft.Synapse/workspaces/datasets",
        "properties": {
            "description": "Any file in ADLS, addressed by container/folder/file. Generated by tools/build_synapse.py.",
            "linkedServiceName": {"referenceName": "ls_adls", "type": "LinkedServiceReference"},
            "parameters": {
                "container": {"type": "string"},
                "folder": {"type": "string", "defaultValue": ""},
                "file": {"type": "string"},
            },
            "annotations": ["copilot-generated"],
            "type": "Binary",
            "typeProperties": {
                "location": {
                    "type": "AzureBlobFSLocation",
                    "fileName": expr("@dataset().file"),
                    "folderPath": expr("@dataset().folder"),
                    "fileSystem": expr("@dataset().container"),
                }
            },
        },
    }
    return {"ds_adls_binary": binary}


def copy_activity(spec, config):
    containers = config["storage"]["containers"]
    table, source_file = spec["table"], spec["source_file"]
    return {
        "name": "copy_{}_landing_to_raw".format(table),
        "description": "Copy {} from {}/ to {}/{}/ingest_date=<run date>/".format(
            source_file, containers["landing"], containers["raw"], table),
        "type": "Copy",
        "dependsOn": [],
        "policy": {"timeout": "0.00:30:00", "retry": 1, "retryIntervalInSeconds": 30},
        "typeProperties": {
            "source": {"type": "BinarySource",
                       "storeSettings": {"type": "AzureBlobFSReadSettings", "recursive": False}},
            "sink": {"type": "BinarySink", "storeSettings": {"type": "AzureBlobFSWriteSettings"}},
            "enableStaging": False,
        },
        "inputs": [{
            "referenceName": "ds_adls_binary", "type": "DatasetReference",
            "parameters": {"container": containers["landing"], "folder": "", "file": source_file},
        }],
        "outputs": [{
            "referenceName": "ds_adls_binary", "type": "DatasetReference",
            "parameters": {
                "container": containers["raw"],
                "folder": expr("{}/ingest_date=@{{formatDateTime(pipeline().TriggerTime,'yyyy-MM-dd')}}".format(table)),
                "file": source_file,
            },
        }],
    }


def script_activity(path, config, depends_on):
    text = path.read_text(encoding="utf-8")
    first_line = text.lstrip().splitlines()[0] if text.strip() else ""
    match = TARGET_DB.match(first_line)
    db = match.group(1) if match else config["synapse"]["database"]
    blocks = [b.strip() for b in GO_LINE.split(text) if b.strip()]
    blocks = [b for b in blocks if re.sub(r"--[^\n]*", "", b).strip()]  # drop comment-only blocks
    layer = path.parent.name
    return {
        "name": "{}_{}".format(layer, path.stem),
        "description": "Runs sql/{}/{} ({} block(s)) on database {}".format(layer, path.name, len(blocks), db),
        "type": "Script",
        "dependsOn": depends_on,
        "policy": {"timeout": "0.01:00:00", "retry": 0},
        "linkedServiceName": {"referenceName": "ls_serverless_sql", "type": "LinkedServiceReference",
                              "parameters": {"DBName": db}},
        "typeProperties": {
            "scripts": [{"type": "NonQuery", "text": render_sql_block(b, config)} for b in blocks],
            "scriptBlockExecutionTimeout": "02:00:00",
        },
    }


def pipeline(config, sources):
    name = "pl_{}".format(config["use_case"])
    activities = [copy_activity(spec, config) for spec in sources]
    previous = [a["name"] for a in activities]
    for path in sql_files():
        depends = [{"activity": p, "dependencyConditions": ["Succeeded"]} for p in previous]
        activity = script_activity(path, config, depends)
        activities.append(activity)
        previous = [activity["name"]]
    return name, {
        "name": name,
        "type": "Microsoft.Synapse/workspaces/pipelines",
        "properties": {
            "description": "landing -> raw -> curated (bronze, silver, gold). "
                           "Generated by tools/build_synapse.py from specs/ and sql/ — do not edit by hand.",
            "activities": activities,
            "annotations": ["copilot-generated"],
            "folder": {"name": "copilot-generated"},
        },
    }


def integration_runtime():
    return {
        "name": "AutoResolveIntegrationRuntime",
        "properties": {
            "type": "Managed",
            "typeProperties": {"computeProperties": {
                "location": "AutoResolve",
                "dataFlowProperties": {"computeType": "General", "coreCount": 8, "timeToLive": 0},
            }},
        },
    }


def render(config, sources):
    files = {}
    for name, body in linked_services(config).items():
        files["linkedService/{}.json".format(name)] = body
    for name, body in datasets().items():
        files["dataset/{}.json".format(name)] = body
    pl_name, pl_body = pipeline(config, sources)
    files["pipeline/{}.json".format(pl_name)] = pl_body
    files["integrationRuntime/AutoResolveIntegrationRuntime.json"] = integration_runtime()
    return {path: json.dumps(body, indent=4, ensure_ascii=False) + "\n" for path, body in files.items()}


# ---------------------------------------------------------------------- main

def main(argv):
    command = argv[1] if len(argv) > 1 else "build"
    if command not in ("validate", "build", "check"):
        print(__doc__)
        return 2

    config, sources, models = load_all()
    errors = validate(config, sources, models)
    if errors:
        print("Validation failed:")
        for e in errors:
            print("  - " + e)
        return 1
    print("Validation passed: {} source spec(s), {} model spec(s), {} SQL file(s).".format(
        len(sources), len(models), len(sql_files())))
    if command == "validate":
        return 0

    rendered = render(config, sources)
    if command == "check":
        stale = [p for p, content in rendered.items()
                 if not (OUT_DIR / p).exists() or (OUT_DIR / p).read_text(encoding="utf-8") != content]
        if stale:
            print("synapse/ is out of date. Run: python3 tools/build_synapse.py build")
            for p in stale:
                print("  - synapse/" + p)
            return 1
        print("synapse/ is up to date.")
        return 0

    for path, content in rendered.items():
        target = OUT_DIR / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print("wrote synapse/" + path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
