#!/usr/bin/env python3
"""
Enhance unified glass catalog with coating side information from IGSDB
"""

import pandas as pd
import requests
import time
from tqdm import tqdm

# === CONFIGURATION ===
API_KEY = "0e94db9c8cda032d3eaa083e21984350c17633ca"
IGSDB_HEADERS = {
    "accept": "application/json",
    "Authorization": f"Token {API_KEY}"
}

CATALOG_FILE = "unified_glass_catalog.csv"
OUTPUT_FILE = "unified_glass_catalog_enhanced.csv"

def get_product_id_from_nfrc(nfrc_id: int) -> int:
    """Get product ID from NFRC ID"""
    url = f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nfrc_id}"
    resp = requests.get(url, headers=IGSDB_HEADERS, timeout=5)
    if not resp.ok:
        return None
    data = resp.json()
    return data[0].get("product_id") if data else None

def fetch_coating_info(prod_id: int) -> dict:
    """Fetch coating information from IGSDB"""
    if not prod_id:
        return {"coating_side": "none", "coating_name": "none", "emissivity": None}
    
    resp = requests.get(f"https://igsdb.lbl.gov/api/v1/products/{prod_id}/", headers=IGSDB_HEADERS, timeout=5)
    if not resp.ok:
        return {"coating_side": "none", "coating_name": "none", "emissivity": None}
    
    d = resp.json()
    
    # Get coating side
    coating_side = (d.get("coated_side") or "none").lower()
    if coating_side == "none":
        for layer in d.get("layers", []):
            if layer.get("type") == "coating":
                coating_side = layer.get("location", "none").lower()
                break
    
    # Get coating name
    coating_name = d.get("coating_name") or "none"
    
    # Get emissivity if available
    emissivity = None
    md = d.get("measured_data", {})
    if md:
        # Try to get emissivity from measured data
        emissivity = md.get("emissivity_front") or md.get("emissivity_back")
    
    return {
        "coating_side": coating_side,
        "coating_name": coating_name, 
        "emissivity": emissivity
    }

def enhance_catalog():
    """Enhance catalog with coating information"""
    print("🔍 Enhancing glass catalog with coating information...")
    
    # Load existing catalog
    df = pd.read_csv(CATALOG_FILE)
    print(f"📊 Loaded {len(df)} glass types")
    
    # Add new columns
    df["Coating_Side"] = ""
    df["Coating_Name"] = ""
    df["Emissivity"] = None
    df["IGSDB_Status"] = ""
    
    # Process each glass type
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Fetching coating info"):
        nfrc_id = row["NFRC_ID"]
        
        try:
            # Get product ID
            prod_id = get_product_id_from_nfrc(nfrc_id)
            if not prod_id:
                df.at[idx, "IGSDB_Status"] = "NFRC ID not found"
                df.at[idx, "Coating_Side"] = "unknown"
                df.at[idx, "Coating_Name"] = "unknown"
                continue
            
            # Get coating info
            coating_info = fetch_coating_info(prod_id)
            
            df.at[idx, "Coating_Side"] = coating_info["coating_side"]
            df.at[idx, "Coating_Name"] = coating_info["coating_name"]
            df.at[idx, "Emissivity"] = coating_info["emissivity"]
            df.at[idx, "IGSDB_Status"] = "✅ Found"
            
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Error processing NFRC {nfrc_id}: {e}")
            df.at[idx, "IGSDB_Status"] = f"Error: {str(e)}"
            df.at[idx, "Coating_Side"] = "error"
            df.at[idx, "Coating_Name"] = "error"
    
    # Save enhanced catalog
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Enhanced catalog saved to {OUTPUT_FILE}")
    
    # Show summary
    print("\n📊 Coating Side Summary:")
    coating_summary = df["Coating_Side"].value_counts()
    for side, count in coating_summary.items():
        print(f"   {side}: {count}")
    
    print("\n📋 Sample Enhanced Data:")
    print(df[["NFRC_ID", "Short_Name", "Coating_Side", "Coating_Name", "IGSDB_Status"]].head(10))
    
    return df

if __name__ == "__main__":
    enhanced_df = enhance_catalog()
    print("\n🎉 Catalog enhancement complete!")
    print(f"💾 Enhanced catalog available at: {OUTPUT_FILE}")
    print("🔄 You can now use this enhanced catalog in your workflow")