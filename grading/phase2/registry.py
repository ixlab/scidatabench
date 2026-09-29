"""Per-platform merge and comparison rules for Phase 2 (supplementary S3).

Three things have to be fixed per platform before results can be compared:

    merge unit   which calls fold into one table
    record key   what names a row, independently of the path taken to fetch it
    value cols   which columns are compared; everything else is ignored

Row identity is `(merge unit, record key)`. The unit is part of the identity
because several platforms return different columns for the same key under
different units — Materials Project's `summary` and `thermo` endpoints both
key on `material_id` but carry disjoint fields, and merging on the key alone
would collide them.

Every column list and uniqueness claim here was checked against the gold
snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Columns whose value changes without the observation changing. Excluded from
# value comparison everywhere.
GLOBAL_VOLATILE = frozenset({
    "last_updated", "last_modified", "lastcrawled", "lastparsed", "crawlid",
    "date_of_last_change", "version", "_timestamp", "downloaded_at",
    "snapshot_utc",
})


@dataclass(frozen=True)
class PlatformSpec:
    result_type: str = "relation"      # relation | id_set | record | table_stats
    # Row key. Columns are looked up case-insensitively; a spec may list
    # alternatives and the first fully-present option wins.
    key: tuple[tuple[str, ...], ...] = ()
    # Where the merge unit comes from: "function" (the endpoint the agent
    # called), "call_kwarg:<name>", "table" (vizier's per-table split), or
    # "" for a single unit per scenario.
    unit_from: str = ""
    # Optional folding applied to a "function" unit: maps an endpoint name to
    # the KIND OF DATA it returns. Without it the unit is the endpoint string,
    # so two endpoints that serve the same observations through different
    # APIs never meet and the agent scores zero coverage on data it actually
    # retrieved — which is the opposite of what result equivalence is for.
    unit_map: dict = field(default_factory=dict)
    time_col: tuple[str, ...] = ()     # first present is used; () = no time axis
    # Value columns. Empty means "compare whatever gold and agent share",
    # minus volatile and minus the key itself.
    value_cols: tuple[str, ...] = ()
    volatile: frozenset[str] = field(default_factory=frozenset)
    # Round timestamps to this bucket for time coverage.
    time_bucket: str = "M"             # M = month, Y = year, D = day
    note: str = ""


REGISTRY: dict[str, PlatformSpec] = {

    # --- SciDataBench ----------------------------------------------------
    "usgs": PlatformSpec(
        # One package, two generations of API, four unrelated schemas. USGS is
        # migrating NWIS to the Water Data (OGC) APIs; gold is written against
        # the new ones, and agents reach for both. `nwis.get_dv` and
        # `waterdata.get_daily` return the SAME observations — checked against
        # the live services for site 01594440, 1985-2017: 12,053 rows each,
        # every date shared, every value identical to 1e-9 — they just present
        # them differently (see _normalise_usgs). Folding them onto one unit is
        # what lets the metric grade the data instead of the endpoint.
        #
        # Daily and instantaneous stay APART: `get_dv`/`get_daily` are daily
        # aggregates and `get_iv`/`get_continuous` are the sub-hourly series.
        # Same subject, different observations.
        unit_from="function",
        unit_map={
            "get_dv": "daily", "get_daily": "daily",
            "get_iv": "continuous", "get_continuous": "continuous",
            "get_samples": "samples", "get_qwdata": "samples",
            "get_results": "samples", "get_usgs_samples": "samples",
            "get_field_measurements": "field",
            "get_discharge_measurements": "field",
            "get_measurements": "field", "get_gwlevels": "field",
            "get_info": "sites", "get_monitoring_locations": "sites",
            "get_discharge_peaks": "peaks", "get_peak_data": "peaks",
        },
        # `time_series_id` is deliberately NOT in the key. It is a waterdata
        # surrogate with no NWIS counterpart, and the key is chosen per frame,
        # so keying on it would make gold and a normalised NWIS frame pick
        # different keys and never match. The cost is that several continuous
        # series at one site and parameter collapse onto one row identity —
        # identically on both sides, so coverage stays comparable.
        key=(("Result_MeasureIdentifier",),                   # samples
             ("monitoring_location_id", "parameter_code",
              "statistic_id", "time"),                        # daily/continuous
             ("monitoring_location_id", "parameter_code", "time"),
             ("field_measurement_id",),
             ("monitoring_location_id", "time")),
        time_col=("time", "Activity_StartDate"),
        value_cols=("value", "unit_of_measure", "approval_status",
                    "Result_Measure", "Result_MeasureUnit",
                    "Result_Characteristic", "Result_MeasureQualifierCode"),
        # The `*_id` columns are per-response surrogates the service re-issues;
        # `geometry` is the site point repeated on every row.
        volatile=frozenset({"geometry", "geometry_type", "last_modified",
                            "daily_id", "continuous_id", "field_measurement_id",
                            "time_series_id", "LastChangeDate", "qualifier"}),
        note="NWIS and Water Data endpoints are folded onto one unit per kind "
             "of observation; see _normalise_usgs for the column mapping",
    ),
    "epa": PlatformSpec(
        key=(("state_code", "county_code", "site_number", "parameter_code",
              "poc", "date_local", "sample_duration_code",
              "pollutant_standard", "event_type"),                  # 6/6
             ("state_code", "county_code", "site_number", "parameter_code",
              "poc", "date_local")),
        time_col=("date_local", "date_gmt"),
        value_cols=("arithmetic_mean", "first_max_value", "first_max_hour",
                    "aqi", "observation_count", "observation_percent",
                    "units_of_measure", "sample_measurement"),
        # The monitor's coordinates and the method text are metadata that AQS
        # revises without the measurement changing.
        volatile=frozenset({"latitude", "longitude", "datum", "method",
                            "method_code", "local_site_name", "address",
                            "state", "county", "city", "cbsa_code", "cbsa",
                            "date_of_last_change"}),
        note="site x parameter x POC x day, split by averaging period and "
             "standard — a monitor reports the same day under several",
    ),
    "gbif": PlatformSpec(
        # `gbifID` first, `key` second. The two carry the SAME occurrence id —
        # checked on a 59-record scenario, 59/59 identical — but which one is
        # present depends on how the records were fetched. Gold mostly comes
        # from the Download API's simple CSV, which names it `gbifID` and has
        # no `key` at all (111 of 133 gold calls); the Search API returns both.
        # Keying on `key` alone left gold with no named key, so it fell back to
        # whole-row identity while the agent keyed on `key` — nothing could
        # ever match, and all 74 scenarios scored record_cov ~0 against agents
        # that had in fact retrieved MORE rows than gold (median over = 1.17).
        key=(("gbifID",), ("key",)),
        time_col=("eventDate", "year"),
        # An occurrence record carries 40+ columns, most of them GBIF's own
        # interpretation bookkeeping. Compare what the scenario is about:
        # what was seen, where, when, and on what evidence.
        value_cols=("scientificName", "taxonKey", "speciesKey", "acceptedTaxonKey",
                    "decimalLatitude", "decimalLongitude", "countryCode",
                    "stateProvince", "eventDate", "year", "month", "day",
                    "basisOfRecord", "occurrenceStatus", "datasetKey",
                    "kingdom", "phylum", "class", "order", "family", "genus",
                    "species", "taxonRank", "individualCount"),
        volatile=frozenset({"lastCrawled", "lastParsed", "lastInterpreted",
                            "crawlId", "protocol", "installationKey",
                            "hostingOrganizationKey", "publishingOrgKey",
                            "modified", "issues", "facts", "relations",
                            "gadm", "media", "identifiers", "extensions"}),
        note="`key` is GBIF's stable occurrence id and is unique per response",
    ),
    "neon": PlatformSpec(
        # A NEON product ships one zip per site-month, and each zip holds
        # several unrelated tables (bet_sorting, bet_fielddata, ...). The
        # table is the merge unit; `uid` identifies a row inside it and is
        # stable across releases.
        unit_from="table",
        # Observational tables carry `uid`. Instrumented (sensor) tables do
        # not: a row there is one averaging interval at one sensor position,
        # so it is identified by site, position and interval start. The
        # position columns are injected from the filename when the zip is
        # stacked (grader._neon_parse), as NEON's stackByTable does.
        key=(("uid",),
             ("siteID", "horizontalPosition", "verticalPosition",
              "startDateTime")),
        time_col=("collectDate", "startDateTime", "endDate", "date"),
        value_cols=(),                  # schema differs per table
        volatile=frozenset({"publicationDate", "release", "uid"}),
        note="metadata tables (variables, validation, categoricalCodes, "
             "readme, ...) are dropped before merging — see NEON_META_TABLES",
    ),

    # --- SciDataBench-Onboard ---------------------------------------------

    # --- A. stable schema, clear key ------------------------------------
    "argo": PlatformSpec(
        key=(("PLATFORM_NUMBER", "CYCLE_NUMBER", "PRES"),),
        time_col=("TIME",),
        value_cols=("TEMP", "PSAL", "PRES"),
        # N_POINTS is an index produced by xarray -> dataframe, not data.
        volatile=frozenset({"N_POINTS", "DATA_MODE", "DIRECTION"}),
        note="one row per (float, cycle, depth); *_QC and *_ERROR ignored",
    ),
    "noaa_ghcn": PlatformSpec(
        key=(("STATION", "DATE"),),
        time_col=("DATE",),
        value_cols=("TMAX", "TMIN", "PRCP"),
        note="station x date, the same shape as USGS/EPA",
    ),
    "usgs_eq": PlatformSpec(
        key=(("event_id",),),
        time_col=("time",),
        value_cols=("latitude", "longitude", "depth_m", "magnitude"),
        # Event descriptions get reworded by the catalogue.
        volatile=frozenset({"description", "magnitude_type"}),
    ),
    "cmip6": PlatformSpec(
        result_type="id_set",
        key=(("id",),),
        note="ESGF dataset listing, not the climate data; `version` excluded "
             "because a re-published dataset changes it",
    ),
    "matproj": PlatformSpec(
        key=(("material_id",), ("battery_id",)),
        unit_from="function",           # summary / thermo / elasticity / ...
        value_cols=(),                  # whatever _fields the scenario asked for
        note="key on the RETURNED material_id: MP re-issued its ids, so the "
             "queried id may not appear in the response at all",
    ),

    # --- B. sparse schema, key present ----------------------------------
    "obis": PlatformSpec(
        key=(("id",),),
        time_col=("eventDate", "date_year"),
        value_cols=("decimalLatitude", "decimalLongitude", "eventDate",
                    "date_year", "scientificName", "aphiaID", "depth",
                    "basisOfRecord", "dataset_id"),
        note="188-column-wide sparse union; compare a core set, never the "
             "column set itself",
    ),
    "inaturalist": PlatformSpec(
        key=(("id",),),
        time_col=("observed_on",),
        value_cols=("observed_on", "quality_grade", "taxon.id", "taxon.name",
                    "place_ids", "location"),
        # Identification threads keep growing on old observations.
        volatile=frozenset({"identifications", "non_owner_ids", "comments",
                            "faves", "votes", "reviewed_by",
                            "project_observations", "updated_at",
                            "identifications_count", "comments_count"}),
    ),

    # --- C. schema differs per dataset ----------------------------------
    "census_acs": PlatformSpec(
        key=(("state", "county", "tract", "block group"),
             ("state", "county", "tract"),
             ("state", "county"),
             ("zip code tabulation area",),
             ("state", "public use microdata area"),
             ("state",),
             ("us",)),
        unit_from="call_kwarg:dataset+year",
        value_cols=(),                  # the requested _E variables
        # NAME is a place label that gets revised; GEO_ID duplicates the key.
        volatile=frozenset({"NAME", "NAME_1", "GEO_ID"}),
        note="PUMS is excluded from the benchmark: anonymisation leaves no "
             "row identifier (96.7% of rows duplicate another row)",
    ),
    "pangaea": PlatformSpec(
        result_type="table_stats",      # no row key exists
        unit_from="call_kwarg:id",      # the dataset DOI
        note="72% of columns are float and DOIs pin the version, so compare "
             "row count + column set + per-column summary statistics rather "
             "than hashing the table",
    ),
    "vizier": PlatformSpec(
        unit_from="table",              # one call returns a TableList
        key=(("PSRJ",), ("CompId",), ("RAJ2000", "DEJ2000"), ("recno",)),
        value_cols=(),
        volatile=frozenset({"recno"}),
        note="published catalogues; coordinates key the ones with no id column",
    ),
    "ensembl": PlatformSpec(
        result_type="record",
        key=(("id",),),
        unit_from="function",
        # `start`/`end` move between Ensembl releases, so they are reported
        # but do not decide the verdict; see the markdown registry.
        # `seq` is the payload of the sequence_id endpoint and is compared
        # directly; it is stable unless the assembly changes, which
        # `assembly_name` catches.
        value_cols=("id", "biotype", "seq_region_name", "strand",
                    "assembly_name", "species", "seq", "molecule"),
        volatile=frozenset({"version", "description", "start", "end",
                            "db_type", "object_type", "display_name",
                            "canonical_transcript", "logic_name", "source"}),
    ),
}


def spec_for(platform: str) -> PlatformSpec:
    return REGISTRY.get(platform, PlatformSpec())


def is_volatile(platform: str, column: str) -> bool:
    c = str(column).strip().lower()
    if c in GLOBAL_VOLATILE:
        return True
    return c in {v.lower() for v in spec_for(platform).volatile}
