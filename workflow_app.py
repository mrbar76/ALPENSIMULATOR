"""
Alpen IGU Workflow - Step-by-Step Process with Smart Flip Management

Step 1: Smart Ingredient Management (Interactive flip editing + auto-flip logic)
Step 2: Rule Configuration (Configure rules for each ingredient)  
Step 3: Generate Configurations (Run the configuration generator)
Step 4: Run Simulation (PyWinCalc simulation)
Step 5: Optimize & Filter (Select optimal glass configurations)
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import sys
import time
import os
import glob
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

try:
    from configurable_rules import AlpenRulesConfig
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

st.set_page_config(page_title="ALPENSIMULATOR - Smart Flip Management", layout="wide")

# Try to import PyWinCalc with graceful fallback
try:
    import pywincalc
    PYWINCALC_AVAILABLE = True
    st.success("✅ PyWinCalc loaded successfully - Real thermal simulation available!")
except ImportError as e:
    PYWINCALC_AVAILABLE = False
    st.warning(f"⚠️ PyWinCalc not available: {e}")
    st.info("📊 Using mock simulation data - Install PyWinCalc locally for real thermal calculations")

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

# Smart flip logic functions
def get_coating_type(glass_name, notes=""):
    """Determine coating type from glass name and notes"""
    name_lower = glass_name.lower()
    notes_lower = notes.lower() if notes else ""
    
    if any(keyword in name_lower for keyword in ['loe', 'low-e', 'low e']):
        if any(keyword in name_lower for keyword in ['272', '277', '366', '180']):
            return 'low_e_hard' if any(keyword in name_lower for keyword in ['272', '277']) else 'low_e_soft'
        else:
            return 'low_e_soft'  # Default to soft coat
    elif any(keyword in name_lower for keyword in ['i89', 'guardian']):
        return 'high_performance'
    elif 'clear' in name_lower:
        return 'clear'
    else:
        return 'unknown'

def get_smart_flip_recommendation(glass_name, position, coating_type=None, notes=""):
    """Get intelligent flip recommendation based on glass properties and position"""
    if not coating_type:
        coating_type = get_coating_type(glass_name, notes)
    
    recommendations = {
        'clear': {
            'outer': False,      # No coating, flip doesn't matter
            'quad_inner': False,
            'center': False,
            'inner': False
        },
        'low_e_hard': {  # Hard coat Low-E (like LoE 272, 277)
            'outer': True,       # Coating faces interior (surface 2)
            'quad_inner': False, # Coating faces exterior (surface 6 or 7)
            'center': False,     # Coating faces air gap
            'inner': False       # Coating faces interior (surface 3 or 5)
        },
        'low_e_soft': {  # Soft coat Low-E (like LoE 366, 180)
            'outer': True,       # Coating faces interior (surface 2) - protected position
            'quad_inner': False, # Coating faces exterior in protected position
            'center': True,      # Coating in protected air gap position
            'inner': False       # Coating faces interior (protected)
        },
        'high_performance': {  # i89, Guardian, etc.
            'outer': True,       # Usually face interior for best performance
            'quad_inner': False,
            'center': True,
            'inner': False
        }
    }
    
    return recommendations.get(coating_type, recommendations['clear'])

def create_interactive_catalog_editor():
    """Create interactive glass catalog editor with flip management"""
    st.subheader("🔧 Interactive Glass Catalog with Smart Flip Management")
    
    # Load catalog
    try:
        catalog_df = pd.read_csv("unified_glass_catalog.csv")
    except FileNotFoundError:
        st.error("❌ unified_glass_catalog.csv not found")
        return
    
    # Add smart flip recommendations
    st.info("💡 **Smart Flip Logic**: Automatically recommends optimal orientations based on coating properties")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        manufacturer_filter = st.selectbox(
            "Filter by Manufacturer",
            ["All"] + list(catalog_df['Manufacturer'].unique())
        )
    with col2:
        coating_filter = st.selectbox(
            "Filter by Coating Type",
            ["All", "Clear Glass", "Low-E Hard Coat", "Low-E Soft Coat", "High Performance"]
        )
    with col3:
        position_filter = st.selectbox(
            "Show Available for Position",
            ["All", "Outer", "Quad-Inner", "Center", "Inner"]
        )
    
    # Apply filters
    filtered_df = catalog_df.copy()
    
    if manufacturer_filter != "All":
        filtered_df = filtered_df[filtered_df['Manufacturer'] == manufacturer_filter]
    
    if coating_filter != "All":
        coating_map = {
            "Clear Glass": "clear",
            "Low-E Hard Coat": "low_e_hard", 
            "Low-E Soft Coat": "low_e_soft",
            "High Performance": "high_performance"
        }
        target_coating = coating_map[coating_filter]
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: get_coating_type(row['Short_Name'], row.get('Notes', '')) == target_coating, axis=1)
        ]
    
    if position_filter != "All":
        position_col = f"Can_{position_filter.replace('-', '')}"
        if position_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[position_col] == True]
    
    # Batch operations
    st.subheader("⚡ Batch Operations")
    batch_col1, batch_col2, batch_col3 = st.columns(3)
    
    with batch_col1:
        if st.button("🤖 Apply Smart Flip Logic", help="Auto-set flips based on coating properties"):
            for idx, row in filtered_df.iterrows():
                coating_type = get_coating_type(row['Short_Name'], row.get('Notes', ''))
                
                for position in ['outer', 'quad_inner', 'center', 'inner']:
                    pos_col = position.replace('_', '').replace('quad', 'Quad').replace('outer', 'Outer').replace('inner', 'Inner').replace('center', 'Center')
                    if row[f'Can_{pos_col}']:
                        smart_flip = get_smart_flip_recommendation(
                            row['Short_Name'], position, coating_type, row.get('Notes', '')
                        )[position]
                        catalog_df.loc[catalog_df['NFRC_ID'] == row['NFRC_ID'], f'Flip_{pos_col}'] = smart_flip
            
            catalog_df.to_csv("unified_glass_catalog.csv", index=False)
            st.success("✅ Smart flip logic applied to all filtered glasses!")
            st.rerun()
    
    with batch_col2:
        if st.button("❌ Clear All Flips", help="Set all flips to False"):
            for position in ['Outer', 'QuadInner', 'Center', 'Inner']:
                catalog_df.loc[catalog_df['NFRC_ID'].isin(filtered_df['NFRC_ID']), f'Flip_{position}'] = False
            catalog_df.to_csv("unified_glass_catalog.csv", index=False)
            st.success("✅ All flips cleared for filtered glasses!")
            st.rerun()
    
    with batch_col3:
        if st.button("💾 Save Catalog", help="Save current catalog state"):
            catalog_df.to_csv("unified_glass_catalog.csv", index=False)
            st.success("✅ Catalog saved!")
    
    # Interactive editor for individual glasses  
    st.subheader(f"✏️ Individual Glass Settings ({len(filtered_df)} glasses)")
    
    for idx, row in filtered_df.iterrows():
        with st.expander(f"🔧 {row['Short_Name']} (NFRC {row['NFRC_ID']})"):
            coating_type = get_coating_type(row['Short_Name'], row.get('Notes', ''))
            
            # Show glass info
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.metric("Manufacturer", row['Manufacturer'])
                st.metric("Coating Type", coating_type.replace('_', ' ').title())
            with info_col2:
                if row.get('Notes'):
                    st.text_area("Notes", row['Notes'], height=60, disabled=True, key=f"notes_{row['NFRC_ID']}")
            
            # Position settings with flip checkboxes
            st.write("**Position Settings with Smart Recommendations:**")
            flip_cols = st.columns(4)
            
            positions = [
                ('Outer', 'outer'),
                ('QuadInner', 'quad_inner'), 
                ('Center', 'center'),
                ('Inner', 'inner')
            ]
            
            for i, (pos_col, pos_key) in enumerate(positions):
                with flip_cols[i]:
                    can_use = row[f'Can_{pos_col}']
                    current_flip = row[f'Flip_{pos_col}']
                    
                    if can_use:
                        # Get smart recommendation
                        smart_recommendation = get_smart_flip_recommendation(
                            row['Short_Name'], pos_key, coating_type, row.get('Notes', '')
                        )[pos_key]
                        
                        # Show recommendation indicator
                        if smart_recommendation:
                            st.markdown(f"**{pos_col.replace('Inner', '-Inner')}** 🤖")
                            st.markdown("✅ **Recommended**")
                        else:
                            st.markdown(f"**{pos_col.replace('Inner', '-Inner')}**")
                            st.markdown("⭕ Not Recommended")
                        
                        # Flip checkbox
                        new_flip = st.checkbox(
                            f"Flip Glass",
                            value=current_flip,
                            key=f"flip_{row['NFRC_ID']}_{pos_col}",
                            help=f"Smart recommendation: {'FLIP' if smart_recommendation else 'NO FLIP'}"
                        )
                        
                        # Update if changed
                        if new_flip != current_flip:
                            catalog_df.loc[catalog_df['NFRC_ID'] == row['NFRC_ID'], f'Flip_{pos_col}'] = new_flip
                            catalog_df.to_csv("unified_glass_catalog.csv", index=False)
                            st.success(f"✅ {pos_col} flip updated!")
                    else:
                        st.markdown(f"**{pos_col.replace('Inner', '-Inner')}**")
                        st.markdown("❌ Not Available")

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

# Mode indicator
if PYWINCALC_AVAILABLE:
    st.success("🔥 **FULL VERSION**: Real PyWinCalc + Smart Flip Management")
else:
    st.info("📊 **ENHANCED DEMO**: Smart Flip Management + Mock Simulation")

# Header
st.title("🔧 ALPENSIMULATOR - Smart Flip Management")
st.subheader("Materials Science Approach: Smart Ingredients → Rules → Configuration → Simulation → Optimization")

# Progress indicator
progress_steps = [
    "1️⃣ Smart Ingredient Management",
    "2️⃣ Rule Configuration", 
    "3️⃣ Generate Configurations",
    "4️⃣ Run Simulation",
    "5️⃣ Optimize & Filter"
]

current_step = st.session_state.workflow_step
progress = current_step / len(progress_steps)

st.progress(progress)

col1, col2, col3, col4, col5 = st.columns(5)
for i, step in enumerate(progress_steps, 1):
    with [col1, col2, col3, col4, col5][i-1]:
        if i < current_step:
            st.success(f"✅ {step}")
        elif i == current_step:
            st.info(f"🔄 {step}")
        else:
            st.write(f"⏸️ {step}")

st.divider()

# === STEP 1: SMART INGREDIENT MANAGEMENT ===
if current_step == 1:
    st.header("1️⃣ Smart Ingredient Management")
    st.subheader("Interactive Glass Catalog with Intelligent Flip Logic")
    
    # Create the interactive catalog editor
    create_interactive_catalog_editor()
    
    st.divider()
    
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
    
    if st.button("Proceed to Step 2: Configure Rules", type="primary"):
        st.session_state.workflow_step = 2
        st.rerun()

# === STEP 2: RULE CONFIGURATION ===
elif current_step == 2:
    st.header("2️⃣ Rule Configuration")
    st.subheader("Configure Rules for Each Ingredient Type")
        
        # Load current glass catalogs
        try:
            glass_io_df = pd.read_csv('input_glass_catalog_inner_outer.csv')
            glass_center_df = pd.read_csv('input_glass_catalog_center.csv')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Inner/Outer Glass")
                st.dataframe(glass_io_df, use_container_width=True, height=250)
                
                col_add, col_remove = st.columns(2)
                
                with col_add:
                    # Add new glass
                    with st.expander("➕ Add New Inner/Outer Glass"):
                        new_position = st.selectbox("Position", ["Inner", "Outer"])
                        new_name = st.text_input("Glass Name (include thickness)", "e.g., Generic Clear 6mm")
                        new_nfrc = st.number_input("NFRC ID", min_value=1, value=1000)
                        new_manufacturer = st.text_input("Manufacturer", "Generic")
                        
                        if st.button("Add Glass"):
                            new_row = {
                                'Position': new_position,
                                'Short_Name': new_name,
                                'NFRC_ID': new_nfrc,
                                'manufacturer': new_manufacturer
                            }
                            glass_io_df = pd.concat([glass_io_df, pd.DataFrame([new_row])], ignore_index=True)
                            glass_io_df.to_csv('input_glass_catalog_inner_outer.csv', index=False)
                            st.success(f"Added {new_name} to catalog!")
                            st.rerun()
                
                with col_remove:
                    # Remove existing glass
                    with st.expander("🗑️ Remove Inner/Outer Glass"):
                        if len(glass_io_df) > 0:
                            glass_options = []
                            for idx, row in glass_io_df.iterrows():
                                glass_options.append(f"{row['Short_Name']} (NFRC {row['NFRC_ID']}) - {row['Position']}")
                            
                            selected_glass_to_remove = st.selectbox(
                                "Select glass to remove",
                                options=range(len(glass_options)),
                                format_func=lambda x: glass_options[x]
                            )
                            
                            if st.button("🗑️ Remove Selected Glass", type="secondary"):
                                removed_glass = glass_io_df.iloc[selected_glass_to_remove]
                                glass_io_df_updated = glass_io_df.drop(glass_io_df.index[selected_glass_to_remove]).reset_index(drop=True)
                                glass_io_df_updated.to_csv('input_glass_catalog_inner_outer.csv', index=False)
                                st.error(f"Removed {removed_glass['Short_Name']} from catalog!")
                                st.rerun()
                        else:
                            st.info("No glass to remove")
            
            with col2:
                st.subheader("Center Glass")
                st.dataframe(glass_center_df, use_container_width=True, height=250)
                
                col_add_center, col_remove_center = st.columns(2)
                
                with col_add_center:
                    # Add new center glass
                    with st.expander("➕ Add New Center Glass"):
                        new_center_name = st.text_input("Center Glass Name", "e.g., Generic 1.5mm Clear")
                        new_center_thickness = st.number_input("Thickness (mm)", min_value=0.1, max_value=2.0, value=1.1, step=0.1)
                        new_center_nfrc = st.number_input("Center NFRC ID", min_value=1, value=2000)
                        new_center_surfaces = st.text_input("Quad Surfaces", "2,3")
                        
                        if st.button("Add Center Glass"):
                            new_center_row = {
                                'Position': 'center',
                                'Short_Name': new_center_name,
                                'Glass_Thickness': new_center_thickness,
                                'NFRC_ID': new_center_nfrc,
                                'quads_surfaces': new_center_surfaces
                            }
                            glass_center_df = pd.concat([glass_center_df, pd.DataFrame([new_center_row])], ignore_index=True)
                            glass_center_df.to_csv('input_glass_catalog_center.csv', index=False)
                            st.success(f"Added {new_center_name} to center catalog!")
                            st.rerun()
                
                with col_remove_center:
                    # Remove existing center glass
                    with st.expander("🗑️ Remove Center Glass"):
                        if len(glass_center_df) > 0:
                            center_options = []
                            for idx, row in glass_center_df.iterrows():
                                center_options.append(f"{row['Short_Name']} (NFRC {row['NFRC_ID']}) - {row['Glass_Thickness']}mm")
                            
                            selected_center_to_remove = st.selectbox(
                                "Select center glass to remove",
                                options=range(len(center_options)),
                                format_func=lambda x: center_options[x]
                            )
                            
                            if st.button("🗑️ Remove Selected Center Glass", type="secondary"):
                                removed_center = glass_center_df.iloc[selected_center_to_remove]
                                glass_center_df_updated = glass_center_df.drop(glass_center_df.index[selected_center_to_remove]).reset_index(drop=True)
                                glass_center_df_updated.to_csv('input_glass_catalog_center.csv', index=False)
                                st.error(f"Removed {removed_center['Short_Name']} from center catalog!")
                                st.rerun()
                        else:
                            st.info("No center glass to remove")
        
        except Exception as e:
            st.error(f"Could not load glass catalogs: {e}")
    
    with tab2:
        st.subheader("Gas Fill Types")
        
        try:
            gas_df = pd.read_csv('input_gas_types.csv')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Current Gas Types")
                st.dataframe(gas_df, use_container_width=True)
                
                # Remove gas type
                with st.expander("🗑️ Remove Gas Type"):
                    if len(gas_df) > 0:
                        gas_options = gas_df['Gas Type'].tolist()
                        selected_gas_to_remove = st.selectbox(
                            "Select gas type to remove",
                            options=gas_options
                        )
                        
                        if st.button("🗑️ Remove Selected Gas Type", type="secondary"):
                            gas_df_updated = gas_df[gas_df['Gas Type'] != selected_gas_to_remove].reset_index(drop=True)
                            gas_df_updated.to_csv('input_gas_types.csv', index=False)
                            st.error(f"Removed {selected_gas_to_remove} from gas types!")
                            st.rerun()
                    else:
                        st.info("No gas types to remove")
            
            with col2:
                st.subheader("Add New Gas Type")
                new_gas = st.text_input("Gas Type", "e.g., 85K, Air, Custom")
                
                if st.button("Add Gas Type") and new_gas:
                    new_gas_row = {'Gas Type': new_gas}
                    gas_df = pd.concat([gas_df, pd.DataFrame([new_gas_row])], ignore_index=True)
                    gas_df.to_csv('input_gas_types.csv', index=False)
                    st.success(f"Added {new_gas} to gas types!")
                    st.rerun()
                
                st.subheader("Gas Properties")
                st.info("""
                **Standard Gas Types:**
                - **Air**: 1.0x cost, 0.024 W/m·K
                - **95A**: 1.1x cost, 0.016 W/m·K (95% Argon)
                - **90K**: 1.35x cost, 0.009 W/m·K (90% Krypton)
                """)
        
        except Exception as e:
            st.error(f"Could not load gas types: {e}")
    
    with tab3:
        st.subheader("Outer Airspace (OA) Sizes")
        
        try:
            oa_df = pd.read_csv('input_oa_sizes.csv')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Current OA Sizes")
                st.dataframe(oa_df, use_container_width=True)
                
                # Remove OA size
                with st.expander("🗑️ Remove OA Size"):
                    if len(oa_df) > 0:
                        oa_options = []
                        for idx, row in oa_df.iterrows():
                            oa_options.append(f"{row['OA (in)']}\" ({row['OA (mm)']:.1f}mm)")
                        
                        selected_oa_to_remove = st.selectbox(
                            "Select OA size to remove",
                            options=range(len(oa_options)),
                            format_func=lambda x: oa_options[x]
                        )
                        
                        if st.button("🗑️ Remove Selected OA Size", type="secondary"):
                            removed_oa = oa_df.iloc[selected_oa_to_remove]
                            oa_df_updated = oa_df.drop(oa_df.index[selected_oa_to_remove]).reset_index(drop=True)
                            oa_df_updated.to_csv('input_oa_sizes.csv', index=False)
                            st.error(f"Removed {removed_oa['OA (in)']}\" OA size!")
                            st.rerun()
                    else:
                        st.info("No OA sizes to remove")
            
            with col2:
                st.subheader("Add New OA Size")
                new_oa_inches = st.number_input("OA (inches)", min_value=0.1, max_value=3.0, value=1.0, step=0.125)
                new_oa_mm = new_oa_inches * 25.4
                
                st.write(f"Calculated: {new_oa_mm:.2f} mm")
                
                if st.button("Add OA Size"):
                    new_oa_row = {'OA (in)': new_oa_inches, 'OA (mm)': new_oa_mm}
                    oa_df = pd.concat([oa_df, pd.DataFrame([new_oa_row])], ignore_index=True)
                    oa_df.to_csv('input_oa_sizes.csv', index=False)
                    st.success(f"Added {new_oa_inches}\" OA size!")
                    st.rerun()
        
        except Exception as e:
            st.error(f"Could not load OA sizes: {e}")
    
    with tab4:
        st.subheader("📊 Ingredient Summary")
        
        try:
            gas_df = pd.read_csv('input_gas_types.csv')
            oa_df = pd.read_csv('input_oa_sizes.csv')
            glass_io_df = pd.read_csv('input_glass_catalog_inner_outer.csv')
            glass_center_df = pd.read_csv('input_glass_catalog_center.csv')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Gas Types", len(gas_df))
                for gas in gas_df['Gas Type'].dropna():
                    st.text(f"• {gas}")
            
            with col2:
                st.metric("OA Sizes", len(oa_df))
                st.text(f"Range: {oa_df['OA (in)'].min():.3f}\" - {oa_df['OA (in)'].max():.3f}\"")
            
            with col3:
                outer_count = len(glass_io_df[glass_io_df['Position'] == 'Outer'])
                inner_count = len(glass_io_df[glass_io_df['Position'] == 'Inner'])
                st.metric("Outer Glass", outer_count)
                st.metric("Inner Glass", inner_count)
            
            with col4:
                st.metric("Center Glass", len(glass_center_df))
            
            # Calculate potential combinations
            total_combinations = len(gas_df) * len(oa_df) * outer_count * len(glass_center_df) * inner_count
            
            st.subheader("🔢 Potential Combinations")
            st.success(f"**Triple Configurations**: ~{total_combinations:,} potential combinations")
            
            # Show ingredients are ready
            if len(gas_df) > 0 and len(oa_df) > 0 and outer_count > 0 and inner_count > 0 and len(glass_center_df) > 0:
                st.success("✅ All ingredient types present - Ready for Step 2!")
                if st.button("Proceed to Step 2: Rule Configuration", type="primary"):
                    st.session_state.workflow_step = 2
                    st.session_state.ingredients_modified = True
                    st.rerun()
            else:
                st.warning("⚠️ Missing ingredient types - Add all required ingredients first")
        
        except Exception as e:
            st.error(f"Could not load ingredient summary: {e}")

# === STEP 2: RULE CONFIGURATION ===
elif current_step == 2:
    st.header("2️⃣ Rule Configuration")
    st.subheader("Configure Rules for Each Ingredient Type")
    
    if not RULES_AVAILABLE:
        st.error("Rules system not available. Please check configurable_rules.py")
        st.stop()
    
    config = AlpenRulesConfig()
    
    # Surface Numbering Visual Guide
    st.subheader("🔢 IGU Surface Numbering Reference")
    st.info("💡 Understanding surface numbers is critical for coating placement rules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔷 Triple-Pane Surfaces")
        st.code("""
        Outdoor ←                    → Indoor
        
        [Glass 1] |gap| [Glass 2] |gap| [Glass 3]
            ↓        ↓        ↓        ↓        ↓
           S1       S2       S3      S4       S5  S6
        
        ✨ Critical Coating Surfaces:
        • S2, S5: Standard Low-E coatings
        • S4: Center glass coatings (NxLite)  
        • S6: i89 High-Performance coating ← FIXED!
        
        🔄 Flipping Rules:
        • Outer glass → targets S2
        • Center glass → targets S4
        • Inner glass → targets S6 (for i89)
        """)
    
    with col2:
        st.subheader("🔶 Quad-Pane Surfaces")
        st.code("""
        Outdoor ←                                    → Indoor
        
        [G1] |gap| [G2] |gap| [G3] |gap| [G4]
         ↓     ↓     ↓     ↓     ↓     ↓     ↓
        S1    S2    S3    S4    S5    S6   S7  S8
        
        ✨ Critical Coating Surfaces:
        • S2, S7: Standard Low-E coatings
        • S4: Quad-inner glass coatings
        • S6: Center glass coatings (NxLite)
        • S8: i89 High-Performance coating ← FIXED!
        
        🔄 Flipping Rules:
        • Outer glass → targets S2  
        • Quad-inner → targets S4
        • Center glass → targets S6
        • Inner glass → targets S8 (for i89)
        """)
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔢 Constants", "✨ Coating Rules", "🔄 Glass Flipping Rules", "🧪 Test Rules"])
    
    with tab1:
        st.subheader("Core Constants")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📏 Thickness Rules")
            
            current_tol = config.get_tolerance()
            new_tol = st.number_input("Thickness Tolerance (mm)", min_value=0.1, max_value=1.0, value=current_tol, step=0.1)
            if new_tol != current_tol and st.button("Update Tolerance"):
                config.update_rule("constants.TOL", new_tol)
                st.success("Updated!")
                st.rerun()
            
            current_min_edge = config.get_min_edge_nominal()
            new_min_edge = st.number_input("Min Edge Thickness (mm)", min_value=2.0, max_value=6.0, value=current_min_edge, step=0.5)
            if new_min_edge != current_min_edge and st.button("Update Min Edge"):
                config.update_rule("constants.MIN_EDGE_NOMINAL", new_min_edge)
                st.success("Updated!")
                st.rerun()
        
        with col2:
            st.subheader("🌀 Airspace Rules")
            
            current_min_gap = config.get_min_airgap()
            new_min_gap = st.number_input("Min Air Gap (mm)", min_value=1.0, max_value=10.0, value=current_min_gap, step=0.5)
            if new_min_gap != current_min_gap and st.button("Update Min Gap"):
                config.update_rule("constants.MIN_AIRGAP", new_min_gap)
                st.success("Updated!")
                st.rerun()
            
            current_quad_oa = config.get_quad_oa_min_inch()
            new_quad_oa = st.number_input("Quad OA Min (inches)", min_value=0.5, max_value=1.5, value=current_quad_oa, step=0.125)
            if new_quad_oa != current_quad_oa and st.button("Update Quad OA"):
                config.update_rule("constants.QUAD_OA_MIN_INCH", new_quad_oa)
                st.success("Updated!")
                st.rerun()
        
        with col3:
            st.subheader("🪟 Glass Rules")
            
            current_center_max = config.get_center_max_thickness()
            new_center_max = st.number_input("Center Glass Max (mm)", min_value=0.5, max_value=2.0, value=current_center_max, step=0.1)
            if new_center_max != current_center_max and st.button("Update Center Max"):
                config.update_rule("constants.CENTER_MAX_THICKNESS", new_center_max)
                st.success("Updated!")
                st.rerun()
    
    with tab2:
        st.subheader("Coating Placement Rules")
        st.info("🎯 **Key Fix**: i89 coating now correctly on Surface 6 (Triple) and Surface 8 (Quad)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔷 Triple Surface Map")
            triple_surfaces = config.get_surface_map('triple')
            for surface_num, description in triple_surfaces.items():
                if surface_num == 6:
                    st.success(f"**Surface {surface_num}**: {description} ← i89 coating ✅")
                elif surface_num in [2, 5]:
                    st.info(f"Surface {surface_num}: {description} ← Standard low-E")
                elif surface_num == 4:
                    st.warning(f"Surface {surface_num}: {description} ← Center coating")
                else:
                    st.text(f"Surface {surface_num}: {description}")
        
        with col2:
            st.subheader("🔶 Quad Surface Map")
            quad_surfaces = config.get_surface_map('quad')
            for surface_num, description in quad_surfaces.items():
                if surface_num == 8:
                    st.success(f"**Surface {surface_num}**: {description} ← i89 coating ✅")
                elif surface_num in [2, 7]:
                    st.info(f"Surface {surface_num}: {description} ← Standard low-E")
                elif surface_num == 6:
                    st.warning(f"Surface {surface_num}: {description} ← Center coating")
                else:
                    st.text(f"Surface {surface_num}: {description}")
        
        st.subheader("🔄 Flipping Rules for Coated Glass")
        st.info("💡 **Your Insight**: Flipping rules should work with coated glass to achieve correct surface placement")
        
        # Test flipping with coated glass
        col1, col2, col3 = st.columns(3)
        with col1:
            test_coating = st.selectbox("Coating Type", ["i89", "LoE-180", "NxLite", "Custom"])
        with col2:
            test_coating_side = st.selectbox("Current Coating Side", ["front", "back"])
        with col3:
            test_igu_type = st.selectbox("IGU Type", ["triple", "quad"])
        
        if test_coating:
            should_flip_result = config.should_flip("inner", test_coating_side, test_coating, test_igu_type)
            if should_flip_result:
                st.success(f"🔄 **FLIP GLASS** - {test_coating} coating will end up on correct surface")
            else:
                st.info(f"⏹️ **KEEP ORIENTATION** - {test_coating} coating already on correct surface")
    
    with tab3:
        st.subheader("🔄 Glass Unit Flipping Rules")
        st.info("💡 **Your Request**: Set flipping rules on specific glass units selected")
        st.warning("⚠️ **Key Insight**: Flipping rules should be applied to individual glass selections, not general rules")
        
        # Load glass data
        try:
            glass_io_df = pd.read_csv('input_glass_catalog_inner_outer.csv')
            glass_center_df = pd.read_csv('input_glass_catalog_center.csv')
            
            # Initialize glass-specific flipping rules in session state
            if 'glass_flip_rules' not in st.session_state:
                st.session_state.glass_flip_rules = {}
            
            st.subheader("🪟 Select Glass Units and Configure Flipping")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Inner/Outer Glass Units")
                
                # Create enhanced view with names + NFRC
                glass_enhanced = glass_io_df.copy()
                glass_enhanced['Display_Name'] = glass_enhanced['Short_Name'] + ' (NFRC ' + glass_enhanced['NFRC_ID'].astype(str) + ')'
                
                # Select glass and configure flipping
                selected_io_glass = st.selectbox(
                    "Select Inner/Outer Glass Unit",
                    options=glass_enhanced['NFRC_ID'].tolist(),
                    format_func=lambda x: glass_enhanced[glass_enhanced['NFRC_ID'] == x]['Display_Name'].iloc[0]
                )
                
                if selected_io_glass:
                    selected_glass_info = glass_enhanced[glass_enhanced['NFRC_ID'] == selected_io_glass].iloc[0]
                    
                    st.write(f"**Selected**: {selected_glass_info['Display_Name']}")
                    st.write(f"**Position**: {selected_glass_info['Position']}")
                    st.write(f"**Manufacturer**: {selected_glass_info['manufacturer']}")
                    
                    # Detect coating type from name
                    glass_name = selected_glass_info['Short_Name'].lower()
                    detected_coating = "none"
                    if 'i89' in glass_name:
                        detected_coating = "i89"
                    elif 'loe' in glass_name:
                        detected_coating = "loe"
                    elif 'nxlite' in glass_name:
                        detected_coating = "nxlite"
                    
                    st.write(f"**Detected Coating**: {detected_coating}")
                    
                    # Configure flipping rules for this specific glass
                    st.subheader("🔄 Flipping Configuration")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        coating_side = st.selectbox(
                            f"Coating Side (NFRC {selected_io_glass})",
                            ["front", "back", "none"],
                            key=f"coating_side_{selected_io_glass}"
                        )
                    
                    with col_b:
                        force_flip = st.selectbox(
                            f"Force Flip Rule (NFRC {selected_io_glass})",
                            ["Auto (Use Standard Rules)", "Always Flip", "Never Flip"],
                            key=f"force_flip_{selected_io_glass}"
                        )
                    
                    # Store rule for this specific glass
                    if st.button(f"Save Flipping Rule for NFRC {selected_io_glass}"):
                        st.session_state.glass_flip_rules[selected_io_glass] = {
                            'glass_name': selected_glass_info['Display_Name'],
                            'position': selected_glass_info['Position'],
                            'coating_side': coating_side,
                            'force_flip': force_flip,
                            'detected_coating': detected_coating
                        }
                        st.success(f"✅ Saved flipping rule for {selected_glass_info['Display_Name']}")
                        st.rerun()
            
            with col2:
                st.subheader("Center Glass Units")
                
                # Create enhanced view for center glass
                center_enhanced = glass_center_df.copy()
                center_enhanced['Display_Name'] = center_enhanced['Short_Name'] + ' (NFRC ' + center_enhanced['NFRC_ID'].astype(str) + ')'
                
                selected_center_glass = st.selectbox(
                    "Select Center Glass Unit",
                    options=center_enhanced['NFRC_ID'].tolist(),
                    format_func=lambda x: center_enhanced[center_enhanced['NFRC_ID'] == x]['Display_Name'].iloc[0]
                )
                
                if selected_center_glass:
                    selected_center_info = center_enhanced[center_enhanced['NFRC_ID'] == selected_center_glass].iloc[0]
                    
                    st.write(f"**Selected**: {selected_center_info['Display_Name']}")
                    st.write(f"**Thickness**: {selected_center_info['Glass_Thickness']}mm")
                    
                    # Detect coating for center glass
                    center_name = selected_center_info['Short_Name'].lower()
                    center_coating = "none"
                    if 'nxlite' in center_name:
                        center_coating = "nxlite"
                    elif 'loe' in center_name:
                        center_coating = "loe"
                    
                    st.write(f"**Detected Coating**: {center_coating}")
                    
                    # Configure center glass flipping
                    st.subheader("🔄 Center Glass Flipping")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        center_coating_side = st.selectbox(
                            f"Coating Side (Center NFRC {selected_center_glass})",
                            ["front", "back", "none"],
                            key=f"center_coating_side_{selected_center_glass}"
                        )
                    
                    with col_b:
                        center_force_flip = st.selectbox(
                            f"Force Flip Rule (Center NFRC {selected_center_glass})",
                            ["Auto (Use Standard Rules)", "Always Flip", "Never Flip"],
                            key=f"center_force_flip_{selected_center_glass}"
                        )
                    
                    # Store center glass rule
                    if st.button(f"Save Center Glass Rule for NFRC {selected_center_glass}"):
                        st.session_state.glass_flip_rules[f"center_{selected_center_glass}"] = {
                            'glass_name': selected_center_info['Display_Name'],
                            'position': 'Center',
                            'coating_side': center_coating_side,
                            'force_flip': center_force_flip,
                            'detected_coating': center_coating
                        }
                        st.success(f"✅ Saved center glass rule for {selected_center_info['Display_Name']}")
                        st.rerun()
            
            # Show all configured flipping rules
            if st.session_state.glass_flip_rules:
                st.divider()
                st.subheader("📋 Configured Glass Unit Flipping Rules")
                
                for glass_id, rule in st.session_state.glass_flip_rules.items():
                    with st.expander(f"🔧 {rule['glass_name']} - {rule['position']}"):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.write(f"**Glass**: {rule['glass_name']}")
                            st.write(f"**Position**: {rule['position']}")
                        
                        with col2:
                            st.write(f"**Coating**: {rule['detected_coating']}")
                            st.write(f"**Coating Side**: {rule['coating_side']}")
                        
                        with col3:
                            st.write(f"**Flip Rule**: {rule['force_flip']}")
                            
                            # Predict flipping behavior
                            if rule['force_flip'] == "Always Flip":
                                st.error("🔄 WILL FLIP")
                            elif rule['force_flip'] == "Never Flip":
                                st.success("⏹️ NO FLIP")
                            else:
                                # Use standard rules to predict
                                will_flip = config.should_flip(rule['position'].lower(), rule['coating_side'], rule['detected_coating'])
                                if will_flip:
                                    st.warning("🔄 AUTO FLIP")
                                else:
                                    st.info("⏹️ AUTO NO FLIP")
                        
                        with col4:
                            if st.button(f"Remove Rule", key=f"remove_{glass_id}"):
                                del st.session_state.glass_flip_rules[glass_id]
                                st.rerun()
                
                st.success(f"✅ {len(st.session_state.glass_flip_rules)} glass unit flipping rules configured!")
            else:
                st.info("ℹ️ No glass-specific flipping rules configured yet. Select glasses above to configure their flipping behavior.")
        
        except Exception as e:
            st.error(f"Could not load glass data: {e}")
    
    with tab4:
        st.subheader("Test Rule Configuration")
        
        # Sample configurations to test
        test_configs = [
            {'name': 'Valid Triple', 'igu_type': 'triple', 'glasses': [102, 107, 102, None]},
            {'name': 'Invalid Triple (Glass 4)', 'igu_type': 'triple', 'glasses': [102, 107, 102, 119]},
            {'name': 'Valid Quad', 'igu_type': 'quad', 'glasses': [102, 107, 22720, 102]},
        ]
        
        for test_config in test_configs:
            with st.expander(f"Test: {test_config['name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.json({
                        'IGU Type': test_config['igu_type'],
                        'Glass Layers': test_config['glasses']
                    })
                
                with col2:
                    is_valid, errors = config.validate_igu_configuration(
                        test_config['igu_type'],
                        test_config['glasses']
                    )
                    
                    if is_valid:
                        st.success("✅ VALID")
                    else:
                        st.error("❌ INVALID")
                        for error in errors:
                            st.write(f"• {error}")
        
        # Rules configured check
        st.subheader("✅ Configuration Complete")
        if st.button("Proceed to Step 3: Generate Configurations", type="primary"):
            st.session_state.workflow_step = 3
            st.session_state.rules_configured = True
            st.rerun()

# === STEP 3: GENERATE CONFIGURATIONS ===
elif current_step == 3:
    st.header("3️⃣ Generate IGU Configurations")
    st.subheader("Run the Configuration Generator with Your Ingredients and Rules")
    
    # IGU Structure Diagrams
    st.subheader("🏗️ IGU Structure Diagrams")
    st.info("💡 Understanding how glass layers and air gaps are calculated from Total OA")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔷 Triple-Pane IGU")
        st.code("""
        Outdoor ←                    → Indoor
        
        [Glass 1] |gap| [Glass 2] |gap| [Glass 3]
            ↑        ↑        ↑        ↑        ↑
           S1       S2       S3      S4       S5,S6
        Outer    Air Gap  Center  Air Gap   Inner
          │        │        │        │        │
          │        │        └─ ≤1.1mm         │
          │        │                          │
          └─ ≥3mm ─┴── Same air gap size ────┴─ ≥3mm
        
        🧮 Air Gap Formula:
        Gap = (Total OA - Glass₁ - Glass₂ - Glass₃) ÷ 2
        
        📊 Example: OA=22mm, Glass=[6,1.1,6]mm
        Gap = (22 - 6 - 1.1 - 6) ÷ 2 = 4.45mm each
        """)
    
    with col2:
        st.subheader("🔶 Quad-Pane IGU")  
        st.code("""
        Outdoor ←                                    → Indoor
        
        [G1] |gap| [G2] |gap| [G3] |gap| [G4]
         ↑     ↑     ↑     ↑     ↑     ↑     ↑
        S1    S2    S3    S4    S5    S6   S7,S8
        Outer  │  QuadInner │  Center  │  Inner
         │     │      │     │     │     │    │
         │     │      │     │     └─≤1.1mm   │
         │     │      └─≥3mm─┘               │
         └─≥3mm┴──── Same air gap size ─────┴─≥3mm
        
        🧮 Air Gap Formula:
        Gap = (Total OA - G₁ - G₂ - G₃ - G₄) ÷ 3
        
        📊 Example: OA=25mm, Glass=[6,6,1.1,6]mm  
        Gap = (25 - 6 - 6 - 1.1 - 6) ÷ 3 = 1.97mm each
        """)
    
    st.divider()
    
    # Show current settings
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
                gas_df = pd.read_csv('input_gas_types.csv')
                oa_df = pd.read_csv('input_oa_sizes.csv')
                glass_io_df = pd.read_csv('input_glass_catalog_inner_outer.csv')
                glass_center_df = pd.read_csv('input_glass_catalog_center.csv')
                
                outer_count = len(glass_io_df[glass_io_df['Position'] == 'Outer'])
                inner_count = len(glass_io_df[glass_io_df['Position'] == 'Inner'])
                
                triple_est = len(gas_df) * len(oa_df) * outer_count * len(glass_center_df) * inner_count
                quad_candidates = len(oa_df[oa_df['OA (in)'] > config.get_quad_oa_min_inch()])
                quad_est = len(gas_df) * quad_candidates * outer_count * len(glass_center_df) * len(glass_center_df) * inner_count
                
                st.metric("Est. Triple", f"~{triple_est:,}")
                st.metric("Est. Quad", f"~{quad_est:,}")
                
            except Exception as e:
                st.error(f"Could not estimate: {e}")
    
    # Generation controls
    st.subheader("🚀 Run Configuration Generator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚡ Fast Generation")
        st.info("Generate ~4,000 configs in 30-60 seconds for testing")
        st.metric("Max Configs", "4,000")
        st.metric("Time", "30-60s")
        
        if st.button("⚡ Fast Generate", type="primary"):
            generator_mode = "fast"
    
    with col2:
        st.subheader("🔥 Full Generation")
        st.warning("Generate all possible configs (may take 5-10 minutes)")
        st.metric("Max Configs", "All")
        st.metric("Time", "5-10 min")
        
        if st.button("🔥 Full Generate"):
            generator_mode = "full"
    
    # Run generator based on mode
    if 'generator_mode' in locals():
        if generator_mode == "fast":
            with st.spinner("⚡ Fast generating configurations..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        ["python3", "igu_input_generator_fast.py"],
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 minute timeout
                    )
                    
                    st.subheader("Fast Generation Output:")
                    st.code(result.stdout[-1000:])  # Show last 1000 chars
                    
                    if result.returncode == 0:
                        st.success("✅ Fast generation completed!")
                        # Process results below
                    else:
                        st.error("❌ Fast generation failed!")
                        st.code(result.stderr)
                        
                except Exception as e:
                    st.error(f"Fast generation failed: {e}")
        
        elif generator_mode == "full":
            with st.spinner("🔥 Full generating configurations..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        ["python3", "igu_input_generator_configurable.py"],
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 minute timeout
                    )
                    
                    st.subheader("Full Generation Output:")
                    st.code(result.stdout[-1000:])  # Show last 1000 chars
                    
                    if result.returncode == 0:
                        st.success("✅ Full generation completed!")
                        # Process results below
                    else:
                        st.error("❌ Full generation failed!")
                        st.code(result.stderr)
                        
                except Exception as e:
                    st.error(f"Full generation failed: {e}")
        
        # Process results if generation succeeded
        if 'result' in locals() and result.returncode == 0:
            # Show detailed results
            try:
                df = pd.read_csv('igu_simulation_input_table.csv')
                st.success(f"✅ Generated {len(df):,} IGU configurations")
                
                # Configuration Summary
                st.subheader("📊 Configuration Summary")
                igu_counts = df['IGU Type'].value_counts()
                gas_counts = df['Gas Type'].value_counts()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Triple Configs", f"{igu_counts.get('Triple', 0):,}")
                with col2:
                    st.metric("Quad Configs", f"{igu_counts.get('Quad', 0):,}")
                with col3:
                    st.metric("Gas Types", len(gas_counts))
                    for gas, count in gas_counts.items():
                        st.text(f"• {gas}: {count:,}")
                
                # Show sample configurations
                st.subheader("Sample Generated Configurations")
                st.dataframe(df.head(10), use_container_width=True)
                
                st.divider()
                
                # Ready for simulation
                st.session_state.configurations_generated = True
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success("🎉 Configurations ready for simulation!")
                with col2:
                    if st.button("Proceed to Step 4: Run Simulation", type="primary"):
                        st.session_state.workflow_step = 4
                        st.rerun()
                
            except Exception as e:
                st.error(f"Could not load generated configurations: {e}")
        
        # Handle generation failure
        elif 'result' in locals() and result.returncode != 0:
            st.error("Configuration generation failed!")
            st.text("Error output:")
            st.code(result.stderr)

# === STEP 4: RUN SIMULATION ===
elif current_step == 4:
    st.header("4️⃣ Run PyWinCalc Simulation")
    st.subheader("Execute Thermal and Optical Performance Simulation")
    
    # Check for configurations
    try:
        df = pd.read_csv('igu_simulation_input_table.csv')
        st.success(f"✅ Found {len(df):,} configurations ready for simulation")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Input Configurations", f"{len(df):,}")
        with col2:
            gas_types = len(df['Gas Type'].unique())
            st.metric("Gas Types", gas_types)
        
        # Sample configurations
        st.subheader("Configuration Preview")
        st.dataframe(df.head(), use_container_width=True)
        
        # Check for existing simulation results
        st.subheader("📁 Simulation Status")
        
        import glob
        result_files = glob.glob("*simulation_results*.csv")
        test_files = glob.glob("test_simulation_results_*.csv")
        
        if result_files or test_files:
            col1, col2 = st.columns(2)
            
            with col1:
                if test_files:
                    latest_test = max(test_files, key=lambda x: Path(x).stat().st_mtime)
                    test_df_results = pd.read_csv(latest_test)
                    st.success(f"✅ Quick Test Results Available")
                    st.info(f"📄 {latest_test}")
                    st.metric("Test Rows", len(test_df_results))
                    
                    if st.button("📊 View Quick Test Results"):
                        st.session_state.show_test_results = True
            
            with col2:
                if result_files:
                    full_results = [f for f in result_files if not f.startswith("test_")]
                    if full_results:
                        latest_full = max(full_results, key=lambda x: Path(x).stat().st_mtime)
                        full_df_results = pd.read_csv(latest_full)
                        st.success(f"✅ Full Simulation Results Available")
                        st.info(f"📄 {latest_full}")
                        st.metric("Total Rows", len(full_df_results))
                        
                        if st.button("📊 View Full Results"):
                            st.session_state.show_full_results = True
        
        st.divider()
        
        # Simulation controls
        st.subheader("🧪 Run New Simulation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚡ Quick Test")
            st.info("Process first 50 rows for immediate results (~30-60 seconds)")
            st.metric("Test Rows", "50")
            st.metric("Estimated Time", "30-60s")
            
            if st.button("⚡ Run Quick Test", type="primary"):
                run_simulation_mode = "quick"
        
        with col2:
            st.subheader("🔥 Full Simulation") 
            st.warning(f"Process all {len(df):,} rows (may take 10-30 minutes)")
            batch_size = st.number_input("Batch Size", min_value=100, max_value=len(df), value=len(df))
            st.metric("Total Rows", f"{batch_size:,}")
            st.metric("Estimated Time", "10-30 min")
            
            if st.button("🔥 Run Full Simulation"):
                run_simulation_mode = "full"
        
        # Run simulation based on mode
        if 'run_simulation_mode' in locals():
            if run_simulation_mode == "quick":
                st.subheader("⚡ Running Quick Test")
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("Initializing simulation...")
                    progress_bar.progress(10)
                    
                    import subprocess
                    import threading
                    import time
                    
                    # Start simulation
                    status_text.text("Starting simulation process...")
                    progress_bar.progress(20)
                    
                    result = subprocess.run(
                        ["python3", "simulation_small_test.py"],
                        capture_output=True,
                        text=True,
                        timeout=180  # 3 minute timeout
                    )
                    
                    progress_bar.progress(80)
                    status_text.text("Processing results...")
                    
                    if result.returncode == 0:
                        progress_bar.progress(100)
                        status_text.text("✅ Quick Test completed successfully!")
                        
                        st.success("✅ Quick Test completed!")
                        
                        # Look for test results file
                        import glob
                        result_files = glob.glob("test_simulation_results_*.csv")
                        if result_files:
                            latest_result = max(result_files, key=lambda x: Path(x).stat().st_mtime)
                            results_df = pd.read_csv(latest_result)
                            
                            st.success(f"📁 Test results: {latest_result}")
                            st.success(f"📊 Tested {len(results_df):,} configurations successfully")
                            
                            # Show detailed results with glass descriptions
                            show_detailed_results(results_df, "Quick Test Results")
                            
                            st.info("🎉 **Success!** Your simulation system is working correctly. Ready for full simulation.")
                            
                            # Option to run full simulation
                            if st.button("🚀 Now Run Full Simulation", type="secondary"):
                                run_simulation_mode = "full"
                                st.rerun()
                        else:
                            st.warning("No test results file found")
                        
                        # Show console output (optional)
                        with st.expander("📋 View Console Output"):
                            st.code(result.stdout[-1500:])
                    else:
                        progress_bar.progress(0)
                        status_text.text("❌ Quick Test failed!")
                        st.error("Quick Test failed!")
                        st.code(result.stderr)
                
                except Exception as e:
                    progress_bar.progress(0)
                    status_text.text(f"❌ Error: {e}")
                    st.error(f"Quick Test failed: {e}")
            
            elif run_simulation_mode == "full":
                st.subheader("🔥 Running Full Simulation")
                
                # Progress tracking for full simulation
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text(f"Initializing full simulation ({batch_size:,} rows)...")
                    progress_bar.progress(5)
                    
                    import subprocess
                    
                    status_text.text("Starting simulation process...")
                    progress_bar.progress(10)
                    
                    result = subprocess.run(
                        ["python3", "Alpen_IGU_Simulation.py"],
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minute timeout
                        input="y\\n"  # Auto-answer 'y' to process all rows
                    )
                    
                    progress_bar.progress(90)
                    status_text.text("Processing results...")
                    
                    if result.returncode == 0:
                        progress_bar.progress(100)
                        status_text.text("✅ Full simulation completed successfully!")
                        
                        st.success("✅ Full Simulation completed!")
                        
                        # Look for full results
                        import glob
                        full_results = glob.glob("igu_simulation_results_*.csv")
                        if full_results:
                            latest_result = max(full_results, key=lambda x: Path(x).stat().st_mtime)
                            results_df = pd.read_csv(latest_result)
                            
                            st.success(f"📁 Full results: {latest_result}")
                            st.success(f"📊 Simulated {len(results_df):,} configurations successfully")
                            
                            # Show detailed results
                            show_detailed_results(results_df, "Full Simulation Results")
                        else:
                            st.warning("No full simulation results file found")
                        
                        # Show console output (optional)
                        with st.expander("📋 View Console Output"):
                            st.code(result.stdout[-2000:])
                    else:
                        progress_bar.progress(0)
                        status_text.text("❌ Full simulation failed!")
                        st.error("Full Simulation failed!")
                        st.code(result.stderr)
                
                except Exception as e:
                    progress_bar.progress(0)
                    status_text.text(f"❌ Error: {e}")
                    st.error(f"Full Simulation failed: {e}")
        
        # Handle viewing existing results
        if st.session_state.get('show_test_results', False):
            st.session_state.show_test_results = False
            import glob
            test_files = glob.glob("test_simulation_results_*.csv")
            if test_files:
                latest_test = max(test_files, key=lambda x: Path(x).stat().st_mtime)
                test_df_results = pd.read_csv(latest_test)
                show_detailed_results(test_df_results, "Quick Test Results (Existing)")
        
        if st.session_state.get('show_full_results', False):
            st.session_state.show_full_results = False
            import glob
            result_files = glob.glob("*simulation_results*.csv")
            full_results = [f for f in result_files if not f.startswith("test_")]
            if full_results:
                latest_full = max(full_results, key=lambda x: Path(x).stat().st_mtime)
                full_df_results = pd.read_csv(latest_full)
                show_detailed_results(full_df_results, "Full Simulation Results (Existing)")
                with st.spinner(f"🔥 Running Full Simulation ({batch_size:,} rows)..."):
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["python3", "Alpen_IGU_Simulation.py"],
                            capture_output=True,
                            text=True,
                            timeout=1800,  # 30 minute timeout
                            input="y\\n"  # Auto-answer 'y' to process all rows
                        )
                        
                        st.subheader("Full Simulation Output:")
                        st.code(result.stdout[-2000:])  # Show last 2000 chars
                        
                        if result.returncode == 0:
                            st.success("✅ Full Simulation completed!")
                            
                            # Look for results file
                            import glob
                            result_files = glob.glob("igu_simulation_results_*.csv")
                            if result_files:
                                latest_result = max(result_files, key=lambda x: Path(x).stat().st_mtime)
                                results_df = pd.read_csv(latest_result)
                                
                                st.success(f"📁 Results saved: {latest_result}")
                                st.success(f"📊 Simulated {len(results_df):,} configurations")
                                
                                # Show sample results
                                st.subheader("📊 Full Simulation Results")
                                display_cols = ['IGU Type', 'OA (in)', 'Gas Type', 'U-Value (Btu/hr.ft2.F)', 'SHGC', 'VT']
                                available_cols = [col for col in display_cols if col in results_df.columns]
                                st.dataframe(results_df[available_cols].head(10), use_container_width=True)
                                
                                st.session_state.simulation_completed = True
                                
                                if st.button("Proceed to Step 5: Optimize & Filter", type="primary"):
                                    st.session_state.workflow_step = 5
                                    st.rerun()
                            else:
                                st.warning("No results file found")
                        else:
                            st.error("Full Simulation failed!")
                            st.code(result.stderr)
                    
                    except Exception as e:
                        st.error(f"Full Simulation failed: {e}")
    
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
    import glob
    result_files = glob.glob("igu_simulation_results_*.csv")
    
    if not result_files:
        st.error("❌ No simulation results found. Please complete Step 4 first.")
        if st.button("Return to Step 4"):
            st.session_state.workflow_step = 4
            st.rerun()
        st.stop()
    
    latest_result = max(result_files, key=lambda x: Path(x).stat().st_mtime)
    results_df = pd.read_csv(latest_result)
    
    st.success(f"📊 Loaded {len(results_df):,} simulation results from {latest_result}")
    
    # Optimization interface
    tab1, tab2, tab3 = st.tabs(["🎯 Performance Targets", "🔍 Filter Results", "📈 Optimization"])
    
    with tab1:
        st.subheader("Set Performance Targets")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("U-Value Targets")
            u_min = results_df['U-Value (Btu/hr.ft2.F)'].min()
            u_max = results_df['U-Value (Btu/hr.ft2.F)'].max()
            
            u_excellent = st.number_input("Excellent U-Value", min_value=float(u_min), max_value=float(u_max), value=0.15)
            u_target = st.number_input("Target U-Value", min_value=float(u_min), max_value=float(u_max), value=0.25)
        
        with col2:
            st.subheader("SHGC Targets")
            shgc_min = results_df['SHGC'].min()
            shgc_max = results_df['SHGC'].max()
            
            shgc_min_target = st.number_input("Min SHGC", min_value=float(shgc_min), max_value=float(shgc_max), value=float(shgc_min))
            shgc_max_target = st.number_input("Max SHGC", min_value=float(shgc_min), max_value=float(shgc_max), value=float(shgc_max))
        
        with col3:
            st.subheader("VT Targets")
            vt_min = results_df['VT'].min()
            vt_max = results_df['VT'].max()
            
            vt_min_target = st.number_input("Min VT", min_value=float(vt_min), max_value=float(vt_max), value=0.35)
    
    with tab2:
        st.subheader("Filter Results")
        
        # Apply filters
        filtered_df = results_df[
            (results_df['U-Value (Btu/hr.ft2.F)'] <= u_target) &
            (results_df['SHGC'] >= shgc_min_target) &
            (results_df['SHGC'] <= shgc_max_target) &
            (results_df['VT'] >= vt_min_target)
        ]
        
        st.success(f"✅ {len(filtered_df):,} configurations meet performance targets")
        
        if len(filtered_df) > 0:
            # Show top performers
            st.subheader("🏆 Top 10 Performers")
            top_10 = filtered_df.nsmallest(10, 'U-Value (Btu/hr.ft2.F)')
            
            display_cols = ['IGU Type', 'OA (in)', 'Gas Type', 'U-Value (Btu/hr.ft2.F)', 'SHGC', 'VT', 'IGU Name']
            st.dataframe(top_10[display_cols], use_container_width=True)
            
            # Export filtered results
            if st.button("💾 Export Filtered Results"):
                export_filename = f"filtered_results_{len(filtered_df)}_configs.csv"
                filtered_df.to_csv(export_filename, index=False)
                st.success(f"📁 Exported to {export_filename}")
        else:
            st.warning("No configurations meet the current criteria. Adjust targets.")
    
    with tab3:
        st.subheader("Multi-Objective Optimization")
        
        st.info("🎯 **Optimization Weights** - How important is each performance metric?")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            u_weight = st.slider("U-Value Weight", 0.0, 1.0, 0.4, 0.05)
        with col2:
            shgc_weight = st.slider("SHGC Weight", 0.0, 1.0, 0.3, 0.05)
        with col3:
            vt_weight = st.slider("VT Weight", 0.0, 1.0, 0.25, 0.05)
        with col4:
            cost_weight = st.slider("Cost Weight", 0.0, 1.0, 0.05, 0.05)
        
        # Normalize weights
        total_weight = u_weight + shgc_weight + vt_weight + cost_weight
        if total_weight > 0:
            u_weight /= total_weight
            shgc_weight /= total_weight
            vt_weight /= total_weight
            cost_weight /= total_weight
        
        if st.button("🚀 Run Optimization"):
            # Calculate optimization scores
            if len(filtered_df) > 0:
                # Normalize metrics (higher is better)
                u_normalized = 1 - (filtered_df['U-Value (Btu/hr.ft2.F)'] - filtered_df['U-Value (Btu/hr.ft2.F)'].min()) / (filtered_df['U-Value (Btu/hr.ft2.F)'].max() - filtered_df['U-Value (Btu/hr.ft2.F)'].min())
                shgc_normalized = (filtered_df['SHGC'] - filtered_df['SHGC'].min()) / (filtered_df['SHGC'].max() - filtered_df['SHGC'].min())
                vt_normalized = (filtered_df['VT'] - filtered_df['VT'].min()) / (filtered_df['VT'].max() - filtered_df['VT'].min())
                cost_normalized = 0.5  # Placeholder
                
                # Calculate weighted score
                optimization_score = (
                    u_weight * u_normalized +
                    shgc_weight * shgc_normalized +
                    vt_weight * vt_normalized +
                    cost_weight * cost_normalized
                )
                
                optimized_df = filtered_df.copy()
                optimized_df['Optimization_Score'] = optimization_score
                optimized_df = optimized_df.sort_values('Optimization_Score', ascending=False)
                
                st.success("🏆 Optimization Complete!")
                
                # Show top optimized results
                st.subheader("🥇 Top 10 Optimized Selections")
                top_optimized = optimized_df.head(10)
                
                display_cols = ['IGU Type', 'OA (in)', 'Gas Type', 'U-Value (Btu/hr.ft2.F)', 'SHGC', 'VT', 'Optimization_Score']
                st.dataframe(top_optimized[display_cols], use_container_width=True)
                
                # Final export
                if st.button("💾 Export Final Optimized Selections"):
                    final_filename = f"optimized_selections_top_{len(top_optimized)}.csv"
                    top_optimized.to_csv(final_filename, index=False)
                    st.success(f"🎉 Final selections exported to {final_filename}")
                    
                    st.balloons()
                    st.success("🎉 **WORKFLOW COMPLETE!** Your optimized IGU selections are ready!")

# Navigation
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if current_step > 1:
        if st.button("⬅️ Previous Step"):
            st.session_state.workflow_step -= 1
            st.rerun()

with col2:
    st.write(f"**Step {current_step} of {len(progress_steps)}**")

with col3:
    if current_step < len(progress_steps):
        # Only allow next step if current step is completed
        can_proceed = False
        if current_step == 1 and st.session_state.ingredients_modified:
            can_proceed = True
        elif current_step == 2 and st.session_state.rules_configured:
            can_proceed = True
        elif current_step == 3 and st.session_state.configurations_generated:
            can_proceed = True
        elif current_step == 4 and st.session_state.simulation_completed:
            can_proceed = True
        
        if can_proceed:
            if st.button("Next Step ➡️"):
                st.session_state.workflow_step += 1
                st.rerun()

st.caption("🔧 Alpen IGU Workflow System - Step-by-step materials science approach")