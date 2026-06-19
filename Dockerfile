# syntax=docker/dockerfile:1
#
# APEX dev / runtime image.
#   * Python 3.9 + APEX dependencies — run search.py and the AFlow optimizer.
#   * Node.js 22 — for the planned Vite/React workflow-browser UI. It also
#     resolves the host "npm requires node >=22.9.0" error, so npm works here.
#
# Build:
#   docker build -t apex .
#
# Run a search (API key + config provided at runtime, never baked in):
#   docker run --rm -it \
#     -e OPENAI_API_KEY=sk-... \
#     -v "$PWD/config2.yaml:/app/config2.yaml" \
#     -v "$PWD/apex_outputs:/app/apex_outputs" \
#     -v "$PWD/apex_logs:/app/apex_logs" \
#     -v "$PWD/logs:/app/logs" \
#     apex \
#     python search.py --dataset EnigmataSudoku --bundle_id 0 \
#       --opt_temperature 0 --worker_temperature 0 --aggregator_temperature 0
#
# Puzzle data (data/) is baked from data.zip at build. Use a different set by
# mounting one:  -v "$PWD/data:/app/data"
#
# Workflow-viewer corpus (all_workflows.jsonl, 117MB) is NOT baked. Provide it
# at runtime, either as the extracted file:
#   -v "$PWD/all_workflows.jsonl:/app/all_workflows.jsonl"
# or mount the zip and extract inside the container (unzip is installed):
#   -v "$PWD/all_workflows.zip:/app/all_workflows.zip"   # then: unzip all_workflows.zip
#
# Interactive shell for debugging:
#   docker run --rm -it apex bash

FROM python:3.9-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# --- System packages -------------------------------------------------------
# git + build-essential: VCS and a compile fallback for any source-built wheels
#   (e.g. python-sat from the enigmata requirements).
# unzip: extract data.zip (puzzles) and all_workflows.zip (viewer corpus).
# Node.js 22 (via NodeSource): toolchain for the Vite/React UI; its npm satisfies
#   the engine requirement that fails on the host (node 18 / npm 9.2.0).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git build-essential ca-certificates curl gnupg unzip \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (own layer: rebuilds only when requirements change) -
COPY requirements.txt ./
COPY thirdparty/enigmata/requirement.txt ./enigmata-requirement.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -r enigmata-requirement.txt

# --- Application source -----------------------------------------------------
# Brings in the vendored aflow (thirdparty/aflow), the checked-out enigmata
# submodule (thirdparty/enigmata), search.py, models.py, data.zip, etc.
COPY . .

# --- Puzzle data -----------------------------------------------------------
# The extracted data/ dir is NOT copied from the build context (it's dev-local /
# gitignored); data.zip is the canonical source. Extract it here. Override at
# runtime by mounting a host data set: -v "$PWD/data:/app/data".
RUN unzip -q -o data.zip && rm -f data.zip

# aflow internal imports expect aflow/ on sys.path; enigmata is imported as a
# top-level package, so thirdparty/ must be on it too (mirrors search.py).
ENV PYTHONPATH=/app:/app/thirdparty/aflow:/app/thirdparty \
    EXP_RESULTS_DIR=apex_outputs \
    EXP_LOGS_DIR=apex_logs

# config2.yaml is intentionally NOT baked in — mount it at runtime (-v). The API
# key is read from $OPENAI_API_KEY at call time, so no secrets live in the image.

CMD ["python", "search.py", "--help"]
