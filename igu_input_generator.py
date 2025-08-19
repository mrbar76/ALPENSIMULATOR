#!/usr/bin/env python3
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

GLASS_CENTER_PATH      = "input_glass_catalog_center.csv"
GLASS_INNER_OUTER_PATH = "input_glass_catalog_inner_outer.csv"
OA_SIZES_PATH          = "input_oa_sizes.csv"
GAS_TYPES_PATH         = "input_gas_types.csv"
OUTPUT_PATH            = "igu_simulation_input_table.csv"

TOL               = 0.3   # mm tolerance for measured thickness
MIN_EDGE_NOMINAL  = 3.0   # mm for outer/inner nominal
MIN_AIRGAP        = 6.0   # mm minimum air gap (constrained by min spacer size)
QUAD_OA_MIN_INCH  = 0.75  # in, skip quads at or below this OA

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

def should_flip(position: str, coating_side: str, coating_name: str='') -> bool:
    """
    Determine if glass should be flipped based on coating placement requirements.
    
    COATING SURFACE REQUIREMENTS:
    - Triples: Standard low-e on surfaces 2 and 5, center coatings on surface 4
    - Quads: Standard low-e on surfaces 2 and 7, center coatings on surface 4
    - i89 coating: Always on surface 5 (triple) or 7 (quad)
    - NxLite and center coatings: Always on surface 4
    """
    
    # Special handling for i89 coating - must be on inner glass exterior face
    if position == "inner" and "i89" in coating_name.lower():
        return coating_side == "back"  # Keep i89 on exterior face (surface 5/7)
    
    # Standard coating placement rules
    coating_rules = {
        "outer":      {"back": False, "front": True},   # Want coating on surface 2 (back)
        "center":     {"back": False, "front": True},   # Want coating on surface 4 (back)
        "quad_inner": {"back": False, "front": True},   # Want coating on surface 4 (back)
        "inner":      {"front": False, "back": True},   # Want coating on surface 5/7 (front)
    }
    
    return coating_rules.get(position, {}).get(coating_side, False)

def validate_coating_conflicts(configs: list) -> bool:
    """
    Validate that no two low-e coatings are on the same glass lite.
    Returns True if configuration is valid, False if conflicts exist.
    """
    coatings = []
    for i, config in enumerate(configs):
        meta = config.get('meta', {})
        coating_name = meta.get('coating_name', 'none')
        if coating_name.lower() != 'none':
            coatings.append({
                'glass_position': i,
                'coating': coating_name,
                'nfrc_id': config.get('nfrc_id')
            })
    
    # Check for conflicts (same NFRC ID with multiple coatings)
    nfrc_coatings = {}
    for coating in coatings:
        nfrc_id = coating['nfrc_id']
        if nfrc_id in nfrc_coatings:
            # Multiple coatings on same glass lite - conflict!
            return False
        nfrc_coatings[nfrc_id] = coating
    
    return True

def calculate_air_gap(oa_mm: float, thks: list, gaps: int) -> float:
    return (oa_mm - sum(thks)) / gaps


def edges_manufacturer_match(m_o: str, m_i: str) -> bool:
    if not m_o or not m_i:
        return False
    mo = m_o.strip().lower()
    mi = m_i.strip().lower()
    if "generic" in (mo, mi):
        return True
    # Allow if either is a substring of the other
    return mo in mi or mi in mo


def center_allowed(meta: dict, igu_type: str) -> bool:
    t  = meta.get("thickness_mm",0)
    cs = meta.get("coating_side","none")
    if t > 1.1 + TOL:           # thin ≤1.1
        return False
    if igu_type=="Quad" and cs!="none":  # quad-inner uncoated
        return False
    return True

def quad_center_rule(meta: dict) -> bool:
    return meta.get("thickness_mm",0) <= 1.1 + TOL


# === MAIN ===

def main():
    # load inputs
    outer_df  = pd.read_csv(GLASS_INNER_OUTER_PATH)
    outer_df  = outer_df[outer_df["Position"].str.lower()=="outer"]
    inner_df  = pd.read_csv(GLASS_INNER_OUTER_PATH)
    inner_df  = inner_df[inner_df["Position"].str.lower()=="inner"]
    center_df = pd.read_csv(GLASS_CENTER_PATH)
    oa_df     = pd.read_csv(OA_SIZES_PATH)
    gas_df    = pd.read_csv(GAS_TYPES_PATH)

# — NEW: only for center panes, split "2" or "2,3" into a list of ints
    center_df["quads_surfaces"] = (
    center_df["quads_surfaces"]
      .astype(str)
      .str.split(",")
      .apply(lambda L: [int(x) for x in L])
)

    # pre-calc nominal
    outer_df["Nominal"] = outer_df["Short_Name"].apply(parse_nominal_thickness)
    inner_df["Nominal"] = inner_df["Short_Name"].apply(parse_nominal_thickness)
    center_df["Nominal"] = center_df["Short_Name"].apply(parse_nominal_thickness)
    # ——— NEW: parse allowed quad slots from CSV (e.g. "2" or "2,3")
    
    cache = {}
    results = []

    # TRIPLES
    triple_iters = len(oa_df)*len(gas_df)*len(outer_df)*len(center_df)*len(inner_df)
    print(f"Generating Triples ({triple_iters:,} combos)...")
    pbar = tqdm(total=triple_iters, unit="cfg")
    for _, oa in oa_df.iterrows():
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]
        for _, gas in gas_df.iterrows():
            for o in outer_df.itertuples():
                for c in center_df.itertuples():
                    for i in inner_df.itertuples():
                        pbar.update(1)
                        m_o = get_meta(o.NFRC_ID, cache)
                        m_c = get_meta(c.NFRC_ID, cache)
                        m_i = get_meta(i.NFRC_ID, cache)
                        if not (m_o and m_c and m_i): continue
                        
                        # Validate coating conflicts
                        glass_configs = [
                            {'meta': m_o, 'nfrc_id': o.NFRC_ID},
                            {'meta': m_c, 'nfrc_id': c.NFRC_ID},
                            {'meta': m_i, 'nfrc_id': i.NFRC_ID}
                        ]
                        if not validate_coating_conflicts(glass_configs): continue
                        
                        # edge rules
                        if m_o["thickness_mm"] < MIN_EDGE_NOMINAL or m_i["thickness_mm"] < MIN_EDGE_NOMINAL or \
                           abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL:
                            continue
                        if not edges_manufacturer_match(m_o["manufacturer"], m_i["manufacturer"]): continue
                        # center thin
                        if not center_allowed(m_c, "Triple"): continue
                        # low-e order
                        if parse_lowe_value(o.Short_Name)<parse_lowe_value(i.Short_Name): continue
                        # gap
                        ag = calculate_air_gap(oa_mm,[m_o["thickness_mm"],m_c["thickness_mm"],m_i["thickness_mm"]],2)
                        if ag<MIN_AIRGAP: continue
                        # flip
                        flips = [
                            should_flip("outer", m_o["coating_side"], m_o["coating_name"]),
                            should_flip("center", m_c["coating_side"], m_c["coating_name"]),
                            should_flip("inner", m_i["coating_side"], m_i["coating_name"])
                        ]
                        results.append({
                            "IGU Type":"Triple","OA (in)":oa_in,"OA (mm)":oa_mm,"Gas Type":gas["Gas Type"],
                            "Glass 1 NFRC ID":o.NFRC_ID,"Glass 2 NFRC ID":c.NFRC_ID,"Glass 3 NFRC ID":i.NFRC_ID,"Glass 4 NFRC ID":"",
                            "Flip Glass 1":flips[0],"Flip Glass 2":flips[1],"Flip Glass 3":flips[2],
                            "Air Gap (mm)":round(ag,2)
                        })
    pbar.close()

    # QUADS
    quad_candidates = oa_df[oa_df["OA (in)"] > QUAD_OA_MIN_INCH]
    quad_iters = (
        len(quad_candidates)
        * len(gas_df)
        * len(outer_df)
        * len(center_df)
        * len(center_df)
        * len(inner_df)
    )
    print(f"Generating Quads ({quad_iters:,} combos)...")
    pbar = tqdm(total=quad_iters, unit="cfg")

    for _, oa in quad_candidates.iterrows():
        oa_mm, oa_in = oa["OA (mm)"], oa["OA (in)"]

        for _, gas in gas_df.iterrows():
            for o in outer_df.itertuples():

                for qi in center_df.itertuples():    # quad-inner candidate
                    # only allow panes flagged for surface 2
                    if 2 not in qi.quads_surfaces:
                        continue

                    for c in center_df.itertuples():   # true-center candidate
                        # only allow panes flagged for surface 3
                        if 3 not in c.quads_surfaces:
                            continue

                        for i in inner_df.itertuples():
                            pbar.update(1)

                            # fetch metadata
                            m_o = get_meta(o.NFRC_ID, cache)
                            m_q = get_meta(qi.NFRC_ID, cache)
                            m_c = get_meta(c.NFRC_ID, cache)
                            m_i = get_meta(i.NFRC_ID, cache)
                            if not (m_o and m_q and m_c and m_i):
                                continue

                            # Validate coating conflicts
                            glass_configs = [
                                {"meta": m_o, "nfrc_id": o.NFRC_ID},
                                {"meta": m_q, "nfrc_id": qi.NFRC_ID},
                                {"meta": m_c, "nfrc_id": c.NFRC_ID},
                                {"meta": m_i, "nfrc_id": i.NFRC_ID},
                            ]
                            if not validate_coating_conflicts(glass_configs):
                                continue

                            # edge‐thickness & manufacturer match
                            if (
                                m_o["thickness_mm"] < MIN_EDGE_NOMINAL
                                or m_i["thickness_mm"] < MIN_EDGE_NOMINAL
                                or abs(m_o["thickness_mm"] - m_i["thickness_mm"]) > TOL
                                or not edges_manufacturer_match(
                                    m_o["manufacturer"], m_i["manufacturer"]
                                )
                            ):
                                continue

                            # Low-E ordering
                            if parse_lowe_value(o.Short_Name) < parse_lowe_value(i.Short_Name):
                                continue

                            # gap
                            ag = calculate_air_gap(
                                oa_mm,
                                [
                                    m_o["thickness_mm"],
                                    m_q["thickness_mm"],
                                    m_c["thickness_mm"],
                                    m_i["thickness_mm"],
                                ],
                                3,
                            )
                            if ag < MIN_AIRGAP:
                                continue

                            # flip logic
                            flips = [
                                should_flip("outer", m_o["coating_side"], m_o["coating_name"]),
                                should_flip("quad_inner", m_q["coating_side"], m_q["coating_name"]),
                                should_flip("center", m_c["coating_side"], m_c["coating_name"]),
                                should_flip("inner", m_i["coating_side"], m_i["coating_name"]),
                            ]

                            # append result
                            results.append(
                                {
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
                                }
                            )

    pbar.close()

    # dedupe & save
    df_out = pd.DataFrame(results).drop_duplicates(
        subset=["IGU Type","OA (in)","Gas Type","Glass 1 NFRC ID","Glass 2 NFRC ID","Glass 3 NFRC ID","Glass 4 NFRC ID"]
    )
    df_out.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Wrote {len(df_out)} configurations to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
