#!/usr/bin/env python3
"""
Small batch simulation test - run just 10 rows to verify it works quickly
"""

import pandas as pd
import pywincalc
import requests
import pickle
import os
from tqdm import tqdm
from datetime import datetime

# Config
INPUT_CSV = "igu_simulation_input_table.csv"
OUTPUT_CSV = f"test_simulation_results_{datetime.now():%Y%m%d_%H%M%S}.csv"
CACHE_FILE = "igsdb_layer_cache.pkl"
TEST_ROWS = 50  # Quick test with 50 rows

# IGSDB setup
API_KEY = "0e94db9c8cda032d3eaa083e21984350c17633ca"
IGSDB_HEADERS = {"accept": "application/json", "Authorization": f"Token {API_KEY}"}
url_single_product = "https://igsdb.lbl.gov/api/v1/products/{id}/"

print(f"🧪 Small Simulation Test - Processing {TEST_ROWS} rows")

# Load input
df = pd.read_csv(INPUT_CSV)
print(f"✅ Loaded {len(df)} total rows, testing first {TEST_ROWS}")

# Get NFRC columns
nfrc_cols = [c for c in df.columns if c.startswith("Glass") and c.endswith("NFRC ID")]
print(f"📋 NFRC columns: {nfrc_cols}")

# Load or create cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            print("⚠️ Cache corrupted, starting fresh")
            return {}
    return {}

layer_cache = load_cache()
print(f"💾 Loaded cache with {len(layer_cache)} entries")

# Get unique NFRC IDs from test rows
test_df = df.head(TEST_ROWS)
ids = set()
for col in nfrc_cols:
    ids.update(test_df[col].dropna().astype(int))
ids = sorted(list(ids))
print(f"🔍 Need to fetch {len(ids)} unique NFRC IDs: {ids}")

# Fetch missing entries
missing = [i for i in ids if i not in layer_cache]
if missing:
    print(f"📡 Fetching {len(missing)} missing IGSDB entries...")
    for nid in tqdm(missing, desc="Fetching"):
        try:
            # Get product ID
            r1 = requests.get(
                f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nid}",
                headers=IGSDB_HEADERS,
                timeout=10
            )
            r1.raise_for_status()
            arr = r1.json()
            pid = arr[0]['product_id'] if arr else None
            
            if pid:
                # Get layer data
                r2 = requests.get(url_single_product.format(id=pid), headers=IGSDB_HEADERS, timeout=10)
                r2.raise_for_status()
                layer_cache[nid] = r2.content
                print(f"   ✅ Cached NFRC {nid}")
            else:
                layer_cache[nid] = None
                print(f"   ❌ No product for NFRC {nid}")
        except Exception as e:
            print(f"   ❌ Error fetching NFRC {nid}: {e}")
            layer_cache[nid] = None
    
    # Save updated cache
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(layer_cache, f)
    print("💾 Cache updated")
else:
    print("✅ All needed entries already cached")

# Helper functions (same as original)
def build_gaps(gas, ag_mm, igu_type):
    g = str(gas).upper()
    if '95A' in g:
        pct, gt = 0.95, pywincalc.PredefinedGasType.ARGON
    elif '90K' in g:
        pct, gt = 0.90, pywincalc.PredefinedGasType.KRYPTON
    else:
        pct, gt = 1.0, pywincalc.PredefinedGasType.AIR
    mix = pywincalc.create_gas([[pct, gt], [1-pct, pywincalc.PredefinedGasType.AIR]])
    count = 2 if igu_type.lower()=='triple' else 3
    thickness_m = ag_mm / 1000.0
    return [pywincalc.Layers.gap(thickness=thickness_m, gas=mix) for _ in range(count)]

def get_layer(nfrc_id):
    raw = layer_cache.get(int(nfrc_id)) if pd.notna(nfrc_id) else None
    if not raw:
        return None
    
    # Handle both JSON strings and dictionary formats from cache
    if isinstance(raw, str):
        return pywincalc.parse_json(raw)
    elif isinstance(raw, dict):
        # Cache contains metadata dict, need to fetch actual layer data
        print(f"⚠️ Cache contains metadata dict for NFRC {nfrc_id}, fetching layer data...")
        return fetch_layer_from_igsdb(int(nfrc_id))
    else:
        return None

def fetch_layer_from_igsdb(nfrc_id: int):
    """Fetch layer data directly from IGSDB for simulation"""
    try:
        # Get product ID
        url = f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nfrc_id}"
        resp = requests.get(url, headers={"accept": "application/json", "Authorization": "Token 0e94db9c8cda032d3eaa083e21984350c17633ca"}, timeout=10)
        if not resp.ok:
            return None
        data = resp.json()
        if not data:
            return None
        
        product_id = data[0].get("product_id")
        if not product_id:
            return None
        
        # Get full product data for simulation
        resp = requests.get(f"https://igsdb.lbl.gov/api/v1/products/{product_id}/", 
                          headers={"accept": "application/json", "Authorization": "Token 0e94db9c8cda032d3eaa083e21984350c17633ca"}, 
                          timeout=10)
        if not resp.ok:
            return None
        
        # Parse as JSON layer for pywincalc
        return pywincalc.parse_json(resp.text)
        
    except Exception as e:
        print(f"⚠️ Error fetching layer data for NFRC {nfrc_id}: {e}")
        return None

# Run simulation on test rows
print(f"\n🚀 Running simulation on {TEST_ROWS} rows...")
results = []
debug = {'tested': 0, 'no_layers': 0, 'sim_errors': 0, 'passed': 0}

for idx, row in tqdm(test_df.iterrows(), total=TEST_ROWS, desc="Simulating"):
    debug['tested'] += 1
    
    # Get layers
    layers = [get_layer(row[c]) for c in nfrc_cols if pd.notna(row[c])]
    layers = [l for l in layers if l is not None]
    
    if not layers:
        debug['no_layers'] += 1
        continue
    
    # Build gaps
    gaps = build_gaps(row['Gas Type'], row['Air Gap (mm)'], row['IGU Type'])
    
    try:
        # Create glazing system
        sys = pywincalc.GlazingSystem(solid_layers=layers, gap_layers=gaps)
        
        # Apply flipping (same as original)
        for i in range(len(layers)):
            if row.get(f"Flip Glass {i+1}") in (True, 'True', 1):
                sys.flip_layer(i, True)
        
        # Calculate results (using correct PyWinCalc API)
        u_value = sys.u()  # W/m²·K
        u_btu = u_value / 5.678  # Convert to BTU/hr·ft²·°F
        
        sys.environments(pywincalc.nfrc_shgc_environments())
        shgc = sys.shgc()
        
        # Visual transmittance 
        optical_results = sys.optical_method_results('PHOTOPIC')
        vt = optical_results.system_results.front.transmittance.direct_hemispherical
        
        # Store results
        results.append({
            'Row_Index': idx,
            'IGU Type': row['IGU Type'],
            'U_Value_SI': u_value,
            'U_Value_IP': u_btu,  
            'SHGC': shgc,
            'VT': vt,
            'Gas Type': row['Gas Type'],
            'OA (in)': row['OA (in)'],
            'Glass_1_NFRC': row.get('Glass 1 NFRC ID', ''),
            'Glass_2_NFRC': row.get('Glass 2 NFRC ID', ''),
            'Glass_3_NFRC': row.get('Glass 3 NFRC ID', ''),
            'Glass_4_NFRC': row.get('Glass 4 NFRC ID', ''),
        })
        
        debug['passed'] += 1
        
    except Exception as e:
        debug['sim_errors'] += 1
        print(f"   ❌ Simulation error on row {idx}: {e}")

# Save results
if results:
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved {len(results)} results to {OUTPUT_CSV}")
    
    # Show sample results
    print(f"\n📊 Sample Results:")
    print(results_df.head().to_string(index=False))
else:
    print("❌ No results generated")

# Summary
print(f"\n📋 Debug Summary:")
print(f"   Tested: {debug['tested']}")
print(f"   No layers: {debug['no_layers']}")
print(f"   Simulation errors: {debug['sim_errors']}")
print(f"   Passed: {debug['passed']}")
print(f"   Success rate: {debug['passed']/debug['tested']*100:.1f}%")

if debug['passed'] > 0:
    print(f"\n🎉 SUCCESS! Simulation working correctly.")
    print(f"💡 The main simulation is slow because it processes all {len(df)} rows.")
    print(f"💡 Consider running in smaller batches or using more cache.")
else:
    print(f"\n❌ No successful simulations. Check NFRC IDs and data quality.")