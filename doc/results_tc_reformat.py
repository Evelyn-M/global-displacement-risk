#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 15:09:18 2024

@author: simonameiler
"""

import pandas as pd
from pathlib import Path

thresh = 0.55

# Load both CSV files
path_results = Path('/Users/simonameiler/Documents/work/03_code/repos/global-displacement-risk/data/results')
tc_admin0_template = pd.read_csv(path_results/'tc_admin0_0.55.csv')
tc_admin0_data = pd.read_csv(path_results/f'displacement_risk_tc_global_admin0_{thresh}_check.csv')

# Mapping of scenarios and periods
scenario_mapping = {
    'ERA-5': 'current',
    'ssp245': 'optimistic',
    'ssp370': 'medium',
    'ssp585': 'pessimistic'
}

period_mapping = {
    'hist': 2020
}

# Apply the mappings to the displacement file
tc_admin0_data['scenario'] = tc_admin0_data['Scenario'].map(scenario_mapping)
tc_admin0_data['year'] = tc_admin0_data['Period'].map(period_mapping).fillna(tc_admin0_data['Period'])

# Rename columns to match the format of the first file
tc_admin0_formatted = tc_admin0_data.rename(columns={
    'iso3': 'admin0',
    'AAD': 'AAD',
    'RP_10': 'PMD_10',
    'RP_25': 'PMD_25',
    'RP_100': 'PMD_100',
    'RP_250': 'PMD_250'
})

# Select only the relevant columns
tc_admin0_formatted = tc_admin0_formatted[['admin0', 'scenario', 'year', 'AAD', 'PMD_10', 'PMD_25', 'PMD_100', 'PMD_250']]

# Reorder based on the first file's 'admin0', ensuring no changes to unique combinations of 'admin0', 'scenario', and 'year'
sorted_admin0 = tc_admin0_template['admin0'].unique()
admin0_order_mapping = {country: idx for idx, country in enumerate(sorted_admin0)}

# Add a column to the displacement data to reflect the order of the admin0 as in the first file
tc_admin0_formatted['order'] = tc_admin0_formatted['admin0'].map(admin0_order_mapping)

# Sort the reformatted file based on this new 'order' column
tc_admin0_sorted = tc_admin0_formatted.sort_values(by='order').drop(columns='order')

# Identify missing countries
missing_admin0 = set(sorted_admin0) - set(tc_admin0_sorted['admin0'])

# Define the scenario and year combinations to be added for each missing country
scenarios_years = pd.DataFrame({
    'scenario': ['current', 'medium', 'medium', 'optimistic', 'optimistic', 'pessimistic', 'pessimistic'],
    'year': [2020, 2050, 2100, 2050, 2100, 2050, 2100]
})

# For each missing country, replicate the scenario and year combinations
missing_admin0_expanded = []
for country in missing_admin0:
    country_df = scenarios_years.copy()
    country_df['admin0'] = country
    missing_admin0_expanded.append(country_df)

# Concatenate all the country-specific dataframes
missing_admin0_final = pd.concat(missing_admin0_expanded, ignore_index=True)

# Reindex to have the same columns as the second file, with NaN for the remaining columns
missing_admin0_final = missing_admin0_final.reindex(columns=tc_admin0_sorted.columns)

# Append the new missing countries with scenario/year information to the existing dataframe
displacement_risk_tc_global_admin0_complete = pd.concat([tc_admin0_sorted, missing_admin0_final])

# Sort the final dataframe by 'admin0' to maintain the order
displacement_risk_tc_global_admin0_complete = displacement_risk_tc_global_admin0_complete.sort_values(by=['admin0', 'scenario', 'year'])

# Save the final complete version
displacement_risk_tc_global_admin0_complete.to_csv(path_results/f'tc_admin0_{thresh}_event-based.csv', index=False)
