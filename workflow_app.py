"""
ALPENSIMULATOR - Clean Workflow Integration
Strings together all working components in a structured 5-step workflow
"""

import streamlit as st
import pandas as pd
import os
import glob
import subprocess
import sys
from datetime import datetime

# Page configuration
st.set_page_config(page_title="ALPENSIMULATOR - Complete Workflow", layout="wide")

# Initialize session state
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1

st.title("🏔️ ALPENSIMULATOR - Complete IGU Workflow")
st.markdown("**End-to-end IGU analysis: From catalog management to performance optimization**")
st.caption("🔄 Updated with enhanced coating analysis and compatibility fixes")

# Debug info
try:
    import streamlit
    st.caption(f"Running Streamlit {streamlit.__version__}")
except:
    pass

# Progress indicator
progress_steps = [
    "1️⃣ Glass Catalog Management",
    "2️⃣ Generation Rules & Configuration", 
    "3️⃣ Generate IGU Configurations",
    "4️⃣ Run Thermal Simulation",
    "5️⃣ Optimize & Filter Results"
]

current_step = st.session_state.workflow_step
cols = st.columns(len(progress_steps))
for i, (col, step) in enumerate(zip(cols, progress_steps)):
    with col:
        if i + 1 <= current_step:
            st.success(step)
        elif i + 1 == current_step:
            st.info(step)
        else:
            st.write(step)

st.divider()

# === STEP 1: GLASS CATALOG MANAGEMENT ===
if current_step == 1:
    st.header("1️⃣ Glass Catalog Management")
    st.subheader("Manage your glass catalog and position capabilities")
    
    # Load existing catalog (enhanced version with coating info)
    catalog_file = "unified_glass_catalog_enhanced.csv"
    backup_catalog = "unified_glass_catalog.csv"
    
    try:
        with st.spinner("Loading glass catalog..."):
            catalog_df = pd.read_csv(catalog_file)
        st.success(f"✅ Loaded {len(catalog_df)} glass types from enhanced catalog with coating information")
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            outer_count = len(catalog_df[catalog_df['Can_Outer'] == True])
            st.metric("Outer Capable", outer_count)
        with col2:
            center_count = len(catalog_df[catalog_df['Can_Center'] == True]) 
            st.metric("Center Capable", center_count)
        with col3:
            inner_count = len(catalog_df[catalog_df['Can_Inner'] == True])
            st.metric("Inner Capable", inner_count)
        with col4:
            quad_inner_count = len(catalog_df[catalog_df['Can_QuadInner'] == True])
            st.metric("Quad Inner Capable", quad_inner_count)
        with col5:
            coated_count = len(catalog_df[catalog_df['Coating_Side'].isin(['front', 'back'])])
            st.metric("Coated Glass", coated_count)
        
        # IGU Surface Diagrams
        with st.expander("🔍 IGU Surface Reference", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Triple-Pane IGU Surfaces:**")
                st.text("""
        Outside ←                    → Inside
        
        Glass 1    Air Gap    Glass 2    Air Gap    Glass 3
        ┌─────┐               ┌─────┐               ┌─────┐
        │  1  │ 2           3 │  4  │ 5           6 │  7  │
        └─────┘               └─────┘               └─────┘
        Outer                 Center                Inner
        
        • Surface 2: Standard low-E (outer glass back)
        • Surface 4: Center coatings (center glass back) 
        • Surface 5: Inner low-E (inner glass front)
                """)
            
            with col2:
                st.markdown("**Quad-Pane IGU Surfaces:**")
                st.text("""
        Outside ←                                          → Inside
        
        Glass 1  Gap  Glass 2  Gap  Glass 3  Gap  Glass 4
        ┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐
        │  1  │ 2 3 │  4  │ 5 6 │  7  │ 8 9 │ 10  │
        └─────┘     └─────┘     └─────┘     └─────┘
        Outer      Quad-Inner   Center      Inner
        
        • Surface 2: Standard low-E (outer glass back)
        • Surface 6: Center coatings (center glass back)
        • Surface 8: Inner low-E (inner glass front)
                """)
            
            st.info("💡 **Coating Side Logic:** 'Front' = faces inside, 'Back' = faces outside. Flipping changes which surface the coating ends up on.")
        
        # Coating side distribution
        with st.expander("🎨 Coating Information Summary", expanded=False):
            if 'Coating_Side' in catalog_df.columns and len(catalog_df) > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    try:
                        coating_summary = catalog_df['Coating_Side'].value_counts()
                        st.write("**Coating Side Distribution:**")
                        for side, count in coating_summary.items():
                            st.write(f"• {side}: {count}")
                    except Exception as e:
                        st.write("**Coating Side Distribution:** Error loading data")
                with col2:
                    if 'Coating_Name' in catalog_df.columns:
                        try:
                            coating_names = catalog_df[catalog_df['Coating_Name'].notna() & (catalog_df['Coating_Name'] != 'N/A')]['Coating_Name'].value_counts()
                            st.write("**Top Coating Types:**")
                            for name, count in coating_names.head(5).items():
                                st.write(f"• {name}: {count}")
                        except Exception as e:
                            st.write("**Top Coating Types:** Error loading data")
                with col3:
                    if 'Emissivity' in catalog_df.columns:
                        try:
                            coated_glass = catalog_df[catalog_df['Coating_Side'].isin(['front', 'back'])]
                            if len(coated_glass) > 0:
                                avg_emissivity = coated_glass['Emissivity'].mean()
                                st.metric("Avg Coated Emissivity", f"{avg_emissivity:.3f}")
                            clear_glass = catalog_df[catalog_df['Coating_Side'] == 'neither']
                            if len(clear_glass) > 0:
                                clear_emissivity = clear_glass['Emissivity'].iloc[0]
                                st.metric("Clear Glass Emissivity", f"{clear_emissivity:.3f}")
                        except Exception as e:
                            st.write("**Emissivity Data:** Error loading data")
        
        st.markdown("""
        **🔄 Flip Logic Guide:**
        - **Back-coated glass** in outer position: Usually flipped to put coating on surface 2
        - **Front-coated glass** in inner position: Usually flipped to put coating on surface 5/7  
        - **Center glass**: Depends on coating type and IGU configuration
        - **Clear glass**: No flipping needed (no coating to position)
        """)
        
        # Catalog editor
        st.subheader("📝 Catalog Editor")
        st.info("Edit position capabilities and flip logic for each glass type")
        
        # Build column config dynamically based on available columns
        column_config = {
            "Can_Outer": st.column_config.CheckboxColumn("Can be Outer"),
            "Can_QuadInner": st.column_config.CheckboxColumn("Can be Quad Inner"),  
            "Can_Center": st.column_config.CheckboxColumn("Can be Center"),
            "Can_Inner": st.column_config.CheckboxColumn("Can be Inner"),
            "Flip_Outer": st.column_config.CheckboxColumn("Flip when Outer"),
            "Flip_QuadInner": st.column_config.CheckboxColumn("Flip when Quad Inner"),
            "Flip_Center": st.column_config.CheckboxColumn("Flip when Center"), 
            "Flip_Inner": st.column_config.CheckboxColumn("Flip when Inner")
        }
        
        # Add enhanced columns if they exist (using try-catch for compatibility)
        try:
            if 'Coating_Side' in catalog_df.columns:
                column_config["Coating_Side"] = st.column_config.TextColumn("Coating Side", 
                    help="Which side the coating is on (front/back/neither)")
            if 'Coating_Name' in catalog_df.columns:
                column_config["Coating_Name"] = st.column_config.TextColumn("Coating Name", 
                    help="Name of the coating from IGSDB")
            if 'Emissivity' in catalog_df.columns:
                column_config["Emissivity"] = st.column_config.NumberColumn("Emissivity", 
                    format="%.3f", help="Emissivity value from IGSDB")
            if 'IGSDB_Status' in catalog_df.columns:
                column_config["IGSDB_Status"] = st.column_config.TextColumn("IGSDB Status", 
                    help="Status of IGSDB data retrieval")
        except AttributeError:
            # Fallback for older Streamlit versions - just show basic columns
            st.info("💡 Enhanced coating information columns available - may require newer Streamlit version")
        
        # Use data editor with simplified config for maximum compatibility
        try:
            edited_df = st.data_editor(
                catalog_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config=column_config
            )
        except Exception as e:
            st.warning(f"⚠️ Column configuration error, using basic editor. Error: {str(e)}")
            # Fallback to basic data editor without custom column config
            edited_df = st.data_editor(
                catalog_df,
                use_container_width=True,
                num_rows="dynamic"
            )
        
        # Save changes
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Catalog Changes", type="primary"):
                edited_df.to_csv(catalog_file, index=False)
                st.session_state.catalog_df = edited_df
                st.success("✅ Catalog saved successfully!")
                st.rerun()
        
        with col2:
            if st.button("➡️ Proceed to Step 2", type="primary"):
                st.session_state.catalog_df = edited_df
                st.session_state.workflow_step = 2
                st.rerun()
                
    except FileNotFoundError:
        # Try backup catalog
        try:
            catalog_df = pd.read_csv(backup_catalog)
            st.warning(f"⚠️ Enhanced catalog not found, using backup: {backup_catalog}")
            st.info("Run 'enhance_catalog_with_coating_info.py' to add coating information")
        except FileNotFoundError:
            st.error(f"❌ No catalog files found!")
            st.info("Please ensure unified_glass_catalog.csv exists in the project directory")

# === STEP 2: GENERATION RULES ===
elif current_step == 2:
    st.header("2️⃣ Generation Rules & Configuration") 
    st.subheader("Built-in manufacturing and physics rules")
    
    st.success("✅ **Using proven rules from the original generator**")
    
    # Display the built-in rules from the original generator
    st.info("""
    **🔧 Manufacturing Constraints:**
    • Edge glass minimum thickness: 3.0mm
    • Center glass maximum thickness: 1.1mm (for tight fit)
    • Thickness tolerance between outer/inner: ±0.3mm
    • Minimum air gap: 3.0mm
    
    **🏭 Manufacturer Compatibility:**
    • Outer and inner glass must be from same manufacturer OR one can be "Generic"
    • Ensures structural and warranty compatibility
    
    **⚗️ Physics & Performance:**
    • Air gap = (OA - total glass thickness) ÷ number of gaps
    • Air gap constrained by available spacer sizes (6-20mm)
    • Coating placement validated (inner ≤ outer emissivity)
    • Position constraints enforced (quad-inner thickness limits)
    • Low-E coating ordering rules applied
    
    **📏 Standard Specifications:**
    • OA sizes: 0.88", 1.0", 1.25"
    • Gas types: 90K, 95A argon fills
    • Spacer thickness: 6mm minimum, 20mm maximum (structural frame)
    • Air gap: Calculated physics-based space between glass panes
    • Surface coatings: Proper placement validation
    """)
    
    # Show configuration constants
    st.subheader("📊 Current Configuration Constants")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Configs per Type", "2,000", help="Limits generation for performance")
        st.metric("Min Edge Thickness", "3.0mm", help="Manufacturing constraint")
    with col2:
        st.metric("Max Center Thickness", "1.1mm", help="Tight fit requirement") 
        st.metric("Thickness Tolerance", "±0.3mm", help="Outer/inner matching")
    with col3:
        st.metric("Spacer Range", "6-20mm", help="Available spacer sizes that create air gaps")
        st.metric("Min Air Gap", "6.0mm", help="Determined by minimum spacer size")
    
    # Configuration file status
    st.subheader("🗂️ Configuration Files")
    
    required_files = [
        ("unified_glass_catalog.csv", "Glass catalog with position capabilities"),
        ("input_oa_sizes.csv", "Standard OA sizes"),
        ("input_gas_types.csv", "Available gas fill types")
    ]
    
    all_present = True
    for filename, description in required_files:
        if os.path.exists(filename):
            st.success(f"✅ {filename} - {description}")
        else:
            st.error(f"❌ {filename} - {description}")
            all_present = False
    
    if not all_present:
        st.warning("⚠️ Some configuration files are missing. Generation may use defaults.")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Step 1"):
            st.session_state.workflow_step = 1
            st.rerun()
    with col2:
        if st.button("➡️ Proceed to Step 3", type="primary"):
            st.session_state.workflow_step = 3
            st.rerun()

# === STEP 3: GENERATE CONFIGURATIONS ===
elif current_step == 3:
    st.header("3️⃣ Generate IGU Configurations")
    st.subheader("Run the unified configuration generator")
    
    # Check for unified generator
    generator_file = "igu_input_generator_unified.py"
    
    if os.path.exists(generator_file):
        st.success(f"✅ Found unified generator: {generator_file}")
        
        # Generator controls
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🚀 Run Configuration Generator")
            
            st.info("**Generator will create ALL valid configurations like the original configurator**")
            
            if st.button("🚀 Generate Configurations", type="primary"):
                with st.spinner("Running unified configuration generator..."):
                    
                    # Show progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Import and run the unified generator
                        sys.path.append('.')
                        from igu_input_generator_unified import generate_unified_configs
                        
                        # Update progress
                        progress_bar.progress(20)
                        status_text.text("Loading glass catalog...")
                        
                        # Run generator
                        progress_bar.progress(40)
                        status_text.text("Generating configurations...")
                        
                        result_df = generate_unified_configs()
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Generation complete!")
                        
                        if len(result_df) > 0:
                            st.success(f"✅ Generated {len(result_df):,} valid configurations")
                            
                            # Show breakdown
                            triples = len(result_df[result_df['IGU Type'] == 'Triple'])
                            quads = len(result_df[result_df['IGU Type'] == 'Quad'])
                            st.info(f"📊 **Breakdown:** {triples:,} Triples, {quads:,} Quads")
                            
                            # Show preview
                            st.subheader("Configuration Preview")
                            st.dataframe(result_df.head(), use_container_width=True)
                            
                        else:
                            st.warning("⚠️ No valid configurations generated. Check your rules and glass catalog.")
                        
                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        st.info("Make sure all required files are present and properly configured")
        
        with col2:
            st.subheader("ℹ️ Generator Info")
            st.info("**Features:**")
            st.write("• Real IGSDB thickness data")
            st.write("• Physics-based air gap calculation") 
            st.write("• Manufacturing constraints")
            st.write("• Position capability filtering")
            st.write("• Rule validation")
    
    else:
        st.error(f"❌ Generator file not found: {generator_file}")
        st.info("Please ensure the unified generator exists")
    
    # Check for existing results
    config_file = "igu_simulation_input_table.csv"
    if os.path.exists(config_file):
        df = pd.read_csv(config_file)
        st.success(f"✅ Found existing configurations: {len(df):,} entries")
        
        # Show preview
        st.subheader("Existing Configurations")
        st.dataframe(df.head(), use_container_width=True)
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Step 2"):
            st.session_state.workflow_step = 2
            st.rerun()
    with col2:
        if st.button("➡️ Proceed to Step 4", type="primary"):
            if os.path.exists(config_file):
                st.session_state.workflow_step = 4
                st.rerun()
            else:
                st.error("❌ No configurations found. Please run the generator first.")

# === STEP 4: RUN SIMULATION ===
elif current_step == 4:
    st.header("4️⃣ Run Thermal Simulation")
    st.subheader("Execute thermal performance analysis")
    
    # Check for simulation script
    simulation_file = "Alpen_IGU_Simulation.py"
    config_file = "igu_simulation_input_table.csv"
    
    if not os.path.exists(config_file):
        st.error("❌ No configuration file found. Please complete Step 3 first.")
    elif not os.path.exists(simulation_file):
        st.error(f"❌ Simulation script not found: {simulation_file}")
    else:
        # Load configurations
        df = pd.read_csv(config_file)
        st.success(f"✅ Loaded {len(df):,} configurations for simulation")
        
        # Simulation controls
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚡ Quick Simulation")
            st.info("Process subset for testing")
            
            quick_limit = st.number_input("Number of configurations", min_value=10, max_value=100, value=50)
            
            if st.button("⚡ Run Quick Simulation", type="primary"):
                with st.spinner("Running thermal simulation..."):
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Create limited input file
                        quick_df = df.head(quick_limit)
                        quick_file = "igu_simulation_input_quick.csv"
                        quick_df.to_csv(quick_file, index=False)
                        
                        progress_bar.progress(20)
                        status_text.text("Preparing simulation...")
                        
                        # Run simulation as subprocess
                        result = subprocess.run([
                            sys.executable, simulation_file, "--input", quick_file
                        ], capture_output=True, text=True, timeout=300)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Simulation complete!")
                        
                        if result.returncode == 0:
                            st.success(f"✅ Quick simulation completed successfully!")
                            
                            # Look for results
                            result_files = glob.glob("*results*quick*.csv")
                            if result_files:
                                results_df = pd.read_csv(result_files[0])
                                st.success(f"📊 Generated {len(results_df)} thermal performance results")
                                st.dataframe(results_df.head(), use_container_width=True)
                        else:
                            st.error(f"❌ Simulation failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        st.error("❌ Simulation timed out (5 minutes)")
                    except Exception as e:
                        st.error(f"❌ Simulation error: {str(e)}")
        
        with col2:
            st.subheader("🔥 Full Simulation")
            st.warning("Process all configurations")
            
            if st.button("🔥 Run Full Simulation"):
                with st.spinner("Running full thermal simulation..."):
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        progress_bar.progress(10)
                        status_text.text("Starting full simulation...")
                        
                        # Run full simulation
                        result = subprocess.run([
                            sys.executable, simulation_file
                        ], capture_output=True, text=True, timeout=1800)  # 30 minutes
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Full simulation complete!")
                        
                        if result.returncode == 0:
                            st.success(f"✅ Full simulation completed successfully!")
                            
                            # Look for results
                            result_files = glob.glob("*results*.csv")
                            if result_files:
                                results_df = pd.read_csv(result_files[-1])  # Latest file
                                st.success(f"📊 Generated {len(results_df)} thermal performance results")
                                st.dataframe(results_df.head(), use_container_width=True)
                        else:
                            st.error(f"❌ Full simulation failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        st.error("❌ Full simulation timed out (30 minutes)")
                    except Exception as e:
                        st.error(f"❌ Simulation error: {str(e)}")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Step 3"):
            st.session_state.workflow_step = 3
            st.rerun()
    with col2:
        # Check for simulation results
        result_files = glob.glob("*results*.csv")
        if result_files:
            if st.button("➡️ Proceed to Step 5", type="primary"):
                st.session_state.workflow_step = 5
                st.rerun()
        else:
            st.button("➡️ Proceed to Step 5", disabled=True, help="Run simulation first")

# === STEP 5: OPTIMIZATION & FILTERING ===
elif current_step == 5:
    st.header("5️⃣ Optimize & Filter Results")
    st.subheader("Find optimal IGU configurations")
    
    # Check for optimization script
    optimization_files = ["alpen_advisor_v46.py", "Alpen_Advisor_v47.py", "alpen_advisor.py"]
    optimization_script = None
    
    for opt_file in optimization_files:
        if os.path.exists(opt_file):
            optimization_script = opt_file
            break
    
    # Look for simulation results
    result_files = glob.glob("*results*.csv")
    
    if not result_files:
        st.error("❌ No simulation results found. Please complete Step 4 first.")
    elif not optimization_script:
        st.error("❌ No optimization script found. Looking for: " + ", ".join(optimization_files))
    else:
        st.success(f"✅ Found optimization script: {optimization_script}")
        st.success(f"✅ Found {len(result_files)} result file(s)")
        
        # Show available results
        st.subheader("📊 Available Results")
        for i, file in enumerate(result_files):
            df = pd.read_csv(file)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**{file}**")
            with col2:
                st.write(f"{len(df):,} configurations")
            with col3:
                if st.button(f"📊 View", key=f"view_{i}"):
                    st.dataframe(df.head(10), use_container_width=True)
        
        # Optimization controls
        st.subheader("🎯 Run Optimization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚡ Quick Optimization")
            
            selected_file = st.selectbox("Select result file", result_files)
            
            # Performance targets
            target_u_value = st.number_input("Target U-value (max)", min_value=0.1, max_value=1.0, value=0.25, step=0.01)
            target_shgc = st.number_input("Target SHGC (min)", min_value=0.1, max_value=1.0, value=0.25, step=0.01)
            
            if st.button("⚡ Run Quick Optimization", type="primary"):
                with st.spinner("Running optimization analysis..."):
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        progress_bar.progress(20)
                        status_text.text("Loading simulation results...")
                        
                        # Run optimization script
                        result = subprocess.run([
                            sys.executable, optimization_script, 
                            "--input", selected_file,
                            "--u_value", str(target_u_value),
                            "--shgc", str(target_shgc),
                            "--quick"
                        ], capture_output=True, text=True, timeout=300)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Optimization complete!")
                        
                        if result.returncode == 0:
                            st.success("✅ Optimization completed successfully!")
                            st.code(result.stdout)
                            
                            # Look for optimization results
                            opt_files = glob.glob("*optimized*.csv")
                            if opt_files:
                                opt_df = pd.read_csv(opt_files[-1])
                                st.success(f"📊 Found {len(opt_df)} optimized configurations")
                                st.dataframe(opt_df, use_container_width=True)
                        else:
                            st.error(f"❌ Optimization failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        st.error("❌ Optimization timed out")
                    except Exception as e:
                        st.error(f"❌ Optimization error: {str(e)}")
        
        with col2:
            st.subheader("🔥 Advanced Optimization")
            st.info("Multi-objective optimization with detailed analysis")
            
            if st.button("🔥 Run Advanced Optimization"):
                with st.spinner("Running advanced optimization..."):
                    try:
                        # Run advanced optimization
                        result = subprocess.run([
                            sys.executable, optimization_script, 
                            "--input", selected_file,
                            "--advanced"
                        ], capture_output=True, text=True, timeout=600)
                        
                        if result.returncode == 0:
                            st.success("✅ Advanced optimization completed!")
                            st.code(result.stdout)
                        else:
                            st.error(f"❌ Advanced optimization failed: {result.stderr}")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Step 4"):
            st.session_state.workflow_step = 4
            st.rerun()
    with col2:
        if st.button("🔄 Restart Workflow"):
            st.session_state.workflow_step = 1
            st.rerun()

# === WORKFLOW SUMMARY ===
st.divider()
st.subheader("📋 Workflow Summary")
st.info("""
**Complete ALPENSIMULATOR Workflow:**
1. **Glass Catalog** - Manage glass types and position capabilities
2. **Rules & Config** - Set up generation rules and constraints  
3. **Generate** - Create IGU configurations with physics validation
4. **Simulate** - Run thermal performance analysis
5. **Optimize** - Find best configurations for your requirements

**All existing Python scripts are preserved and integrated through this workflow.**
""")