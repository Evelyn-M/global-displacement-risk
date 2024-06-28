## Global displacement risk

This repository contains the code base to model the global displacement risk due to tropical cyclones and coastal flooding. The project is the result of a collaboration between the internal displacment monitoring center (IDMC), then UN University Bonn, and ETH Zurich.

### Contributors and contact
- [Simona Meiler](mailto:simona.meiler@usys.ethz.ch)
- [Evelyn Mühlhofer](mailto:evelyn.muehlhofer@usys.ethz.ch)
- [Samuel Lüthi](mailto:samuel.luethi@usys.ethz.ch)



### Content
The repository is divided into 3 parts:
  - /main_scripts
    - All scripts needed for replicating the analysis. Please note that the model was run on the Euler cluster at ETH Zurich. Some of these scripts are slightly opaque. We recommend therefore looking at the tutorials.
The scripts are separated into content-wise grouped modules (e.g. “vulnerability”, “exposure”, etc.); iinto a complete computation chain script (“displacement_risk_..”); into bash-scripts for running these on the Euler cluster (“job_..”).
  - /doc
    - Tutorials for understanding the individual model components and additional scripts created during the project. 
Scripts starting with “tutorial_” exemplify the use of methods in the corresponding main_script module (e.g. tutorial_vulnerability demonstrates the workings of the “main_scripts/vulnerability.py” module) 
Scripts starting with “sensitvity_check” test how results respond to various assumptions taken in the modelling process (such as the setting of building thresholds or the impact function source taken.
Scripts starting with “results_overview” look at the raw results produce and give a first data handling glimpse of these.
  - /data
    - Small data files needed for the calculations. Due to obvious data constraints we cannot upload the complete datasets. However, they are available upon reasonable and non-commercial requests.

### Model approach
- To estimate global displacement, we calculated global building damages from tropical cyclone winds and coastal flooding. We assume that people are displaced when 55% (30-70%) of a building gets destroyed.
- Thus, we combine information on hazard (TC, coastal flood), exposure (building type), and vulnerability (ability of buildings to withstand a hazard) for estimating building damages.
- We use only globally consistent models & data layers to ensure intercomparison of results.
- This approach is obviously a strong simplification of the complex processes that actually lead to natural catastrophe induced displacement.

### Data source
Sources used in the scripts are detailed here.
- Hazard:
  - Tropical cyclones: 
We used synthetic tropical cyclone event sets from the MIT model (Emanuel et al., 2006, 2008). The MIT model was run to produce tropical cyclone event sets for the historical period downscaled from ERA-5 reanalysis (Meiler et al., 2022) and for future climate conditions based on downscaling from nine different GCMs for SSP2-4.5, SSP3-7.0, SSP5-8.5 for future time periods 2041-2060 and 2081-2100 as detailed in Meiler et al. (2023). 
The Holland (2008) parametric wind model was used to derive 2D windfields for each tropical cyclone in the MIT event set at a resolution of 150 arcsec on land (3600 arcsec over the ocean). Max. sustained wind speeds at each grid point form the hazard intensity variable used for displacement risk calculation.

- Coastal floods:
  - Coastal flood hazard maps were produced after Kasmalkar et al. (2023). They represent floods from storm surges and sea-level rise (SLR). We use coastal flood hazard maps depicting the flood depth of the 2-, 5-, 10-, 25-, 50-, 100-, 250-, 500-, 1000-yr return period (RP) at a horizontal resolution of 1 km. Future SLR is considered for the years 2050, 2100 and RCP 2.6 and 8.5.

- Exposure: 
  - Buildings: We used the [BEM](https://giri.unepgrid.ch/sites/default/files/2023-09/GIRI_BEM_report_UNIGE.pdf) (building exposure model) layer from UNEP Grid.
  - Population: The BEM layer also contains information on population based on the global human settlement layer.

- Vulnerability: 
  - TC wind: We used the building type specific HAZUS vulnerability to curves and linked them to the BEM building types. For simplicity, we approximated the original curves using a cubic sigmoid function
  - Coastal floods: We relied on building type specific flood impact functions from IVM and CIMA foundation. Again, by linking the impact functions to the BEM building types.

### System requirements

- All python analysis was performed on python version 3.9
- Calculations were done using the  [CLIMADA](https://github.com/CLIMADA-project/climada_python) model developed by the Weather & Climate risks group at ETH Zurich. Analysis was performed on the model version CLIMADA 4.1.1
