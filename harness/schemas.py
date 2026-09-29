"""Per-phase output structure (the JSON envelope the agent must emit).

For phase 1 / 2 the structure is fully fixed by the platform. For phase 3
the value's shape (number / dict-with-keys / list-of-length-N) is dictated
by the scenario's `expected`, so we derive a "shell" from it and present
that to the agent. For phase 4 we condition on which of `numeric_check`
and `qualitative_check` are enabled.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Phase 1 — comparison keys per platform (single source of truth)
# ---------------------------------------------------------------------------

PHASE1_KEYS: dict[str, list[str]] = {
    "neon": ["data_products", "sites"],
    # `temporal_range` is intentionally NOT graded — it's a direct
    # transcription of date words from the user prompt, not real
    # identifier discovery, so it added noise (format mismatches between
    # dict / string / list representations) without measuring anything
    # the agent had to figure out.
    "gbif": ["taxon_keys", "country_codes", "state_provinces", "dataset_keys"],
    "usgs": ["sites", "parameter_codes"],
    "epa":  ["sites", "state_codes", "county_codes",
             "parameter_codes", "cbsa_codes"],

    # --- SciDataBench-Onboard platforms -------------------------------------
    # Same rule as `temporal_range` above: `geographic_scope` is excluded
    # everywhere it appears (argo / noaa_ghcn / obis / usgs_eq). Its values
    # mix free-text place names with coordinate ranges in the same field
    # ("Bay of Bengal" vs "26°S-16°S", "33.193"/"103.855"/"200"), so a set
    # comparison measures transcription formatting, not discovery. Same for
    # vizier's `catalog_keywords`, which holds paper titles and author names
    # rather than catalogue identifiers.
    "argo":        ["float_wmo_ids", "parameters"],
    "census_acs":  ["tables", "variables", "state_codes", "county_codes",
                    "geographies"],
    "cmip6":       ["source_ids", "experiment_ids", "variable_ids",
                    "table_ids", "variant_labels"],
    "ensembl":     ["gene_symbols", "gene_ids", "transcript_ids", "species"],
    "inaturalist": ["taxon_names", "taxon_ids", "place_names", "place_ids"],
    "matproj":     ["material_ids", "formulas", "elements", "chemsys",
                    "properties"],
    "noaa_ghcn":   ["station_ids", "parameters"],
    "obis":        ["scientific_names", "aphia_ids"],
    "pangaea":     ["dataset_ids", "parameters"],
    "usgs_eq":     ["event_ids"],
    "vizier":      ["catalogs", "target_names"],
}


# How this benchmark ADDRESSES the platform: through a Python client, or
# through the service's HTTP API. Phase 1 / 2 prompts branch on this, because
# telling an agent to `import noaa_ncei` would be a fabricated instruction —
# that namespace is ours, not a package.
#
# "rest" is a benchmark convention, NOT a claim that no Python client exists.
# All four REST platforms do have one:
#     census_acs  `census` 0.8.27      (datamade; works)
#     ensembl     `ensembl-rest` 0.3.4 (single-author, last release 2023)
#     matproj     `mp-api` 0.46.4      (official)
#     noaa_ghcn   `meteostat` 2.1.4    (cannot resolve GHCN-Daily station ids,
#                                       which is why the gold was rewritten to
#                                       NCEI — see scripts/rewrite_noaa_ghcn_gold.py)
# The gold and the cache were materialised over HTTP, so grading addresses
# these platforms the same way. The prompts must therefore describe the
# request namespace without asserting anything false about the ecosystem.
PHASE2_INTERFACE: dict[str, str] = {
    "census_acs": "rest",
    "ensembl":    "rest",
    "matproj":    "rest",
    "noaa_ghcn":  "rest",
}


PHASE2_PACKAGE: dict[str, str] = {
    "neon": "neonutilities",
    "gbif": "pygbif",
    "usgs": "dataretrieval",
    "epa":  "pyaqsapi",

    # --- held-out onboarding platforms ------------------------------------
    "argo":        "argopy",
    "cmip6":       "intake_esgf",
    "inaturalist": "pyinaturalist",
    "obis":        "pyobis",
    "pangaea":     "pangaeapy",
    "usgs_eq":     "obspy",
    "vizier":      "astroquery.vizier",
    # REST platforms: the value is a human-readable API name, not an
    # importable module. Guard with PHASE2_INTERFACE before using it in an
    # `import {pkg}` instruction.
    "census_acs":  "Census Data API",
    "ensembl":     "Ensembl REST API",
    "matproj":     "Materials Project REST API",
    "noaa_ghcn":   "NOAA NCEI Access API",
}


# The agent has no package to introspect for these, so the prompt states the
# request namespace — the same service `dir()` / `help()` gives the
# Python-client platforms for free. These blocks describe the *interface*,
# never which endpoint or parameters this scenario needs.
#
# `module` / `function` below are the namespace the benchmark uses to address
# an endpoint; the executor (scripts/exec_agent_calls.py) dispatches on them.
# Several scenario prompts name a Python client (`mp_api`, `census`,
# `meteostat`). That is not a contradiction — it names the platform, while
# this block fixes how the call is WRITTEN DOWN, so a declared call can be
# executed and compared against a gold that was materialised over HTTP.
REST_INTERFACE_SPEC: dict[str, str] = {
    "census_acs": (
        "## Request format — Census Data API\n"
        "Declare each query as one envelope entry with "
        "`\"module\": \"census\"`, `\"function\": \"acs_data\"`, and `kwargs` "
        "holding the API's query string parameters verbatim:\n"
        "  - `year`     : survey year, integer (e.g. 2019)\n"
        "  - `dataset`  : dataset path (e.g. `acs/acs5`, `acs/acs1`, "
        "`acs/acs5/subject`)\n"
        "  - `get`      : comma-separated variable ids, or `group(TABLEID)` "
        "for a whole table. Only ONE `group(...)` per call is allowed.\n"
        "  - `for`      : target geography (e.g. `tract:*`, `county:*`, "
        "`state:06`)\n"
        "  - `in`       : containing geography (e.g. `state:06`, "
        "`state:06 county:075`). `state:*` is NOT accepted for tract or "
        "block-group geographies — issue one call per state instead.\n"
        "The API key is supplied by the harness; do not include it."
    ),
    "ensembl": (
        "## Request format — Ensembl REST API\n"
        "Declare each request as one envelope entry with "
        "`\"module\": \"ensembl_rest\"` and `function` set to one of these "
        "endpoint names:\n"
        "  - `lookup_symbol`  : kwargs `species`, `symbol` "
        "(+ optional `expand`)\n"
        "  - `lookup_id`      : kwargs `id` (+ optional `expand`)\n"
        "  - `sequence_id`    : kwargs `id`, optional `type` "
        "(`genomic`/`cds`/`protein`), `expand_5prime`, `expand_3prime`\n"
        "  - `overlap_region` : kwargs `species`, `region` "
        "(e.g. `7:140424943-140624564`), `feature` (e.g. `gene`)\n"
        "  - `homology_id`    : kwargs `id`, optional `species`, "
        "`target_species`\n"
    ),
    "matproj": (
        "## Request format — Materials Project REST API\n"
        "Declare each request as one envelope entry with "
        "`\"module\": \"mp_api\"` and `function` set to the endpoint path, "
        "e.g. `materials/summary`, `materials/thermo`, "
        "`materials/elasticity`, `materials/dielectric`, "
        "`materials/piezoelectric`, `materials/insertion_electrodes`.\n"
        "`kwargs` are the query parameters, e.g.:\n"
        "  - `material_ids` : comma-separated ids (`mp-149,mp-2534`)\n"
        "  - `formula` / `chemsys` / `elements`\n"
        "  - `_fields`      : comma-separated fields to return — always "
        "include the ones the task needs\n"
        "The API key is supplied by the harness; do not include it."
    ),
    "noaa_ghcn": (
        "## Request format — NOAA NCEI Access API\n"
        "Declare each request as one envelope entry with "
        "`\"module\": \"noaa_ncei\"`, `\"function\": \"access_data\"`, and "
        "`kwargs`:\n"
        "  - `dataset`   : e.g. `daily-summaries`, `global-summary-of-the-year`\n"
        "  - `stations`  : comma-separated GHCN station ids "
        "(e.g. `USW00094728`)\n"
        "  - `startDate` / `endDate` : `YYYY-MM-DD`\n"
        "  - `dataTypes` : comma-separated element codes "
        "(e.g. `TMAX,TMIN,PRCP`)\n"
        "  - `format`    : `json`\n"
        "Queries are addressed by station id — resolve place names to GHCN "
        "station ids first."
    ),
}


def phase2_interface(platform: str) -> str:
    """"python" (an installed client library) or "rest" (raw HTTP)."""
    return PHASE2_INTERFACE.get(platform, "python")


# ---------------------------------------------------------------------------
# Phase 1 envelope
# ---------------------------------------------------------------------------

# One concrete placeholder per key, matching the type the agent should
# emit. Empty lists ([]) caused Gemini Flash to occasionally short-circuit
# to an empty AIMessage — string placeholders avoid that failure mode.
PHASE1_VALUE_HINT: dict[str, dict[str, str]] = {
    "neon": {
        "data_products":   "<DPID, e.g. DP1.10022.001>",
        "sites":           "<4-letter site code, e.g. SRER>",
    },
    "gbif": {
        "taxon_keys":      "<integer GBIF taxon key>",
        "country_codes":   "<ISO 3166-1 alpha-2 code>",
        "state_provinces": "<state or province name>",
        "dataset_keys":    "<UUID of GBIF dataset>",
    },
    "usgs": {
        "sites":           "<8+ digit USGS site number, e.g. 01115170>",
        "parameter_codes": "<5-digit parameter code, e.g. 00060>",
    },
    "epa": {
        "sites":           "<EPA AQS site identifier>",
        "state_codes":     "<2-digit state FIPS code>",
        "county_codes":    "<3-digit county FIPS code>",
        "parameter_codes": "<5-digit AQS parameter code>",
        "cbsa_codes":      "<5-digit CBSA code>",
    },

    # --- held-out onboarding platforms ------------------------------------
    "argo": {
        "float_wmo_ids":   "<7-digit WMO float id, e.g. 5901172>",
        "parameters":      "<Argo variable name, e.g. TEMP, PSAL, PRES>",
    },
    "census_acs": {
        "tables":          "<ACS table id, e.g. B19013>",
        "variables":       "<ACS variable id, e.g. B19013_001E>",
        "state_codes":     "<2-digit state FIPS code, e.g. 06>",
        "county_codes":    "<3-digit county FIPS code, e.g. 075>",
        "geographies":     "<geography level, e.g. tract, county, state>",
    },
    "cmip6": {
        "source_ids":      "<CMIP6 model id, e.g. CanESM5>",
        "experiment_ids":  "<experiment id, e.g. historical, ssp585>",
        "variable_ids":    "<variable id, e.g. tas, pr>",
        "table_ids":       "<table id, e.g. Amon, day>",
        "variant_labels":  "<variant label, e.g. r1i1p1f1>",
    },
    "ensembl": {
        "gene_symbols":    "<gene symbol, e.g. BRCA2>",
        "gene_ids":        "<Ensembl gene id, e.g. ENSG00000139618>",
        "transcript_ids":  "<Ensembl transcript id, e.g. ENST00000380152>",
        "species":         "<species name, e.g. homo_sapiens>",
    },
    "inaturalist": {
        "taxon_names":     "<scientific name, e.g. Vespa velutina>",
        "taxon_ids":       "<integer iNaturalist taxon id>",
        "place_names":     "<place name, e.g. Galicia>",
        "place_ids":       "<integer iNaturalist place id>",
    },
    "matproj": {
        "material_ids":    "<Materials Project id, e.g. mp-149>",
        "formulas":        "<chemical formula, e.g. SiO2>",
        "elements":        "<element symbol, e.g. Li>",
        "chemsys":         "<chemical system, e.g. Li-Fe-O>",
        "properties":      "<MP field name, e.g. band_gap>",
    },
    "noaa_ghcn": {
        "station_ids":     "<GHCN station id, e.g. USW00094728>",
        "parameters":      "<GHCN element code, e.g. TMAX, PRCP>",
    },
    "obis": {
        "scientific_names": "<scientific name, e.g. Acanthaster planci>",
        "aphia_ids":        "<integer WoRMS AphiaID>",
    },
    "pangaea": {
        "dataset_ids":     "<PANGAEA DOI, e.g. 10.1594/PANGAEA.905471>",
        "parameters":      "<measured parameter name, e.g. Temperature>",
    },
    "usgs_eq": {
        "event_ids":       "<USGS event id, e.g. us2000ahv0>",
    },
    "vizier": {
        "catalogs":        "<VizieR catalogue id, e.g. B/psr/psr>",
        "target_names":    "<target name, e.g. J0835-4510>",
    },
}


# ---------------------------------------------------------------------------
# Keys the agent is still asked for, but that phase 1 does NOT score.
#
# The established way to stop grading a key is to leave it out of PHASE1_KEYS
# entirely — that is how `temporal_range`, `data_types` and `statistic_codes`
# are handled for usgs, and `taxa` / `has_coordinate` / `basis_of_record` for
# gbif. It works there because PHASE1_KEYS drives three things at once and all
# three are fine to drop together: the grading key set (compare.py), the JSON
# schema shown to the agent (phase1_envelope_template), and the gold handed to
# phase 2 as history (history._gold_phase1). usgs phase-2 prompts restate the
# date range in prose (21 of 22 scenarios), so losing `temporal_range` from the
# history costs nothing.
#
# These four keys cannot be dropped that way. They are the *arguments* of the
# phase-2 call — `source_id`, `wmo`, `material_ids`, `stations` — and only some
# phase-2 prompts restate them (cmip6: 6 of 21). Removing them from PHASE1_KEYS
# would leave 15 cmip6 scenarios with no way to know which models to fetch, and
# would also change the phase-1 prompt, making every existing run
# non-comparable. So they stay in PHASE1_KEYS and are excluded at the
# comparator instead.
#
# Why they are not gradable: each names an instance the source paper selected,
# not a term resolvable from the platform's own catalogue. Checked directly —
#   cmip6.source_ids   an ESGF search on the gold experiment/variable/table
#                      returns every gold model (recall 1.00) plus 30-60 more
#                      (precision 0.15-0.56). The paper's narrowing rule is in
#                      the paper.
#   argo.float_wmo_ids the Java 2008 box holds floats 5901171/5901172/5901174;
#                      which one the study followed is the study's choice.
#   matproj.material_ids, noaa_ghcn.station_ids  same shape.
#
# The agent is still asked for them, so "how often does it get the instance
# right" stays measurable as a separate statistic, and the prompt is unchanged.
# ---------------------------------------------------------------------------

PHASE1_UNGRADED: dict[str, set[str]] = {
    "cmip6":     {"source_ids"},
    "argo":      {"float_wmo_ids"},
    "matproj":   {"material_ids"},
    "noaa_ghcn": {"station_ids"},
}


def phase1_graded_keys(platform: str) -> list[str]:
    """PHASE1_KEYS minus the keys phase 1 deliberately does not score."""
    skip = PHASE1_UNGRADED.get(platform, frozenset())
    return [k for k in PHASE1_KEYS[platform] if k not in skip]


def phase1_envelope_template(platform: str) -> dict[str, list]:
    """A list-per-key template with one placeholder string per key. The
    agent fills the lists with actual identifiers (or returns an empty
    list for keys that don't apply to this scenario)."""
    hints = PHASE1_VALUE_HINT.get(platform, {})
    return {k: [hints.get(k, "<FILL>")] for k in PHASE1_KEYS[platform]}


# ---------------------------------------------------------------------------
# Phase 2 envelope
# ---------------------------------------------------------------------------

def phase2_envelope_template(platform: str) -> list[dict]:
    """List of {module, function, kwargs[, requires_pagination]} objects.

    GBIF entries include a top-level boolean `requires_pagination` —
    `pygbif.occurrences.search` is capped at 300 records per call, so the
    agent must predict whether the query will exceed that and need
    iterating `offset`.
    """
    if phase2_interface(platform) == "rest":
        # No package to introspect — `module` is the fixed namespace the
        # benchmark uses to address this API, `function` the endpoint.
        module_hint, fn_hint = _REST_ENVELOPE_HINT[platform]
        return [{
            "module": module_hint,
            "function": fn_hint,
            "kwargs": {"<query parameter>": "<value>"},
        }]
    entry: dict = {
        "module": f"{PHASE2_PACKAGE[platform]} (or one of its submodules)",
        "function": "<function name>",
        "kwargs": {"<arg>": "<value>"},
    }
    if platform == "gbif":
        entry["requires_pagination"] = "<true|false>"
    return [entry]


# (module, function) placeholders shown in the REST platforms' envelope
# template. Kept next to REST_INTERFACE_SPEC, which documents them in prose.
_REST_ENVELOPE_HINT: dict[str, tuple[str, str]] = {
    "census_acs": ("census",       "acs_data"),
    "ensembl":    ("ensembl_rest", "<endpoint name>"),
    "matproj":    ("mp_api",       "<endpoint path, e.g. materials/summary>"),
    "noaa_ghcn":  ("noaa_ncei",    "access_data"),
}


# ---------------------------------------------------------------------------
# Phase 3 envelope (shape adaptive)
# ---------------------------------------------------------------------------

_FILL_SENTINEL: Any = "<FILL>"


def _shape_shell(expected: Any) -> Any:
    """Recursively replace leaf values with a string placeholder,
    preserving dict keys and list length. Strings are used (rather than
    null) because Gemini 2.5 Flash + bound tools occasionally returns an
    empty response when JSON templates contain `null` — string sentinels
    avoid that failure mode.
    """
    if isinstance(expected, dict):
        return {k: _shape_shell(v) for k, v in expected.items()}
    if isinstance(expected, list):
        return [_shape_shell(v) for v in expected]
    return _FILL_SENTINEL


def phase3_envelope_template(expected: Any, declared_unit: str | None) -> dict:
    """Build the phase-3 output template the agent should fill in.

    Placeholder values are the string "<FILL>" (not null) — see _shape_shell.
    """
    return {
        "value": _shape_shell(expected),
        "unit": declared_unit if declared_unit is not None else "<FILL or null>",
    }


# ---------------------------------------------------------------------------
# Phase 4 envelope
# ---------------------------------------------------------------------------

def phase4_envelope_template(numeric_enabled: bool,
                             qualitative_enabled: bool) -> dict:
    """Always include `files_produced`. numeric / qualitative answers are
    only requested when their check is enabled."""
    out: dict = {"files_produced": ["<absolute path to PNG>"]}
    if numeric_enabled:
        out["numeric_answer"] = "<FILL: number>"
    if qualitative_enabled:
        out["qualitative_answer"] = "<FILL: text>"
    return out
