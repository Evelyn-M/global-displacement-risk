#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 10:10:42 2024

@author: simonameiler
------

Processing data for validation of risk computations.
"""

import numpy as np

def extract_idmc_data(df, iso3=None, hazard_sub_type=None, calculation='full'):
    """
    Extracts a subset of the given iDMC DataFrame based on ISO3 and Hazard Sub Type.
    Allows calculation of 'full', 'mean', 'median', or 'sum' over 'Disaster Internal Displacements'.

    Parameters:
    - df: pandas DataFrame to select from.
    - iso3: ISO3 code of the country (str).
    - hazard_sub_type: Hazard Sub Type to filter by (str).
    - calculation: One of 'full', 'mean', 'median', 'sum'. Determines the type of calculation to return.

    Returns:
    - The requested DataFrame or value based on the calculation.
    """
    # Filter DataFrame based on 'ISO3' and 'Hazard Sub Type' if provided
    if iso3:
        df = df[df['ISO3'] == iso3]
    if hazard_sub_type:
        df = df[df['Hazard Sub Type'] == hazard_sub_type]
    
    # Select specific columns
    columns = ['ISO3', 'Country / Territory', 'Year', 'Event Name', 'Date of Event (start)',
               'Disaster Internal Displacements', 'Disaster Internal Displacements (Raw)',
               'Hazard Category', 'Hazard Type', 'Hazard Sub Type', 'Event Codes (Code:Type)']
    df = df[columns]
    
    # Calculate based on the calculation type
    if calculation in ['mean', 'median']:
        # Calculate annual sums
        annual_sums = df.groupby('Year')['Disaster Internal Displacements'].sum()
        # Get full year range and fill missing years with 0
        full_year_range = np.arange(df['Year'].min(), df['Year'].max() + 1)
        annual_sums = annual_sums.reindex(full_year_range, fill_value=0)
        return annual_sums.mean() if calculation == 'mean' else annual_sums.median()
    elif calculation == 'sum':
        return df['Disaster Internal Displacements'].sum()
    else:
        return df
