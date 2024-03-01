#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 12:03:08 2024

@author: evelynm

------

Formatting exposure layers for the displacement risk computations
"""


from climada.entity.exposures import Exposures
from climada.util import coordinates as u_coords
import shapely
import pyproj
import geopandas as gpd
import pandas as pd

# GLOBAL LAYERS

# global high resolution settlement layer
path_ghsl = '/Users/evelynm/Documents/UNU_IDMC/data/exposure/GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0/GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.tif'

# BEM values residential
path_bem_res = '/Users/evelynm/Documents/UNU_IDMC/data/exposure/bem_global_raster/bem_1x1_valfis_res.tif'

# BEM values non-residential
path_bem_nres = '/Users/evelynm/Documents/UNU_IDMC/data/exposure/bem_global_raster/bem_1x1_valfis_nres.tif'

path_grid = '/Users/evelynm/Documents/UNU_IDMC/data/exposure/grid_1x1_gid.tif'

# grid for BEM
path_grid_tif = '/Users/evelynm/Documents/UNU_IDMC/data/exposure/grid_1x1_gid.tif'

# COUNTRY SUB-LAYERS
cntry_name = 'Somalia'
cntry_iso = u_coords.country_to_iso(cntry_name)
path_cntry_bem_csv = f'/Users/evelynm/Documents/UNU_IDMC/data/exposure/bem_cntry_files/{cntry_iso.lower()}_bem_1x1_valfis.csv'

geom_cntry = shapely.ops.unary_union(
    [geom for geom in
     u_coords.get_country_geometries([cntry_iso]).geometry])


# Load GHSL Exposure
proj_54009 = pyproj.crs.CRS.from_string('esri:54009')
proj_4326 = pyproj.crs.CRS(4326)

exp_ghsl = Exposures.from_raster(
    path_ghsl, src_crs=proj_54009, dst_crs=proj_4326, geometry=[geom_cntry])

exp_ghsl.gdf = gpd.GeoDataFrame(
    exp_ghsl.gdf,
    geometry=gpd.points_from_xy(exp_ghsl.gdf.longitude, exp_ghsl.gdf.latitude),
    crs="EPSG:4326")

# Load BEM Exposure (res)
exp_bem_res = Exposures.from_raster(
    path_bem_res, geometry=[geom_cntry])
exp_bem_res.gdf = gpd.GeoDataFrame(
    exp_bem_res.gdf,
    geometry=gpd.points_from_xy(
        exp_bem_res.gdf.longitude, exp_bem_res.gdf.latitude),
    crs="EPSG:4326")

# Load BEM Exposure (nres)
exp_bem_nres = Exposures.from_raster(
    path_bem_nres, geometry=[geom_cntry])
exp_bem_nres.gdf = gpd.GeoDataFrame(
    exp_bem_nres.gdf,
    geometry=gpd.points_from_xy(
        exp_bem_nres.gdf.longitude, exp_bem_nres.gdf.latitude),
    crs="EPSG:4326")


# reshape csv-based df of BEM sub-indicators
df_bem_parts = pd.read_csv(path_cntry_bem_csv)
df_bem_parts = df_bem_parts[(
    (df_bem_parts['bs_value_r'] > 0) & (df_bem_parts['bs_value_nr'] > 0) &
    (df_bem_parts['valhum'] > 0) & (
        df_bem_parts['valfis'] > 0)  # 11115126 -> 6085413
)]

df_bem_parts['sector_se_seismo'] = df_bem_parts.sector + \
    '_'+df_bem_parts.se_seismo
df_bem_parts.pop('sector')
df_bem_parts.pop('se_seismo')

df_bem_parts_pivot = df_bem_parts.pivot(
    index=['id_1x'], columns='sector_se_seismo',
    values=['bs_value_r', 'bs_value_nr',
            'valhum', 'valfis', 'bd_1_floor', 'bd_2_floor', 'bd_3_floor'])
df_bem_parts_pivot['cpx'] = df_bem_parts.groupby('id_1x')['cpx'].mean()
# df_bem_parts_pivot.size/df_bem_parts.size =  0.9509977981176239
# del df_bem_parts


# Load BEM grid as exposure
exp_bem_grid = Exposures.from_raster(path_grid_tif, geometry=[geom_cntry])
exp_bem_res.gdf = gpd.GeoDataFrame(
    exp_bem_grid.gdf,
    geometry=gpd.points_from_xy(
        exp_bem_grid.gdf.longitude, exp_bem_grid.gdf.latitude),
    crs="EPSG:4326")
