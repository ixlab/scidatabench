# S2. Phase 1 Key Schema

This section specifies the per-platform key schema against which Phase 1
(knowledge discovery) is graded (paper, Section 2.2, *Phase 1*). It covers
the four platforms of SciDataBench and the eleven of SciDataBench-Onboard.

## S2.1 Scoring rule

A platform indexes its content with several kinds of identifier at once, so
the agent's Phase 1 answer is a JSON object with one list per key, and the
gold is an object of the same shape. For a platform with graded key set
$\mathcal{K}$, each key $k \in \mathcal{K}$ is scored separately as a set
comparison between the agent's identifiers $A_k$ and the gold identifiers
$G_k$:

$$
P_k = \frac{|A_k \cap G_k|}{|A_k|}, \qquad
R_k = \frac{|A_k \cap G_k|}{|G_k|}, \qquad
F_{1,k} = \frac{2 P_k R_k}{P_k + R_k}.
$$

The scenario score is the unweighted mean over the platform's graded keys,
and the scenario passes when that mean reaches the threshold $\tau$:

$$
\text{score} = \frac{1}{|\mathcal{K}|} \sum_{k \in \mathcal{K}} F_{1,k},
\qquad
\text{pass} \iff \text{score} \ge \tau, \qquad \tau = 0.9 .
$$

Conventions:

- **Empty sets.** If $A_k = G_k = \varnothing$, then $F_{1,k} = 1$. If
  exactly one of the two is empty, $F_{1,k} = 0$.
- **All graded keys count, including keys the scenario does not use.** The
  mean runs over every graded key of the platform, not only the keys that
  carry a gold identifier. A key the scenario does not use contributes 1 if
  the agent leaves it empty and 0 if the agent puts anything in it. An EPA
  AQS scenario that names only a parameter code is therefore scored over five
  keys: an agent that returns the correct parameter code and nothing else
  scores 1.0, and one that also adds a site identifier scores 0.8 and fails.
- **Matching.** Identifiers are compared as exact strings, after conversion
  with `str()`. Matching is case-sensitive, and leading zeros and separators
  are significant (`00060` ≠ `60`). No other normalisation is applied.
  Order and duplicates are ignored, because both sides are compared as sets.

## S2.2 What the agent is shown

The Phase 1 prompt ends with an output template that lists every key of the
platform's prompted schema, each holding one placeholder that shows the
expected format. For example, for NEON:

```json
{
  "data_products": ["<DPID, e.g. DP1.10022.001>"],
  "sites": ["<4-letter site code, e.g. SRER>"]
}
```

## S2.3 Key schema per platform

*Scenarios* is the number of scenarios in the published set whose gold names
at least one identifier under the key. *Per scenario* is the mean number of
gold identifiers under the key, taken over those scenarios, with the maximum
in parentheses.

### SciDataBench (n = 245)

| Platform | Key | Identifier | Example | Scenarios | Per scenario |
|---|---|---|---|---:|---:|
| **NEON** (n = 23) | `data_products` | NEON data product ID | `DP1.10022.001` | 23 | 1.9 (7) |
| | `sites` | 4-letter NEON site code | `SRER` | 15 | 7.4 (36) |
| **GBIF** (n = 51) | `taxon_keys` | GBIF backbone taxon key | `2803315` | 50 | 1.9 (19) |
| | `country_codes` | ISO 3166-1 alpha-2 code | `BR` | 30 | 1.4 (5) |
| | `state_provinces` | State or province name | `Oaxaca` | 3 | 2.7 (6) |
| | `dataset_keys` | GBIF dataset UUID | `336b6790-062f-…` | 1 | 1.0 (1) |
| **USGS** (n = 160) | `sites` | USGS site number (8–15 digits) | `01594440` | 151 | 7.2 (63) |
| | `parameter_codes` | 5-digit NWIS parameter code | `00060` | 142 | 3.0 (27) |
| **EPA AQS** (n = 11) | `sites` | 9-digit AQS site ID (state + county + site) | `360551007` | 4 | 3.0 (5) |
| | `state_codes` | 2-digit state FIPS code | `12` | 3 | 1.3 (2) |
| | `county_codes` | 3-digit county FIPS code | `037` | 2 | 1.5 (2) |
| | `parameter_codes` | 5-digit AQS parameter code | `88101` | 10 | 2.9 (11) |
| | `cbsa_codes` | 5-digit CBSA code | `35620` | 1 | 4.0 (4) |

### SciDataBench-Onboard (n = 210)

| Platform | Key | Identifier | Example | Scenarios | Per scenario |
|---|---|---|---|---:|---:|
| **Argo** (n = 15) | `parameters` | Argo variable name | `TEMP`, `PSAL` | 15 | 3.7 (8) |
| **American Community Survey** (n = 22) | `tables` | ACS table ID | `B19013` | 20 | 4.0 (9) |
| | `variables` | ACS variable ID | `B19013_001E` | 5 | 3.2 (8) |
| | `state_codes` | 2-digit state FIPS code | `06` | 14 | 1.8 (6) |
| | `county_codes` | County FIPS code | `06037` | 7 | 3.1 (8) |
| | `geographies` | Census geography level | `tract` | 21 | 1.0 (1) |
| **CMIP6** (n = 29) | `experiment_ids` | Experiment ID | `ssp585` | 29 | 3.6 (9) |
| | `variable_ids` | Variable ID | `tas`, `pr` | 28 | 3.7 (15) |
| | `table_ids` | MIP table ID | `Amon` | 22 | 1.3 (3) |
| | `variant_labels` | Variant label | `r1i1p1f1` | 10 | 2.9 (10) |
| **Ensembl** (n = 30) | `gene_symbols` | Gene symbol | `POLD1` | 26 | 2.4 (11) |
| | `gene_ids` | Ensembl gene ID | `ENSG00000157388` | 7 | 1.4 (4) |
| | `transcript_ids` | Ensembl transcript ID | `ENSMUST00000212287` | 2 | 1.0 (1) |
| | `species` | Ensembl species name | `homo_sapiens` | 29 | 1.8 (8) |
| **iNaturalist** (n = 16) | `taxon_names` | Scientific name | `Apis mellifera` | 13 | 2.4 (8) |
| | `taxon_ids` | iNaturalist taxon ID | `40151` | 5 | 2.6 (9) |
| | `place_names` | Place name | `Denmark` | 10 | 1.3 (3) |
| | `place_ids` | iNaturalist place ID | `6779` | 4 | 1.0 (1) |
| **Materials Project** (n = 27) | `formulas` | Chemical formula | `KBr` | 3 | 2.3 (4) |
| | `elements` | Element symbol | `O` | 9 | 5.2 (26) |
| | `chemsys` | Chemical system | `Ga-As` | 6 | 1.0 (1) |
| | `properties` | Materials Project field name | `energy_per_atom` | 26 | 2.0 (5) |
| **NOAA GHCN** (n = 25) | `parameters` | GHCN element code | `PRCP` | 25 | 1.7 (5) |
| **OBIS** (n = 13) | `scientific_names` | Scientific name | `Acanthaster` | 13 | 1.6 (3) |
| | `aphia_ids` | WoRMS AphiaID | `206734` | 4 | 1.0 (1) |
| **PANGAEA** (n = 16) | `dataset_ids` | PANGAEA dataset DOI | `10.1594/PANGAEA.905471` | 16 | 4.0 (20) |
| | `parameters` | Measured parameter name | `Temperature` | 6 | 4.2 (6) |
| **USGS Earthquake Catalog** (n = 7) | `event_ids` | ComCat event ID | `us2000ahv0` | 7 | 1.6 (3) |
| **VizieR** (n = 10) | `catalogs` | VizieR catalogue ID | `B/psr` | 10 | 2.4 (6) |
| | `target_names` | Astronomical target name | `ILT J1101+5521` | 2 | 1.0 (1) |
