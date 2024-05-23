"""
End-to-end computation chain for displacement risk from tropical cyclones, per country and building damage threshold.
To be called by bash script on a cluster.
"""

import os
import pandas as pd
import numpy as np
import copy as cp
import sys
from pathos.multiprocessing import ProcessingPool as Pool

from climada.hazard import TropCyclone, Hazard
from climada.entity.exposures import Exposures
from climada.engine import ImpactCalc
from climada.entity import ImpactFunc, ImpactFuncSet
from climada.util.constants import SYSTEM_DIR

os.chdir('/cluster/project/climate/meilers/scripts/displacement/global-displacement-risk')
import exposure, vulnerability

def calculate_impact(exp_obj, fut_haz_dict, impf_set_tc_step, tc_haz_sel):
    impcalc = ImpactCalc(exp_obj, impf_set_tc_step, tc_haz_sel)
    impact = impcalc.impact()

    freq_curve = impact.calc_freq_curve(return_per=np.arange(1, 251, 1))
    rp_indices = [9, 24, 49, 99, 249]
    pm_data_hist = [freq_curve.impact[idx] for idx in rp_indices]

    impact_dict = {}
    for fut, haz in fut_haz_dict.items():
        impcalc_fut = ImpactCalc(exp_obj, impf_set_tc_step, haz)
        impact_fut = impcalc_fut.impact()
        impact_dict[fut] = impact_fut

    aai_agg_dict = {'ERA-5_hist': impact.aai_agg}
    pmd_dict = {'ERA-5_hist': pm_data_hist}
    for fut, imp in impact_dict.items():
        aai_agg_dict[fut] = imp.aai_agg
        freq_curve = imp.calc_freq_curve(return_per=np.arange(1, 251, 1))
        pm_data = [freq_curve.impact[idx] for idx in rp_indices]
        pmd_dict[fut] = pm_data

    return aai_agg_dict, pmd_dict

def process_imp(exp_obj, key, fut_haz_dict, impf_set_tc_step, tc_haz_sel):
    aai_agg_dict, pmd_dict = calculate_impact(exp_obj, fut_haz_dict, impf_set_tc_step, tc_haz_sel)

    data = {'Model': [], 'Scenario': [], 'Period': [], 'AAD': []}
    for fut_key, value in aai_agg_dict.items():
        parts = fut_key.split('_')
        model, scenario, period = (parts if len(parts) == 3 else parts + [""])[:3]
        data['Model'].append(model)
        data['Scenario'].append(scenario)
        data['Period'].append(period)
        data['AAD'].append(value)

    df = pd.DataFrame(data)
    for rp, rp_value in zip([10, 25, 50, 100, 250], zip(*pmd_dict.values())):
        df[f'RP_{rp}'] = rp_value

    filtered_df = df[(df['Model'] != 'ERA-5')]
    df_abs = filtered_df.groupby(['Scenario', 'Period']).median().reset_index()
    hist_df = df_abs.iloc[0]
    hist_values = hist_df[2::]

    diff_df = df_abs.copy()
    for column in ['AAD', 'RP_10', 'RP_25', 'RP_50', 'RP_100', 'RP_250']:
        diff_df[column] = diff_df[column] - hist_values[column]

    era5_df = df[df['Model'] == 'ERA-5'].drop(columns=['Model', 'Scenario', 'Period'])
    df_fut = diff_df.copy()
    for column in ['AAD', 'RP_10', 'RP_25', 'RP_50', 'RP_100', 'RP_250']:
        df_fut[column] = df_fut[column] + era5_df[column].values[0]

    df_fut['Exposure'] = key
    return df_fut

def main(cntry_iso, building_thresh):
    os.chdir('/cluster/project/climate/meilers/scripts/displacement/global-displacement-risk')

    reg = 'WP'
    gdf_bem_subcomps = exposure.gdf_from_bem_subcomps(cntry_iso, opt='full')
    gdf_bem_subcomps = gdf_bem_subcomps[gdf_bem_subcomps.valhum > 1]
    gdf_bem_subcomps["impf_TC"] = gdf_bem_subcomps.apply(lambda row: vulnerability.DICT_PAGER_TCIMPF_HAZUS[row.se_seismo], axis=1)
    gdf_bem_subcomps = exposure.assign_admin1_attr(gdf_bem_subcomps, exposure.path_admin1_attrs, source='gadm')

    exp = Exposures(gdf_bem_subcomps.copy())
    exp.gdf.rename({'valhum': 'value'}, axis=1, inplace=True)
    exp.value_unit = 'Pop. count'
    exp.gdf['longitude'] = exp.gdf.geometry.x
    exp.gdf['latitude'] = exp.gdf.geometry.y
    exp.gdf = exp.gdf[~np.isnan(exp.gdf.latitude)]

    ad1 = np.unique(exp.gdf.admin1).tolist()
    exp_dict = {'admin0': exp}
    for admin1 in ad1:
        admin1_gdf = exp.gdf[exp.gdf.admin1 == admin1]
        exp_admin1 = cp.deepcopy(exp)
        exp_admin1.gdf = admin1_gdf
        exp_dict[f'admin1_{int(admin1)}'] = exp_admin1

    lat_min, lat_max, lon_min, lon_max = exp.gdf['latitude'].min(), exp.gdf['latitude'].max(), exp.gdf['longitude'].min(), exp.gdf['longitude'].max()
    hazard_dir = SYSTEM_DIR/"hazard"/"present"
    tc_haz = TropCyclone.from_hdf5(hazard_dir.joinpath(f'TC_{reg}_0150as_MIT_H08.hdf5'))
    tc_haz_sel = tc_haz.select(extent=(lon_min, lon_max, lat_min, lat_max))

    models = ['cesm2', 'cnrm6', 'ecearth6', 'fgoals', 'ipsl6', 'miroc6', 'mpi6', 'mri6', 'ukmo6']
    rcp = 'ssp370'
    scenario = ['20thcal', 'cal', '_2cal']
    yr_dict = {'20thcal': 'hist', 'cal': 2050, '_2cal': 2100}
    hazard_dir = SYSTEM_DIR/"hazard"/"future"
    fut_haz_dict = {}
    for gcm in models:
        for scen in scenario:
            haz_str = f"TC_{reg}_0150as_MIT_{gcm}_{rcp}{scen}_H08.hdf5" if scen != '20thcal' else f"TC_{reg}_0150as_MIT_{gcm}_{scen}_H08.hdf5"
            haz = TropCyclone.from_hdf5(hazard_dir.joinpath(haz_str))
            haz_sel = haz.select(extent=(lon_min, lon_max, lat_min, lat_max))
            fut_haz_dict[f'{gcm}_{rcp}_{yr_dict[scen]}' if scen != '20thcal' else f'{gcm}_{yr_dict[scen]}'] = haz_sel

    impf_set_tc = vulnerability.IMPF_SET_TC_HAZUS
    impf_set_tc_step = ImpactFuncSet()
    for imp_id in impf_set_tc.get_ids(haz_type='TC'):
        y = impf_set_tc.get_func(fun_id=imp_id)[0].intensity
        x = impf_set_tc.get_func(fun_id=imp_id)[0].mdd
        thresh = np.interp(building_thresh, x, y)
        impf_set_tc_step.append(ImpactFunc.from_step_impf(intensity=(0, thresh, thresh * 10), haz_type='TC', impf_id=imp_id, intensity_unit='m/s'))

    with Pool() as pool:
        results = pool.map(process_imp, exp_dict.values(), exp_dict.keys(), [fut_haz_dict]*len(exp_dict), [impf_set_tc_step]*len(exp_dict), [tc_haz_sel]*len(exp_dict))

    combined_df = pd.concat(results, ignore_index=True)
    combined_df.to_csv(f"/cluster/project/climate/meilers/results/combined_{cntry_iso}_{building_thresh}.csv")

if __name__ == '__main__':
    cntry_iso = sys.argv[1]
    building_thresh = float(sys.argv[2])
    main(cntry_iso, building_thresh)
