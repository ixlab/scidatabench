# S3. Phase 2 Result Equivalence

This section specifies how Phase 2 (API-call construction) is graded on the
data the calls return (paper, Section 2.2, *Phase 2*): how each side's call
outputs are merged into one table, which columns identify and compare a row,
how equivalent retrieval routes are folded together, and how the resulting
measurements become a verdict. Threshold symbols ($\epsilon_{\text{rec}}$,
$\epsilon_{\text{val}}$, $\epsilon_{\text{tim}}$, $\Omega$, $\delta$) are those
of the paper.

## S3.1 Merge specification

For each scenario, the outputs of all calls on one side (gold or agent) are
folded into a single table. A row is identified by
$\text{id}(r) = (u(r), \kappa(r))$, where $u$ is the merge unit and $\kappa$ is
the record key.

- **Record key.** A platform lists one or more candidate keys. For each
  returned table, the first candidate whose columns are all present is used,
  with column names matched case-insensitively. If no candidate is present,
  the whole row (excluding the excluded columns) becomes the identity, and
  $\text{val}$ is not computed, because the identity already contains every
  value.
- **Duplicates.** A row fetched by more than one call is kept once per side.
- **Compared columns.** $\text{val}$ is computed over the listed columns that
  both sides carry. Where the table says *all shared*, it is computed over
  every column both sides carry except the key and the excluded columns.
- **Time axis.** $\text{tim}$ uses the first listed time column that both
  sides carry, bucketed by calendar month.

### SciDataBench

| Platform | Merge unit | Record key (candidates, in order) | Time column | Compared columns |
|---|---|---|---|---|
| USGS | Kind of observation the endpoint returns (S3.2) | 1. `Result_MeasureIdentifier`<br>2. `monitoring_location_id`, `parameter_code`, `statistic_id`, `time`<br>3. `monitoring_location_id`, `parameter_code`, `time`<br>4. `field_measurement_id`<br>5. `monitoring_location_id`, `time` | `time`, `Activity_StartDate` | `value`, `unit_of_measure`, `approval_status`, `Result_Measure`, `Result_MeasureUnit`, `Result_Characteristic`, `Result_MeasureQualifierCode` |
| EPA AQS | Scenario | 1. `state_code`, `county_code`, `site_number`, `parameter_code`, `poc`, `date_local`, `sample_duration_code`, `pollutant_standard`, `event_type`<br>2. `state_code`, `county_code`, `site_number`, `parameter_code`, `poc`, `date_local` | `date_local`, `date_gmt` | `arithmetic_mean`, `first_max_value`, `first_max_hour`, `aqi`, `observation_count`, `observation_percent`, `units_of_measure`, `sample_measurement` |
| GBIF | Scenario | 1. `gbifID`<br>2. `key` | `eventDate`, `year` | `scientificName`, `taxonKey`, `speciesKey`, `acceptedTaxonKey`, `decimalLatitude`, `decimalLongitude`, `countryCode`, `stateProvince`, `eventDate`, `year`, `month`, `day`, `basisOfRecord`, `occurrenceStatus`, `datasetKey`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `species`, `taxonRank`, `individualCount` |
| NEON | Data table (S3.4) | 1. `uid`<br>2. `siteID`, `horizontalPosition`, `verticalPosition`, `startDateTime` | `collectDate`, `startDateTime`, `endDate`, `date` | All shared |

### SciDataBench-Onboard

| Platform | Merge unit | Record key (candidates, in order) | Time column | Compared columns |
|---|---|---|---|---|
| Argo | Scenario | `PLATFORM_NUMBER`, `CYCLE_NUMBER`, `PRES` | `TIME` | `TEMP`, `PSAL`, `PRES` |
| American Community Survey | (`dataset`, `year`) call arguments | 1. `state`, `county`, `tract`, `block group`<br>2. `state`, `county`, `tract`<br>3. `state`, `county`<br>4. `zip code tabulation area`<br>5. `state`, `public use microdata area`<br>6. `state`<br>7. `us` | — | All shared |
| CMIP6 | Scenario | `id` (ESGF dataset ID) | — | None (membership only) |
| Ensembl | Endpoint | `id` | — | `id`, `biotype`, `seq_region_name`, `strand`, `assembly_name`, `species`, `seq`, `molecule` |
| iNaturalist | Scenario | `id` | `observed_on` | `observed_on`, `quality_grade`, `taxon.id`, `taxon.name`, `place_ids`, `location` |
| Materials Project | Endpoint | 1. `material_id` (as returned)<br>2. `battery_id` | — | All shared |
| NOAA GHCN | Scenario | `STATION`, `DATE` | `DATE` | `TMAX`, `TMIN`, `PRCP` |
| OBIS | Scenario | `id` | `eventDate`, `date_year` | `decimalLatitude`, `decimalLongitude`, `eventDate`, `date_year`, `scientificName`, `aphiaID`, `depth`, `basisOfRecord`, `dataset_id` |
| PANGAEA | Dataset DOI (`id` call argument) | None; compared on table statistics (S3.4) | — | — |
| USGS Earthquake Catalog | Scenario | `event_id` | `time` | `latitude`, `longitude`, `depth_m`, `magnitude` |
| VizieR | Catalogue table | 1. `PSRJ`<br>2. `CompId`<br>3. `RAJ2000`, `DEJ2000`<br>4. `recno` | — | All shared |

### Excluded columns

These columns can change without the observation changing. They are never
compared and never form part of a whole-row identity.

| Platform | Columns |
|---|---|
| All | `last_updated`, `last_modified`, `lastcrawled`, `lastparsed`, `crawlid`, `date_of_last_change`, `version`, `_timestamp`, `downloaded_at`, `snapshot_utc` |
| USGS | `geometry`, `geometry_type`, `daily_id`, `continuous_id`, `field_measurement_id`, `time_series_id`, `LastChangeDate`, `qualifier` |
| EPA AQS | `latitude`, `longitude`, `datum`, `method`, `method_code`, `local_site_name`, `address`, `state`, `county`, `city`, `cbsa_code`, `cbsa` |
| GBIF | `lastCrawled`, `lastParsed`, `lastInterpreted`, `crawlId`, `protocol`, `installationKey`, `hostingOrganizationKey`, `publishingOrgKey`, `modified`, `issues`, `facts`, `relations`, `gadm`, `media`, `identifiers`, `extensions` |
| NEON | `publicationDate`, `release`, `uid` |
| Argo | `N_POINTS`, `DATA_MODE`, `DIRECTION` |
| American Community Survey | `NAME`, `NAME_1`, `GEO_ID` |
| Ensembl | `description`, `start`, `end`, `db_type`, `object_type`, `display_name`, `canonical_transcript`, `logic_name`, `source` |
| iNaturalist | `identifications`, `non_owner_ids`, `comments`, `faves`, `votes`, `reviewed_by`, `project_observations`, `updated_at`, `identifications_count`, `comments_count` |
| USGS Earthquake Catalog | `description`, `magnitude_type` |
| VizieR | `recno` |

## S3.2 Route folding (USGS)

USGS serves the same observations through two API generations, the legacy
NWIS services and the Water Data OGC APIs, and `dataretrieval` exposes both.
Two steps make the two routes compare as the same data.

**Endpoint to merge unit.** Endpoints that return the same kind of observation
share a merge unit. An endpoint not listed here forms a unit of its own name.

| Merge unit | Endpoints |
|---|---|
| daily | `get_dv`, `get_daily` |
| continuous | `get_iv`, `get_continuous` |
| samples | `get_qwdata`, `get_samples`, `get_results`, `get_usgs_samples` |
| field | `get_field_measurements`, `get_discharge_measurements`, `get_measurements`, `get_gwlevels` |
| sites | `get_info`, `get_monitoring_locations` |
| peaks | `get_peak_data`, `get_discharge_peaks` |

**NWIS columns to Water Data columns.** NWIS returns a wide table that
encodes the parameter and statistic in the column name (`00060_Mean`), whereas
Water Data returns a long table. Each NWIS value column is rewritten into
Water Data rows as follows. Tables already in the Water Data vocabulary are
left unchanged.

| NWIS | Water Data |
|---|---|
| `site_no` (`01594440`) | `monitoring_location_id` (`USGS-01594440`) |
| `datetime` | `time`, converted to UTC and truncated to the day |
| Parameter code in the column name (`00060_…`) | `parameter_code` (`00060`) |
| Statistic suffix `_Mean`, `_Max`, `_Min`, `_Sum`, `_Median`, or none | `statistic_id` `00003`, `00001`, `00002`, `00006`, `00008`, or `00003` |
| Cell value | `value` (rows with no value are dropped) |
| Approval code in `<column>_cd`: `A`, `P`, `e` (first code if several) | `approval_status`: `Approved`, `Provisional`, `Estimated` |

## S3.3 Canonicalisation

Every key cell and compared cell is canonicalised before comparison:

- Missing values (`None`, `NaN`, `NaT`, and the strings `nan`, `none`,
  `nat`, `<na>`) become empty.
- Surrounding whitespace is removed.
- A numeric value in integer form is written as an integer
  (`5901172.0` → `5901172`); any other finite number is rounded to six
  decimal places. Infinite values are kept as text.
- Everything else is compared as a string, case-sensitively.

Two cells agree ($a \simeq g$) when their canonical forms are equal, or when
both are numeric and $|a - g| / |g| \le \delta$. An empty cell agrees only
with another empty cell.

Merge-unit values taken from call arguments (PANGAEA's DOI, and the
American Community Survey's `dataset` and `year`) are matched after removing
a DOI prefix (`doi:`, `https://doi.org/`, `http://doi.org/`,
`https://dx.doi.org/`, `http://dx.doi.org/`) and folding case.

Time values are parsed as ISO 8601 with varying precision, falling back to
mixed formats, and converted to UTC before bucketing.

## S3.4 Platform-specific handling

**NEON.** A data product is delivered as one archive per site and month, each
holding several tables. Each file is assigned to its table from the file
name, and the table is the merge unit. Metadata tables (`validation`,
`categoricalCodes`, `variables`, `readme`, `sensor_positions`,
`science_review_flags`, `issueLog`, `citation`) and product-level files that
carry no month are dropped. Every table receives `siteID` from the file name.
Sensor tables also receive `horizontalPosition` and `verticalPosition`, as
NEON's `stackByTable` adds them, because the same table is published once per
sensor position. A sensor product publishes each measurement at several
averaging intervals, and on both sides only the coarsest interval is kept for
each (product, horizontal position, vertical position).

**PANGAEA.** Datasets expose no row key, so each dataset DOI (merge unit) is
compared on its shape and per-column statistics:

- *Row score:* $\max\!\left(0,\ 1 - |n_a - n_g| / n_g\right)$, where $n_a$ and
  $n_g$ are the agent and gold row counts.
- *Statistic score:* the fraction of checks that agree, over the columns both
  sides carry. For a numeric column, the sum, mean, minimum and maximum are
  each compared under $\simeq$. For any other column, the sets of non-missing
  values must be equal.

$\text{rec}$ is the mean row score over the gold DOIs, and $\text{val}$ is the
mean statistic score. $\text{tim}$ does not apply. $\text{over}$ is the number
of agent DOIs divided by the number of gold DOIs. A gold DOI that the agent
did not retrieve scores 0 on both. A gold DOI whose table is empty is not
scored.

## S3.5 Verdicts

A scenario receives exactly one verdict, checked in this order:

| Verdict | Condition | Counted as pass |
|---|---|---|
| NO-ANSWER | The agent declared no call, or only calls that configure the client or consume another call's output | No |
| NOT-CALLABLE | The agent declared a retrieval call, but none returned data (error, timeout, or not a callable function) | No |
| WRONG-SLICE | Data was returned but fails the pass criterion, including returned tables with no rows or no usable column | No |
| OVER-BROAD | The pass criterion holds and $\text{over} > 1 + \epsilon_{\text{over}}$ | Yes |
| PASS | The pass criterion holds and $\text{over} \le 1 + \epsilon_{\text{over}}$ | Yes |

The pass criterion is the one in the paper:

$$
\text{rec} \ge 1-\epsilon_{\text{rec}} \;\wedge\;
\text{val} \ge 1-\epsilon_{\text{val}} \;\wedge\;
\text{tim} \ge 1-\epsilon_{\text{tim}} \;\wedge\;
\text{over} \le \Omega .
$$

A measurement that does not apply is omitted from the conjunction:

- $\text{val}$ does not apply when the result is membership only (CMIP6), when
  the result is identified by the whole row, or when the two sides share no
  compared column.
- $\text{tim}$ does not apply when the platform has no time column, when the
  time column is missing from one side, or when the gold time column cannot
  be parsed.
