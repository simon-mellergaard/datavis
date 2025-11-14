"""
Formatting functions for data processing. The script should format the raw data
file and transform it into a cleaned version called UFM_cleaned.xlsx.
"""

import pandas as pd
import numpy as np
from pathlib import Path


# Load data
data = pd.read_excel("UFM_samlet_30OCT2025.xlsx", header=0)

# Make all columns lowercase
data.columns = [col.lower() for col in data.columns]


# Write the cleaned data to a new Excel file
cleaned_data_path = Path("UFM_cleaned.xlsx")
data.to_excel(cleaned_data_path, index=False)