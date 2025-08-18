"""
Original Alpen Rules Editor - Make existing rules verbose and editable

Works with the actual igu_input_generator.py logic and structure,
making the hardcoded rules visible and editable while maintaining
the same workflow: CSV inputs → rule checking → configuration generation
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="Original Alpen Rules", layout="wide")
st.title("🔧 Original Alpen IGU Rules - Verbose & Editable")

st.info("📋 **Your Current Workflow**: CSV Ingredients → Rule Validation → IGU Generation → Simulation → Optimization")

# Load actual input data
@st.cache_data
def load_original_data():
    """Load the original CSV input files"""
    data = {}
    try:
        data['gas_types'] = pd.read_csv('input_gas_types.csv')
        data['oa_sizes'] = pd.read_csv('input_oa_sizes.csv')  
        data['glass_inner_outer'] = pd.read_csv('input_glass_catalog_inner_outer.csv')
        data['glass_center'] = pd.read_csv('input_glass_catalog_center.csv')
        
        # Try to load existing configurations if available
        try:
            data['configurations'] = pd.read_csv('igu_simulation_input_table.csv')
        except:
            data['configurations'] = pd.DataFrame()
            
        # Try to load latest results
        result_files = list(Path('.').glob('igu_simulation_results_*.csv'))
        if result_files:
            latest_results = max(result_files, key=lambda x: x.stat().st_mtime)
            data['results'] = pd.read_csv(latest_results)
        else:
            data['results'] = pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}
    
    return data

data = load_original_data()

if not data:
    st.error("❌ Could not load original data files")
    st.stop()

# Sidebar - Original Data Summary
st.sidebar.header("📊 Your Original Data")

if 'gas_types' in data:
    gas_count = len(data['gas_types'])
    st.sidebar.metric("Gas Types", gas_count)
    with st.sidebar.expander("Gas Types"):
        for gas in data['gas_types']['Gas Type'].dropna():
            st.write(f"• {gas}")

if 'oa_sizes' in data:
    oa_count = len(data['oa_sizes'])
    st.sidebar.metric("OA Sizes", oa_count)
    with st.sidebar.expander("OA Sizes (in)"):
        for oa in data['oa_sizes']['OA (in)'].dropna():
            st.write(f"• {oa}")

if 'glass_inner_outer' in data:
    glass_io_count = len(data['glass_inner_outer'])
    st.sidebar.metric("Inner/Outer Glass", glass_io_count)

if 'glass_center' in data:
    glass_c_count = len(data['glass_center'])
    st.sidebar.metric("Center Glass", glass_c_count)

if 'configurations' in data and len(data['configurations']) > 0:
    config_count = len(data['configurations'])
    st.sidebar.metric("Generated Configs", f"{config_count:,}")
    
    # Show triple vs quad split
    igu_counts = data['configurations']['IGU Type'].value_counts()
    for igu_type, count in igu_counts.items():
        st.sidebar.text(f"{igu_type}: {count:,}")

if 'results' in data and len(data['results']) > 0:
    result_count = len(data['results'])
    st.sidebar.metric("Simulation Results", f"{result_count:,}")

# Main interface
tab1, tab2, tab3, tab4 = st.tabs([
    "🧬 IGU Configuration Rules", 
    "🔍 Current Rule Analysis", 
    "⚙️ Rule Parameters", 
    "🧪 Test Rules"
])

with tab1:
    st.header("🧬 IGU Configuration Rules from igu_input_generator.py")
    st.subheader("Current Hardcoded Rules (Extracted from Code)")
    
    # Show the actual rules extracted from the code
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔷 Triple-Pane Rules")
        st.code("""
# TRIPLE CONFIGURATION RULES:
✅ Glass Layers: 1, 2, 3 (no Glass 4)
✅ OA Range: All sizes allowed
✅ Edge Glass: MIN_EDGE_NOMINAL = 3.0mm
✅ Center Glass: thickness ≤ 1.1mm + 0.3mm tolerance
✅ Manufacturer Match: Outer/Inner must match
✅ Low-E Order: parse_lowe_value(outer) >= parse_lowe_value(inner)
✅ Min Air Gap: 3.0mm minimum
✅ Coating Placement:
   - Standard low-e: surfaces 2 and 5
   - Center coatings: surface 4  
   - i89 coating: surface 5
        """)
    
    with col2:
        st.subheader("🔶 Quad-Pane Rules")  
        st.code("""
# QUAD CONFIGURATION RULES:
✅ Glass Layers: 1, 2, 3, 4 (all required)
✅ OA Range: > 0.75 inches (QUAD_OA_MIN_INCH)
✅ Edge Glass: MIN_EDGE_NOMINAL = 3.0mm  
✅ Center Glass: thickness ≤ 1.1mm + 0.3mm tolerance
✅ Quad Center Rule: uncoated only for inner center
✅ Manufacturer Match: Outer/Inner must match
✅ Min Air Gap: 3.0mm minimum
✅ Coating Placement:
   - Standard low-e: surfaces 2 and 7
   - Center coatings: surface 4
   - i89 coating: surface 7
        """)
    
    st.subheader("📋 Extracted Constants from Code")
    
    # Make these editable
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📏 Thickness Rules")
        min_edge_nominal = st.number_input(
            "MIN_EDGE_NOMINAL (mm)", 
            value=3.0, 
            step=0.1,
            help="Minimum thickness for outer/inner glass"
        )
        
        tolerance = st.number_input(
            "Thickness Tolerance (mm)", 
            value=0.3, 
            step=0.1,
            help="Tolerance for measured vs nominal thickness"
        )
        
        center_max_thickness = st.number_input(
            "Center Glass Max (mm)", 
            value=1.1, 
            step=0.1,
            help="Maximum thickness for center glass"
        )
    
    with col2:
        st.subheader("🌀 Airspace Rules")
        min_airgap = st.number_input(
            "MIN_AIRGAP (mm)", 
            value=3.0, 
            step=0.1,
            help="Minimum air gap between glass layers"
        )
        
        quad_oa_min = st.number_input(
            "QUAD_OA_MIN_INCH", 
            value=0.75, 
            step=0.125,
            help="Minimum OA for quad configurations"
        )
    
    with col3:
        st.subheader("🏭 Manufacturer Rules")
        require_edge_match = st.checkbox(
            "Require Edge Manufacturer Match", 
            value=True,
            help="Outer and inner glass must be same manufacturer"
        )
        
        allow_center_different = st.checkbox(
            "Allow Different Center Manufacturer", 
            value=True,
            help="Center glass can be different manufacturer"
        )
    
    # Show editable coating rules
    st.subheader("✨ Coating Placement Rules")
    
    coating_rules = st.text_area(
        "Coating Logic (as code comments)",
        value="""# Surface numbering: 1=outside air, 2=glass1 inside, 3=glass2 outside, etc.
# Triple surfaces: 1, 2, 3, 4, 5, 6
# Quad surfaces: 1, 2, 3, 4, 5, 6, 7, 8

TRIPLE COATING RULES:
- Standard low-e: surfaces 2 and 5 (protected positions)
- Center coatings: surface 4 (between center glass layers)  
- i89 coating: always surface 5 (inner glass exterior face)
- NxLite coatings: always surface 4

QUAD COATING RULES:
- Standard low-e: surfaces 2 and 7 (protected positions)
- Center coatings: surface 4 (protected center position)
- i89 coating: always surface 7 (inner glass exterior face)
- Inner center glass: uncoated only""",
        height=200
    )

with tab2:
    st.header("🔍 Current Rule Analysis")
    st.subheader("Analysis of Your Actual Generated Configurations")
    
    if 'configurations' in data and len(data['configurations']) > 0:
        configs = data['configurations']
        
        # Analyze triple vs quad distribution
        st.subheader("📊 IGU Type Distribution")
        igu_counts = configs['IGU Type'].value_counts()
        
        col1, col2 = st.columns(2)
        with col1:
            for igu_type, count in igu_counts.items():
                pct = count / len(configs) * 100
                st.metric(f"{igu_type} Configurations", f"{count:,} ({pct:.1f}%)")
        
        with col2:
            # Show why certain combinations were filtered out
            st.subheader("🎯 Rule Application Results")
            
            # Analyze OA distribution for quads (should be > 0.75")
            if 'Quad' in igu_counts:
                quad_configs = configs[configs['IGU Type'] == 'Quad']
                min_quad_oa = quad_configs['OA (in)'].min()
                st.metric("Min Quad OA", f"{min_quad_oa:.3f}\"")
                if min_quad_oa <= 0.75:
                    st.warning(f"⚠️ Found quads with OA ≤ 0.75\" (violates QUAD_OA_MIN_INCH rule)")
                else:
                    st.success(f"✅ All quads have OA > 0.75\"")
        
        # Glass analysis
        st.subheader("🪟 Glass Layer Analysis")
        
        # Check glass 4 usage
        has_glass_4 = configs['Glass 4 NFRC ID'].notna() & (configs['Glass 4 NFRC ID'] != '')
        glass_4_count = has_glass_4.sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Configs with Glass 4", f"{glass_4_count:,}")
        with col2:
            no_glass_4 = (~has_glass_4).sum()  
            st.metric("Configs without Glass 4", f"{no_glass_4:,}")
        with col3:
            if glass_4_count > 0:
                quad_with_glass_4 = configs[(configs['IGU Type'] == 'Quad') & has_glass_4]
                st.metric("Quads with Glass 4", f"{len(quad_with_glass_4):,}")
        
        # Gas type analysis
        st.subheader("💨 Gas Type Usage")
        gas_counts = configs['Gas Type'].value_counts()
        for gas, count in gas_counts.items():
            pct = count / len(configs) * 100
            st.text(f"{gas}: {count:,} ({pct:.1f}%)")
        
        # OA size analysis
        st.subheader("🌀 OA Size Distribution")
        oa_counts = configs['OA (in)'].value_counts().sort_index()
        for oa, count in oa_counts.items():
            pct = count / len(configs) * 100
            st.text(f"{oa}\" OA: {count:,} ({pct:.1f}%)")
    
    else:
        st.warning("⚠️ No configuration data found. Run igu_input_generator.py first.")

with tab3:
    st.header("⚙️ Rule Parameters")
    st.subheader("Make Your Hardcoded Rules Editable")
    
    st.info("💡 **Goal**: Extract hardcoded constants from igu_input_generator.py and make them configurable")
    
    # Current constants from the code
    current_constants = {
        "TOL": 0.3,
        "MIN_EDGE_NOMINAL": 3.0, 
        "MIN_AIRGAP": 3.0,
        "QUAD_OA_MIN_INCH": 0.75,
        "center_max_thickness": 1.1
    }
    
    st.subheader("📝 Current Constants (from code)")
    for key, value in current_constants.items():
        st.text(f"{key} = {value}")
    
    st.subheader("🔧 Editable Rule Configuration")
    
    # Create editable version
    with st.expander("🎛️ Edit Rule Parameters"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_tol = st.number_input("Thickness Tolerance (TOL)", value=0.3, step=0.1, format="%.1f")
            new_min_edge = st.number_input("Min Edge Nominal (mm)", value=3.0, step=0.5, format="%.1f") 
            new_min_airgap = st.number_input("Min Air Gap (mm)", value=3.0, step=0.5, format="%.1f")
        
        with col2:
            new_quad_oa_min = st.number_input("Quad OA Min (inches)", value=0.75, step=0.125, format="%.3f")
            new_center_max = st.number_input("Center Glass Max (mm)", value=1.1, step=0.1, format="%.1f")
        
        if st.button("💾 Generate Updated Configuration File"):
            config = {
                "rule_parameters": {
                    "TOL": new_tol,
                    "MIN_EDGE_NOMINAL": new_min_edge,
                    "MIN_AIRGAP": new_min_airgap, 
                    "QUAD_OA_MIN_INCH": new_quad_oa_min,
                    "center_max_thickness": new_center_max
                },
                "manufacturer_rules": {
                    "require_edge_match": require_edge_match,
                    "allow_center_different": allow_center_different
                },
                "coating_rules": {
                    "triple_lowe_surfaces": [2, 5],
                    "quad_lowe_surfaces": [2, 7],
                    "center_coating_surface": 4,
                    "i89_surface_triple": 5,
                    "i89_surface_quad": 7
                }
            }
            
            with open("alpen_rules_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            st.success("✅ Saved configuration to alpen_rules_config.json")
            st.json(config)

with tab4:
    st.header("🧪 Test Rules Against Your Data")
    st.subheader("Validate Rules Using Your Actual Input Data")
    
    if 'configurations' in data and len(data['configurations']) > 0:
        st.subheader("🔬 Rule Validation Test")
        
        configs = data['configurations']
        
        # Test 1: Glass 4 rule
        st.subheader("Test 1: Glass 4 Rule Validation")
        triple_configs = configs[configs['IGU Type'] == 'Triple']
        quad_configs = configs[configs['IGU Type'] == 'Quad']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text("Triple Configs:")
            if len(triple_configs) > 0:
                # Check if any triples have glass 4
                triple_with_glass_4 = triple_configs[
                    triple_configs['Glass 4 NFRC ID'].notna() & 
                    (triple_configs['Glass 4 NFRC ID'] != '')
                ]
                
                if len(triple_with_glass_4) > 0:
                    st.error(f"❌ Found {len(triple_with_glass_4)} triples with Glass 4!")
                    st.dataframe(triple_with_glass_4[['IGU Type', 'Glass 1 NFRC ID', 'Glass 2 NFRC ID', 'Glass 3 NFRC ID', 'Glass 4 NFRC ID']].head())
                else:
                    st.success("✅ All triples correctly have no Glass 4")
            else:
                st.warning("No triple configurations found")
        
        with col2:
            st.text("Quad Configs:")
            if len(quad_configs) > 0:
                # Check if any quads are missing glass 4
                quad_without_glass_4 = quad_configs[
                    quad_configs['Glass 4 NFRC ID'].isna() | 
                    (quad_configs['Glass 4 NFRC ID'] == '')
                ]
                
                if len(quad_without_glass_4) > 0:
                    st.error(f"❌ Found {len(quad_without_glass_4)} quads without Glass 4!")
                    st.dataframe(quad_without_glass_4[['IGU Type', 'Glass 1 NFRC ID', 'Glass 2 NFRC ID', 'Glass 3 NFRC ID', 'Glass 4 NFRC ID']].head())
                else:
                    st.success("✅ All quads correctly have Glass 4")
            else:
                st.warning("No quad configurations found")
        
        # Test 2: OA size rule for quads
        st.subheader("Test 2: Quad OA Size Rule")
        if len(quad_configs) > 0:
            small_oa_quads = quad_configs[quad_configs['OA (in)'] <= 0.75]
            
            if len(small_oa_quads) > 0:
                st.error(f"❌ Found {len(small_oa_quads)} quads with OA ≤ 0.75\"!")
                st.dataframe(small_oa_quads[['IGU Type', 'OA (in)', 'Gas Type']].head())
            else:
                st.success("✅ All quads have OA > 0.75\"")
        
        # Test 3: Gas type validation
        st.subheader("Test 3: Gas Type Validation")
        valid_gases = set(data['gas_types']['Gas Type'].dropna()) if 'gas_types' in data else set()
        config_gases = set(configs['Gas Type'].dropna())
        
        invalid_gases = config_gases - valid_gases
        if invalid_gases:
            st.error(f"❌ Found invalid gas types: {invalid_gases}")
        else:
            st.success(f"✅ All gas types valid: {config_gases}")
    
    else:
        st.warning("⚠️ No configuration data to test against")

# Footer
st.divider()
st.caption("🔧 Original Alpen Rules Editor - Making your existing igu_input_generator.py rules verbose and editable")
st.caption("📁 Works with your actual CSV files and maintains the same workflow logic")