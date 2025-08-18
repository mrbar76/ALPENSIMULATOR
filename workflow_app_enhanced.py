"""
ALPENSIMULATOR Enhanced Version - Smart Flip Management & Interactive Catalog
Features:
- Interactive flip editing in glass catalog
- Intelligent auto-flip logic based on coating properties
- Visual flip recommendations
- Easy-to-use checkbox interface
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

st.set_page_config(page_title="ALPENSIMULATOR - Enhanced", layout="wide")

# Mode indicator
if PYWINCALC_AVAILABLE:
    st.success("🔥 **ENHANCED VERSION**: Real PyWinCalc + Smart Flip Management")
else:
    st.info("📊 **ENHANCED DEMO**: Smart Flip Management + Mock Simulation")

# Smart flip logic functions
def get_coating_type(glass_name, notes=""):
    """Determine coating type from glass name and notes"""
    name_lower = glass_name.lower()
    notes_lower = notes.lower() if notes else ""
    
    if any(keyword in name_lower for keyword in ['loe', 'low-e', 'low e']):
        if any(keyword in name_lower for keyword in ['272', '277', '366', '180']):
            return 'low_e_hard'  # Hard coat Low-E
        else:
            return 'low_e_soft'  # Soft coat Low-E
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
    
    # Interactive editor
    st.subheader(f"📊 Catalog Editor ({len(filtered_df)} glasses)")
    
    # Batch operations
    st.subheader("⚡ Batch Operations")
    batch_col1, batch_col2, batch_col3 = st.columns(3)
    
    with batch_col1:
        if st.button("🤖 Apply Smart Flip Logic", help="Auto-set flips based on coating properties"):
            for idx, row in filtered_df.iterrows():
                coating_type = get_coating_type(row['Short_Name'], row.get('Notes', ''))
                
                for position in ['outer', 'quad_inner', 'center', 'inner']:
                    if row[f'Can_{position.replace("_", "").title()}']:
                        smart_flip = get_smart_flip_recommendation(
                            row['Short_Name'], position, coating_type, row.get('Notes', '')
                        )[position]
                        catalog_df.loc[catalog_df['NFRC_ID'] == row['NFRC_ID'], f'Flip_{position.replace("_", "").title()}'] = smart_flip
            
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
    
    # Individual glass editor
    st.subheader("✏️ Individual Glass Settings")
    
    for idx, row in filtered_df.iterrows():
        with st.expander(f"🔧 {row['Short_Name']} (NFRC {row['NFRC_ID']})"):
            coating_type = get_coating_type(row['Short_Name'], row.get('Notes', ''))
            
            # Show glass info
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Manufacturer", row['Manufacturer'])
            with info_col2:
                st.metric("Coating Type", coating_type.replace('_', ' ').title())
            with info_col3:
                if row.get('Notes'):
                    st.text_area("Notes", row['Notes'], height=60, disabled=True)
            
            # Position availability and flip settings
            st.write("**Position Settings:**")
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
                        rec_indicator = "🤖 Recommended" if smart_recommendation else "🤖 Not Recommended"
                        rec_color = "green" if smart_recommendation else "gray"
                        
                        st.markdown(f"**{pos_col.replace('Inner', '-Inner')}**")
                        st.markdown(f"<span style='color: {rec_color}'>{rec_indicator}</span>", unsafe_allow_html=True)
                        
                        # Flip checkbox
                        new_flip = st.checkbox(
                            f"Flip Glass",
                            value=current_flip,
                            key=f"flip_{row['NFRC_ID']}_{pos_col}",
                            help=f"Current: {'Flipped' if current_flip else 'Normal'}"
                        )
                        
                        # Update if changed
                        if new_flip != current_flip:
                            catalog_df.loc[catalog_df['NFRC_ID'] == row['NFRC_ID'], f'Flip_{pos_col}'] = new_flip
                            st.success(f"✅ {pos_col} flip updated!")
                    else:
                        st.markdown(f"**{pos_col.replace('Inner', '-Inner')}**")
                        st.markdown("❌ Not Available")
    
    # Summary statistics
    st.subheader("📈 Catalog Summary")
    summary_cols = st.columns(4)
    
    with summary_cols[0]:
        total_glasses = len(filtered_df)
        st.metric("Total Glasses", total_glasses)
    
    with summary_cols[1]:
        total_flipped = sum([
            filtered_df[f'Flip_{pos}'].sum() 
            for pos in ['Outer', 'QuadInner', 'Center', 'Inner']
        ])
        st.metric("Total Flips Set", int(total_flipped))
    
    with summary_cols[2]:
        coating_counts = filtered_df.apply(
            lambda row: get_coating_type(row['Short_Name'], row.get('Notes', '')), axis=1
        ).value_counts()
        st.metric("Coating Types", len(coating_counts))
    
    with summary_cols[3]:
        manufacturers = len(filtered_df['Manufacturer'].unique())
        st.metric("Manufacturers", manufacturers)
    
    # Coating type breakdown
    if len(coating_counts) > 0:
        st.subheader("🎯 Coating Type Breakdown")
        for coating, count in coating_counts.items():
            st.text(f"{coating.replace('_', ' ').title()}: {count} glasses")

# Initialize session state
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1

# Header
st.title("🔧 ALPENSIMULATOR - Enhanced with Smart Flip Management")
st.subheader("Materials Science Approach: Ingredients → Rules → Configuration → Simulation → Optimization")

# Progress indicator
progress_steps = [
    "1️⃣ Smart Ingredient Management",
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

# === STEP 1: ENHANCED INGREDIENT MANAGEMENT ===
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

# Add other workflow steps here (similar to previous versions)
# ... (Steps 2-5 would be similar to workflow_app_full.py)

# Footer
st.divider()
st.markdown(f"""
---
**🔬 ALPENSIMULATOR Enhanced** - {'Real PyWinCalc' if PYWINCALC_AVAILABLE else 'Mock'} + Smart Flip Management  
**🧠 Smart Features**: Intelligent coating-based flip recommendations  
**⚡ Interactive Editing**: Real-time catalog management with visual feedback  
**🚀 Built with Materials Science Principles** | **☁️ Deployed on Streamlit Cloud**
""")