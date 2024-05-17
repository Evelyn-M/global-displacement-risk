#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 10:10:42 2024

@author: simonameiler
------

Processing data for validation of risk computations.
"""

import numpy as np
    
def extract_idmc_data(df, iso3=None, hazard_sub_type=None, calculation='full', start_year=None, end_year=None):
    """
    Extracts a subset of the given iDMC DataFrame based on ISO3, Hazard Sub Type, and Year range.
    Allows calculation of 'full', 'mean', 'median', or 'sum' over 'Disaster Internal Displacements'.

    Parameters:
    - df: pandas DataFrame to select from.
    - iso3: ISO3 code of the country (str).
    - hazard_sub_type: Hazard Sub Type to filter by (str).
    - calculation: One of 'full', 'mean', 'median', 'sum'. Determines the type of calculation to return.
    - start_year: Starting year of the range to include (inclusive).
    - end_year: Ending year of the range to include (inclusive).

    Returns:
    - The requested DataFrame or value based on the calculation.
    """
    # Filter DataFrame based on 'ISO3', 'Hazard Sub Type', and 'Year' range if provided
    if iso3:
        df = df[df['ISO3'] == iso3]
    if hazard_sub_type:
        df = df[df['Hazard Sub Type'] == hazard_sub_type]
    if start_year is not None:
        df = df[df['Year'] >= start_year]
    if end_year is not None:
        df = df[df['Year'] <= end_year]
    
    # Select specific columns
    columns = ['ISO3', 'Country / Territory', 'Year', 'Event Name', 'Date of Event (start)',
               'Disaster Internal Displacements', 'Disaster Internal Displacements (Raw)',
               'Hazard Category', 'Hazard Type', 'Hazard Sub Type', 'Event Codes (Code:Type)']
    df = df[columns]
    
    # Calculate based on the calculation type
    if calculation in ['mean', 'median']:
        # Calculate annual sums
        annual_sums = df.groupby('Year')['Disaster Internal Displacements'].sum()
        # Ensure all years in the specified range are included, fill missing years with 0
        if start_year and end_year:
            full_year_range = np.arange(start_year, end_year + 1)
            annual_sums = annual_sums.reindex(full_year_range, fill_value=0)
        return annual_sums.mean() if calculation == 'mean' else annual_sums.median()
    elif calculation == 'sum':
        return df['Disaster Internal Displacements'].sum()
    else:
        return df

