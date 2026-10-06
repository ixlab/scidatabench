# SciDataBench-Onboard

210 scenarios over eleven further scientific data platforms, built the same way as SciDataBench and covering its first two phases: knowledge discovery (Phase 1) and API-call construction (Phase 2).

## Contents

| Platform | Folder | Scenarios |
|---|---|---:|
| Argo | `argo/` | 15 |
| American Community Survey | `census_acs/` | 22 |
| CMIP6 | `cmip6/` | 29 |
| Ensembl | `ensembl/` | 30 |
| iNaturalist | `inaturalist/` | 16 |
| Materials Project | `matproj/` | 27 |
| NOAA GHCN | `noaa_ghcn/` | 25 |
| OBIS | `obis/` | 13 |
| PANGAEA | `pangaea/` | 16 |
| USGS Earthquake Catalog | `usgs_eq/` | 7 |
| VizieR | `vizier/` | 10 |
| **Total** | | **210** |

Each scenario is one JSON file, `<platform>/<scenario>.json`. `papers.csv` lists the source paper of every scenario.

## Scenario fields

| Field | Content |
|---|---|
| `source_doi` | DOI of the paper the scenario is built from |
| `research_question` | The paper's research question |
| `phase_1.user_prompt` | Request for the platform identifiers |
| `phase_1.expected` | Gold identifiers, one list per key of the platform's schema |
| `phase_2.user_prompt` | Request for the data |
| `phase_2.expected` | Gold calls, each with `module`, `function` and `kwargs` |

## Source papers

### Argo (15)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| BoBBLE: Ocean–Atmosphere Interaction and Its Impact on the South Asian Monsoon | P. N. Vinayachandran | 2018 | Bulletin of the American Meteorological Society | [10.1175/bams-d-16-0230.1](https://doi.org/10.1175/bams-d-16-0230.1) |
| Coastal upwelling events along the southern coast of Java during the 2008 positive Indian Ocean Dipole | Takanori Horii | 2018 | Journal of Oceanography | [10.1007/s10872-018-0475-z](https://doi.org/10.1007/s10872-018-0475-z) |
| Continuous Flow of Upper Labrador Sea Water around Cape Hatteras | Magdalena Andres | 2018 | Scientific Reports | [10.1038/s41598-018-22758-z](https://doi.org/10.1038/s41598-018-22758-z) |
| Iron from a submarine source impacts the productive layer of the Western Tropical South Pacific (WTSP) | Cécile Guieu | 2018 | Scientific Reports | [10.1038/s41598-018-27407-z](https://doi.org/10.1038/s41598-018-27407-z) |
| Observed Warming of Sea Surface Temperature in Response to Tropical Cyclone Thane in the Bay of Bengal | Simi Mathew | 2018 | Current Science | [10.18520/cs/v114/i07/1407-1413](https://doi.org/10.18520/cs/v114/i07/1407-1413) |
| On the Steadiness and Instability of the Intermediate Western Boundary Current between 24° and 18°S | Dante C. Napolitano | 2019 | Journal of Physical Oceanography | [10.1175/jpo-d-19-0011.1](https://doi.org/10.1175/jpo-d-19-0011.1) |
| Percampuran Turbulen Di Tenggara Samudera Hindia Saat Siklon Tropis Marcus Menggunakan Data ARGO Float | Muhammad Hafidz Ibnu Khaldun | 2020 | Journal of Marine and Aquatic Sciences | [10.24843/jmas.2020.v06.i02.p17](https://doi.org/10.24843/jmas.2020.v06.i02.p17) |
| Remote assessment of the fate of phytoplankton in the Southern Ocean sea-ice zone | Sébastien Moreau | 2020 | Nature Communications | [10.1038/s41467-020-16931-0](https://doi.org/10.1038/s41467-020-16931-0) |
| 2019‒2020 Australian bushfire air particulate pollution and impact on the South Pacific Ocean | Mengyu Li | 2021 | Scientific Reports | [10.1038/s41598-021-91547-y](https://doi.org/10.1038/s41598-021-91547-y) |
| Double-diffusive mixing makes a small contribution to the global ocean circulation | Carine G. van der Boog | 2021 | Communications Earth & Environment | [10.1038/s43247-021-00113-x](https://doi.org/10.1038/s43247-021-00113-x) |
| Glider observations of thermohaline staircases in the tropical North Atlantic using an automated classifier | Callum Rollo | 2022 | Geoscientific instrumentation, methods and data systems | [10.5194/gi-11-359-2022](https://doi.org/10.5194/gi-11-359-2022) |
| Process-Oriented Estimation of Chlorophyll-a Vertical Profile in the Mediterranean Sea Using MODIS and Oceanographic Float Products | Xiaojuan Li | 2022 | Frontiers in Marine Science | [10.3389/fmars.2022.933680](https://doi.org/10.3389/fmars.2022.933680) |
| Efficient biological carbon export to the mesopelagic ocean induced by submesoscale fronts | Mingxian Guo | 2024 | Nature Communications | [10.1038/s41467-024-44846-7](https://doi.org/10.1038/s41467-024-44846-7) |
| Marine heatwaves are shaping the vertical structure of phytoplankton in the global ocean | Xueying Ma | 2025 | Communications Earth & Environment | [10.1038/s43247-025-02718-y](https://doi.org/10.1038/s43247-025-02718-y) |
| BGC-Argo float reveals shifts in nitrogen-carbon cycling in an oxygen-deficient zone | Mariana B. Bif | 2026 | Communications Earth & Environment | [10.1038/s43247-026-03410-5](https://doi.org/10.1038/s43247-026-03410-5) |

### American Community Survey (22)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Disparities in rooftop photovoltaics deployment in the United States by race and ethnicity | Deborah A. Sunter | 2019 | Nature Sustainability | [10.1038/s41893-018-0204-z](https://doi.org/10.1038/s41893-018-0204-z) |
| Addressing Food Insecurity through a Health Equity Lens: a Case Study of Large Urban School Districts during the COVID-19 Pandemic | Gabriella M. McLoughlin | 2020 | Journal of Urban Health | [10.1007/s11524-020-00476-0](https://doi.org/10.1007/s11524-020-00476-0) |
| Association Between State-Level Income Inequality and COVID-19 Cases and Mortality in the USA | Carlos Irwin A. Oronce | 2020 | Journal of General Internal Medicine | [10.1007/s11606-020-05971-3](https://doi.org/10.1007/s11606-020-05971-3) |
| Rental Housing Spot Markets: How Online Information Exchanges Can Supplement Transacted-Rents Data | Geoff Boeing | 2020 | Journal of Planning Education and Research | [10.1177/0739456x20904435](https://doi.org/10.1177/0739456x20904435) |
| Who’s ditching the bus? | Simon Berrebi | 2020 | Transportation Research Part A Policy and Practice | [10.1016/j.tra.2020.02.016](https://doi.org/10.1016/j.tra.2020.02.016) |
| Geographic disparities in violent crime during the COVID-19 lockdown in Miami-Dade County, Florida, 2018–2020 | Imelda K. Moise | 2021 | Journal of Experimental Criminology | [10.1007/s11292-021-09474-x](https://doi.org/10.1007/s11292-021-09474-x) |
| Impact of Race and Socioeconomic Status on Outcomes in Patients Hospitalized with COVID-19 | Daniel Quan | 2021 | Journal of General Internal Medicine | [10.1007/s11606-020-06527-1](https://doi.org/10.1007/s11606-020-06527-1) |
| Multi-Level Socioenvironmental Contributors to Childhood Asthma in New York City: a Cluster Analysis | Sana Khan | 2021 | Journal of Urban Health | [10.1007/s11524-021-00582-7](https://doi.org/10.1007/s11524-021-00582-7) |
| Neighborhood Poverty and Incident Heart Failure: an Analysis of Electronic Health Records from 2005 to 2018 | Leah Rethy | 2021 | Journal of General Internal Medicine | [10.1007/s11606-021-06785-7](https://doi.org/10.1007/s11606-021-06785-7) |
| Neighborhood characteristics associated with COVID-19 burden—the modifying effect of age | Xueying Zhang | 2021 | Journal of Exposure Science & Environmental Epidemiology | [10.1038/s41370-021-00329-1](https://doi.org/10.1038/s41370-021-00329-1) |
| Small area estimation of socioeconomic indicators for sampled and unsampled domains | Jan Pablo Burgard | 2021 | AStA Advances in Statistical Analysis | [10.1007/s10182-021-00426-4](https://doi.org/10.1007/s10182-021-00426-4) |
| The Impact of Socioeconomic Status on the Clinical Outcomes of COVID-19; a Retrospective Cohort Study | C. C. Little | 2021 | Journal of Community Health | [10.1007/s10900-020-00944-3](https://doi.org/10.1007/s10900-020-00944-3) |
| The relationship between air pollutants and maternal socioeconomic factors on preterm birth in California urban counties | Zesemayat K. Mekonnen | 2021 | Journal of Exposure Science & Environmental Epidemiology | [10.1038/s41370-021-00323-7](https://doi.org/10.1038/s41370-021-00323-7) |
| A Method for Measuring Coupled Individual and Social Vulnerability to Environmental Hazards | Joe Tuccillo | 2022 | Annals of the American Association of Geographers | [10.1080/24694452.2021.1989283](https://doi.org/10.1080/24694452.2021.1989283) |
| Commute distance and jobs-housing fit | Evelyn Blumenberg | 2022 | Transportation | [10.1007/s11116-022-10264-1](https://doi.org/10.1007/s11116-022-10264-1) |
| Neighborhood Racial and Economic Privilege and Timing of Pubertal Onset in Girls | Julia Acker | 2022 | Journal of Adolescent Health | [10.1016/j.jadohealth.2022.10.013](https://doi.org/10.1016/j.jadohealth.2022.10.013) |
| Neighborhood segregation and cognitive change: Multi‐Ethnic Study of Atherosclerosis | Lilah M. Besser | 2022 | Alzheimer s & Dementia | [10.1002/alz.12705](https://doi.org/10.1002/alz.12705) |
| Socioeconomic biases in urban mixing patterns of US metropolitan areas | Rafiazka Millanida Hilman | 2022 | EPJ Data Science | [10.1140/epjds/s13688-022-00341-x](https://doi.org/10.1140/epjds/s13688-022-00341-x) |
| Structural racism is associated with adverse postnatal outcomes among Black preterm infants | Kayla L. Karvonen | 2022 | Pediatric Research | [10.1038/s41390-022-02445-6](https://doi.org/10.1038/s41390-022-02445-6) |
| American Community Survey (ACS) Data Uncertainty and the Analysis of Segregation Dynamics | Ran Wei | 2023 | Population Research and Policy Review | [10.1007/s11113-023-09754-6](https://doi.org/10.1007/s11113-023-09754-6) |
| Association between passively collected walking and bicycling data and purposefully collected active commuting survey data—United States, 2019 | Graycie W. Soto | 2023 | Health & Place | [10.1016/j.healthplace.2023.103002](https://doi.org/10.1016/j.healthplace.2023.103002) |
| Boil water alerts and their impact on the unexcused absence rate in public schools in Jackson, Mississippi | Myungjin Kim | 2023 | Nature Water | [10.1038/s44221-023-00062-z](https://doi.org/10.1038/s44221-023-00062-z) |

### CMIP6 (29)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| CMIP6 Models Predict Significant 21st Century Decline of the Atlantic Meridional Overturning Circulation | Wilbert Weijer | 2020 | Geophysical Research Letters | [10.1029/2019gl086075](https://doi.org/10.1029/2019gl086075) |
| Future Changes in Climate over the Arabian Peninsula based on CMIP6 Multimodel Simulations | Mansour Almazroui | 2020 | Earth Systems and Environment | [10.1007/s41748-020-00183-5](https://doi.org/10.1007/s41748-020-00183-5) |
| Greater Greenland Ice Sheet contribution to global sea level rise in CMIP6 | Stefan Hofer | 2020 | Nature Communications | [10.1038/s41467-020-20011-8](https://doi.org/10.1038/s41467-020-20011-8) |
| How will southern hemisphere subtropical anticyclones respond to global warming? Mechanisms and seasonality in CMIP5 and CMIP6 model projections | Abdullah Al Fahad | 2020 | Climate Dynamics | [10.1007/s00382-020-05290-7](https://doi.org/10.1007/s00382-020-05290-7) |
| Indian Ocean Dipole in CMIP5 and CMIP6: characteristics, biases, and links to ENSO | Sebastian McKenna | 2020 | Scientific Reports | [10.1038/s41598-020-68268-9](https://doi.org/10.1038/s41598-020-68268-9) |
| Model uncertainties in climate change impacts on Sahel precipitation in ensembles of CMIP5 and CMIP6 simulations | Paul‐Arthur Monerie | 2020 | Climate Dynamics | [10.1007/s00382-020-05332-0](https://doi.org/10.1007/s00382-020-05332-0) |
| Progress in Simulating the Quasi‐Biennial Oscillation in CMIP Models | Jadwiga H. Richter | 2020 | Journal of Geophysical Research Atmospheres | [10.1029/2019jd032362](https://doi.org/10.1029/2019jd032362) |
| Projected Change in Temperature and Precipitation Over Africa from CMIP6 | Mansour Almazroui | 2020 | Earth Systems and Environment | [10.1007/s41748-020-00161-x](https://doi.org/10.1007/s41748-020-00161-x) |
| Projections of Precipitation and Temperature over the South Asian Countries in CMIP6 | Mansour Almazroui | 2020 | Earth Systems and Environment | [10.1007/s41748-020-00157-7](https://doi.org/10.1007/s41748-020-00157-7) |
| The global energy balance as represented in CMIP6 climate models | Martin Wild | 2020 | Climate Dynamics | [10.1007/s00382-020-05282-7](https://doi.org/10.1007/s00382-020-05282-7) |
| Tracking Improvement in Simulated Marine Biogeochemistry Between CMIP5 and CMIP6 | Roland Séférian | 2020 | Current Climate Change Reports | [10.1007/s40641-020-00160-0](https://doi.org/10.1007/s40641-020-00160-0) |
| Assessment of CMIP6 Performance and Projected Temperature and Precipitation Changes Over South America | Mansour Almazroui | 2021 | Earth Systems and Environment | [10.1007/s41748-021-00233-6](https://doi.org/10.1007/s41748-021-00233-6) |
| Evidence of anthropogenic impacts on global drought frequency, duration, and intensity | Felicia Chiang | 2021 | Nature Communications | [10.1038/s41467-021-22314-w](https://doi.org/10.1038/s41467-021-22314-w) |
| New climate models reveal faster and larger increases in Arctic precipitation than previously projected | Michelle McCrystall | 2021 | Nature Communications | [10.1038/s41467-021-27031-y](https://doi.org/10.1038/s41467-021-27031-y) |
| Next-generation ensemble projections reveal higher climate risks for marine ecosystems | Derek P. Tittensor | 2021 | Nature Climate Change | [10.1038/s41558-021-01173-9](https://doi.org/10.1038/s41558-021-01173-9) |
| Projected Changes in Temperature and Precipitation Over the United States, Central America, and the Caribbean in CMIP6 GCMs | Mansour Almazroui | 2021 | Earth Systems and Environment | [10.1007/s41748-021-00199-5](https://doi.org/10.1007/s41748-021-00199-5) |
| Projected future daily characteristics of African precipitation based on global (CMIP5, CMIP6) and regional (CORDEX, CORDEX-CORE) climate models | Alessandro Dosio | 2021 | Climate Dynamics | [10.1007/s00382-021-05859-w](https://doi.org/10.1007/s00382-021-05859-w) |
| The Climatic Analysis of Summer Monsoon Extreme Precipitation Events over West Africa in CMIP6 Simulations | Nana Ama Browne Klutse | 2021 | Earth Systems and Environment | [10.1007/s41748-021-00203-y](https://doi.org/10.1007/s41748-021-00203-y) |
| Uncertainty of ENSO-amplitude projections in CMIP5 and CMIP6 models | Goratz Beobide‐Arsuaga | 2021 | Climate Dynamics | [10.1007/s00382-021-05673-4](https://doi.org/10.1007/s00382-021-05673-4) |
| Advanced Testing of Low, Medium, and High ECS CMIP6 GCM Simulations Versus ERA5‐T2m | Nicola Scafetta | 2022 | Geophysical Research Letters | [10.1029/2022gl097716](https://doi.org/10.1029/2022gl097716) |
| CMIP6 GCM ensemble members versus global surface temperatures | Nicola Scafetta | 2022 | Climate Dynamics | [10.1007/s00382-022-06493-w](https://doi.org/10.1007/s00382-022-06493-w) |
| Change in Precipitation over the Tibetan Plateau Projected by Weighted CMIP6 Models | Yin Zhao | 2022 | Advances in Atmospheric Sciences | [10.1007/s00376-022-1401-2](https://doi.org/10.1007/s00376-022-1401-2) |
| Constrained CMIP6 projections indicate less warming and a slower increase in water availability across Asia | Yuanfang Chai | 2022 | Nature Communications | [10.1038/s41467-022-31782-7](https://doi.org/10.1038/s41467-022-31782-7) |
| Evidence of localised Amazon rainforest dieback in CMIP6 models | Isobel Parry | 2022 | Earth System Dynamics | [10.5194/esd-13-1667-2022](https://doi.org/10.5194/esd-13-1667-2022) |
| Land transpiration-evaporation partitioning errors responsible for modeled summertime warm bias in the central United States | Jianzhi Dong | 2022 | Nature Communications | [10.1038/s41467-021-27938-6](https://doi.org/10.1038/s41467-021-27938-6) |
| The Biophysical Impacts of Deforestation on Precipitation: Results from the CMIP6 Model Intercomparison | Xing Luo | 2022 | Journal of Climate | [10.1175/jcli-d-21-0689.1](https://doi.org/10.1175/jcli-d-21-0689.1) |
| CMIP6 precipitation and temperature projections for Chile | Álvaro Salazar | 2023 | Climate Dynamics | [10.1007/s00382-023-07034-9](https://doi.org/10.1007/s00382-023-07034-9) |
| Observationally-constrained projections of an ice-free Arctic even under a low emission scenario | Yeon‐Hee Kim | 2023 | Nature Communications | [10.1038/s41467-023-38511-8](https://doi.org/10.1038/s41467-023-38511-8) |
| Hydrological Projections under CMIP5 and CMIP6: Sources and Magnitudes of Uncertainty | Yi Wu | 2024 | Bulletin of the American Meteorological Society | [10.1175/bams-d-23-0104.1](https://doi.org/10.1175/bams-d-23-0104.1) |

### Ensembl (30)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| A genome-wide association study in the Japanese population identifies the 12q24 locus for habitual coffee consumption: The J-MICC Study | Hiroko Nakagawa‐Senda | 2018 | Scientific Reports | [10.1038/s41598-018-19914-w](https://doi.org/10.1038/s41598-018-19914-w) |
| ADIPOR1 is essential for vision and its RPE expression is lost in the Mfrprd6 mouse | Valentin M. Sluch | 2018 | Scientific Reports | [10.1038/s41598-018-32579-9](https://doi.org/10.1038/s41598-018-32579-9) |
| Aminode: Identification of Evolutionary Constraints in the Human Proteome | Kevin T. Chang | 2018 | Scientific Reports | [10.1038/s41598-018-19744-w](https://doi.org/10.1038/s41598-018-19744-w) |
| DNA Methylation of T1R1 Gene in the Vegetarian Adaptation of Grass Carp Ctenopharyngodon idella | Wenjing Cai | 2018 | Scientific Reports | [10.1038/s41598-018-25121-4](https://doi.org/10.1038/s41598-018-25121-4) |
| Dual biomarkers long non-coding RNA GAS5 and microRNA-34a co-expression signature in common solid tumors | Eman A. Toraih | 2018 | PLoS ONE | [10.1371/journal.pone.0198231](https://doi.org/10.1371/journal.pone.0198231) |
| Effects of SCFA on the DNA methylation pattern of adiponectin and resistin in high-fat-diet-induced obese male mice | Yuanyuan Lu | 2018 | British Journal Of Nutrition | [10.1017/s0007114518001526](https://doi.org/10.1017/s0007114518001526) |
| Evidences for a New Role of miR-214 in Chondrogenesis | Vânia Palma Roberto | 2018 | Scientific Reports | [10.1038/s41598-018-21735-w](https://doi.org/10.1038/s41598-018-21735-w) |
| Sixteen diverse laboratory mouse reference genomes define strain-specific haplotypes and novel functional loci | Jingtao Lilue | 2018 | Nature Genetics | [10.1038/s41588-018-0223-8](https://doi.org/10.1038/s41588-018-0223-8) |
| Bivariate genome-wide association analyses of the broad depression phenotype combined with major depressive disorder, bipolar disorder or schizophrenia reveal eight novel genetic loci for depression | Azmeraw T. Amare | 2019 | Molecular Psychiatry | [10.1038/s41380-018-0336-6](https://doi.org/10.1038/s41380-018-0336-6) |
| E2F1 mediates the downregulation of POLD1 in replicative senescence | Shichao Gao | 2019 | Cellular and Molecular Life Sciences | [10.1007/s00018-019-03070-z](https://doi.org/10.1007/s00018-019-03070-z) |
| SNRPB promotes the tumorigenic potential of NSCLC in part by regulating RAB26 | Nianli Liu | 2019 | Cell Death and Disease | [10.1038/s41419-019-1929-y](https://doi.org/10.1038/s41419-019-1929-y) |
| Synchronous inhibition of mTOR and VEGF/NRP1 axis impedes tumor growth and metastasis in renal cancer | Krishnendu Pal | 2019 | npj Precision Oncology | [10.1038/s41698-019-0105-2](https://doi.org/10.1038/s41698-019-0105-2) |
| The Austrian biodatabase for chronic myelomonocytic leukemia (ABCMML) | Klaus Geißler | 2019 | Wiener klinische Wochenschrift | [10.1007/s00508-019-1526-1](https://doi.org/10.1007/s00508-019-1526-1) |
| Associações entre polimorfismos genéticos da enzima álcool desidrogenase e o transtorno por uso de álcool | Jonas Michel Wolf | 2020 | Clinical & Biomedical Research | [10.22491/2357-9730.97531](https://doi.org/10.22491/2357-9730.97531) |
| CRISPR/Cas9-mediated knock-in of alligator cathelicidin gene in a non-coding region of channel catfish genome | Rhoda Mae C. Simora | 2020 | Scientific Reports | [10.1038/s41598-020-79409-5](https://doi.org/10.1038/s41598-020-79409-5) |
| Evolutionary-driven C-MYC gene expression in mammalian fibroblasts | Marcelo Tigre Moura | 2020 | Scientific Reports | [10.1038/s41598-020-67391-x](https://doi.org/10.1038/s41598-020-67391-x) |
| Phenotype expansion of heterozygous FOXC1 pathogenic variants toward involvement of congenital anomalies of the kidneys and urinary tract (CAKUT) | Chen‐Han Wilfred Wu | 2020 | Genetics in Medicine | [10.1038/s41436-020-0844-z](https://doi.org/10.1038/s41436-020-0844-z) |
| SIRT7: an influence factor in healthy aging and the development of age-dependent myeloid stem-cell disorders | Alexander Kaiser | 2020 | Leukemia | [10.1038/s41375-020-0803-3](https://doi.org/10.1038/s41375-020-0803-3) |
| Zebrafish Larvae Carrying a Splice Variant Mutation in cacna1d: A New Model for Schizophrenia-Like Behaviours? | Nancy Saana Banono | 2020 | Molecular Neurobiology | [10.1007/s12035-020-02160-5](https://doi.org/10.1007/s12035-020-02160-5) |
| A chromosome-level genome of Astyanax mexicanus surface fish for comparing population-specific genetic differences contributing to trait evolution | Wesley C. Warren | 2021 | Nature Communications | [10.1038/s41467-021-21733-z](https://doi.org/10.1038/s41467-021-21733-z) |
| Conceptualization of functional single nucleotide polymorphisms of polycystic ovarian syndrome genes: an in silico approach | B. N. Balakrishna Prabhu | 2021 | Journal of Endocrinological Investigation | [10.1007/s40618-021-01498-4](https://doi.org/10.1007/s40618-021-01498-4) |
| Expression and Prognostic Value of MCM Family Genes in Osteosarcoma | Jian Zhou | 2021 | Frontiers in Molecular Biosciences | [10.3389/fmolb.2021.668402](https://doi.org/10.3389/fmolb.2021.668402) |
| FAM83A and FAM83A‑AS1 both play oncogenic roles in lung adenocarcinoma | Gaoming Wang | 2021 | Oncology Letters | [10.3892/ol.2021.12558](https://doi.org/10.3892/ol.2021.12558) |
| Unravelling similarities and differences in the role of circular and linear PVT1 in cancer and human disease | Debora Traversa | 2021 | British Journal of Cancer | [10.1038/s41416-021-01584-7](https://doi.org/10.1038/s41416-021-01584-7) |
| Domain Evolution of Vertebrate Blood Coagulation Cascade Proteins | Abdulbaki Çoban | 2022 | Journal of Molecular Evolution | [10.1007/s00239-022-10071-3](https://doi.org/10.1007/s00239-022-10071-3) |
| Immunogenetic losses co-occurred with seahorse male pregnancy and mutation in tlx1 accompanied functional asplenia | Yali Liu | 2022 | Nature Communications | [10.1038/s41467-022-35338-7](https://doi.org/10.1038/s41467-022-35338-7) |
| MEX3A promotes the malignant progression of ovarian cancer by regulating intron retention in TIMELESS | Fangfang Li | 2022 | Cell Death and Disease | [10.1038/s41419-022-05000-7](https://doi.org/10.1038/s41419-022-05000-7) |
| Pharmacogenomics deliberations of 2-deoxy-d-glucose in the treatment of COVID-19 disease: an in silico approach | Navya B. Prabhu | 2022 | 3 Biotech | [10.1007/s13205-022-03363-4](https://doi.org/10.1007/s13205-022-03363-4) |
| High-density lipoprotein regulates angiogenesis by long non-coding RNA HDRACA | Zhi-Wei Mo | 2023 | Signal Transduction and Targeted Therapy | [10.1038/s41392-023-01558-6](https://doi.org/10.1038/s41392-023-01558-6) |
| Genomics 2 Proteins portal: a resource and discovery tool for linking genetic screening outputs to protein sequences and structures | Seulki Kwon | 2024 | Nature Methods | [10.1038/s41592-024-02409-0](https://doi.org/10.1038/s41592-024-02409-0) |

### iNaturalist (16)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Cavity occupancy by wild honey bees: need for evidence of ecological impacts | Manu E. Saunders | 2021 | Frontiers in Ecology and the Environment | [10.1002/fee.2347](https://doi.org/10.1002/fee.2347) |
| Elm zigzag sawfly,<i>Aproceros leucopoda</i>(Hymenoptera: Argidae), recorded for the first time in North America through community science | Véronique Martel | 2021 | The Canadian Entomologist | [10.4039/tce.2021.44](https://doi.org/10.4039/tce.2021.44) |
| Integrating Natural Resources Education and Citizen Science Communication through the Use of Unmanned Aerial Systems (Drones) | David Kulhavy | 2021 | International Journal of Higher Education | [10.5430/ijhe.v11n2p143](https://doi.org/10.5430/ijhe.v11n2p143) |
| Vespa orientalis, a new alien species in Romania | Mihai Zachi | 2021 | Travaux du Muséum National d’Histoire Naturelle “Grigore Antipa” | [10.3897/travaux.64.e61954](https://doi.org/10.3897/travaux.64.e61954) |
| A comparison of herbarium and citizen science phenology datasets for detecting response of flowering time to climate change in Denmark | Natalie Iwanycki Ahlstrand | 2022 | International Journal of Biometeorology | [10.1007/s00484-022-02238-w](https://doi.org/10.1007/s00484-022-02238-w) |
| Reviewing Observations for the Idaho Amphibian and Reptile iNaturalist Project For Improved Data Quality | Charles R. Peterson | 2022 | Biodiversity Information Science and Standards | [10.3897/biss.6.95052](https://doi.org/10.3897/biss.6.95052) |
| Using the iNaturalist application to identify reports of Green Iguanas (Iguana iguana) on the mainland United States of America outside of populations in Florida | Matthew Mo | 2022 | Reptiles & Amphibians | [10.17161/randa.v29i1.16269](https://doi.org/10.17161/randa.v29i1.16269) |
| Wildlife trade and the establishment of invasive alien species in Indonesia: management, policy, and regulation of the commercial sale of songbirds | Vincent Nijman | 2022 | Biological Invasions | [10.1007/s10530-022-02831-5](https://doi.org/10.1007/s10530-022-02831-5) |
| Rapid increase in knowledge about the distribution of introduced predatory Testacella species (Gastropoda: Stylommatophora) in North America by community scientists | Bernhard Hausdorf | 2023 | Biological Invasions | [10.1007/s10530-023-03071-x](https://doi.org/10.1007/s10530-023-03071-x) |
| The establishment of the association between the Japanese beetle (Coleoptera: Scarabaeidae) and the parasitoid <i>Istocheta aldrichi</i> (Diptera: Tachinidae) in Québec, Canada | Marie-Ève Gagnon | 2023 | The Canadian Entomologist | [10.4039/tce.2023.22](https://doi.org/10.4039/tce.2023.22) |
| Using iNaturalist to monitor the roosting behavior of bats in Panama | Shem Unger | 2023 | Mammalogy Notes | [10.47603/mano.v9n1.361](https://doi.org/10.47603/mano.v9n1.361) |
| Discovering urban nature: citizen science and biodiversity on a university campus | Patrícia Tiago | 2024 | Urban Ecosystems | [10.1007/s11252-024-01526-0](https://doi.org/10.1007/s11252-024-01526-0) |
| New northernmost records of the shield mantis Choeradodis rhombicollis (Latreille, 1833) (Mantidae: Choeradodinae) in Mexico | Manuel de Luna | 2024 | REVISTA CHILENA DE ENTOMOLOGÍA | [10.35249/rche.50.1.24.01](https://doi.org/10.35249/rche.50.1.24.01) |
| Status of the invasion of Carpobrotus edulis in Uruguay based on citizen science records | Florencia Grattarola | 2024 | Biological Invasions | [10.1007/s10530-023-03242-w](https://doi.org/10.1007/s10530-023-03242-w) |
| Citizen science reveals alarming update on the invasion of the Asian mantleslug Meghimatium pictum in Brazil | Rafael M. Rosa | 2025 | PLoS ONE | [10.1371/journal.pone.0330518](https://doi.org/10.1371/journal.pone.0330518) |
| Past and Present in the Ecological Connectivity of Protected Areas Through Land Cover and Graph-Based Metrics | Antonio Vidal-Llamas | 2025 | Environmental Management | [10.1007/s00267-025-02206-1](https://doi.org/10.1007/s00267-025-02206-1) |

### Materials Project (27)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Advanced sulfide solid electrolyte by core-shell structural design | Fan Wu | 2018 | Nature Communications | [10.1038/s41467-018-06123-2](https://doi.org/10.1038/s41467-018-06123-2) |
| Deep neural networks for accurate predictions of crystal stability | Weike Ye | 2018 | Nature Communications | [10.1038/s41467-018-06322-x](https://doi.org/10.1038/s41467-018-06322-x) |
| Identifying an efficient, thermally robust inorganic phosphor host via machine learning | Ya Zhuo | 2018 | Nature Communications | [10.1038/s41467-018-06625-z](https://doi.org/10.1038/s41467-018-06625-z) |
| Matminer: An open source toolkit for materials data mining | Logan Ward | 2018 | Computational Materials Science | [10.1016/j.commatsci.2018.05.018](https://doi.org/10.1016/j.commatsci.2018.05.018) |
| Physical descriptor for the Gibbs energy of inorganic crystalline solids and temperature-dependent materials chemistry | Christopher J. Bartel | 2018 | Nature Communications | [10.1038/s41467-018-06682-4](https://doi.org/10.1038/s41467-018-06682-4) |
| PyCDT: A Python toolkit for modeling point defects in semiconductors and insulators | Danny Broberg | 2018 | Computer Physics Communications | [10.1016/j.cpc.2018.01.004](https://doi.org/10.1016/j.cpc.2018.01.004) |
| The role of decomposition reactions in assessing first-principles predictions of solid stability | Christopher J. Bartel | 2018 | npj Computational Materials | [10.1038/s41524-018-0143-2](https://doi.org/10.1038/s41524-018-0143-2) |
| Functional Role of Fe-Doping in Co-Based Perovskite Oxide Catalysts for Oxygen Evolution Reaction | Bae‐Jung Kim | 2019 | Journal of the American Chemical Society | [10.1021/jacs.8b12101](https://doi.org/10.1021/jacs.8b12101) |
| Machine Learning the Voltage of Electrode Materials in Metal-Ion Batteries | Rajendra P. Joshi | 2019 | ACS Applied Materials & Interfaces | [10.1021/acsami.9b04933](https://doi.org/10.1021/acsami.9b04933) |
| Acid-Stable Oxides for Oxygen Electrocatalysis | Zhenbin Wang | 2020 | ACS Energy Letters | [10.1021/acsenergylett.0c01625](https://doi.org/10.1021/acsenergylett.0c01625) |
| Origin of Disorder Tolerance in Piezoelectric Materials and Design of Polar Systems | Handong Ling | 2020 | Chemistry of Materials | [10.1021/acs.chemmater.9b04614](https://doi.org/10.1021/acs.chemmater.9b04614) |
| Discovery of novel Li SSE and anode coatings using interpretable machine learning and high-throughput multi-property screening | Shreyas Honrao | 2021 | Scientific Reports | [10.1038/s41598-021-94275-5](https://doi.org/10.1038/s41598-021-94275-5) |
| Machine Learning Assisted Prediction of Cathode Materials for Zn‐Ion Batteries | Linming Zhou | 2021 | Advanced Theory and Simulations | [10.1002/adts.202100196](https://doi.org/10.1002/adts.202100196) |
| Machine Learning-Aided Materials Design Platform for Predicting the Mechanical Properties of Na-Ion Solid-State Electrolytes | Junho Jo | 2021 | ACS Applied Energy Materials | [10.1021/acsaem.1c01223](https://doi.org/10.1021/acsaem.1c01223) |
| Determination of Gibbs Free Energy in the Compound Formation of Li-P and Li-Fe-O by Pymatgen | Anis Yuniati | 2022 | Kaunia Integration and Interconnection Islam and Science | [10.14421/kaunia.3554](https://doi.org/10.14421/kaunia.3554) |
| Screening of bimetallic electrocatalysts for water purification with machine learning | Richard Tran | 2022 | The Journal of Chemical Physics | [10.1063/5.0092948](https://doi.org/10.1063/5.0092948) |
| CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling | Bowen Deng | 2023 | Nature Machine Intelligence | [10.1038/s42256-023-00716-3](https://doi.org/10.1038/s42256-023-00716-3) |
| Metal hydride composition-derived parameters as machine learning features for material design and H2 storage | Sean Nations | 2023 | Journal of Energy Storage | [10.1016/j.est.2023.107980](https://doi.org/10.1016/j.est.2023.107980) |
| Structural and electronic properties of Ta2O5 with one formula unit | Yangwu Tong | 2023 | Computational Materials Science | [10.1016/j.commatsci.2023.112482](https://doi.org/10.1016/j.commatsci.2023.112482) |
| Thermoelectric Prediction from Material Descriptors Using Machine Learning Technique | Pakawat Sungphueng | 2023 | Current Applied Science and Technology | [10.55003/cast.2023.06.23.014](https://doi.org/10.55003/cast.2023.06.23.014) |
| An interpretable formula for lattice thermal conductivity of crystals | Xiaoying Wang | 2024 | Materials Today Physics | [10.1016/j.mtphys.2024.101549](https://doi.org/10.1016/j.mtphys.2024.101549) |
| Crystal net catalog of model flat band materials | Paul M. Neves | 2024 | npj Computational Materials | [10.1038/s41524-024-01220-x](https://doi.org/10.1038/s41524-024-01220-x) |
| Dielectric tensor prediction for inorganic materials using latent information from preferred potential | Zetian Mao | 2024 | npj Computational Materials | [10.1038/s41524-024-01450-z](https://doi.org/10.1038/s41524-024-01450-z) |
| Learning from machine learning: the case of band-gap directness in semiconductors | Elton Ogoshi | 2024 | Discover Materials | [10.1007/s43939-024-00073-x](https://doi.org/10.1007/s43939-024-00073-x) |
| Machine Learning-Driven Density Prediction for Nanomaterials | Shams Ansaf | 2024 | Wasit Journal of Pure sciences | [10.31185/wjps.538](https://doi.org/10.31185/wjps.538) |
| A generative model for inorganic materials design | Claudio Zeni | 2025 | Nature | [10.1038/s41586-025-08628-5](https://doi.org/10.1038/s41586-025-08628-5) |
| Transformer-generated atomic embeddings to enhance prediction accuracy of crystal properties with machine learning | Luozhijie Jin | 2025 | Nature Communications | [10.1038/s41467-025-56481-x](https://doi.org/10.1038/s41467-025-56481-x) |

### NOAA GHCN (25)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Climate and the Global Famine of 1876–78 | Deepti Singh | 2018 | Journal of Climate | [10.1175/jcli-d-18-0159.1](https://doi.org/10.1175/jcli-d-18-0159.1) |
| Convective suppression before and during the United States Northern Great Plains flash drought of 2017 | Tobias Gerken | 2018 | Hydrology and earth system sciences | [10.5194/hess-22-4155-2018](https://doi.org/10.5194/hess-22-4155-2018) |
| Extreme heat in India and anthropogenic climate change | Geert Jan van Oldenborgh | 2018 | Natural hazards and earth system sciences | [10.5194/nhess-18-365-2018](https://doi.org/10.5194/nhess-18-365-2018) |
| Rainfall variability over Malawi during the late 19th century | David J. Nash | 2018 | International Journal of Climatology | [10.1002/joc.5396](https://doi.org/10.1002/joc.5396) |
| Superstatistical distribution of daily precipitation extremes: A worldwide assessment | Carlo De Michele | 2018 | Scientific Reports | [10.1038/s41598-018-31838-z](https://doi.org/10.1038/s41598-018-31838-z) |
| A probabilistic gridded product for daily precipitation extremes over the United States | Mark D. Risser | 2019 | Climate Dynamics | [10.1007/s00382-019-04636-0](https://doi.org/10.1007/s00382-019-04636-0) |
| European maize landraces made accessible for plant breeding and genome-based studies | Armin C. Hölker | 2019 | Theoretical and Applied Genetics | [10.1007/s00122-019-03428-8](https://doi.org/10.1007/s00122-019-03428-8) |
| Evaluation of variability among different precipitation products in the Northern Great Plains | Xiaoyong Xu | 2019 | Journal of Hydrology Regional Studies | [10.1016/j.ejrh.2019.100608](https://doi.org/10.1016/j.ejrh.2019.100608) |
| Maximizing ENSO as a source of western US hydroclimate predictability | Christina M. Patricola | 2019 | Climate Dynamics | [10.1007/s00382-019-05004-8](https://doi.org/10.1007/s00382-019-05004-8) |
| COVID-19, staying at home, and domestic violence | Linchi Hsu | 2020 | Review of Economics of the Household | [10.1007/s11150-020-09526-7](https://doi.org/10.1007/s11150-020-09526-7) |
| Living with floating vegetation invasions | Fritz Kleinschroth | 2020 | AMBIO | [10.1007/s13280-020-01360-6](https://doi.org/10.1007/s13280-020-01360-6) |
| The effects of urban development and current green infrastructure policy on future climate change resilience | Charlotte Shade | 2020 | Ecology and Society | [10.5751/es-12076-250437](https://doi.org/10.5751/es-12076-250437) |
| Evaluation of precipitation indices in suites of dynamically and statistically downscaled regional climate models over Florida | Abhishekh Srivastava | 2021 | Climate Dynamics | [10.1007/s00382-021-05980-w](https://doi.org/10.1007/s00382-021-05980-w) |
| Four distinct Northeast US heat wave circulation patterns and associated mechanisms, trends, and electric usage | Laurie Agel | 2021 | npj Climate and Atmospheric Science | [10.1038/s41612-021-00186-7](https://doi.org/10.1038/s41612-021-00186-7) |
| Machine learning reveals complex effects of climatic means and weather extremes on wheat yields during different plant developmental stages | Florian Schierhorn | 2021 | Climatic Change | [10.1007/s10584-021-03272-0](https://doi.org/10.1007/s10584-021-03272-0) |
| Penultimate deglaciation Asian monsoon response to North Atlantic circulation collapse | Jasper A. Wassenburg | 2021 | Nature Geoscience | [10.1038/s41561-021-00851-9](https://doi.org/10.1038/s41561-021-00851-9) |
| Understanding model diversity in future precipitation projections for South America | Øivind Hodnebrog | 2021 | Climate Dynamics | [10.1007/s00382-021-05964-w](https://doi.org/10.1007/s00382-021-05964-w) |
| Drought assessment has been outpaced by climate change: empirical arguments for a paradigm shift | Zachary Hoylman | 2022 | Nature Communications | [10.1038/s41467-022-30316-5](https://doi.org/10.1038/s41467-022-30316-5) |
| Near-term regional climate change in East Africa | Yeon‐Woo Choi | 2022 | Climate Dynamics | [10.1007/s00382-022-06591-9](https://doi.org/10.1007/s00382-022-06591-9) |
| Robust bias-correction of precipitation extremes using a novel hybrid empirical quantile-mapping method | Maike Holthuijzen | 2022 | Theoretical and Applied Climatology | [10.1007/s00704-022-04035-2](https://doi.org/10.1007/s00704-022-04035-2) |
| Trends in Quality Controlled Precipitation Indicators in the United States Midwest and Great Lakes Region | William Baule | 2022 | Frontiers in Water | [10.3389/frwa.2022.817342](https://doi.org/10.3389/frwa.2022.817342) |
| Exact Gaussian processes for massive datasets via non-stationary sparsity-discovering kernels | Marcus M. Noack | 2023 | Scientific Reports | [10.1038/s41598-023-30062-8](https://doi.org/10.1038/s41598-023-30062-8) |
| Increased impact of heat domes on 2021-like heat extremes in North America under global warming | Xing Zhang | 2023 | Nature Communications | [10.1038/s41467-023-37309-y](https://doi.org/10.1038/s41467-023-37309-y) |
| Climate Change Trend Using Descriptive Time Series Technique in Machine Learning: A Case of Jimma Zone, Southwestern Ethiopia | Wendafiraw Abdisa Gemmechis | 2024 | International Journal of Environmental Monitoring and Analysis | [10.11648/j.ijema.20241203.12](https://doi.org/10.11648/j.ijema.20241203.12) |
| Exploring the impact of the recent global warming on extreme weather events in Central Asia using the counterfactual climate data ATTRICI v1.1 | Bijan Fallah | 2024 | Climatic Change | [10.1007/s10584-024-03743-0](https://doi.org/10.1007/s10584-024-03743-0) |

### OBIS (13)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Diversity of Deep-Sea Scale-Worms (Annelida, Polynoidae) in the Clarion-Clipperton Fracture Zone | Paulo Bonifácio | 2021 | Frontiers in Marine Science | [10.3389/fmars.2021.656899](https://doi.org/10.3389/fmars.2021.656899) |
| Environmental matching reveals non-uniform range-shift patterns in benthic marine Crustacea | Marianna V. P. Simões | 2021 | Climatic Change | [10.1007/s10584-021-03240-8](https://doi.org/10.1007/s10584-021-03240-8) |
| Occurrence and diet analysis of sea turtles in Korean shore | Ji‐Hee Kim | 2021 | Journal of Ecology and Environment | [10.1186/s41610-021-00206-w](https://doi.org/10.1186/s41610-021-00206-w) |
| Biodiversity and distribution of corals in Chile | Anna Maria Addamo | 2022 | Marine Biodiversity | [10.1007/s12526-022-01271-7](https://doi.org/10.1007/s12526-022-01271-7) |
| First records of two large pelagic fishes in the Red Sea: wahoo (<i>Acanthocybium solandri</i>) and striped marlin (<i>Kajikia audax</i>) | Collin T. Williams | 2022 | Journal of the Marine Biological Association of the United Kingdom | [10.1017/s0025315422000820](https://doi.org/10.1017/s0025315422000820) |
| The distribution of manta rays in the western North Atlantic Ocean off the eastern United States | Nicholas A. Farmer | 2022 | Scientific Reports | [10.1038/s41598-022-10482-8](https://doi.org/10.1038/s41598-022-10482-8) |
| Concise review of the red macroalga dulse, Palmaria palmata (L.) Weber &amp; Mohr | Pierrick Stévant | 2023 | Journal of Applied Phycology | [10.1007/s10811-022-02899-5](https://doi.org/10.1007/s10811-022-02899-5) |
| Modeling present and future distribution of plankton populations in a coastal upwelling zone: the copepod Calanus chilensis as a study case | Reinaldo Rivera | 2023 | Scientific Reports | [10.1038/s41598-023-29541-9](https://doi.org/10.1038/s41598-023-29541-9) |
| The crown-of-thorns seastar species complex: knowledge on the biology and ecology of five corallivorous Acanthaster species | Sven Uthicke | 2023 | Marine Biology | [10.1007/s00227-023-04355-5](https://doi.org/10.1007/s00227-023-04355-5) |
| A transoceanic journey: <i>Melanochlamys diomedea</i>'s first report in the North Atlantic | Laure de Montety | 2024 | Journal of the Marine Biological Association of the United Kingdom | [10.1017/s002531542400047x](https://doi.org/10.1017/s002531542400047x) |
| Incorporating physiological knowledge into correlative species distribution models minimizes bias introduced by the choice of calibration area | Zhixin Zhang | 2024 | Marine Life Science & Technology | [10.1007/s42995-024-00226-0](https://doi.org/10.1007/s42995-024-00226-0) |
| Assessment of future habitat suitability and ecological vulnerability of Collichthys at population and species level | Kaiyu Liu | 2025 | BMC Ecology and Evolution | [10.1186/s12862-024-02339-7](https://doi.org/10.1186/s12862-024-02339-7) |
| Climate-driven shifts in marine habitat explain recent declines of Japanese Chum salmon | Irene D. Alabia | 2025 | Scientific Reports | [10.1038/s41598-025-26397-z](https://doi.org/10.1038/s41598-025-26397-z) |

### PANGAEA (16)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Change in the North Atlantic circulation associated with the mid-Pleistocene transition | Gloria M. Martin-Garcia | 2018 | Climate of the past | [10.5194/cp-14-1639-2018](https://doi.org/10.5194/cp-14-1639-2018) |
| The number of past and future regenerations of iron in the oceanand its intrinsic fertilization efficiency | Benoît Pasquier | 2018 | Biogeosciences | [10.5194/bg-15-7177-2018](https://doi.org/10.5194/bg-15-7177-2018) |
| Application of Sentinel-2 MSI in Arctic Research: Evaluating the Performance of Atmospheric Correction Approaches Over Arctic Sea Ice | Marcel König | 2019 | Frontiers in Earth Science | [10.3389/feart.2019.00022](https://doi.org/10.3389/feart.2019.00022) |
| Depth habitat of the planktonic foraminifera <i>Neogloboquadrina pachyderma</i> in the northern high latitudes explained by sea-ice and chlorophyll concentrations | Mattia Greco | 2019 | Biogeosciences | [10.5194/bg-16-3425-2019](https://doi.org/10.5194/bg-16-3425-2019) |
| Impacts of an Eruption on Cold-Seep Microbial and Faunal Dynamics at a Mud Volcano | F Girard | 2020 | Frontiers in Marine Science | [10.3389/fmars.2020.00241](https://doi.org/10.3389/fmars.2020.00241) |
| Variability in Benthic Ecosystem Functioning in Arctic Shelf and Deep-Sea Sediments: Assessments by Benthic Oxygen Uptake Rates and Environmental Drivers | Joshua Kiesel | 2020 | Frontiers in Marine Science | [10.3389/fmars.2020.00426](https://doi.org/10.3389/fmars.2020.00426) |
| Dynamic Species Distribution Models in the Marine Realm: Predicting Year-Round Habitat Suitability of Baleen Whales in the Southern Ocean | Ahmed El‐Gabbas | 2021 | Frontiers in Marine Science | [10.3389/fmars.2021.802276](https://doi.org/10.3389/fmars.2021.802276) |
| Carbon dioxide sink in the Arctic Ocean from cross-shelf transport of dense Barents Sea water | Andreas Rogge | 2022 | Nature Geoscience | [10.1038/s41561-022-01069-z](https://doi.org/10.1038/s41561-022-01069-z) |
| Case study of a moisture intrusion over the Arctic with the ICOsahedral Non-hydrostatic (ICON) model: resolution dependence of its representation | Hélène Bresson | 2022 | Atmospheric chemistry and physics | [10.5194/acp-22-173-2022](https://doi.org/10.5194/acp-22-173-2022) |
| A new sea ice concentration product in the polar regions derived from the FengYun-3 MWRI sensors | Ying Chen | 2023 | Earth system science data | [10.5194/essd-15-3223-2023](https://doi.org/10.5194/essd-15-3223-2023) |
| Fluctuating sea-level and reversing Monsoon winds drive Holocene lagoon infill in Southeast Asia | Yannis Kappelmann | 2023 | Scientific Reports | [10.1038/s41598-023-31976-z](https://doi.org/10.1038/s41598-023-31976-z) |
| Long-term trends of pH and inorganic carbon in the Eastern North Atlantic: the ESTOC site | Melchor González‐Dávila | 2023 | Frontiers in Marine Science | [10.3389/fmars.2023.1236214](https://doi.org/10.3389/fmars.2023.1236214) |
| The Antarctic Ice Core Chronology 2023 (AICC2023) chronological framework and associated timescale for the European Project for Ice Coring in Antarctica (EPICA) Dome C ice core | Marie Bouchet | 2023 | Climate of the past | [10.5194/cp-19-2257-2023](https://doi.org/10.5194/cp-19-2257-2023) |
| SMOS-derived Antarctic thin sea ice thickness: data description and validation in the Weddell Sea | Lars Kaleschke | 2024 | Earth system science data | [10.5194/essd-16-3149-2024](https://doi.org/10.5194/essd-16-3149-2024) |
| ENSO advances spring phenology of temperate deciduous shrubs more than trees in Southeastern Wisconsin, USA | Alison Donnelly | 2026 | Annals of Forest Science | [10.1186/s13595-026-01325-x](https://doi.org/10.1186/s13595-026-01325-x) |
| Estimating particulate organic matter flux from in-situ optics: A framework for correcting for suspended particles and incorporating depth-dependent degradation | Nasrollah Moradi | 2026 | Biogeosciences | [10.5194/bg-23-2179-2026](https://doi.org/10.5194/bg-23-2179-2026) |

### USGS Earthquake Catalog (7)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Constraining the Source of the Mw 8.1 Chiapas, Mexico Earthquake of 8 September 2017 Using Teleseismic and Tsunami Observations | Mohammad Heidarzadeh | 2018 | Pure and Applied Geophysics | [10.1007/s00024-018-1837-6](https://doi.org/10.1007/s00024-018-1837-6) |
| Landslide detection and susceptibility mapping using geological and remote sensing data: A case study of Azad Kashmir, NW Sub-Himalayas | Muhammad Zeeshan | 2021 | Acta Geodynamica et Geomaterialia | [10.13168/agg.2021.0002](https://doi.org/10.13168/agg.2021.0002) |
| Sensor orientation of the TMD seismic network (Thailand) from P-wave particle motions | Patinya Pornsopin | 2023 | Geoscience Letters | [10.1186/s40562-023-00278-7](https://doi.org/10.1186/s40562-023-00278-7) |
| The basement fault suggestion for the 6th February 2023 Maraş earthquake based on geodetic interseismic displacements | Şenol Hakan Kutoğlu | 2025 | Natural Hazards | [10.1007/s11069-025-07388-9](https://doi.org/10.1007/s11069-025-07388-9) |
| Co-seismic Landslide Susceptibility Assessment Using a Modified Newmark Model: A Case Study of the 2016 Mw 6.7 Imphal Earthquake | Upendra Bhatt | 2026 | Indian Journal of Science and Technology | [10.17485/ijst/v19i13.462](https://doi.org/10.17485/ijst/v19i13.462) |
| Ground motion characteristics of the 2022 Mw 5.9 Keng Tung earthquake in the northern Sunda Block | Ei Mhone Nathar Myo | 2026 | Earth Planets and Space | [10.1186/s40623-026-02506-8](https://doi.org/10.1186/s40623-026-02506-8) |
| Re-evaluation of the interseismic slip deficit rates along the Kamchatka subduction zone | Fumiaki Tomita | 2026 | Earth Planets and Space | [10.1186/s40623-026-02378-y](https://doi.org/10.1186/s40623-026-02378-y) |

### VizieR (10)

| Title | First author | Year | Journal | DOI |
|---|---|---:|---|---|
| Gaia Data Release 2: Variable stars in the colour-absolute magnitude diagram | Gaia Collaboration | 2018 | Repository of the Academy's Library (Library of the Hungarian Academy of Sciences) | [10.48550/arxiv.1804.09382](https://doi.org/10.48550/arxiv.1804.09382) |
| A catalogue of stellar diameters and fluxes for mid-infrared interferometry★ | P. Cruzalèbes | 2019 | Monthly Notices of the Royal Astronomical Society | [10.1093/mnras/stz2803](https://doi.org/10.1093/mnras/stz2803) |
| Runaway and walkaway stars from the ONC with Gaia DR2 | Christina Schoettler | 2020 | Monthly Notices of the Royal Astronomical Society | [10.1093/mnras/staa1228](https://doi.org/10.1093/mnras/staa1228) |
| A stellar stream remnant of a globular cluster below the metallicity floor | Nicolas F. Martin | 2022 | Nature | [10.1038/s41586-021-04162-2](https://doi.org/10.1038/s41586-021-04162-2) |
| pulsar_spectra: A pulsar flux density catalogue and spectrum fitting repository | N. A. Swainston | 2022 | Publications of the Astronomical Society of Australia | [10.1017/pasa.2022.52](https://doi.org/10.1017/pasa.2022.52) |
| Photometric variability of the LAMOST sample of magnetic chemically peculiar stars as seen by TESS | Jonathan Labadie-Bartz | 2023 | Astronomy and Astrophysics | [10.1051/0004-6361/202346657](https://doi.org/10.1051/0004-6361/202346657) |
| eRASSU J060839.5–704014: A double degenerate ultra-compact binary in the direction of the LMC | Chandreyee Maitra | 2023 | Astronomy and Astrophysics | [10.1051/0004-6361/202347811](https://doi.org/10.1051/0004-6361/202347811) |
| The Sydney Radio Star Catalogue: Properties of radio stars at megahertz to gigahertz frequencies | Laura Driessen | 2024 | Publications of the Astronomical Society of Australia | [10.1017/pasa.2024.72](https://doi.org/10.1017/pasa.2024.72) |
| Sporadic radio pulses from a white dwarf binary at the orbital period | Iris de Ruiter | 2025 | Nature Astronomy | [10.1038/s41550-025-02491-0](https://doi.org/10.1038/s41550-025-02491-0) |
| The Rapid ASKAP Continuum Survey (RACS) VI: The RACS-high 1 655.5 MHz images and catalogue | S. W. Duchesne | 2025 | Publications of the Astronomical Society of Australia | [10.1017/pasa.2025.2](https://doi.org/10.1017/pasa.2025.2) |
