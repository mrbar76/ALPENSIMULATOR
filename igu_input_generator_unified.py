#!/usr/bin/env python3
"""
Unified IGU Input Generator - Uses unified glass catalog with position checkboxes
Replaces separate glass catalogs with single multiselect-enabled catalog
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

UNIFIED_GLASS_PATH = "unified_glass_catalog.csv"
OA_SIZES_PATH = "input_oa_sizes.csv"
GAS_TYPES_PATH = "input_gas_types.csv"
OUTPUT_PATH = "igu_simulation_input_table.csv"
CACHE_FILE = "igsdb_layer_cache.pkl"

# Fast generation settings
MAX_CONFIGS_PER_TYPE = 2000
BATCH_SIZE = 500

print("🚀 Unified IGU Input Generator - Multiselect Position Version")
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

def should_flip_unified(position: str, glass_row, igu_type: str='triple') -> bool:
    """Use unified flip logic from catalog"""
    # Handle special case for quad_inner
    if position == "quad_inner":
        flip_column = "Flip_QuadInner"
    else:
        flip_column = f"Flip_{position.title()}"
    
    if flip_column in glass_row.index:
        return glass_row[flip_column] == True
    
    # Fallback to configurable rules
    meta = get_meta_with_cache(glass_row['NFRC_ID'], {})
    coating_side = meta.get("coating_side", "none")
    coating_name = meta.get("coating_name", "")
    return rules_config.should_flip(position.lower(), coating_side, coating_name, igu_type)

def center_allowed_unified(glass_row, meta: dict, igu_type: str) -> bool:
    """Check if glass can be used in center position using unified catalog"""
    # Check position eligibility first
    if not glass_row.get('Can_Center', False) == True:
        return False
    
    # Then apply traditional thickness/coating rules
    thickness_mm = meta.get("thickness_mm", 0)
    coating_side = meta.get("coating_side", "none")
    return rules_config.center_allowed(thickness_mm, coating_side, igu_type)

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

# === UNIFIED GENERATION ===

def generate_unified_configs():
    """Generate configurations using unified glass catalog"""
    
    print("📂 Loading input files...")
    gas_df = pd.read_csv(GAS_TYPES_PATH)
    oa_df = pd.read_csv(OA_SIZES_PATH)
    
    # Load unified glass catalog
    glass_df = pd.read_csv(UNIFIED_GLASS_PATH)
    
    # Filter glass by position capabilities
    outer_df = glass_df[glass_df['Can_Outer'] == True].copy()
    quad_inner_df = glass_df[glass_df['Can_QuadInner'] == True].copy()
    center_df = glass_df[glass_df['Can_Center'] == True].copy()
    inner_df = glass_df[glass_df['Can_Inner'] == True].copy()
    
    print(f"📊 Unified glass catalog summary:")
    print(f"   Total glass types: {len(glass_df)}")
    print(f"   Can be outer: {len(outer_df)}")
    print(f"   Can be quad-inner: {len(quad_inner_df)}")
    print(f"   Can be center: {len(center_df)}")
    print(f"   Can be inner: {len(inner_df)}")
    print(f"   Gas types: {len(gas_df)}")
    print(f"   OA sizes: {len(oa_df)}")
    
    # Load cache
    cache = load_or_create_cache()
    results = []
    
    # Pre-fetch all needed NFRC IDs
    all_nfrc_ids = set(glass_df['NFRC_ID'].dropna())
    
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
    print(f"\\n🔷 Generating Triples (max {MAX_CONFIGS_PER_TYPE:,})...")
    
    triple_count = 0
    for _, oa in oa_df.iterrows():
        if triple_count >= MAX_CONFIGS_PER_TYPE:
            break
            
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            if triple_count >= MAX_CONFIGS_PER_TYPE:
                break
                
            for _, o in outer_df.iterrows():
                if triple_count >= MAX_CONFIGS_PER_TYPE:
                    break
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    continue
                    
                for _, c in center_df.iterrows():
                    if triple_count >= MAX_CONFIGS_PER_TYPE:
                        break
                        
                    m_c = get_meta_with_cache(c.NFRC_ID, cache)
                    if not m_c or not center_allowed_unified(c, m_c, "Triple"):
                        continue
                        
                    for _, i in inner_df.iterrows():
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
                        if not (m_o["manufacturer"].lower() == m_i["manufacturer"].lower()):
                            continue
                            
                        # Calculate air gap
                        ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 2)
                        if ag < MIN_AIRGAP:
                            continue
                            
                        # Apply unified flipping rules
                        flips = [
                            should_flip_unified("Outer", o, "triple"),
                            should_flip_unified("Center", c, "triple"),
                            should_flip_unified("Inner", i, "triple")
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
    print(f"\\n🔶 Generating Quads (max {MAX_CONFIGS_PER_TYPE:,})...")
    print(f"   OA filter: {len(oa_df)} → {len(quad_candidates)} (min OA: {QUAD_OA_MIN_INCH}\\\")") 
    print(f"   Available quad-inner glass: {len(quad_inner_df)}")
    
    quad_count = 0
    total_attempts = 0
    for _, oa in quad_candidates.iterrows():
        if quad_count >= MAX_CONFIGS_PER_TYPE:
            break
            
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            if quad_count >= MAX_CONFIGS_PER_TYPE:
                break
                
            for _, o in outer_df.iterrows():
                if quad_count >= MAX_CONFIGS_PER_TYPE:
                    break
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    continue
                    
                for _, qi in quad_inner_df.iterrows():  # Use proper quad-inner glass
                    if quad_count >= MAX_CONFIGS_PER_TYPE:
                        break
                        
                    m_q = get_meta_with_cache(qi.NFRC_ID, cache)
                    if not m_q or m_q.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                        continue
                        
                    for _, c in center_df.iterrows():  # center
                        if quad_count >= MAX_CONFIGS_PER_TYPE:
                            break
                            
                        m_c = get_meta_with_cache(c.NFRC_ID, cache)
                        if not m_c or not center_allowed_unified(c, m_c, "Quad"):
                            continue
                            
                        for _, i in inner_df.iterrows():
                            if quad_count >= MAX_CONFIGS_PER_TYPE:
                                break
                                
                            total_attempts += 1
                            if total_attempts <= 5:  # Debug first few attempts
                                print(f"   Debug attempt {total_attempts}: trying OA={oa_mm}mm, outer={o.NFRC_ID}, qi={qi.NFRC_ID}, center={c.NFRC_ID}, inner={i.NFRC_ID}")
                                
                            m_i = get_meta_with_cache(i.NFRC_ID, cache)
                            if not m_i:
                                if total_attempts <= 5:
                                    print(f"   Debug: No metadata for inner {i.NFRC_ID}")
                                continue
                                
                            # Apply validation rules
                            if m_i.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                                if total_attempts <= 5:
                                    print(f"   Debug: Inner too thin {m_i.get('thickness_mm', 0)}mm < {MIN_EDGE_NOMINAL}mm")
                                continue
                            if abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                                if total_attempts <= 5:
                                    print(f"   Debug: Thickness mismatch outer={m_o['thickness_mm']}mm vs inner={m_i['thickness_mm']}mm, diff={abs(m_o['thickness_mm'] - m_i['thickness_mm']):.2f}mm > {TOL}mm")
                                continue
                            if not (m_o["manufacturer"].lower() == m_i["manufacturer"].lower()):
                                if total_attempts <= 5:
                                    print(f"   Debug: Manufacturer mismatch outer={m_o['manufacturer']} vs inner={m_i['manufacturer']}")
                                continue
                            
                            # Calculate air gap for 3 gaps
                            ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_q["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 3)
                            if ag < MIN_AIRGAP:
                                if total_attempts <= 5:
                                    print(f"   Debug: Gap too small {ag:.2f}mm < {MIN_AIRGAP}mm for OA={oa_mm}mm, thicknesses=[{m_o['thickness_mm']},{m_q['thickness_mm']},{m_c['thickness_mm']},{m_i['thickness_mm']}]")
                                continue
                                
                            # Apply unified flipping rules for quad
                            flips = [
                                should_flip_unified("Outer", o, "quad"),
                                should_flip_unified("quad_inner", qi, "quad"),
                                should_flip_unified("Center", c, "quad"),
                                should_flip_unified("Inner", i, "quad"),
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
                            
                            # Progress update and sample output
                            if quad_count % 100 == 0:
                                print(f"   Generated {quad_count:,} quads...")
                            elif quad_count <= 3:
                                print(f"   Sample quad {quad_count}: OA={oa_mm}mm, glasses=[{m_o['thickness_mm']},{m_q['thickness_mm']},{m_c['thickness_mm']},{m_i['thickness_mm']}]mm, gap={ag:.2f}mm")
    
    print(f"✅ Generated {quad_count:,} quad configurations")
    
    if quad_count == 0:
        print("🔍 Debugging why no quads were generated...")
        print(f"   Available OA sizes for quads: {len(quad_candidates)}")
        print(f"   Outer glass count: {len(outer_df)}")
        print(f"   Quad-inner glass count: {len(quad_inner_df)}")
        print(f"   Center glass count: {len(center_df)}")
        print(f"   Inner glass count: {len(inner_df)}")
        print(f"   QUAD_OA_MIN_INCH threshold: {QUAD_OA_MIN_INCH}\\\"")
        print(f"   MIN_AIRGAP requirement: {MIN_AIRGAP}mm")
        
        # Sample calculation
        if len(quad_candidates) > 0 and len(quad_inner_df) > 0:
            sample_oa = quad_candidates.iloc[0]["OA (mm)"]
            sample_outer = get_meta_with_cache(outer_df.iloc[0].NFRC_ID, cache)
            sample_qi = get_meta_with_cache(quad_inner_df.iloc[0].NFRC_ID, cache)
            sample_center = get_meta_with_cache(center_df.iloc[0].NFRC_ID, cache)
            sample_inner = get_meta_with_cache(inner_df.iloc[0].NFRC_ID, cache)
            
            if all([sample_outer, sample_qi, sample_center, sample_inner]):
                thicknesses = [sample_outer["thickness_mm"], sample_qi["thickness_mm"], sample_center["thickness_mm"], sample_inner["thickness_mm"]]
                sample_gap = calculate_air_gap(sample_oa, thicknesses, 3)
                print(f"   Sample calculation: OA={sample_oa}mm, thicknesses={thicknesses}, gap={sample_gap:.2f}mm")
    
    # === SAVE RESULTS ===
    print(f"\\n💾 Saving results...")
    df_out = pd.DataFrame(results)
    
    # Deduplicate
    dedupe_columns = ["IGU Type", "OA (in)", "Gas Type", "Glass 1 NFRC ID", "Glass 2 NFRC ID", "Glass 3 NFRC ID", "Glass 4 NFRC ID"]
    df_out = df_out.drop_duplicates(subset=dedupe_columns)
    
    df_out.to_csv(OUTPUT_PATH, index=False)
    
    print(f"✅ Wrote {len(df_out):,} unique configurations to {OUTPUT_PATH}")
    if len(df_out) > 0:
        print(f"   Triple: {len(df_out[df_out['IGU Type'] == 'Triple']):,}")
        print(f"   Quad: {len(df_out[df_out['IGU Type'] == 'Quad']):,}")
    else:
        print("   No configurations generated - check glass position settings")
    
    return df_out

if __name__ == "__main__":
    start_time = time.time()
    df_result = generate_unified_configs()
    elapsed = time.time() - start_time
    
    print(f"\\n🎉 Unified generation complete in {elapsed:.1f} seconds!")
    print(f"📁 Output file: {OUTPUT_PATH}")
    print(f"⚡ Generated {len(df_result):,} configurations using unified catalog")
    print(f"💡 Edit unified_glass_catalog.csv to modify position capabilities and flip logic")