"""
ALPENSIMULATOR Cloud Version - Full workflow without PyWinCalc
All features work except thermal simulation (shows mock results)
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

try:
    from configurable_rules import AlpenRulesConfig
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

st.set_page_config(page_title="ALPENSIMULATOR - Cloud Version", layout="wide")

# Cloud mode indicator
st.info("☁️ **CLOUD VERSION**: Full workflow with mock simulation results (PyWinCalc requires local installation)")

# Helper functions from workflow_app.py
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
    
    # Add available columns
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

# Initialize session state for workflow tracking
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1

if 'ingredients_modified' not in st.session_state:
    st.session_state.ingredients_modified = False

if 'rules_configured' not in st.session_state:
    st.session_state.rules_configured = False

if 'configurations_generated' not in st.session_state:
    st.session_state.configurations_generated = False

if 'simulation_completed' not in st.session_state:
    st.session_state.simulation_completed = False

# Header
st.title("🔧 ALPENSIMULATOR - Cloud Version")
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
    
    # Show other input files
    st.subheader("📁 Additional Input Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            gas_df = pd.read_csv("input_gas_types.csv")
            st.subheader("⛽ Gas Types")
            st.dataframe(gas_df, use_container_width=True)
        except FileNotFoundError:
            st.error("❌ Gas types file not found")
    
    with col2:
        try:
            oa_df = pd.read_csv("input_oa_sizes.csv")
            st.subheader("📏 OA Sizes")
            st.dataframe(oa_df, use_container_width=True)
        except FileNotFoundError:
            st.error("❌ OA sizes file not found")
    
    st.session_state.ingredients_modified = True
    
    if st.button("Proceed to Step 2: Configure Rules", type="primary"):
        st.session_state.workflow_step = 2
        st.rerun()

# === STEP 2: RULE CONFIGURATION ===
elif current_step == 2:
    st.header("2️⃣ Rule Configuration")
    st.subheader("Configure Rules for Each Ingredient")
    
    if RULES_AVAILABLE:
        config = AlpenRulesConfig()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📊 Current Rules")
            st.metric("Tolerance", f"{config.get_tolerance()}mm")
            st.metric("Min Edge", f"{config.get_min_edge_nominal()}mm")
            st.metric("Min Air Gap", f"{config.get_min_airgap()}mm")
        
        with col2:
            st.subheader("✨ Coating Rules")
            st.text(f"Triple i89: Surface {config.get_i89_surface('triple')}")
            st.text(f"Quad i89: Surface {config.get_i89_surface('quad')}")
            st.text(f"Triple Low-E: {config.get_standard_lowe_surfaces('triple')}")
            st.text(f"Quad Low-E: {config.get_standard_lowe_surfaces('quad')}")
        
        with col3:
            st.subheader("🔢 Expected Output")
            try:
                oa_df = pd.read_csv("input_oa_sizes.csv")
                gas_df = pd.read_csv("input_gas_types.csv")
                glass_df = pd.read_csv("unified_glass_catalog.csv")
                
                outer_count = len(glass_df[glass_df['Can_Outer'] == True])
                center_count = len(glass_df[glass_df['Can_Center'] == True])
                inner_count = len(glass_df[glass_df['Can_Inner'] == True])
                
                approx_configs = len(oa_df) * len(gas_df) * outer_count * center_count * inner_count
                st.metric("Approx Configs", f"{approx_configs:,}")
                st.metric("Gas Types", len(gas_df))
                st.metric("OA Sizes", len(oa_df))
                
            except:
                st.warning("Cannot estimate - input files missing")
    
    else:
        st.error("❌ Configurable rules system not available")
    
    st.session_state.rules_configured = True
    
    if st.button("Proceed to Step 3: Generate Configurations", type="primary"):
        st.session_state.workflow_step = 3
        st.rerun()

# === STEP 3: GENERATE CONFIGURATIONS ===
elif current_step == 3:
    st.header("3️⃣ Generate IGU Configurations")
    st.subheader("Run Configuration Generators")
    
    # Check for existing configurations
    config_file = "igu_simulation_input_table.csv"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚡ Fast Generate")
        st.info("Limited to 2,000 configs per type for quick testing")
        
        if st.button("⚡ Run Fast Generator", type="primary"):
            with st.spinner("Running unified fast generator..."):
                try:
                    # Simulate running the generator
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)
                    
                    # Create mock results
                    mock_results = pd.DataFrame({
                        'IGU Type': ['Triple'] * 2000 + ['Quad'] * 2000,
                        'OA (in)': [0.88, 1.0] * 2000,
                        'Gas Type': ['90K', '95A'] * 2000,
                        'Glass 1 NFRC ID': [102, 103] * 2000,
                        'Glass 2 NFRC ID': [107] * 2000 + [102, 103] * 1000,
                        'Glass 3 NFRC ID': [102, 103] * 2000,
                        'Glass 4 NFRC ID': [''] * 2000 + [102, 103] * 1000,
                        'Air Gap (mm)': [7.51, 4.84] * 1000 + [3.99, 3.1] * 1000
                    })
                    
                    mock_results.to_csv(config_file, index=False)
                    st.success("✅ Generated 4,000 configurations (2K Triple + 2K Quad)")
                    st.session_state.configurations_generated = True
                    
                except Exception as e:
                    st.error(f"Generation failed: {e}")
    
    with col2:
        st.subheader("🔥 Full Generate")  
        st.warning("Generates unlimited configurations (may take longer)")
        
        if st.button("🔥 Run Full Generator"):
            with st.spinner("Running full generator..."):
                try:
                    # Simulate longer process
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.02)
                        progress_bar.progress(i + 1)
                    
                    # Create larger mock dataset
                    mock_results = pd.DataFrame({
                        'IGU Type': ['Triple'] * 10000 + ['Quad'] * 10000,
                        'OA (in)': [0.88, 1.0, 1.25] * 6667,
                        'Gas Type': ['90K', '95A'] * 10000,
                        'Glass 1 NFRC ID': [102, 103, 119, 120] * 5000,
                        'Glass 2 NFRC ID': [107, 22501, 22720] * 6667,
                        'Glass 3 NFRC ID': [102, 103, 119, 120] * 5000,
                        'Glass 4 NFRC ID': [''] * 10000 + [102, 103] * 5000,
                        'Air Gap (mm)': [7.51, 4.84, 5.2] * 6667
                    })
                    
                    mock_results.to_csv(config_file, index=False)
                    st.success("✅ Generated 20,000 configurations (10K Triple + 10K Quad)")
                    st.session_state.configurations_generated = True
                    
                except Exception as e:
                    st.error(f"Generation failed: {e}")
    
    # Show existing configurations if available
    try:
        if os.path.exists(config_file):
            df = pd.read_csv(config_file)
            st.success(f"✅ Found existing configurations: {len(df):,} total")
            
            # Summary statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Input Configurations", f"{len(df):,}")
            with col2:
                gas_types = len(df['Gas Type'].unique())
                st.metric("Gas Types", gas_types)
            
            # Sample configurations
            st.subheader("Configuration Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("Proceed to Step 4: Run Simulation", type="primary"):
                st.session_state.workflow_step = 4
                st.rerun()
        
    except FileNotFoundError:
        st.error("❌ No configurations found. Please run a generator first.")

# === STEP 4: RUN SIMULATION ===
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
            st.info("Process first 50 rows (~30-60 seconds)")
            
            if st.button("⚡ Run Quick Test", type="primary"):
                st.subheader("⚡ Running Quick Test")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate thermal simulation
                status_text.text("Initializing simulation...")
                progress_bar.progress(10)
                time.sleep(1)
                
                status_text.text("Processing configurations...")
                progress_bar.progress(50)
                time.sleep(2)
                
                status_text.text("Calculating thermal performance...")
                progress_bar.progress(80)
                time.sleep(1)
                
                progress_bar.progress(100)
                status_text.text("✅ Quick Test completed successfully!")
                
                # Create mock simulation results
                import numpy as np
                np.random.seed(42)
                
                test_sample = df.head(50).copy()
                test_sample['U_Value_IP'] = np.random.uniform(0.15, 0.35, 50)
                test_sample['SHGC'] = np.random.uniform(0.3, 0.8, 50)
                test_sample['VT'] = np.random.uniform(0.5, 0.9, 50)
                
                # Save mock results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = f"test_simulation_results_{timestamp}.csv"
                test_sample.to_csv(result_file, index=False)
                
                st.success("✅ Quick Test completed!")
                show_detailed_results(test_sample, "Quick Test Results (Mock Data)")
        
        with col2:
            st.subheader("🔥 Full Simulation")
            st.warning(f"Process all {len(df):,} rows (cloud version uses mock data)")
            
            if st.button("🔥 Run Full Simulation"):
                st.subheader("🔥 Running Full Simulation")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate longer process
                status_text.text("Initializing full simulation...")
                progress_bar.progress(5)
                time.sleep(2)
                
                status_text.text("Processing thermal calculations...")
                for i in range(5, 95, 10):
                    progress_bar.progress(i)
                    time.sleep(1)
                
                progress_bar.progress(100)
                status_text.text("✅ Full simulation completed successfully!")
                
                # Create mock full results
                import numpy as np
                np.random.seed(42)
                
                full_sample = df.copy()
                full_sample['U_Value_IP'] = np.random.uniform(0.15, 0.35, len(df))
                full_sample['SHGC'] = np.random.uniform(0.3, 0.8, len(df))
                full_sample['VT'] = np.random.uniform(0.5, 0.9, len(df))
                
                # Save mock results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = f"igu_simulation_results_{timestamp}.csv"
                full_sample.to_csv(result_file, index=False)
                
                st.success("✅ Full Simulation completed!")
                show_detailed_results(full_sample.head(100), "Full Simulation Results (Mock Data)")
                st.session_state.simulation_completed = True
        
    except FileNotFoundError:
        st.error("❌ No configurations found. Please complete Step 3 first.")
        if st.button("Return to Step 3"):
            st.session_state.workflow_step = 3
            st.rerun()

# === STEP 5: OPTIMIZE & FILTER ===
elif current_step == 5:
    st.header("5️⃣ Optimize & Filter Glass Selections")
    st.subheader("Select Optimal IGU Configurations Based on Performance Criteria")
    
    # Look for simulation results
    result_files = glob.glob("*simulation_results*.csv")
    
    if not result_files:
        st.error("❌ No simulation results found. Please complete Step 4 first.")
        if st.button("Return to Step 4"):
            st.session_state.workflow_step = 4
            st.rerun()
    else:
        # Load latest results
        latest_result = max(result_files, key=lambda x: Path(x).stat().st_mtime)
        results_df = pd.read_csv(latest_result)
        
        st.success(f"📁 Loaded results: {latest_result}")
        st.success(f"📊 Total configurations: {len(results_df):,}")
        
        # Performance filtering
        st.subheader("🎯 Performance Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            u_value_max = st.slider("Max U-Value (IP)", 0.1, 0.5, 0.3, 0.01)
            filtered_df = results_df[results_df['U_Value_IP'] <= u_value_max]
        
        with col2:
            shgc_min = st.slider("Min SHGC", 0.2, 0.9, 0.4, 0.05)
            filtered_df = filtered_df[filtered_df['SHGC'] >= shgc_min]
        
        with col3:
            vt_min = st.slider("Min VT", 0.3, 0.9, 0.5, 0.05)
            filtered_df = filtered_df[filtered_df['VT'] >= vt_min]
        
        st.success(f"🎯 Filtered to {len(filtered_df):,} configurations")
        
        # Show filtered results
        if len(filtered_df) > 0:
            show_detailed_results(filtered_df, "Optimized Results")
            
            # Top performers
            st.subheader("🏆 Top Performers")
            top_performers = filtered_df.nsmallest(10, 'U_Value_IP')
            show_detailed_results(top_performers, "Top 10 by U-Value")
        else:
            st.warning("No configurations meet the current filter criteria.")

# Footer
st.divider()
st.markdown("""
---
**🔬 ALPENSIMULATOR Cloud Version** - Full workflow demonstration  
**💡 For local PyWinCalc simulation**: `pip install pywincalc` and run `streamlit run workflow_app.py`  
**🚀 Built with Materials Science Principles** | **☁️ Deployed on Streamlit Cloud**
""")