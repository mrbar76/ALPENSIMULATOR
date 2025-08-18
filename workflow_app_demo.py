"""
ALPENSIMULATOR Demo - Cloud Deployment Version
Demonstrates the workflow without requiring PyWinCalc installation
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.append('.')

try:
    from configurable_rules import AlpenRulesConfig
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

st.set_page_config(page_title="ALPENSIMULATOR Demo", layout="wide")

# Demo mode warning
st.warning("🔬 **DEMO MODE**: This is a demonstration version for cloud deployment. Full simulation requires local setup with PyWinCalc.")

# Helper functions
@st.cache_data
def load_glass_catalog():
    """Load unified glass catalog with glass names"""
    try:
        return pd.read_csv("unified_glass_catalog.csv")
    except:
        return pd.DataFrame()

def get_glass_description(nfrc_id, glass_catalog):
    """Get glass description from catalog"""
    if glass_catalog.empty:
        return f"NFRC {nfrc_id}"
    
    match = glass_catalog[glass_catalog['NFRC_ID'] == nfrc_id]
    if not match.empty:
        return match.iloc[0]['Short_Name']
    return f"NFRC {nfrc_id}"

def create_igu_description(row, glass_catalog):
    """Create detailed IGU description with glass names"""
    igu_type = row['IGU Type']
    oa = row.get('OA (in)', 'N/A')
    gas = row.get('Gas Type', 'N/A')
    
    # Get glass descriptions
    glass_descriptions = []
    for i in range(1, 5):
        col = f'Glass_{i}_NFRC' if f'Glass_{i}_NFRC' in row.index else f'Glass {i} NFRC ID'
        if col in row.index and pd.notna(row[col]):
            desc = get_glass_description(row[col], glass_catalog)
            flip = row.get(f'Flip Glass {i}', row.get(f'Flip_Glass_{i}', False))
            flip_text = " (Flipped)" if flip else ""
            glass_descriptions.append(f"G{i}: {desc}{flip_text}")
    
    # Air gap info
    air_gap = row.get('Air Gap (mm)', 'N/A')
    air_gap_text = f" | Gap: {air_gap}mm" if air_gap != 'N/A' else ""
    
    return f"{igu_type} | OA: {oa}\" | {gas}{air_gap_text} | {' → '.join(glass_descriptions)}"

# Initialize session state
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1

# Header
st.title("🔧 ALPENSIMULATOR - Demo Version")
st.subheader("Materials Science Approach: Ingredients → Rules → Configuration → Simulation → Optimization")

# Progress indicator
progress_steps = [
    "1️⃣ Ingredient Management",
    "2️⃣ Rule Configuration", 
    "3️⃣ Generate Configurations",
    "4️⃣ Simulation Demo",
    "5️⃣ Results Preview"
]

cols = st.columns(len(progress_steps))
for i, (col, step) in enumerate(zip(cols, progress_steps)):
    with col:
        if i + 1 <= st.session_state.workflow_step:
            st.success(step)
        else:
            st.info(step)

# Navigation
current_step = st.session_state.workflow_step
step_nav = st.columns(5)
for i in range(5):
    with step_nav[i]:
        if st.button(f"Step {i+1}", key=f"nav_{i+1}"):
            st.session_state.workflow_step = i + 1
            st.rerun()

st.divider()

# === STEP 1: INGREDIENT MANAGEMENT ===
if current_step == 1:
    st.header("1️⃣ Ingredient Management")
    st.subheader("Add or Remove Glass Types, Gas Fills, and OA Sizes")
    
    # Show unified glass catalog
    st.subheader("📊 Unified Glass Catalog")
    
    try:
        glass_df = pd.read_csv("unified_glass_catalog.csv")
        st.success(f"✅ Loaded {len(glass_df)} glass types from unified catalog")
        
        # Show position capabilities summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            outer_count = len(glass_df[glass_df['Can_Outer'] == True])
            st.metric("Can be Outer", outer_count)
        with col2:
            quad_inner_count = len(glass_df[glass_df['Can_QuadInner'] == True])
            st.metric("Can be Quad-Inner", quad_inner_count)
        with col3:
            center_count = len(glass_df[glass_df['Can_Center'] == True])
            st.metric("Can be Center", center_count)
        with col4:
            inner_count = len(glass_df[glass_df['Can_Inner'] == True])
            st.metric("Can be Inner", inner_count)
        
        # Show sample of catalog
        st.dataframe(glass_df.head(10), use_container_width=True)
        
        st.info("💡 **Key Innovation**: Single unified catalog with position checkboxes replaces separate CSV files!")
        
    except FileNotFoundError:
        st.error("❌ unified_glass_catalog.csv not found")
    
    # Show other input files
    st.subheader("📁 Other Input Files")
    
    try:
        gas_df = pd.read_csv("input_gas_types.csv")
        oa_df = pd.read_csv("input_oa_sizes.csv")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⛽ Gas Types")
            st.dataframe(gas_df, use_container_width=True)
        with col2:
            st.subheader("📏 OA Sizes")
            st.dataframe(oa_df, use_container_width=True)
            
    except FileNotFoundError as e:
        st.error(f"❌ Input file not found: {e}")
    
    if st.button("Proceed to Step 2: Configure Rules", type="primary"):
        st.session_state.workflow_step = 2
        st.rerun()

# === STEP 2: RULE CONFIGURATION ===
elif current_step == 2:
    st.header("2️⃣ Rule Configuration")
    st.subheader("Configure Rules for Each Ingredient")
    
    if RULES_AVAILABLE:
        config = AlpenRulesConfig()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Current Rules")
            st.metric("Tolerance", f"{config.get_tolerance()}mm")
            st.metric("Min Edge", f"{config.get_min_edge_nominal()}mm")
            st.metric("Min Air Gap", f"{config.get_min_airgap()}mm")
            st.metric("Quad OA Min", f"{config.get_quad_oa_min_inch()}\"")
        
        with col2:
            st.subheader("✨ Coating Rules")
            st.text(f"Triple i89: Surface {config.get_i89_surface('triple')}")
            st.text(f"Quad i89: Surface {config.get_i89_surface('quad')}")
            st.text(f"Triple Low-E: {config.get_standard_lowe_surfaces('triple')}")
            st.text(f"Quad Low-E: {config.get_standard_lowe_surfaces('quad')}")
    
    else:
        st.error("❌ Configurable rules system not available")
    
    if st.button("Proceed to Step 3: Generate Configurations", type="primary"):
        st.session_state.workflow_step = 3
        st.rerun()

# === STEP 3: GENERATE CONFIGURATIONS ===
elif current_step == 3:
    st.header("3️⃣ Generate IGU Configurations") 
    st.subheader("Create Configurations Using Unified Catalog System")
    
    st.info("🔬 **Demo Mode**: Configuration generation shown with sample data")
    
    # Show sample configurations
    sample_configs = pd.DataFrame({
        'IGU Type': ['Triple', 'Triple', 'Quad', 'Quad'],
        'OA (in)': [0.88, 1.0, 0.88, 1.0],
        'Gas Type': ['90K', '95A', '90K', '95A'],
        'Glass 1 NFRC ID': [102, 103, 102, 103],
        'Glass 2 NFRC ID': [107, 107, 102, 103],
        'Glass 3 NFRC ID': [102, 103, 107, 107],
        'Glass 4 NFRC ID': ['', '', 102, 103],
        'Air Gap (mm)': [7.51, 4.84, 3.99, 3.1]
    })
    
    st.subheader("📊 Sample Generated Configurations")
    st.dataframe(sample_configs, use_container_width=True)
    
    st.success("✅ Demo: Generated 4 sample configurations (2 Triple + 2 Quad)")
    st.info("💡 **Key Achievement**: Quad generation now works (was previously broken)!")
    
    if st.button("Proceed to Step 4: Simulation Demo", type="primary"):
        st.session_state.workflow_step = 4
        st.rerun()

# === STEP 4: SIMULATION DEMO ===
elif current_step == 4:
    st.header("4️⃣ Thermal Simulation Demo")
    st.subheader("PyWinCalc Simulation Results Preview")
    
    st.info("🔬 **Demo Mode**: Showing sample simulation results. Full simulation requires PyWinCalc installation.")
    
    # Load glass catalog for enhanced descriptions
    glass_catalog = load_glass_catalog()
    
    # Sample simulation results
    sample_results = pd.DataFrame({
        'Row_Index': [0, 1, 2, 3],
        'IGU Type': ['Triple', 'Triple', 'Quad', 'Quad'],
        'U_Value_IP': [0.286, 0.176, 0.245, 0.168],
        'SHGC': [0.708, 0.528, 0.687, 0.517],
        'VT': [0.753, 0.721, 0.742, 0.711],
        'Gas Type': ['90K', '90K', '90K', '90K'],
        'OA (in)': [0.88, 0.88, 0.88, 0.88],
        'Glass 1 NFRC ID': [102, 102, 102, 102],
        'Glass 2 NFRC ID': [107, 22720, 102, 103],
        'Glass 3 NFRC ID': [102, 102, 107, 107],
        'Glass 4 NFRC ID': ['', '', 102, 103],
        'Flip Glass 1': [False, False, False, False],
        'Flip Glass 2': [False, True, False, False],
        'Flip Glass 3': [False, False, False, False],
        'Flip Glass 4': ['', '', False, False]
    })
    
    # Create enhanced descriptions
    enhanced_df = sample_results.copy()
    enhanced_df['IGU_Description'] = enhanced_df.apply(
        lambda row: create_igu_description(row, glass_catalog), axis=1
    )
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_u = enhanced_df['U_Value_IP'].mean()
        st.metric("Avg U-Value (IP)", f"{avg_u:.3f}")
    with col2:
        avg_shgc = enhanced_df['SHGC'].mean()
        st.metric("Avg SHGC", f"{avg_shgc:.3f}")
    with col3:
        avg_vt = enhanced_df['VT'].mean()
        st.metric("Avg VT", f"{avg_vt:.3f}")
    with col4:
        unique_configs = len(enhanced_df['IGU Type'].unique())
        st.metric("IGU Types", unique_configs)
    
    # Show enhanced results
    st.subheader("✨ Enhanced Simulation Results")
    st.info("💡 **Key Innovation**: Shows glass names instead of just NFRC numbers!")
    
    display_cols = ['IGU_Description', 'U_Value_IP', 'SHGC', 'VT']
    st.dataframe(
        enhanced_df[display_cols], 
        use_container_width=True,
        column_config={
            "IGU_Description": st.column_config.TextColumn(
                "IGU Configuration",
                help="Detailed IGU description with glass types and properties",
                width="large"
            ),
            "U_Value_IP": st.column_config.NumberColumn(
                "U-Value (IP)",
                help="U-Value in IP units (Btu/hr·ft²·°F)",
                format="%.3f"
            ),
            "SHGC": st.column_config.NumberColumn(
                "SHGC",
                help="Solar Heat Gain Coefficient",
                format="%.3f"
            ),
            "VT": st.column_config.NumberColumn(
                "VT",
                help="Visible Transmittance",
                format="%.3f"
            )
        }
    )
    
    # Download option
    csv = enhanced_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample Results CSV",
        data=csv,
        file_name="alpensimulator_demo_results.csv",
        mime='text/csv'
    )
    
    if st.button("Proceed to Step 5: Results Preview", type="primary"):
        st.session_state.workflow_step = 5
        st.rerun()

# === STEP 5: RESULTS PREVIEW ===
elif current_step == 5:
    st.header("5️⃣ Optimization & Results Preview")
    st.subheader("Professional Materials Science Workflow Complete")
    
    st.success("🎉 **ALPENSIMULATOR Demo Complete!**")
    
    st.subheader("✅ Key Achievements Demonstrated:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **🔧 Technical Innovations:**
        - Unified glass catalog with position checkboxes
        - Fixed quad-pane generation (was broken)
        - Enhanced IGU descriptions with glass names
        - Configurable YAML rules system
        - Progress tracking and result persistence
        """)
    
    with col2:
        st.info("""
        **🧪 Workflow Features:**
        - Materials science approach
        - Step-by-step guided process
        - Professional documentation
        - Cloud deployment ready
        - Colleague collaboration enabled
        """)
    
    st.subheader("🚀 Next Steps for Full Version:")
    st.warning("""
    **For Full Thermal Simulation:**
    1. Install PyWinCalc locally: `pip install pywincalc`
    2. Run: `streamlit run workflow_app.py`
    3. Access complete IGSDB integration
    4. Generate unlimited configurations
    5. Run full thermal performance analysis
    """)
    
    st.subheader("📧 Share with Colleagues:")
    st.info("Share this demo URL with colleagues to showcase the ALPENSIMULATOR workflow!")
    
    if st.button("🔄 Restart Workflow", type="primary"):
        st.session_state.workflow_step = 1
        st.rerun()

# Footer
st.divider()
st.markdown("""
---
**🔬 ALPENSIMULATOR** - Advanced IGU Configuration Generator  
**🧪 Powered by Materials Science** | **🚀 Built with Streamlit**  
**📧 Contact**: For full version access and collaboration opportunities
""")