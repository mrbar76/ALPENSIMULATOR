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

UNIFIED_GLASS_PATH = "unified_glass_catalog_enhanced.csv"
OA_SIZES_PATH = "input_oa_sizes.csv"
GAS_TYPES_PATH = "input_gas_types.csv"
OUTPUT_PATH = "igu_simulation_input_table.csv"
CACHE_FILE = "igsdb_layer_cache.pkl"

# Generation settings  
BATCH_SIZE = 500

print("🚀 Unified IGU Input Generator - Multiselect Position Version")
print("⚡ Generating all valid configurations like original generator")

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

# Function removed - using direct catalog Flip_* columns

# Function removed - using direct catalog Can_Center column

def calculate_air_gap(oa_mm: float, glass_thicknesses: list, gap_count: int) -> float:
    """Calculate ideal air gap based on OA and glass thicknesses."""
    total_glass_thickness = sum(glass_thicknesses)
    total_gap_space = oa_mm - total_glass_thickness
    return total_gap_space / gap_count

def choose_gap_set_fast(oa_target_mm: float, glass_thicknesses: list, gap_count: int) -> dict:
    """
    Fast gap selection using smart search instead of brute force.
    """
    # Get policy settings
    standard_gaps = rules_config.rules.get('oa_selection_policy', {}).get('standard_gap_sizes_mm', [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    near_equal_band = rules_config.rules.get('oa_selection_policy', {}).get('near_equal_band_mm', 0.10)
    min_gap = rules_config.get_min_airgap()
    
    total_glass_thickness = sum(glass_thicknesses)
    total_gap_space = oa_target_mm - total_glass_thickness
    ideal_gap = total_gap_space / gap_count
    
    valid_gaps = [g for g in standard_gaps if g >= min_gap]
    
    # Smart search: start with closest integer gaps to ideal
    base_gap = max(min_gap, min(max(valid_gaps), round(ideal_gap)))
    
    # Generate a focused set of candidates around the ideal
    candidates = []
    
    if gap_count == 2:  # Triple
        # Try combinations around the ideal gap
        for g1_offset in [-2, -1, 0, 1, 2]:
            for g2_offset in [-2, -1, 0, 1, 2]:
                g1 = max(min_gap, min(max(valid_gaps), base_gap + g1_offset))
                g2 = max(min_gap, min(max(valid_gaps), base_gap + g2_offset))
                if g1 in valid_gaps and g2 in valid_gaps:
                    gaps = [g1, g2]
                    oa_actual = total_glass_thickness + sum(gaps)
                    candidates.append({
                        'gaps_mm': gaps,
                        'oa_actual_mm': oa_actual,
                        'oa_actual_in': round(oa_actual / 25.4, 3),
                        'signed_error': oa_actual - oa_target_mm,
                        'oa_error': abs(oa_actual - oa_target_mm)
                    })
    
    elif gap_count == 3:  # Quad
        # Try combinations around the ideal gap  
        for g1_offset in [-1, 0, 1]:
            for g2_offset in [-1, 0, 1]:
                for g3_offset in [-1, 0, 1]:
                    g1 = max(min_gap, min(max(valid_gaps), base_gap + g1_offset))
                    g2 = max(min_gap, min(max(valid_gaps), base_gap + g2_offset))
                    g3 = max(min_gap, min(max(valid_gaps), base_gap + g3_offset))
                    if all(g in valid_gaps for g in [g1, g2, g3]):
                        gaps = [g1, g2, g3]
                        oa_actual = total_glass_thickness + sum(gaps)
                        candidates.append({
                            'gaps_mm': gaps,
                            'oa_actual_mm': oa_actual,
                            'oa_actual_in': round(oa_actual / 25.4, 3),
                            'signed_error': oa_actual - oa_target_mm,
                            'oa_error': abs(oa_actual - oa_target_mm)
                        })
    
    if not candidates:
        return None
    
    # Remove duplicates
    unique_candidates = []
    seen = set()
    for c in candidates:
        key = tuple(c['gaps_mm'])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)
    
    # Sort by absolute error
    unique_candidates.sort(key=lambda c: c['oa_error'])
    best = unique_candidates[0]
    
    # Find near-equal alternatives
    near_equals = [c for c in unique_candidates if c['oa_error'] - best['oa_error'] <= near_equal_band]
    
    # Tie-breaker: prefer undershoot
    undershoots = [c for c in near_equals if c['signed_error'] <= 0]
    
    if undershoots:
        undershoots.sort(key=lambda c: abs(c['signed_error']))
        selected = undershoots[0]
        selected['selection_reason'] = "Preferred undershoot"
    else:
        near_equals.sort(key=lambda c: abs(c['signed_error']))
        selected = near_equals[0]
        selected['selection_reason'] = "Minimum error"
    
    selected['oa_delta_mm'] = selected['signed_error']
    return selected

def edges_manufacturer_match(m_o: str, m_i: str) -> bool:
    """Check if outer and inner glass manufacturers are compatible."""
    if not m_o or not m_i:
        return False
    mo = m_o.strip().lower()
    mi = m_i.strip().lower()
    # Generic is universal - compatible with any manufacturer
    if "generic" in (mo, mi):
        return True
    # Allow if either is a substring of the other (handles variations like "Cardinal Glass Co.")
    return mo in mi or mi in mo

def get_emissivity_from_catalog_or_meta(glass_row, meta: dict) -> float:
    """Get emissivity value from catalog first, fallback to IGSDB metadata."""
    # Try catalog emissivity column first (more reliable if available)
    if 'Emissivity' in glass_row.index and pd.notna(glass_row['Emissivity']):
        return float(glass_row['Emissivity'])
    
    # Fallback to IGSDB metadata if catalog doesn't have it
    if meta and 'emissivity' in meta:
        return float(meta['emissivity'])
    
    # Default to clear glass emissivity if no data available
    return 0.84

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
    
    # Pre-compute emissivity values for all glass to avoid repeated lookups
    print("🔧 Pre-computing emissivity values...")
    for df in [outer_df, quad_inner_df, center_df, inner_df]:
        if len(df) > 0:
            df['_emissivity'] = df.apply(lambda row: get_emissivity_from_catalog_or_meta(row, get_meta_with_cache(row.NFRC_ID, cache)), axis=1)
    
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
    
    # === TRIPLES ===
    triple_iters = len(oa_df)*len(gas_df)*len(outer_df)*len(center_df)*len(inner_df)
    print(f"\\n🔷 Generating Triples ({triple_iters:,} combinations)...")
    
    triple_count = 0
    pbar = tqdm(total=triple_iters, unit="cfg")
    for _, oa in oa_df.iterrows():
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            for _, o in outer_df.iterrows():
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o:
                    continue
                    
                for _, c in center_df.iterrows():
                    pbar.update(1)
                    m_c = get_meta_with_cache(c.NFRC_ID, cache)
                    if not m_c or not c.get('Can_Center', False):
                        continue
                        
                    for _, i in inner_df.iterrows():
                            
                        m_i = get_meta_with_cache(i.NFRC_ID, cache)
                        if not m_i:
                            continue
                            
                        # Apply validation rules
                        # Manufacturer compatibility with Generic flexibility
                        if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                            continue
                        
                        # Low-E ordering: outer emissivity >= inner emissivity (prevent thermal imbalance)
                        if o['_emissivity'] < i['_emissivity']:
                            continue
                            
                        # Choose optimal gap set for target OA
                        gap_result = choose_gap_set_fast(oa_mm, [m_o["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 2)
                        if not gap_result or min(gap_result['gaps_mm']) < MIN_AIRGAP:
                            continue
                            
                        # Apply catalog-only flipping rules
                        flips = [
                            o.get('Flip_Outer', False),
                            c.get('Flip_Center', False),
                            i.get('Flip_Inner', False)
                        ]
                        
                        results.append({
                            "IGU Type": "Triple",
                            "OA Target (in)": oa_in,
                            "OA Target (mm)": oa_mm,
                            "OA Actual (in)": gap_result['oa_actual_in'],
                            "OA Actual (mm)": gap_result['oa_actual_mm'],
                            "OA Delta (mm)": gap_result['oa_delta_mm'],
                            "Gas Type": gas["Gas Type"],
                            "Glass 1 NFRC ID": o.NFRC_ID,
                            "Glass 2 NFRC ID": c.NFRC_ID,
                            "Glass 3 NFRC ID": i.NFRC_ID,
                            "Glass 4 NFRC ID": "",
                            "Flip Glass 1": flips[0],
                            "Flip Glass 2": flips[1],
                            "Flip Glass 3": flips[2],
                            "Gap 1 (mm)": gap_result['gaps_mm'][0],
                            "Gap 2 (mm)": gap_result['gaps_mm'][1],
                            "Selection Reason": gap_result['selection_reason']
                        })
                        
                        triple_count += 1
    
    pbar.close()
    print(f"✅ Generated {triple_count:,} triple configurations")
    
    # === QUADS ===
    quad_candidates = oa_df[oa_df["OA (in)"] > QUAD_OA_MIN_INCH]
    quad_iters = len(quad_candidates)*len(gas_df)*len(outer_df)*len(quad_inner_df)*len(center_df)*len(inner_df)
    print(f"\\n🔶 Generating Quads ({quad_iters:,} combinations)...")
    print(f"   OA filter: {len(oa_df)} → {len(quad_candidates)} (min OA: {QUAD_OA_MIN_INCH}\\\")") 
    print(f"   Available quad-inner glass: {len(quad_inner_df)}")
    
    quad_count = 0
    pbar = tqdm(total=quad_iters, unit="cfg")
    for _, oa in quad_candidates.iterrows():
            
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            for _, o in outer_df.iterrows():
                    
                m_o = get_meta_with_cache(o.NFRC_ID, cache)
                if not m_o:
                    continue
                    
                for _, qi in quad_inner_df.iterrows():  # Use proper quad-inner glass
                        
                    m_q = get_meta_with_cache(qi.NFRC_ID, cache)
                    if not m_q:
                        continue
                        
                    for _, c in center_df.iterrows():  # center
                        pbar.update(1)
                            
                        m_c = get_meta_with_cache(c.NFRC_ID, cache)
                        if not m_c or not c.get('Can_Center', False):
                            continue
                            
                        for _, i in inner_df.iterrows():
                                
                            m_i = get_meta_with_cache(i.NFRC_ID, cache)
                            if not m_i:
                                continue
                                
                            # Apply validation rules
                            # Manufacturer compatibility with Generic flexibility
                            if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                                continue
                            
                            # Low-E ordering: outer emissivity >= inner emissivity (prevent thermal imbalance)
                            if o['_emissivity'] < i['_emissivity']:
                                continue
                            
                            # Choose optimal gap set for target OA 
                            gap_result = choose_gap_set_fast(oa_mm, [m_o["thickness_mm"], m_q["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 3)
                            if not gap_result or min(gap_result['gaps_mm']) < MIN_AIRGAP:
                                continue
                                
                            # Apply catalog-only flipping rules for quad
                            flips = [
                                o.get('Flip_Outer', False),
                                qi.get('Flip_QuadInner', False),
                                c.get('Flip_Center', False),
                                i.get('Flip_Inner', False),
                            ]
                            
                            results.append({
                                "IGU Type": "Quad",
                                "OA Target (in)": oa_in,
                                "OA Target (mm)": oa_mm,
                                "OA Actual (in)": gap_result['oa_actual_in'],
                                "OA Actual (mm)": gap_result['oa_actual_mm'],
                                "OA Delta (mm)": gap_result['oa_delta_mm'],
                                "Gas Type": gas["Gas Type"],
                                "Glass 1 NFRC ID": o.NFRC_ID,
                                "Glass 2 NFRC ID": qi.NFRC_ID,
                                "Glass 3 NFRC ID": c.NFRC_ID,
                                "Glass 4 NFRC ID": i.NFRC_ID,
                                "Flip Glass 1": flips[0],
                                "Flip Glass 2": flips[1],
                                "Flip Glass 3": flips[2],
                                "Flip Glass 4": flips[3],
                                "Gap 1 (mm)": gap_result['gaps_mm'][0],
                                "Gap 2 (mm)": gap_result['gaps_mm'][1],
                                "Gap 3 (mm)": gap_result['gaps_mm'][2],
                                "Selection Reason": gap_result['selection_reason']
                            })
                            
                            quad_count += 1
                            
    
    pbar.close()
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
    dedupe_columns = ["IGU Type", "OA Target (in)", "Gas Type", "Glass 1 NFRC ID", "Glass 2 NFRC ID", "Glass 3 NFRC ID", "Glass 4 NFRC ID"]
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