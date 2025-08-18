"""
ALPENSIMULATOR Full Version - Complete workflow with PyWinCalc
Graceful fallback to mock data if PyWinCalc fails to load
"""

import streamlit as st
import pandas as pd
import requests
import time
import pickle
import os
from tqdm import tqdm
from datetime import datetime
import sys
import json
import glob
from pathlib import Path

# Add current directory to path for imports
sys.path.append('.')

# Try to import PyWinCalc with graceful fallback
try:
    import pywincalc
    PYWINCALC_AVAILABLE = True
    st.success("✅ PyWinCalc loaded successfully - Real thermal simulation available!")
except ImportError as e:
    PYWINCALC_AVAILABLE = False
    st.warning(f"⚠️ PyWinCalc not available: {e}")
    st.info("📊 Using mock simulation data - Install PyWinCalc locally for real thermal calculations")

try:
    from configurable_rules import AlpenRulesConfig
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

st.set_page_config(page_title="ALPENSIMULATOR - Full Version", layout="wide")

# Mode indicator
if PYWINCALC_AVAILABLE:
    st.success("🔥 **FULL VERSION**: Real PyWinCalc thermal simulation enabled")
else:
    st.info("📊 **DEMO MODE**: Mock simulation data (PyWinCalc installation required for real calculations)")

# Helper functions
@st.cache_data
def load_glass_catalog():
    """Load unified glass catalog with glass names"""
    try:
        return pd.read_csv("unified_glass_catalog.csv")
    except:
        try:
            return pd.read_csv("input_glass_catalog_inner_outer.csv")
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

def run_real_simulation(df, limit=None):
    """Run actual PyWinCalc simulation"""
    if not PYWINCALC_AVAILABLE:
        return None
    
    try:
        # Import and run the actual simulation
        from simulation_small_test import run_simulation_batch
        
        sample_df = df.head(limit) if limit else df
        results = run_simulation_batch(sample_df)
        return results
        
    except Exception as e:
        st.error(f"Real simulation failed: {e}")
        return None

def create_mock_results(df, limit=None):
    """Create realistic mock simulation results"""
    import numpy as np
    np.random.seed(42)
    
    sample_df = df.head(limit) if limit else df
    result_df = sample_df.copy()
    
    # Generate realistic thermal performance values
    result_df['U_Value_IP'] = np.random.uniform(0.15, 0.35, len(result_df))
    result_df['SHGC'] = np.random.uniform(0.3, 0.8, len(result_df))
    result_df['VT'] = np.random.uniform(0.5, 0.9, len(result_df))
    
    return result_df

def show_detailed_results(results_df, title):
    """Show simulation results with detailed IGU descriptions"""
    st.subheader(f"✨ {title}")
    
    # Load glass catalog for descriptions
    glass_catalog = load_glass_catalog()
    
    # Create enhanced results with descriptions
    enhanced_df = results_df.copy()
    
    # Add IGU descriptions
    enhanced_df['IGU_Description'] = enhanced_df.apply(
        lambda row: create_igu_description(row, glass_catalog), axis=1
    )
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_u = enhanced_df['U_Value_IP'].mean() if 'U_Value_IP' in enhanced_df.columns else 0
        st.metric("Avg U-Value (IP)", f"{avg_u:.3f}")
    with col2:
        avg_shgc = enhanced_df['SHGC'].mean() if 'SHGC' in enhanced_df.columns else 0
        st.metric("Avg SHGC", f"{avg_shgc:.3f}")
    with col3:
        avg_vt = enhanced_df['VT'].mean() if 'VT' in enhanced_df.columns else 0
        st.metric("Avg VT", f"{avg_vt:.3f}")
    with col4:
        unique_configs = len(enhanced_df['IGU Type'].unique()) if 'IGU Type' in enhanced_df.columns else 0
        st.metric("IGU Types", unique_configs)
    
    # Detailed results table
    display_cols = ['IGU_Description', 'U_Value_IP', 'SHGC', 'VT']
    available_cols = [col for col in display_cols if col in enhanced_df.columns]
    
    if available_cols:
        st.dataframe(
            enhanced_df[available_cols].head(20), 
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
    else:
        st.dataframe(enhanced_df.head(20), use_container_width=True)
    
    # Download option
    csv = enhanced_df.to_csv(index=False)
    st.download_button(
        label=f"📥 Download {title} CSV",
        data=csv,
        file_name=f"enhanced_{title.lower().replace(' ', '_')}.csv",
        mime='text/csv'
    )

# Initialize session state
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1

# Header
st.title("🔧 ALPENSIMULATOR - Full Version")
st.subheader("Materials Science Approach: Ingredients → Rules → Configuration → Simulation → Optimization")

# Progress indicator
progress_steps = [
    "1️⃣ Ingredient Management",
    "2️⃣ Rule Configuration", 
    "3️⃣ Generate Configurations",
    "4️⃣ Run Simulation",
    "5️⃣ Optimize & Filter"
]

cols = st.columns(len(progress_steps))
for i, (col, step) in enumerate(zip(cols, progress_steps)):
    with col:
        if i + 1 <= st.session_state.workflow_step:
            st.success(step)
        elif i + 1 == st.session_state.workflow_step:
            st.info(f"**{step}**")
        else:
            st.info(step)

# Navigation
st.subheader("🧭 Workflow Navigation")
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
    st.subheader("🔧 Unified Glass Catalog System")
    st.info("💡 **Innovation**: Single catalog with multiselect position capabilities")
    
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
        st.subheader("📊 Glass Catalog Preview")
        st.dataframe(glass_df.head(10), use_container_width=True)
        
        with st.expander("🔍 View Full Catalog"):
            st.dataframe(glass_df, use_container_width=True)
        
    except FileNotFoundError:
        st.error("❌ unified_glass_catalog.csv not found")
    
    if st.button("Proceed to Step 2: Configure Rules", type="primary"):
        st.session_state.workflow_step = 2
        st.rerun()

# === STEP 4: RUN SIMULATION (Key difference) ===
elif current_step == 4:
    st.header("4️⃣ Run Thermal Simulation")
    st.subheader("PyWinCalc Thermal Performance Analysis")
    
    # Check for configurations
    try:
        df = pd.read_csv("igu_simulation_input_table.csv")
        st.success(f"✅ Loaded {len(df):,} configurations for simulation")
        
        # Show simulation controls
        st.subheader("🧪 Simulation Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚡ Quick Test")
            if PYWINCALC_AVAILABLE:
                st.info("Real PyWinCalc simulation - First 50 rows (~30-60 seconds)")
            else:
                st.info("Mock simulation data - First 50 rows")
            
            if st.button("⚡ Run Quick Test", type="primary"):
                st.subheader("⚡ Running Quick Test")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Initializing simulation...")
                progress_bar.progress(10)
                time.sleep(1)
                
                if PYWINCALC_AVAILABLE:
                    status_text.text("Running PyWinCalc simulation...")
                    progress_bar.progress(30)
                    
                    # Try real simulation first
                    real_results = run_real_simulation(df, limit=50)
                    
                    if real_results is not None:
                        progress_bar.progress(100)
                        status_text.text("✅ Real PyWinCalc simulation completed!")
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        result_file = f"test_simulation_results_{timestamp}.csv"
                        real_results.to_csv(result_file, index=False)
                        
                        show_detailed_results(real_results, "Quick Test Results (Real PyWinCalc)")
                    else:
                        # Fallback to mock data
                        status_text.text("Falling back to mock simulation...")
                        progress_bar.progress(70)
                        time.sleep(1)
                        
                        mock_results = create_mock_results(df, limit=50)
                        progress_bar.progress(100)
                        status_text.text("✅ Mock simulation completed!")
                        
                        show_detailed_results(mock_results, "Quick Test Results (Mock Data)")
                else:
                    status_text.text("Generating mock simulation data...")
                    progress_bar.progress(50)
                    time.sleep(1)
                    
                    mock_results = create_mock_results(df, limit=50)
                    progress_bar.progress(100)
                    status_text.text("✅ Mock simulation completed!")
                    
                    show_detailed_results(mock_results, "Quick Test Results (Mock Data)")
        
        with col2:
            st.subheader("🔥 Full Simulation")
            if PYWINCALC_AVAILABLE:
                st.warning(f"Real PyWinCalc simulation - All {len(df):,} rows (may take time)")
            else:
                st.warning(f"Mock simulation data - All {len(df):,} rows")
            
            if st.button("🔥 Run Full Simulation"):
                st.subheader("🔥 Running Full Simulation")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                if PYWINCALC_AVAILABLE:
                    status_text.text("Initializing full PyWinCalc simulation...")
                    progress_bar.progress(5)
                    time.sleep(1)
                    
                    # Try real simulation
                    real_results = run_real_simulation(df)
                    
                    if real_results is not None:
                        progress_bar.progress(100)
                        status_text.text("✅ Full PyWinCalc simulation completed!")
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        result_file = f"igu_simulation_results_{timestamp}.csv"
                        real_results.to_csv(result_file, index=False)
                        
                        show_detailed_results(real_results.head(100), "Full Simulation Results (Real PyWinCalc)")
                    else:
                        # Fallback to mock
                        mock_results = create_mock_results(df)
                        show_detailed_results(mock_results.head(100), "Full Simulation Results (Mock Data)")
                else:
                    status_text.text("Generating full mock dataset...")
                    for i in range(5, 95, 10):
                        progress_bar.progress(i)
                        time.sleep(0.5)
                    
                    mock_results = create_mock_results(df)
                    progress_bar.progress(100)
                    status_text.text("✅ Full mock simulation completed!")
                    
                    show_detailed_results(mock_results.head(100), "Full Simulation Results (Mock Data)")
        
    except FileNotFoundError:
        st.error("❌ No configurations found. Please complete Step 3 first.")

# Add other steps here (similar to workflow_app_cloud.py but with real simulation capability)

# Footer
st.divider()
st.markdown(f"""
---
**🔬 ALPENSIMULATOR Full Version** - {'Real PyWinCalc' if PYWINCALC_AVAILABLE else 'Mock'} Thermal Simulation  
**💡 PyWinCalc Status**: {'✅ Available' if PYWINCALC_AVAILABLE else '❌ Install pywincalc for real simulation'}  
**🚀 Built with Materials Science Principles** | **☁️ Deployed on Streamlit Cloud**
""")