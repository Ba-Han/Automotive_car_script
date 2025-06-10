#!pip install pandas beautifulsoup4 openpyxl

import pandas as pd

# Step 1: Load the Excel file
file_path = '/content/accessories (1).xlsx'

# Step 2: Read the Excel file
df = pd.read_excel(file_path)

# Step 3: Forward-fill only the 'Item Number' if it exists
if 'Item Number' in df.columns:
    df['Item Number'] = df['Item Number'].ffill()

# Step 4: Sort only by 'Item Number'
#df = df.sort_values(by='Item Number')

# Step 5: Define the exact columns to keep
columns_to_keep = [
    'Item Number', 'OEM Brand', 'OEM Code', 'OEM Quality', 'OEM Product', 'OEM Price',
    'VC Model', 'VC Engine Code', 'VC Fuel', 'VC Displacement',
    'VC HP', 'VC KW', 'VC Year'
]

# Step 6: Filter only existing columns to avoid KeyError
columns_to_keep = [col for col in columns_to_keep if col in df.columns]
df = df[columns_to_keep]

# Step 7: Save to Excel
output_path = '/content/sorted_filtered_accessories.xlsx'
df.to_excel(output_path, index=False)

print("✅ Filtered & sorted file saved as:", output_path)

##############################################################################################################

import pandas as pd

# Step 1: Load the Excel file
file_path = '/content/accessories (1).xlsx'
df = pd.read_excel(file_path)

# Step 2: Remove unwanted OEM/VC columns (if they exist)
columns_to_remove = [
    'OEM Brand', 'OEM Code', 'OEM Quality', 'OEM Product', 'OEM Price',
    'VC Model', 'VC Engine Code', 'VC Fuel', 'VC Displacement', 'VC HP', 'VC KW', 'VC Year'
]
df = df.drop(columns=[col for col in columns_to_remove if col in df.columns], errors='ignore')

# ✅ Step 3: Remove rows where **all** values are NaN (i.e. blank rows)
df = df.dropna(how='all')

# ✅ Step 4: Format the 'Price' column with '$'
if 'Price' in df.columns:
    df['Price'] = df['Price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")

# Optional: Also remove rows where key columns are empty (e.g., 'Product Name' or 'Product Number')
# df = df[df['Product Name'].notna() & df['Product Number'].notna()]

# Step 5: Save cleaned Excel
output_path = '/content/final_cleaned_output_test.xlsx'
df.to_excel(output_path, index=False)

print("✅ Cleaned Excel saved with no OEM/VC columns and no empty rows:", output_path)
