import pandas as pd
import os
import re
from tqdm import tqdm
from collections import defaultdict

# Config
input_csv = "vertexai_feed.csv"
output_dir = "output_files"
chunksize = 10000  # Adjust based on your available memory

# Prepare output directory
os.makedirs(output_dir, exist_ok=True)

# Initialize dictionary for storing attribute keys per N-level category
product_type_keys = defaultdict(set)

# Function to sanitize filenames
def sanitize_filename(name):
    # Replace special characters with underscores and trim excessive underscores
    return re.sub(r'[^\w\-_.\&]', '_', name)

# Read CSV in chunks
with pd.read_csv(input_csv, chunksize=chunksize) as reader:
    for chunk in tqdm(reader, desc="Processing Chunks"):
        for index, row in chunk.iterrows():
            product_type_full = row.get("product_type", "")
            filterable_attributes = row.get("filterable_attributes", "")

            if pd.isna(product_type_full) or pd.isna(filterable_attributes):
                continue

            # Extract keys from attributes
            attributes = filterable_attributes.split(",")
            keys = {attr.split(":")[0].strip() for attr in attributes if ":" in attr}

            # Create N-level categories
            parts = [part.strip() for part in product_type_full.split(">")]
            for i in range(1, len(parts) + 1):
                category_path = " > ".join(parts[:i])
                product_type_keys[category_path].update(keys)

# Save results
for category_path, keys in product_type_keys.items():
    safe_filename = sanitize_filename(category_path.replace(" > ", "__"))
    output_file = os.path.join(output_dir, f"{safe_filename}.csv")
    df_output = pd.DataFrame({"Attribute Keys": sorted(keys)})
    df_output.to_csv(output_file, index=False)
    print(f"✅ Saved: {output_file}")

print("🎉 Finished! All N-level categories processed.")
