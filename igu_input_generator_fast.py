#!/usr/bin/env python3
"""
Fast IGU Input Generator - Optimized for Streamlit workflow
Processes configurations in batches with progress reporting
"""

import pandas as pd
import requests
import time
import pickle
import os
from tqdm import tqdm
from datetime import datetime

# Import configurable rules system
from configurable_rules import AlpenRulesConfig

# === CONFIGURATION ===
API_KEY = "0e94db9c8cda032d3eaa083e21984350c17633ca"
IGSDB_HEADERS = {
    "accept": "application/json", 
    "Authorization": f"Token {API_KEY}"
}

GLASS_CENTER_PATH      = "input_glass_catalog_center.csv"
GLASS_INNER_OUTER_PATH = "input_glass_catalog_inner_outer.csv"
OA_SIZES_PATH          = "input_oa_sizes.csv"
GAS_TYPES_PATH         = "input_gas_types.csv"
OUTPUT_PATH            = "igu_simulation_input_table.csv"
CACHE_FILE             = "igsdb_layer_cache.pkl"

# Fast generation settings
MAX_CONFIGS_PER_TYPE = 2000  # Limit per IGU type to speed up
BATCH_SIZE = 500  # Process in smaller batches

print("🚀 Fast IGU Input Generator - Optimized Version")
print(f"⚡ Limited to {MAX_CONFIGS_PER_TYPE:,} configs per type for speed")

# Initialize configurable rules system
print("🔧 Loading configurable rules...")
rules_config = AlpenRulesConfig()

# Load constants from config
TOL = rules_config.get_tolerance()
MIN_EDGE_NOMINAL = rules_config.get_min_edge_nominal()
MIN_AIRGAP = rules_config.get_min_airgap()
QUAD_OA_MIN_INCH = rules_config.get_quad_oa_min_inch()
CENTER_MAX_THICKNESS = rules_config.get_center_max_thickness()

print(f"📊 Loaded configurable constants: TOL={TOL}mm, MIN_EDGE={MIN_EDGE_NOMINAL}mm")

# === HELPERS ===

def get_product_id_from_nfrc(nfrc_id: int) -> int:
    url = f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nfrc_id}"
    resp = requests.get(url, headers=IGSDB_HEADERS, timeout=5)
    if not resp.ok:
        return None
    data = resp.json()
    return data[0].get("product_id") if data else None

def fetch_igsdb_metadata(prod_id: int) -> dict:
    if not prod_id:
        return {}
    resp = requests.get(f"https://igsdb.lbl.gov/api/v1/products/{prod_id}/", headers=IGSDB_HEADERS, timeout=5)
    if not resp.ok:
        return {}
    d = resp.json()
    md = d.get("measured_data", {})
    thickness = md.get("thickness") if md.get("thickness") is not None else d.get("thickness", 0)*25.4
    manufacturer = d.get("manufacturer_name") or d.get("manufacturer", {}).get("name","Unknown")
    cs = (d.get("coated_side") or "none").lower()
    if cs == "none":
        for layer in d.get("layers", []):
            if layer.get("type") == "coating":
                cs = layer.get("location","none").lower()
                break
    cn = d.get("coating_name") or "none"
    return {
        "thickness_mm": round(float(thickness),2),
        "manufacturer": manufacturer,
        "coating_side": cs,
        "coating_name": cn
    }

def load_or_create_cache():
    """Load existing cache or create new one"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
            print(f"💾 Loaded cache with {len(cache)} entries")
            return cache
        except:
            print("⚠️ Cache corrupted, starting fresh")
    return {}

def get_meta_with_cache(nfrc_id: int, cache: dict) -> dict:
    """Get metadata with caching and error handling"""
    if nfrc_id not in cache:
        try:
            pid = get_product_id_from_nfrc(nfrc_id)
            if pid:
                meta = fetch_igsdb_metadata(pid)
                cache[nfrc_id] = meta
                time.sleep(0.05)  # Rate limiting
            else:
                cache[nfrc_id] = {}
        except Exception as e:
            print(f"⚠️ Error fetching NFRC {nfrc_id}: {e}")
            cache[nfrc_id] = {}
    
    # Handle case where cache has bytes (from old cache format)
    result = cache[nfrc_id]
    if isinstance(result, bytes):
        print(f"⚠️ Converting old cache format for NFRC {nfrc_id}")
        try:
            pid = get_product_id_from_nfrc(nfrc_id)
            if pid:
                meta = fetch_igsdb_metadata(pid)
                cache[nfrc_id] = meta
                return meta
        except:
            cache[nfrc_id] = {}
            return {}
    
    return result

def should_flip(position: str, coating_side: str, coating_name: str='', igu_type: str='triple') -> bool:
    """Use configurable flipping rules"""
    return rules_config.should_flip(position, coating_side, coating_name, igu_type)

def center_allowed(meta: dict, igu_type: str) -> bool:
    """Check if glass can be used in center position"""
    thickness_mm = meta.get("thickness_mm", 0)
    coating_side = meta.get("coating_side", "none")
    return rules_config.center_allowed(thickness_mm, coating_side, igu_type)

def edges_manufacturer_match(mfr1: str, mfr2: str) -> bool:
    """Check manufacturer matching rule"""
    if not rules_config.edges_manufacturer_match_required():
        return True
    return mfr1.lower() == mfr2.lower()

def calculate_air_gap(oa_mm: float, glass_thicknesses: list, gap_count: int) -> float:
    """Calculate air gap based on OA and glass thicknesses."""
    total_glass_thickness = sum(glass_thicknesses)
    total_gap_space = oa_mm - total_glass_thickness
    return total_gap_space / gap_count

def parse_lowe_value(name: str) -> int:
    for tok in name.replace('-', ' ').split():
        if tok.isdigit(): return int(tok)
        if tok.startswith('i') and tok[1:].isdigit(): return int(tok[1:])
    return 0

# === FAST GENERATION ===

def generate_fast_configs():
    """Generate configurations quickly with limits"""
    
    print("📂 Loading input files...")
    gas_df = pd.read_csv(GAS_TYPES_PATH)
    oa_df = pd.read_csv(OA_SIZES_PATH)
    glass_io_df = pd.read_csv(GLASS_INNER_OUTER_PATH)
    center_df = pd.read_csv(GLASS_CENTER_PATH)
    
    # Filter for position-specific glass
    outer_df = glass_io_df[glass_io_df["Position"] == "Outer"]
    inner_df = glass_io_df[glass_io_df["Position"] == "Inner"]
    
    print(f"📊 Input summary:")
    print(f"   Gas types: {len(gas_df)}")
    print(f"   OA sizes: {len(oa_df)}")
    print(f"   Outer glass: {len(outer_df)}")
    print(f"   Inner glass: {len(inner_df)}")
    print(f"   Center glass: {len(center_df)}")
    
    # Load cache
    cache = load_or_create_cache()
    results = []
    
    # Pre-fetch all needed NFRC IDs
    all_nfrc_ids = set()
    all_nfrc_ids.update(outer_df['NFRC_ID'].dropna())
    all_nfrc_ids.update(inner_df['NFRC_ID'].dropna()) 
    all_nfrc_ids.update(center_df['NFRC_ID'].dropna())
    
    missing_ids = [nid for nid in all_nfrc_ids if nid not in cache]
    if missing_ids:
        print(f"📡 Pre-fetching {len(missing_ids)} missing NFRC IDs...")
        for nid in tqdm(missing_ids, desc="Fetching NFRC data"):
            get_meta_with_cache(nid, cache)
        
        # Save updated cache
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
        print("💾 Cache updated")
    
    # === TRIPLES (Limited) ===
    print(f"\n🔷 Generating Triples (max {MAX_CONFIGS_PER_TYPE:,})...")
    
    triple_count = 0
    for _, oa in oa_df.iterrows():
        if triple_count >= MAX_CONFIGS_PER_TYPE:
            break
            
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            if triple_count >= MAX_CONFIGS_PER_TYPE:
                break
                
            for o in outer_df.itertuples():
                if triple_count >= MAX_CONFIGS_PER_TYPE:
                    break
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    continue
                    
                for c in center_df.itertuples():
                    if triple_count >= MAX_CONFIGS_PER_TYPE:
                        break
                        
                    m_c = get_meta_with_cache(c.NFRC_ID, cache)
                    if not m_c or not center_allowed(m_c, "Triple"):
                        continue
                        
                    for i in inner_df.itertuples():
                        if triple_count >= MAX_CONFIGS_PER_TYPE:
                            break
                            
                        m_i = get_meta_with_cache(i.NFRC_ID, cache)
                        if not m_i:
                            continue
                            
                        # Apply validation rules
                        if m_i.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                            continue
                        if abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                            continue
                        if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                            continue
                            
                        # Calculate air gap
                        ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 2)
                        if ag < MIN_AIRGAP:
                            continue
                            
                        # Apply flipping rules
                        flips = [
                            should_flip("outer", m_o["coating_side"], m_o["coating_name"], "triple"),
                            should_flip("center", m_c["coating_side"], m_c["coating_name"], "triple"),
                            should_flip("inner", m_i["coating_side"], m_i["coating_name"], "triple")
                        ]
                        
                        results.append({
                            "IGU Type": "Triple",
                            "OA (in)": oa_in,
                            "OA (mm)": oa_mm,
                            "Gas Type": gas["Gas Type"],
                            "Glass 1 NFRC ID": o.NFRC_ID,
                            "Glass 2 NFRC ID": c.NFRC_ID,
                            "Glass 3 NFRC ID": i.NFRC_ID,
                            "Glass 4 NFRC ID": "",
                            "Flip Glass 1": flips[0],
                            "Flip Glass 2": flips[1],
                            "Flip Glass 3": flips[2],
                            "Air Gap (mm)": round(ag, 2)
                        })
                        
                        triple_count += 1
                        
                        # Progress update
                        if triple_count % 100 == 0:
                            print(f"   Generated {triple_count:,} triples...")
    
    print(f"✅ Generated {triple_count:,} triple configurations")
    
    # === QUADS (Limited) ===
    quad_candidates = oa_df[oa_df["OA (in)"] > QUAD_OA_MIN_INCH]
    print(f"\n🔶 Generating Quads (max {MAX_CONFIGS_PER_TYPE:,})...")
    print(f"   OA filter: {len(oa_df)} → {len(quad_candidates)} (min OA: {QUAD_OA_MIN_INCH}\")")
    
    quad_count = 0
    for _, oa in quad_candidates.iterrows():
        if quad_count >= MAX_CONFIGS_PER_TYPE:
            break
            
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            if quad_count >= MAX_CONFIGS_PER_TYPE:
                break
                
            for o in outer_df.itertuples():
                if quad_count >= MAX_CONFIGS_PER_TYPE:
                    break
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    continue
                    
                for qi in inner_df.itertuples():  # quad-inner (use inner/outer glass, not center!)
                    if quad_count >= MAX_CONFIGS_PER_TYPE:
                        break
                        
                    m_q = get_meta_with_cache(qi.NFRC_ID, cache)
                    if not m_q or m_q.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                        continue
                        
                    for c in center_df.itertuples():  # center
                        if quad_count >= MAX_CONFIGS_PER_TYPE:
                            break
                            
                        m_c = get_meta_with_cache(c.NFRC_ID, cache)
                        if not m_c or not center_allowed(m_c, "Quad"):
                            continue
                            
                        for i in inner_df.itertuples():
                            if quad_count >= MAX_CONFIGS_PER_TYPE:
                                break
                                
                            m_i = get_meta_with_cache(i.NFRC_ID, cache)
                            if not m_i:
                                continue
                                
                            # Apply validation rules
                            if m_i.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                                continue
                            if abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                                continue
                            if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                                continue
                            
                            # Calculate air gap for 3 gaps
                            ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_q["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 3)
                            if ag < MIN_AIRGAP:
                                continue
                                
                            # Apply flipping rules for quad
                            flips = [
                                should_flip("outer", m_o["coating_side"], m_o["coating_name"], "quad"),
                                should_flip("quad_inner", m_q["coating_side"], m_q["coating_name"], "quad"),
                                should_flip("center", m_c["coating_side"], m_c["coating_name"], "quad"),
                                should_flip("inner", m_i["coating_side"], m_i["coating_name"], "quad"),
                            ]
                            
                            results.append({
                                "IGU Type": "Quad",
                                "OA (in)": oa_in,
                                "OA (mm)": oa_mm,
                                "Gas Type": gas["Gas Type"],
                                "Glass 1 NFRC ID": o.NFRC_ID,
                                "Glass 2 NFRC ID": qi.NFRC_ID,
                                "Glass 3 NFRC ID": c.NFRC_ID,
                                "Glass 4 NFRC ID": i.NFRC_ID,
                                "Flip Glass 1": flips[0],
                                "Flip Glass 2": flips[1],
                                "Flip Glass 3": flips[2],
                                "Flip Glass 4": flips[3],
                                "Air Gap (mm)": round(ag, 2),
                            })
                            
                            quad_count += 1
                            
                            # Progress update
                            if quad_count % 100 == 0:
                                print(f"   Generated {quad_count:,} quads...")
    
    print(f"✅ Generated {quad_count:,} quad configurations")
    
    if quad_count == 0:
        print("🔍 Debugging why no quads were generated...")
        print(f"   Available OA sizes for quads: {len(quad_candidates)}")
        print(f"   Outer glass count: {len(outer_df)}")
        print(f"   Center glass count: {len(center_df)}")
        print(f"   Inner glass count: {len(inner_df)}")
        print(f"   QUAD_OA_MIN_INCH threshold: {QUAD_OA_MIN_INCH}\"")
        print("   Possible issues:")
        print("   - Air gaps too small (need ≥3mm after ÷3)")
        print("   - Glass thickness validation failures")
        print("   - Manufacturer matching requirements")
        print("   💡 Try lowering Quad OA minimum in Step 2")
    
    # === SAVE RESULTS ===
    print(f"\n💾 Saving results...")
    df_out = pd.DataFrame(results)
    
    # Deduplicate
    dedupe_columns = ["IGU Type", "OA (in)", "Gas Type", "Glass 1 NFRC ID", "Glass 2 NFRC ID", "Glass 3 NFRC ID", "Glass 4 NFRC ID"]
    df_out = df_out.drop_duplicates(subset=dedupe_columns)
    
    df_out.to_csv(OUTPUT_PATH, index=False)
    
    print(f"✅ Wrote {len(df_out):,} unique configurations to {OUTPUT_PATH}")
    print(f"   Triple: {len(df_out[df_out['IGU Type'] == 'Triple']):,}")
    print(f"   Quad: {len(df_out[df_out['IGU Type'] == 'Quad']):,}")
    
    return df_out

if __name__ == "__main__":
    start_time = time.time()
    df_result = generate_fast_configs()
    elapsed = time.time() - start_time
    
    print(f"\n🎉 Fast generation complete in {elapsed:.1f} seconds!")
    print(f"📁 Output file: {OUTPUT_PATH}")
    print(f"⚡ Generated {len(df_result):,} configurations for quick testing")
    print(f"💡 For full generation, use the original igu_input_generator_configurable.py")