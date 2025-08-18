#!/usr/bin/env python3
"""
Quick simulation test to identify issues
"""

import pandas as pd
import requests
import pickle
import os
import sys

# Test basic imports first
try:
    import pywincalc
    print("✅ PyWinCalc imported successfully")
except ImportError as e:
    print(f"❌ PyWinCalc import failed: {e}")
    sys.exit(1)

# Load the input data
try:
    df = pd.read_csv("igu_simulation_input_table.csv")
    print(f"✅ Loaded {len(df)} rows of input data")
except Exception as e:
    print(f"❌ Failed to load input data: {e}")
    sys.exit(1)

# Test with just first row
test_row = df.iloc[0]
print(f"🧪 Testing with first row: {test_row['IGU Type']}")
print(f"   Glass NRFCs: {test_row['Glass 1 NFRC ID']}, {test_row['Glass 2 NFRC ID']}, {test_row['Glass 3 NFRC ID']}")

# Test IGSDB API connection
API_KEY = "0e94db9c8cda032d3eaa083e21984350c17633ca"
HEADERS = {"accept": "application/json", "Authorization": f"Token {API_KEY}"}

def test_nfrc_lookup(nfrc_id):
    """Test single NFRC ID lookup"""
    print(f"🔍 Testing NFRC ID {nfrc_id}...")
    
    try:
        # Get product ID
        url = f"https://igsdb.lbl.gov/api/v1/products?type=glazing&nfrc_id={nfrc_id}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if not resp.ok:
            print(f"   ❌ API request failed: {resp.status_code}")
            return False
            
        data = resp.json()
        if not data:
            print(f"   ⚠️ No products found for NFRC {nfrc_id}")
            return False
            
        product_id = data[0].get("product_id")
        print(f"   ✅ Found product ID: {product_id}")
        
        # Get layer data
        layer_url = f"https://igsdb.lbl.gov/api/v1/products/{product_id}/"
        layer_resp = requests.get(layer_url, headers=HEADERS, timeout=10)
        
        if not layer_resp.ok:
            print(f"   ❌ Layer request failed: {layer_resp.status_code}")
            return False
            
        # Get raw content (JSON string) as the original does
        layer_content = layer_resp.content
        print(f"   ✅ Got layer content ({len(layer_content)} bytes)")
        
        # Try to create PyWinCalc layer with raw JSON content
        try:
            layer = pywincalc.parse_json(layer_content)
            print(f"   ✅ PyWinCalc layer created successfully")
            return True
        except Exception as e:
            print(f"   ❌ PyWinCalc layer creation failed: {e}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout for NFRC {nfrc_id}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

# Test the first few NFRC IDs from the test row
test_nfrcs = [test_row['Glass 1 NFRC ID'], test_row['Glass 2 NFRC ID'], test_row['Glass 3 NFRC ID']]
test_nfrcs = [int(x) for x in test_nfrcs if pd.notna(x)]

print(f"\n🧪 Testing NFRC lookups...")
success_count = 0
for nfrc_id in test_nfrcs:
    if test_nfrc_lookup(nfrc_id):
        success_count += 1

print(f"\n📊 Results: {success_count}/{len(test_nfrcs)} NFRC lookups successful")

if success_count == 0:
    print("❌ No NFRC lookups successful - check API key or network")
    sys.exit(1)
elif success_count < len(test_nfrcs):
    print("⚠️ Some NFRC lookups failed - simulation may be slow or incomplete")
else:
    print("✅ All NFRC lookups successful - simulation should work")

print("\n🔥 Quick simulation test with 1 row...")

try:
    # Test gas creation
    print("🌬️ Testing gas creation...")
    gas_type = test_row['Gas Type']
    if gas_type == '90K':  # 90% Krypton
        pct, gt = 0.9, pywincalc.PredefinedGasType.KRYPTON
    elif gas_type == '95A':  # 95% Argon  
        pct, gt = 0.95, pywincalc.PredefinedGasType.ARGON
    else:  # Air
        pct, gt = 1.0, pywincalc.PredefinedGasType.AIR
    
    mix = pywincalc.create_gas([[pct, gt], [1-pct, pywincalc.PredefinedGasType.AIR]])
    gap_count = 2  # Triple
    thickness_m = test_row['Air Gap (mm)'] / 1000.0
    gaps = [pywincalc.Layers.gap(thickness=thickness_m, gas=mix) for _ in range(gap_count)]
    print(f"✅ Created {len(gaps)} gas gaps")
    
    # If we got this far, the simulation should work
    print("✅ Basic simulation components working!")
    print("\n💡 Simulation is probably just slow due to IGSDB API calls.")
    print("💡 Try running with cache file present to speed up subsequent runs.")
    
except Exception as e:
    print(f"❌ Simulation component test failed: {e}")
    import traceback
    traceback.print_exc()