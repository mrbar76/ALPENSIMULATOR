#!/usr/bin/env python3
"""
Alpen IGU Input Generator - Configurable Version

Updated version of igu_input_generator.py that uses configurable rules
instead of hardcoded constants. All rules can now be edited through
the Live Rules Editor without changing code.

Changes from original:
- Replaced hardcoded constants with configurable_rules.py
- Updated should_flip() to use configurable coating placement rules  
- Fixed i89 coating placement: Surface 6 (triple), Surface 8 (quad)
- All validation rules now configurable via YAML
"""

import pandas as pd
import requests
import time
from tqdm import tqdm

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

# Initialize configurable rules system
print("🔧 Loading configurable rules...")
rules_config = AlpenRulesConfig()

# REPLACED HARDCODED CONSTANTS WITH CONFIGURABLE RULES:
# TOL               = 0.3   # mm tolerance for measured thickness
# MIN_EDGE_NOMINAL  = 3.0   # mm for outer/inner nominal  
# MIN_AIRGAP        = 3.0   # mm minimum air gap
# QUAD_OA_MIN_INCH  = 0.75  # in, skip quads at or below this OA

# Now these values come from config/alpen_igu_rules.yaml and can be edited!
TOL = rules_config.get_tolerance()
MIN_EDGE_NOMINAL = rules_config.get_min_edge_nominal()
MIN_AIRGAP = rules_config.get_min_airgap()
QUAD_OA_MIN_INCH = rules_config.get_quad_oa_min_inch()
CENTER_MAX_THICKNESS = rules_config.get_center_max_thickness()

print(f"📊 Loaded configurable constants:")
print(f"   TOL: {TOL}mm")
print(f"   MIN_EDGE_NOMINAL: {MIN_EDGE_NOMINAL}mm")
print(f"   MIN_AIRGAP: {MIN_AIRGAP}mm") 
print(f"   QUAD_OA_MIN_INCH: {QUAD_OA_MIN_INCH}\"")
print(f"   CENTER_MAX_THICKNESS: {CENTER_MAX_THICKNESS}mm")

# === HELPERS ===

def parse_nominal_thickness(name: str) -> float:
    for tok in name.replace('-', ' ').split():
        if tok.lower().endswith('mm'):
            try: return float(tok[:-2])
            except ValueError: pass
    return 0.0

def get_product_id_from_nfrc(nfrc_id: int) -> int:
    url = f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nfrc_id}"
    resp = requests.get(url, headers=IGSDB_HEADERS)
    if not resp.ok:
        print(f"❌ Failed to fetch product ID for NFRC ID {nfrc_id}")
        return None
    data = resp.json()
    if not data:
        print(f"⚠️ No products found for NFRC ID {nfrc_id}")
        return None
    product_id = data[0].get("product_id")
    print(f"✅ NFRC ID {nfrc_id} maps to Product ID {product_id}")
    return product_id

def fetch_igsdb_metadata(prod_id: int) -> dict:
    if not prod_id:
        return {}
    resp = requests.get(f"https://igsdb.lbl.gov/api/v1/products/{prod_id}/", headers=IGSDB_HEADERS)
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

def get_meta(nfrc_id: int, cache: dict) -> dict:
    if nfrc_id not in cache:
        pid = get_product_id_from_nfrc(nfrc_id)
        if not pid:
            print(f"⚠️  NFRC ID {nfrc_id} not found in IGSDB.")
            cache[nfrc_id] = {}
            return cache[nfrc_id]
        meta = fetch_igsdb_metadata(pid)
        if not meta or meta.get("manufacturer", "").lower() == "unknown":
            print(f"⚠️  Metadata missing or incomplete for NFRC ID {nfrc_id} (Product ID: {pid})")
        cache[nfrc_id] = meta
        time.sleep(0.05)
    return cache[nfrc_id]

def parse_lowe_value(name: str) -> int:
    for tok in name.replace('-', ' ').split():
        if tok.isdigit(): return int(tok)
        if tok.startswith('i') and tok[1:].isdigit(): return int(tok[1:])
    return 0

# UPDATED: should_flip now uses configurable rules!
def should_flip(position: str, coating_side: str, coating_name: str='', igu_type: str='triple') -> bool:
    """
    UPDATED: Configurable version of should_flip function.
    
    Now uses rules from config/alpen_igu_rules.yaml instead of hardcoded logic.
    
    CORRECTED COATING SURFACE REQUIREMENTS:
    - Triples: Standard low-e on surfaces 2 and 5, center coatings on surface 4
    - Quads: Standard low-e on surfaces 2 and 7, center coatings on surface 6  
    - i89 coating: Surface 6 (triple) or Surface 8 (quad) - FIXED!
    - NxLite and center coatings: Surface 4 (triple) or Surface 6 (quad)
    """
    return rules_config.should_flip(position, coating_side, coating_name, igu_type)

def validate_coating_conflicts(configs: list) -> bool:
    """
    Validate that no two low-e coatings are on the same glass lite.
    Returns True if configuration is valid, False if conflicts exist.
    """
    coatings = []
    for config in configs:
        if config.get("coating_side") != "none":
            coatings.append(config.get("glass_number", 0))
    
    # Check for duplicates
    return len(coatings) == len(set(coatings))

# UPDATED: center_allowed now uses configurable rules!
def center_allowed(meta: dict, igu_type: str) -> bool:
    """
    UPDATED: Configurable version of center_allowed function.
    
    Now uses CENTER_MAX_THICKNESS from config instead of hardcoded 1.1mm.
    """
    thickness_mm = meta.get("thickness_mm", 0)
    coating_side = meta.get("coating_side", "none")
    
    return rules_config.center_allowed(thickness_mm, coating_side, igu_type)

# UPDATED: quad_center_rule now uses configurable rules!  
def quad_center_rule(meta: dict) -> bool:
    """
    UPDATED: Configurable version of quad_center_rule function.
    """
    thickness_mm = meta.get("thickness_mm", 0)
    return rules_config.quad_center_rule(thickness_mm)

# UPDATED: edges_manufacturer_match now uses configurable rules!
def edges_manufacturer_match(mfr1: str, mfr2: str) -> bool:
    """
    UPDATED: Configurable manufacturer matching rule.
    """
    if not rules_config.edges_manufacturer_match_required():
        return True  # Rule disabled, allow any combination
    
    return mfr1.lower() == mfr2.lower()

def calculate_air_gap(oa_mm: float, glass_thicknesses: list, gap_count: int) -> float:
    """Calculate air gap based on OA and glass thicknesses."""
    total_glass_thickness = sum(glass_thicknesses)
    total_gap_space = oa_mm - total_glass_thickness
    return total_gap_space / gap_count

# === MAIN GENERATION LOGIC ===

def generate_igu_configurations():
    """Generate IGU configurations using configurable rules."""
    
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
    
    cache = {}
    results = []
    
    # === TRIPLES ===
    triple_iters = len(oa_df) * len(gas_df) * len(outer_df) * len(center_df) * len(inner_df)
    print(f"\n🔷 Generating Triples ({triple_iters:,} combinations)...")
    print(f"   Using configurable rules: TOL={TOL}mm, MIN_EDGE_NOMINAL={MIN_EDGE_NOMINAL}mm")
    
    pbar = tqdm(total=triple_iters, unit="cfg", desc="Triple configs")
    
    for _, oa in oa_df.iterrows():
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            for o in outer_df.itertuples():
                m_o = get_meta(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    pbar.update(len(center_df) * len(inner_df))
                    continue
                    
                for c in center_df.itertuples():
                    m_c = get_meta(c.NFRC_ID, cache)
                    if not m_c or not center_allowed(m_c, "Triple"):
                        pbar.update(len(inner_df))
                        continue
                        
                    for i in inner_df.itertuples():
                        pbar.update(1)
                        m_i = get_meta(i.NFRC_ID, cache)
                        if not m_i:
                            continue
                            
                        # Apply configurable validation rules
                        if m_i.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                            continue
                        if abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                            continue
                        if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                            continue
                            
                        # Low-E ordering rule (if enabled)
                        if rules_config.lowe_ordering_required():
                            if parse_lowe_value(o.Short_Name) < parse_lowe_value(i.Short_Name):
                                continue
                        
                        # Calculate air gap with configurable minimum
                        ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 2)
                        if ag < MIN_AIRGAP:
                            continue
                            
                        # Apply configurable flipping rules
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
    
    pbar.close()
    print(f"✅ Generated {len([r for r in results if r['IGU Type'] == 'Triple'])} triple configurations")
    
    # === QUADS ===
    # Apply configurable QUAD_OA_MIN_INCH rule
    quad_candidates = oa_df[oa_df["OA (in)"] > QUAD_OA_MIN_INCH]
    print(f"\n🔶 Quad OA filter: {len(oa_df)} → {len(quad_candidates)} (min OA: {QUAD_OA_MIN_INCH}\")")
    
    quad_iters = (
        len(quad_candidates) * len(gas_df) * len(outer_df) *
        len(center_df) * len(center_df) * len(inner_df)
    )
    print(f"🔶 Generating Quads ({quad_iters:,} combinations)...")
    
    pbar = tqdm(total=quad_iters, unit="cfg", desc="Quad configs")
    
    for _, oa in quad_candidates.iterrows():
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            for o in outer_df.itertuples():
                m_o = get_meta(o.NFRC_ID, cache)
                if not m_o or m_o.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                    pbar.update(len(center_df) * len(center_df) * len(inner_df))
                    continue
                    
                for qi in center_df.itertuples():  # quad-inner candidate
                    m_q = get_meta(qi.NFRC_ID, cache)
                    if not m_q or not quad_center_rule(m_q):
                        pbar.update(len(center_df) * len(inner_df))
                        continue
                        
                    for c in center_df.itertuples():  # center glass
                        m_c = get_meta(c.NFRC_ID, cache)
                        if not m_c or not center_allowed(m_c, "Quad"):
                            pbar.update(len(inner_df))
                            continue
                            
                        for i in inner_df.itertuples():
                            pbar.update(1)
                            m_i = get_meta(i.NFRC_ID, cache)
                            if not m_i:
                                continue
                                
                            # Apply same validation rules as triples
                            if m_i.get("thickness_mm", 0) < MIN_EDGE_NOMINAL:
                                continue
                            if abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                                continue
                            if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]):
                                continue
                                
                            # Low-E ordering rule (if enabled)
                            if rules_config.lowe_ordering_required():
                                if parse_lowe_value(o.Short_Name) < parse_lowe_value(i.Short_Name):
                                    continue
                            
                            # Calculate air gap for 3 gaps
                            ag = calculate_air_gap(oa_mm, [m_o["thickness_mm"], m_q["thickness_mm"], m_c["thickness_mm"], m_i["thickness_mm"]], 3)
                            if ag < MIN_AIRGAP:
                                continue
                                
                            # Apply configurable flipping rules for quad
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
    
    pbar.close()
    print(f"✅ Generated {len([r for r in results if r['IGU Type'] == 'Quad'])} quad configurations")
    
    # === DEDUPE & SAVE ===
    print(f"\n💾 Saving results...")
    df_out = pd.DataFrame(results)
    
    # Apply configurable deduplication  
    dedupe_columns = ["IGU Type", "OA (in)", "Gas Type", "Glass 1 NFRC ID", "Glass 2 NFRC ID", "Glass 3 NFRC ID", "Glass 4 NFRC ID"]
    df_out = df_out.drop_duplicates(subset=dedupe_columns)
    
    df_out.to_csv(OUTPUT_PATH, index=False)
    
    print(f"✅ Wrote {len(df_out):,} unique configurations to {OUTPUT_PATH}")
    print(f"   Triple: {len(df_out[df_out['IGU Type'] == 'Triple']):,}")
    print(f"   Quad: {len(df_out[df_out['IGU Type'] == 'Quad']):,}")
    
    # Show rule summary
    print(f"\n📊 Applied configurable rules:")
    print(f"   i89 coating surfaces: Triple={rules_config.get_i89_surface('triple')}, Quad={rules_config.get_i89_surface('quad')}")
    print(f"   Standard low-E surfaces: Triple={rules_config.get_standard_lowe_surfaces('triple')}, Quad={rules_config.get_standard_lowe_surfaces('quad')}")
    print(f"   Edge manufacturer matching: {'Enabled' if rules_config.edges_manufacturer_match_required() else 'Disabled'}")
    print(f"   Low-E ordering: {'Enabled' if rules_config.lowe_ordering_required() else 'Disabled'}")
    
    return df_out

if __name__ == "__main__":
    print("🚀 Alpen IGU Input Generator - Configurable Version")
    print("🔧 All rules now configurable via config/alpen_igu_rules.yaml")
    print("💡 Edit rules at: http://localhost:8505 (Live Rules Editor)")
    print()
    
    # Load and display current rules
    rule_summary = rules_config.get_rule_summary()
    print(f"📋 Rules loaded from: {rule_summary['config_file']}")
    print(f"   Constants defined: {rule_summary['constants_count']}")
    print(f"   IGU types: {', '.join(rule_summary['igu_types'])}")
    print(f"   Gas types: {', '.join(rule_summary['supported_gases'])}")
    print()
    
    # Generate configurations
    df_result = generate_igu_configurations()
    
    print(f"\n🎉 Configuration generation complete!")
    print(f"📁 Output file: {OUTPUT_PATH}")
    print(f"🔧 Modify rules anytime at: http://localhost:8505")