"""
End-to-end computation chain for displacement risk from coastal flood, per country, rcp and reference year.
To be called by bash script on cluster.
"""

# =============================================================================
# Function definitions and package loading here
# =============================================================================

import copy
import numpy as np
import os
from pathlib import Path
import pandas as pd
import sys
from multiprocessing import Pool
import itertools


from climada.hazard import TropCyclone, Hazard
from climada.entity.exposures import Exposures
from climada.engine import ImpactCalc

os.chdir('/cluster/project/climate/evelynm/global-displacement-risk') 
import exposure
import vulnerability
import impact_postproc
import coastal_flood_hazard

# Constants
PATH_CF_TILES = Path('/cluster/work/climate/evelynm/IDMC_UNU/hazard/coastal_flood/venDEM_scaled_1km')
PATH_RESULTS = Path('/cluster/work/climate/evelynm/IDMC_UNU/results/risk_cf')
DMG_THRESHS = {'low' : 0.3, 'med' : 0.5, 'high': 0.7}



# wrapper function needed to parallelize
def loadhaz_calcimp(cntry_iso, rcp, ref_year):
    # for logging purposes
    print(cntry_iso, rcp, ref_year)
    
    # load hazard
    tiles = coastal_flood_hazard.find_tiles(
        exp.gdf['latitude'].min(), exp.gdf['latitude'].max(), exp.gdf['longitude'].min(), exp.gdf['longitude'].max())
    CF = coastal_flood_hazard.generate_hazard_object(tiles, PATH_CF_TILES, rcp, ref_year, 'FL')
    rps = 1/CF.frequency[:7]
    #CF.write_hdf5('/cluster/project/climate/meilers/scripts/displacement/haz_test_cf_debug.hdf5')
    imp = ImpactCalc(exp, vulnerability.IMPF_SET_FL_CIMA, CF).impact(save_mat=True)
    
    # check 3 thresholds
    dict_thresh = {}
    for thresh in DMG_THRESHS.keys():
        dict_thresh[thresh] = imp.imp_mat > DMG_THRESHS[thresh]
    
    # impact df per scenario & rp + aed
    dict_df_imps_admin1 = {}
    for thresh, sparse_bool in dict_thresh.items():
        dict_df_imps_admin1[thresh] = impact_postproc.agg_sparse_rps(sparse_bool, exp.gdf, rps, thresh, group_admin1=True)
        dict_df_imps_admin1[thresh] = impact_postproc.compute_aeds(dict_df_imps_admin1[thresh], rps, thresh)
        dict_df_imps_admin1[thresh] = impact_postproc.compute_admin0(dict_df_imps_admin1[thresh])
        print(f'computed {cntry_iso}_{rcp}_{ref_year}_{thresh}')
        dict_df_imps_admin1[thresh].to_csv(path_save / f'{cntry_iso}_{rcp}_{ref_year}_{thresh}_cima.csv')
    return dict_df_imps_admin1

# =============================================================================
# Execution
# =============================================================================
if __name__ == '__main__': 
    cntry_iso = sys.argv[1]
    path_save = PATH_RESULTS / cntry_iso
    ref_years = [2020,2020,2020, 2050,2050,2050,2100,2100,2100]
    rcps = ['RCP26', 'RCP45', 'RCP85', 'RCP26', 'RCP45', 'RCP85', 'RCP26', 'RCP45', 'RCP85']
    
    if not path_save.is_dir():
        os.mkdir(path_save)
    
    # load bem, make exp
    gdf_bem_subcomps = exposure.gdf_from_bem_subcomps(cntry_iso, opt='full')
    gdf_bem_subcomps = gdf_bem_subcomps[gdf_bem_subcomps.valhum>1] # filter out rows with basically no population
    gdf_bem_subcomps['se_seismo'] = gdf_bem_subcomps.se_seismo.astype(str) # avoid typeerrors in some exposures
    gdf_bem_subcomps['se_seismo'] = gdf_bem_subcomps['se_seismo'].replace({'inf':'INF'})
    gdf_bem_subcomps = exposure.assign_admin1_attr(gdf_bem_subcomps, exposure.path_admin1_attrs, source='gadm')
    
    exp = Exposures(gdf_bem_subcomps.copy())
    exp.value_unit = 'building_unit'
    exp.gdf['longitude'] = exp.gdf.geometry.x
    exp.gdf['latitude'] = exp.gdf.geometry.y
    exp.gdf['value'] = 1
    
    # exposure check
    invalid_geometries = ~exp.gdf.is_valid
    print(f"Number of invalid geometries: {invalid_geometries.sum()}")
    # Drop rows with NaN values in the geometry column
    exp.gdf = exp.gdf.dropna(subset=['geometry'])
    print(f"Rows with NaN values dropped. Remaining rows: {len(exp.gdf)}")
    
    print('loaded exposure')
    
    #exp.write_hdf5('/cluster/project/climate/meilers/scripts/displacement/exp_test_cf_debug.hdf5')
    
    # scenario 1: capra/cima impfs (only this one; skip ivm for large countries)
    try:
        exp.gdf['impf_FL'] = exp.gdf['se_seismo'].map(vulnerability.DICT_PAGER_FLIMPF_CIMA)
    except:
        print('Missing building types in cima-impf')

    # Parallelize
    with Pool() as pool:
        dict_list = pool.starmap(loadhaz_calcimp,
                                 zip(itertools.repeat(cntry_iso, 9),
                                     rcps,
                                     ref_years))
    
    for dict_df_imps_admin1, rcp, ref_year in zip(dict_list, rcps, ref_years):
        #save all necessary outputs
        pd.concat(dict_df_imps_admin1.values(), axis=1).to_csv(path_save / f'{cntry_iso}_{rcp}_{ref_year}_cima.csv')

        