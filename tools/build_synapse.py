#!/usr/bin/env python3
"""Build Synapse Git artifacts (pipeline, linked services, datasets) from specs + SQL.

Copilot writes readable SQL in sql/<layer>/*.sql. This script turns it into the JSON
files Synapse Studio reads from Git (synapse/), so nobody hand-edits pipeline JSON.

Usage (always through the wrapper, which manages .venv):
    ./tools/build.sh validate   # check specs + SQL conventions
    ./tools/build.sh build      # (re)write synapse/**/*.json
    ./tools/build.sh check      # CI: fail if synapse/ is out of date

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
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:
    # Started with an interpreter that lacks PyYAML (for example Homebrew python3).
    # Re-run inside the project's .venv, creating it on first use.
    venv_python = ROOT / ".venv" / "bin" / "python3"
    if os.environ.get("BUILD_SYNAPSE_BOOTSTRAPPED"):
        sys.exit("PyYAML is still missing in .venv. Run: ./tools/build.sh validate")
    if not venv_python.exists():
        print("Creating project environment in .venv (first run only)...", flush=True)
        subprocess.check_call([sys.executable, "-m", "venv", str(ROOT / ".venv")])
    if subprocess.call([str(venv_python), "-c", "import yaml"], stderr=subprocess.DEVNULL) != 0:
        print("Installing requirements.txt into .venv (first run only)...", flush=True)
        subprocess.check_call([str(venv_python), "-m", "pip", "install", "--quiet",
                               "--disable-pip-version-check", "-r", str(ROOT / "requirements.txt")])
    os.environ["BUILD_SYNAPSE_BOOTSTRAPPED"] = "1"
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:])
CONFIG_FILE = ROOT / "config" / "environment.yaml"
SOURCES_DIR = ROOT / "specs" / "sources"
MODELS_DIR = ROOT / "specs" / "models"
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "synapse"

LAYERS = ["00_setup", "bronze", "silver", "gold"]
ALLOWED_TYPES = re.compile(r"^(INT|BIGINT|SMALLINT|BIT|DATE|DATETIME2|VARCHAR\(\d+\)|DECIMAL\(\d+,\d+\))$")
ALLOWED_CHECKS = {"not_null", "regex", "valid_type", "max_length", "min_value",
                  "allowed_values", "references", "unique"}
TYPE_HINT = "INT, BIGINT, SMALLINT, BIT, DATE, DATETIME2, VARCHAR(n), DECIMAL(p,s)"
CHECK_PARAMS = {
    "regex": ("pattern",),
    "max_length": ("value",),
    "min_value": ("value",),
    "allowed_values": ("values",),
    "references": ("ref_table", "ref_column"),
}
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


PARSE_ERRORS = []


def load_yaml(path):
    """Load a YAML file. Syntax errors are collected in PARSE_ERRORS instead of crashing."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = " at line {}".format(mark.line + 1) if mark else ""
        PARSE_ERRORS.append(
            "{}: invalid YAML{} ({}). Put values that contain ': ' or '#' in double quotes, "
            "e.g. description: \"Customer id (TODO confirm)\"".format(
                path.relative_to(ROOT), where, getattr(exc, "problem", exc)))
        return {"_parse_error": True}


def load_all():
    config = load_yaml(CONFIG_FILE)
    sources = []
    for path in sorted(SOURCES_DIR.glob("*.yaml")):
        spec = load_yaml(path)
        spec["_file"] = path.stem
        sources.append(spec)
    models = [load_yaml(p) for p in sorted(MODELS_DIR.glob("*.yaml"))]
    return config, sources, models


def sql_files():
    files = []
    for layer in LAYERS:
        files.extend(sorted((SQL_DIR / layer).glob("*.sql")))
    return files


# ---------------------------------------------------------------- validation

def validate(config, sources, models):
    errors = list(PARSE_ERRORS)
    tables = set()
    for spec in sources:
        if spec.get("_parse_error"):
            continue  # only the YAML syntax error is useful until the file parses
        name = spec.get("table", "<missing table>")
        if name != spec["_file"]:
            errors.append("specs/sources/{}.yaml: 'table' is '{}' but must equal the file name '{}'".format(
                spec["_file"], name, spec["_file"]))
        for key in ("table", "description", "source_file", "format", "business_key", "columns", "dq_rules"):
            if not spec.get(key):
                errors.append("specs/sources/{}: missing '{}' (see specs/_templates/source_spec.template.yaml)".format(name, key))
        if not str(spec.get("source_file", "")).endswith(".csv"):
            errors.append("specs/sources/{}: source_file must be the CSV file name, e.g. {}.csv".format(name, name))
        cols = {}
        for col in spec.get("columns") or []:
            cname = col.get("name", "")
            if not re.match(r"^[a-z][a-z0-9_]*$", cname):
                errors.append("{}.{}: column names must be snake_case".format(name, cname))
            if not ALLOWED_TYPES.match(str(col.get("type", ""))):
                errors.append("{}.{}: unsupported type '{}'; use one of {}".format(name, cname, col.get("type"), TYPE_HINT))
            if not isinstance(col.get("nullable"), bool):
                errors.append("{}.{}: 'nullable' must be true or false".format(name, cname))
            if not col.get("description"):
                errors.append("{}.{}: missing description".format(name, cname))
            cols[cname] = col
        for key in spec.get("business_key") or []:
            if key not in cols:
                errors.append("{}: business_key '{}' is not a column".format(name, key))
            elif cols[key].get("nullable") is not False:
                errors.append("{}.{}: business key columns must be nullable: false (add a not_null rule instead)".format(name, key))
        for rule in spec.get("dq_rules") or []:
            rname = rule.get("name") or "<unnamed rule on {}>".format(rule.get("column"))
            check = rule.get("check")
            if not rule.get("name"):
                errors.append("{}: {} needs a 'name' like <column>_<check>".format(name, rname))
            if "rule" in rule:
                errors.append("{}: rule '{}' uses 'rule:'; the key is 'check:'".format(name, rname))
            if check not in ALLOWED_CHECKS:
                errors.append("{}: rule '{}' has unknown check '{}'; use one of {}".format(
                    name, rname, check, ", ".join(sorted(ALLOWED_CHECKS))))
            for param in CHECK_PARAMS.get(check, ()):
                if rule.get(param) in (None, "", []):
                    errors.append("{}: rule '{}' (check {}) needs '{}'".format(name, rname, check, param))
            if rule.get("column") not in cols:
                errors.append("{}: rule '{}' column '{}' not found".format(name, rname, rule.get("column")))
            if rule.get("action") not in ("reject", "warn"):
                errors.append("{}: rule '{}' needs action: reject or action: warn".format(name, rname))
        tables.add(name)

    for model in models:
        if model.get("_parse_error"):
            continue
        mname = model.get("model", "<missing model>")
        for key in ("model", "layer", "description", "grain", "sources", "join", "columns"):
            if not model.get(key):
                errors.append("specs/models/{}: missing '{}'".format(mname, key))
        if model.get("layer") not in (None, "gold"):
            errors.append("specs/models/{}: layer must be 'gold'".format(mname))
        for col in model.get("columns") or []:
            for key in ("name", "expression", "description"):
                if not col.get(key):
                    errors.append("specs/models/{}: column '{}' missing '{}'".format(mname, col.get("name", "?"), key))
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
                "folder": {"type": "string"},
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
    root = {
        "name": "ds_adls_binary_root",
        "type": "Microsoft.Synapse/workspaces/datasets",
        "properties": {
            "description": "Any file at the ROOT of an ADLS container (no folder), e.g. landing/<file>. "
                           "Generated by tools/build_synapse.py.",
            "linkedServiceName": {"referenceName": "ls_adls", "type": "LinkedServiceReference"},
            "parameters": {
                "container": {"type": "string"},
                "file": {"type": "string"},
            },
            "annotations": ["copilot-generated"],
            "type": "Binary",
            "typeProperties": {
                "location": {
                    "type": "AzureBlobFSLocation",
                    "fileName": expr("@dataset().file"),
                    "fileSystem": expr("@dataset().container"),
                }
            },
        },
    }
    return {"ds_adls_binary": binary, "ds_adls_binary_root": root}


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
            # landing files sit at the container root; Synapse rejects an empty folder value,
            # so the source uses a dataset that has no folder parameter at all
            "referenceName": "ds_adls_binary_root", "type": "DatasetReference",
            "parameters": {"container": containers["landing"], "file": source_file},
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
    # Built-in credential Synapse creates for the workspace managed identity. It must be in Git,
    # otherwise "Overwrite live mode" / Publish deletes it from the live workspace.
    files["credential/WorkspaceSystemIdentity.json"] = {
        "name": "WorkspaceSystemIdentity",
        "properties": {"type": "ManagedIdentity"},
    }
    return {path: json.dumps(body, indent=4, ensure_ascii=False) + "\n" for path, body in files.items()}


def same_json(path, content):
    """True when the file holds the same JSON as content. Formatting is ignored, because
    Synapse Studio re-saves files with its own indentation when it commits to Git."""
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")) == json.loads(content)
    except ValueError:
        return False


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
        stale = [p for p, content in rendered.items() if not same_json(OUT_DIR / p, content)]
        if stale:
            print("synapse/ is out of date. Run: ./tools/build.sh build")
            for p in stale:
                print("  - synapse/" + p)
            return 1
        print("synapse/ is up to date.")
        return 0

    for path, content in rendered.items():
        target = OUT_DIR / path
        if same_json(target, content):
            print("unchanged synapse/" + path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print("wrote synapse/" + path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
