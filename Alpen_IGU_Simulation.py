#!/usr/bin/env python3
"""
Alpen IGU Simulation Runner (Fixed Indentation)
- Reads igu_simulation_input_table.csv
- Caches IGSDB JSON
- Extracts nominal & actual thickness
- Builds IGU Name
- Computes performance
- Debug counters to track filtering
"""
import pandas as pd
import requests
import pywincalc
from igsdb_interaction import url_single_product, headers as IGSDB_HEADERS
from tqdm import tqdm
from datetime import datetime
import pickle
import os
import json

# --- Config ---
INPUT_CSV  = "igu_simulation_input_table.csv"
OUTPUT_CSV = f"igu_simulation_results_{datetime.now():%Y%m%d_%H%M%S}.csv"
CACHE_FILE = "igsdb_layer_cache.pkl"

# --- Prompt for batch ---
def prompt_batch_size(total):
    # Check if running in non-interactive mode (from Streamlit/script)
    import sys
    if not sys.stdin.isatty():
        print(f"Non-interactive mode detected. Processing all {total} rows automatically.")
        return total
    
    while True:
        try:
            ans = input(f"Process all {total} rows? (y/n): ").strip().lower()
            if ans == 'y':
                return total
            if ans == 'n':
                try:
                    num = int(input("How many rows? ").strip())
                    return min(num, total)
                except ValueError:
                    print("Enter a number or 'y'/ 'n'.")
            else:
                print("Please answer 'y' or 'n'.")
        except EOFError:
            print(f"EOF detected. Processing all {total} rows automatically.")
            return total

# --- Load input & cache ---
print("Loading input and caching IGSDB data...")
df = pd.read_csv(INPUT_CSV)
nfrc_cols = [c for c in df.columns if c.startswith("Glass") and c.endswith("NFRC ID")]

# Load or init cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return pickle.load(open(CACHE_FILE, 'rb'))
        except:
            print("⚠️ Cache corrupt, resetting.")
    return {}
layer_cache = load_cache()

# Gather IDs to fetch
ids = set()
for col in nfrc_cols:
    ids |= set(df[col].dropna().astype(int))
# Fetch missing
missing = [i for i in ids if i not in layer_cache]
if missing:
    print(f"Fetching {len(missing)} IGSDB entries...")
    for nid in tqdm(missing, unit="id"):
        try:
            r1 = requests.get(
                f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nid}",
                headers=IGSDB_HEADERS
            )
            r1.raise_for_status()
            arr = r1.json()
            pid = arr[0]['product_id'] if arr else None
            if pid:
                r2 = requests.get(url_single_product.format(id=pid), headers=IGSDB_HEADERS)
                r2.raise_for_status()
                layer_cache[nid] = r2.content
            else:
                layer_cache[nid] = None
        except Exception as e:
            print(f"Error fetching NFRC {nid}: {e}")
            layer_cache[nid] = None
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(layer_cache, f)
else:
    print("Cache is up to date.")

# --- Helpers ---

def build_gaps(gas, ag_mm, igu_type):
    """Build gap layers based on gas and IGU type"""
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
        headers = {"accept": "application/json", "Authorization": "Token 0e94db9c8cda032d3eaa083e21984350c17633ca"}
        resp = requests.get(url, headers=headers, timeout=10)
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
                          headers=headers, 
                          timeout=10)
        if not resp.ok:
            return None
        
        # Parse as JSON layer for pywincalc
        return pywincalc.parse_json(resp.text)
        
    except Exception as e:
        print(f"⚠️ Error fetching layer data for NFRC {nfrc_id}: {e}")
        return None


def extract_info(nfrc_id, _):
    """Return manufacturer, coating, actual_mm, nominal_mm, label segment"""
    if pd.isna(nfrc_id):
        return ("Unknown", "none", None, None, "")
    raw = layer_cache.get(int(nfrc_id))
    if not raw:
        return ("Unknown", "none", None, None, "")
    
    # Handle both JSON strings and dictionary formats
    if isinstance(raw, str):
        data = json.loads(raw)
    elif isinstance(raw, dict):
        # Use the metadata dict directly (from new cache format)
        data = raw
    else:
        return ("Unknown", "none", None, None, "")
    
    # manufacturer & coating
    mfr = data.get('manufacturer', 'Unknown')
    coat = data.get('coating_name', 'none')
    
    # actual thickness
    actu = data.get('thickness_mm')
    if actu is None:
        # Fallback for old format
        md = data.get('measured_data', {})
        if md.get('thickness') is not None:
            actu = round(float(md['thickness']), 1)
        else:
            actu = round(float(data.get('thickness', 0)) * 25.4, 1)
    
    # nominal = nearest whole mm
    nominal = int(round(actu)) if actu is not None else None
    # label segment
    seg = f"{mfr} {coat if coat!='none' else ''} {actu:.1f}mm".replace('  ', ' ').strip()
    return (mfr, coat, actu, nominal, seg)

def build_gaps(gas, ag_mm, igu_type):
    """Build gap layers based on gas and IGU type"""
    g = str(gas).upper()
    if '95A' in g:
        pct, gt = 0.95, pywincalc.PredefinedGasType.ARGON
    elif '90K' in g:
        pct, gt = 0.90, pywincalc.PredefinedGasType.KRYPTON
    else:
        pct, gt = 1.0, pywincalc.PredefinedGasType.AIR
    mix = pywincalc.create_gas([[pct, gt], [1-pct, pywincalc.PredefinedGasType.AIR]])
    count = 2 if igu_type.lower() == 'triple' else 3
    thickness_m = ag_mm / 1000.0
    return [pywincalc.Layers.gap(thickness=thickness_m, gas=mix) for _ in range(count)]

# --- Run with debug --- ---
total = len(df)
batch = prompt_batch_size(total)
print(f"Simulating {batch}/{total} configs...")
debug = {'tested':0,'no_layers':0,'sim_errors':0,'passed':0}
results = []
for idx, row in tqdm(df.iloc[:batch].iterrows(), total=batch, desc="Simulating"):
    debug['tested'] += 1
    layers = [get_layer(row[c]) for c in nfrc_cols if pd.notna(row[c])]
    if not layers:
        debug['no_layers'] += 1
        continue
    gaps = build_gaps(row['Gas Type'], row['Air Gap (mm)'], row['IGU Type'])
    try:
        sys = pywincalc.GlazingSystem(solid_layers=layers, gap_layers=gaps)
        for i in range(len(layers)):
            if row.get(f"Flip Glass {i+1}") in (True,'True',1):
                sys.flip_layer(i, True)
        u = sys.u()
        ubtu = u/5.678
        sys.environments(pywincalc.nfrc_shgc_environments())
        shgc = sys.shgc()
        tvis = sys.optical_method_results('PHOTOPIC').system_results.front.transmittance.direct_hemispherical
        temps_u = [t-273.15 for t in sys.layer_temperatures(pywincalc.TarcogSystemType.U)]
        temps_s = [t-273.15 for t in sys.layer_temperatures(pywincalc.TarcogSystemType.SHGC)]
        # Build IGU Name and metadata
        oa = row['OA (in)']
        segments = []
        out = row.to_dict()
        for i, col in enumerate(nfrc_cols, start=1):
            nominal = row.get(f"Glass {i} Nominal Thickness")
            mfr, coat, actu, nom, seg = extract_info(row[col], nominal)
            out[f"Glass {i} Manufacturer"]      = mfr
            out[f"Glass {i} Coating Name"]       = coat
            out[f"Glass {i} Actual Thickness"]   = actu
            out[f"Glass {i} Nominal Thickness"]  = nom
            if seg:
                segments.append(seg)
        igu_name = f"{oa:.3f}in – {' / '.join(segments)} – {row['Gas Type']}"
        out['IGU Name'] = igu_name
        # Add performance
        out.update({
            'U-Value (W/m2.K)':u,
            'U-Value (Btu/hr.ft2.F)':ubtu,
            'SHGC':shgc,
            'VT':tvis,
            'Interior Temp - Summer (C)':temps_s[-1],
            'Interior Temp - Winter (C)':temps_u[-1],
            'Exterior Temp - Summer (C)':temps_s[0],
            'Exterior Temp - Winter (C)':temps_u[0]
        })
        results.append(out)
        debug['passed'] += 1
    except Exception as e:
        debug['sim_errors'] += 1
        print(f"Error at row {idx}: {e}")
# Summary
print("--- Debug Summary ---")
print(debug)
if results:
    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved {len(results)} results to {OUTPUT_CSV}")
else:
    print("❌ No simulations succeeded.")
