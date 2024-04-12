"""
Created in April 2024

description: Load TC hazard from the MIT model and calculate RP maps for given
            intensities. Store as netCDF files.
            future periods - GCM output
            CLIMADA branch: feature/write_haz_rp_maps

@author: simonameiler
"""

import sys

# import CLIMADA modules:
from climada.hazard import TropCyclone
from climada.util.constants import SYSTEM_DIR

############################################################################

def main(region, model, scenario):
    
    region = str(region)
    model = str(model)
    scenario = str(scenario)
    
    res = 150
        
    haz_dir = SYSTEM_DIR/"hazard"/"future"
    haz_str = f"TC_{region}_0{res}as_MIT_{model}_{scenario}_H08.hdf5"
    rp_maps_dir = SYSTEM_DIR/"hazard"/"RPmaps"
    rp_map_str = f"TC_{region}_0{res}as_MIT_{model}_{scenario}_RP-maps.nc"
    
    tc_haz = TropCyclone.from_hdf5(haz_dir.joinpath(haz_str))
    tc_haz.write_netcdf_local_exceedance_inten(
        return_periods=[1, 10, 25, 50, 100, 250], 
        filename=rp_maps_dir.joinpath(rp_map_str))

if __name__ == "__main__":
    main(*sys.argv[1:])
