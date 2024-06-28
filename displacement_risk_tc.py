import os
import pandas as pd
import numpy as np
import copy
import sys
from pathlib import Path

from climada.hazard import TropCyclone, Hazard
from climada.entity.exposures import Exposures
from climada.engine import ImpactCalc
from climada.entity import ImpactFunc, ImpactFuncSet
from climada.util.constants import SYSTEM_DIR

# Ensure the script runs from the correct directory
os.chdir('/cluster/project/climate/meilers/scripts/displacement/global-displacement-risk')

import exposure
import vulnerability

def get_region(country):
    """Get TC regions based on the country code."""
    from climada.entity.impact_funcs.trop_cyclone import ImpfSetTropCyclone
    iso3n_per_region = ImpfSetTropCyclone.get_countries_per_region()[3]
    region_ids_TC_bsn = dict(iso3n_per_region)
    
    # Combine regions as needed
    region_ids_TC_bsn['AP'] = region_ids_TC_bsn.pop('NA1') + region_ids_TC_bsn.pop('NA2')
    region_ids_TC_bsn['IO'] = region_ids_TC_bsn.pop('NI')
    region_ids_TC_bsn['SH'] = region_ids_TC_bsn.pop('OC') + region_ids_TC_bsn.pop('SI')
    region_ids_TC_bsn['WP'] = region_ids_TC_bsn.pop('WP1') + region_ids_TC_bsn.pop('WP2') + region_ids_TC_bsn.pop('WP3') + region_ids_TC_bsn.pop('WP4')
    
    for region, countries in region_ids_TC_bsn.items():
        if country in countries:
            return region
    return None

def assign_basin(lon_min, lon_max, lat_min, lat_max):
    """Assign a basin based on geographical coordinates."""
    BASIN_BOUNDS = {
        'AP': [-180.0, 10.0, 0.0, 85.0],
        'IO': [10.0, 100.0, 0.0, 85.0],
        'SH': [-180.0, 180.0, -85.0, 0.0],
        'WP': [100.0, 180.0, 0.0, 85.0],
    }

    assigned_basins = []
    
    for basin, bounds in BASIN_BOUNDS.items():
        b_lon_min, b_lon_max, b_lat_min, b_lat_max = bounds
        
        if (lon_min >= b_lon_min and lon_max <= b_lon_max and
            lat_min >= b_lat_min and lat_max <= b_lat_max):
            return basin
        
        if (lon_min <= b_lon_max and lon_max >= b_lon_min and
            lat_min <= b_lat_max and lat_max >= b_lat_min):
            assigned_basins.append(basin)
    
    if len(assigned_basins) > 1:
        return 'ROW'
    
    return assigned_basins[0] if assigned_basins else 'Unknown Basin'

def calculate_impact(exp_obj, fut_haz_dict, impf_set_tc_step, tc_haz_sel):
    """Calculate impact and produce AAD and PMD for historical and future scenarios."""
    try:
        impcalc = ImpactCalc(exp_obj, impf_set_tc_step, tc_haz_sel)
        impact = impcalc.impact(save_mat=False)
        
        freq_curve = impact.calc_freq_curve(return_per=np.arange(1, 251, 1))
        rp_indices = [9, 24, 49, 99, 249]
        pm_data_hist = [freq_curve.impact[idx] for idx in rp_indices]

        impact_dict = {}
        for fut, haz in fut_haz_dict.items():
            impcalc_fut = ImpactCalc(exp_obj, impf_set_tc_step, haz)
            impact_fut = impcalc_fut.impact(save_mat=False)
            impact_dict[fut] = impact_fut

        aai_agg_dict = {'ERA-5_hist': impact.aai_agg}
        pmd_dict = {'ERA-5_hist': pm_data_hist}
        for fut, imp in impact_dict.items():
            aai_agg_dict[fut] = imp.aai_agg
            freq_curve = imp.calc_freq_curve(return_per=np.arange(1, 251, 1))
            pm_data = [freq_curve.impact[idx] for idx in rp_indices]
            pmd_dict[fut] = pm_data

        return aai_agg_dict, pmd_dict

    except Exception as e:
        print("Error in calculate_impact function:", str(e))
        raise

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

    # Calculate delta values
    delta_df_list = []
    for model in df['Model'].unique():
        model_df = df[df['Model'] == model]
        if not model_df[model_df['Scenario'] == 'hist'].empty:
            hist_values = model_df[model_df['Scenario'] == 'hist'].iloc[0]
            for period in ['2050', '2100']:
                scenario_df = model_df[model_df['Period'] == period]
                if not scenario_df.empty:
                    delta_values = scenario_df.iloc[0].copy()
                    for col in df.columns[3:]:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            delta_values[col] = scenario_df.iloc[0][col] - hist_values[col]
                    delta_df_list.append(delta_values)

    delta_df = pd.DataFrame(delta_df_list)

    diff_df = delta_df.groupby('Period').median().reset_index()

    era5_df = df[df['Model'] == 'ERA-5'].drop(columns=['Model', 'Scenario', 'Period'])
    era5_df['Scenario'] = 'ERA-5'
    era5_df['Exposure'] = key
    era5_df['Period'] = 'hist'

    df_fut = diff_df.copy()
    for column in ['AAD', 'RP_10', 'RP_25', 'RP_50', 'RP_100', 'RP_250']:
        df_fut[column] = df_fut[column] + era5_df[column].values[0]

    df_fut['Exposure'] = key
    df_fut['Scenario'] = rcp

    res_df = pd.concat([era5_df, df_fut[df_fut['Period'] != 'hist']], ignore_index=True)

    columns_order = ['Exposure', 'Period', 'Scenario', 'AAD', 'RP_10', 'RP_25', 'RP_50', 'RP_100', 'RP_250']
    res_df = res_df[columns_order]

    return res_df

def log_no_tropical_cyclones(cntry_iso, results_dir):
    """Log a note indicating no tropical cyclones were present for the country."""
    country_results_dir = os.path.join(results_dir, cntry_iso)
    os.makedirs(country_results_dir, exist_ok=True)
    note_path = os.path.join(country_results_dir, "note.txt")
    with open(note_path, 'w') as file:
        file.write(f"No tropical cyclones were present for {cntry_iso}.\n")

def main(cntry_iso, rcp, building_thresh):
    """Main function to calculate and save displacement risks."""
    reg = get_region(cntry_iso)
    
    PATH_RESULTS = Path('/cluster/work/climate/evelynm/IDMC_UNU/results/risk_tc')
    path_save = PATH_RESULTS/cntry_iso
    
    if not path_save.is_dir():
        os.mkdir(path_save)
    
    # Load exposure
    gdf_bem_subcomps = exposure.gdf_from_bem_subcomps(cntry_iso, opt='full')
    gdf_bem_subcomps = gdf_bem_subcomps[gdf_bem_subcomps.valhum > 1]  # filter out rows with basically no population
    
    gdf_bem_subcomps['impf_TC'] = gdf_bem_subcomps.apply(lambda row: vulnerability.DICT_PAGER_TCIMPF_CAPRA[row.se_seismo], axis=1)
    gdf_bem_subcomps = exposure.assign_admin1_attr(gdf_bem_subcomps, exposure.path_admin1_attrs, source='gadm')
    
    # Make exposure
    exp = Exposures(gdf_bem_subcomps.copy())
    exp.gdf.rename({'valhum': 'value'}, axis=1, inplace=True)
    exp.value_unit = 'Pop. count'
    exp.gdf['longitude'] = exp.gdf.geometry.x
    exp.gdf['latitude'] = exp.gdf.geometry.y
    exp.gdf = exp.gdf[~np.isnan(exp.gdf.latitude)]  # drop nan centroids
    
    print(f'Total population {cntry_iso}: {exp.gdf.value.sum():,.0f}')
    
    lat_min, lat_max, lon_min, lon_max = exp.gdf['latitude'].min(), exp.gdf['latitude'].max(), exp.gdf['longitude'].min(), exp.gdf['longitude'].max()
    if reg == 'ROW':
        assigned_basin = assign_basin(lon_min, lon_max, lat_min, lat_max)
        print(f'The country is assigned to the {assigned_basin} basin.')
        reg = assigned_basin if assigned_basin != 'ROW' else 'ROW'
    
    # Load hazard data
    hazard_dir = SYSTEM_DIR / 'hazard' / 'present'
    if reg != 'ROW':
        tc_haz = TropCyclone.from_hdf5(hazard_dir.joinpath(f'TC_{reg}_0150as_MIT_H08.hdf5'))
    else:
        haz_list = []
        for bsn in ['AP', 'IO', 'SH', 'WP']:
            haz = TropCyclone.from_hdf5(hazard_dir.joinpath(f'TC_{bsn}_0150as_MIT_H08.hdf5'))
            haz_list.append(haz)
        tc_haz = Hazard.concat(haz_list)
    
    tc_haz_sel = tc_haz.select(extent=(lon_min, lon_max, lat_min, lat_max))
    
    # Check if the hazard selection has intensity attribute
    try:
        _ = tc_haz_sel.intensity
    except AttributeError:
        log_no_tropical_cyclones(cntry_iso, PATH_RESULTS)
        print(f"No tropical cyclones were present for {cntry_iso}. Logging this information and skipping further processing.")
        return
    
    models = ['cesm2', 'cnrm6', 'ecearth6', 'fgoals', 'ipsl6', 'miroc6', 'mpi6', 'mri6', 'ukmo6']
    scenario = ['20thcal', 'cal', '_2cal']
    yr_dict = {'20thcal': 'hist', 'cal': 2050, '_2cal': 2100}
    
    hazard_dir = SYSTEM_DIR / 'hazard' / 'future'
    fut_haz_dict = {}
    for gcm in models:
        for scen in scenario:
            if reg != 'ROW':
                if scen == '20thcal':
                    haz_str = f'TC_{reg}_0150as_MIT_{gcm}_{scen}_H08.hdf5'
                    haz = TropCyclone.from_hdf5(hazard_dir.joinpath(haz_str))
                    haz_sel = haz.select(extent=(lon_min, lon_max, lat_min, lat_max))
                    fut_haz_dict[gcm+'_'+str(yr_dict[scen])] = haz_sel
                else:
                    haz_str = f'TC_{reg}_0150as_MIT_{gcm}_{rcp}{scen}_H08.hdf5'
                    haz = TropCyclone.from_hdf5(hazard_dir.joinpath(haz_str))
                    haz_sel = haz.select(extent=(lon_min, lon_max, lat_min, lat_max))
                    fut_haz_dict[gcm+'_'+rcp+'_'+str(yr_dict[scen])] = haz_sel
            else:
                haz_list = []
                for bsn in ['AP', 'IO', 'SH', 'WP']:
                    if scen == '20thcal':
                        haz_str = f'TC_{bsn}_0150as_MIT_{gcm}_{scen}_H08.hdf5'
                    else:
                        haz_str = f'TC_{bsn}_0150as_MIT_{gcm}_{rcp}{scen}_H08.hdf5'
                    haz = TropCyclone.from_hdf5(hazard_dir.joinpath(haz_str))
                    haz_list.append(haz)
                combined_haz = Hazard.concat(haz_list)
                haz_sel = combined_haz.select(extent=(lon_min, lon_max, lat_min, lat_max))
                if scen == '20thcal':
                    fut_haz_dict[gcm+'_'+str(yr_dict[scen])] = haz_sel
                else:
                    fut_haz_dict[gcm+'_'+rcp+'_'+str(yr_dict[scen])] = haz_sel
    
    ad1 = np.unique(exp.gdf.admin1).tolist()
    
    exp_dict = {'admin0': exp}
    for admin1 in ad1:
        admin1_gdf = exp.gdf[exp.gdf.admin1 == admin1]
        exp_admin1 = copy.deepcopy(exp)
        exp_admin1.gdf = admin1_gdf
        exp_dict[f'admin1_{int(admin1)}'] = exp_admin1
    
    impf_set_tc = vulnerability.IMPF_SET_TC_CAPRA
    impf_set_tc_step = ImpactFuncSet()
    for imp_id in impf_set_tc.get_ids(haz_type='TC'):
        y = impf_set_tc.get_func(fun_id=imp_id)[0].intensity
        x = impf_set_tc.get_func(fun_id=imp_id)[0].mdd
        thresh = np.interp(building_thresh, x, y)
        impf_set_tc_step.append(ImpactFunc.from_step_impf(intensity=(0, thresh, thresh * 10), haz_type='TC', impf_id=imp_id, intensity_unit='m/s'))

    results = []
    for key, exp_obj in exp_dict.items():
        res_df = process_imp(exp_obj, key, fut_haz_dict, impf_set_tc_step, tc_haz_sel)
        results.append(res_df)

    combined_df = pd.concat(results, ignore_index=True)
    combined_df.to_csv(path_save/f'{cntry_iso}_{rcp}_{building_thresh}_TC.csv')
    

if __name__ == '__main__':
    cntry_iso = sys.argv[1]
    rcp = sys.argv[2]
    building_thresh = float(sys.argv[3])
    main(cntry_iso, rcp, building_thresh)
