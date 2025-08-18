"""
Live Alpen Rules Editor

Interactive interface for editing the actual Alpen IGU rules
without changing code. All hardcoded values become configurable.
"""

import streamlit as st
import pandas as pd
from configurable_rules import AlpenRulesConfig

st.set_page_config(page_title="Live Alpen Rules Editor", layout="wide")
st.title("🔧 Live Alpen IGU Rules Editor")
st.subheader("Make Every Rule Configurable - No More Hardcoded Values!")

# Initialize rules system
@st.cache_resource
def init_rules_config():
    return AlpenRulesConfig()

config = init_rules_config()

# Sidebar - Rule Summary
st.sidebar.header("📊 Current Rules Status")
summary = config.get_rule_summary()

st.sidebar.success("✅ Rules System Active")
st.sidebar.metric("Config File", summary['config_file'].split('/')[-1])
st.sidebar.metric("Constants", summary['constants_count'])
st.sidebar.metric("IGU Types", len(summary['igu_types']))
st.sidebar.metric("Gas Types", len(summary['supported_gases']))

st.sidebar.header("🎯 Quick Actions")
if st.sidebar.button("🔄 Reload Rules"):
    config.load_rules()
    st.sidebar.success("Rules reloaded!")
    st.rerun()

if st.sidebar.button("💾 Save Changes"):
    if config.save_rules():
        st.sidebar.success("Rules saved!")
    else:
        st.sidebar.error("Save failed!")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔢 Constants & Core Rules",
    "✨ Coating & Surface Rules", 
    "🔄 Flipping Logic",
    "🧪 Test & Validate",
    "📋 Rule Documentation"
])

with tab1:
    st.header("🔢 Core Constants (Previously Hardcoded)")
    st.info("These values were hardcoded in igu_input_generator.py - now they're configurable!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📏 Thickness Rules")
        
        # TOL (tolerance)
        current_tol = config.get_tolerance()
        new_tol = st.number_input(
            "Thickness Tolerance (TOL) [mm]",
            min_value=0.1,
            max_value=1.0,
            value=current_tol,
            step=0.1,
            help="Tolerance for measured vs nominal thickness"
        )
        if new_tol != current_tol:
            if st.button("Update TOL", key="update_tol"):
                config.update_rule("constants.TOL", new_tol)
                st.success(f"Updated TOL: {current_tol} → {new_tol}")
                st.rerun()
        
        # MIN_EDGE_NOMINAL
        current_min_edge = config.get_min_edge_nominal()
        new_min_edge = st.number_input(
            "Min Edge Nominal [mm]",
            min_value=2.0,
            max_value=6.0,
            value=current_min_edge,
            step=0.5,
            help="Minimum thickness for outer/inner glass"
        )
        if new_min_edge != current_min_edge:
            if st.button("Update Min Edge", key="update_min_edge"):
                config.update_rule("constants.MIN_EDGE_NOMINAL", new_min_edge)
                st.success(f"Updated MIN_EDGE_NOMINAL: {current_min_edge} → {new_min_edge}")
                st.rerun()
        
        # CENTER_MAX_THICKNESS
        current_center_max = config.get_center_max_thickness()
        new_center_max = st.number_input(
            "Center Glass Max [mm]",
            min_value=0.5,
            max_value=2.0,
            value=current_center_max,
            step=0.1,
            help="Maximum thickness for center glass"
        )
        if new_center_max != current_center_max:
            if st.button("Update Center Max", key="update_center_max"):
                config.update_rule("constants.CENTER_MAX_THICKNESS", new_center_max)
                st.success(f"Updated CENTER_MAX_THICKNESS: {current_center_max} → {new_center_max}")
                st.rerun()
    
    with col2:
        st.subheader("🌀 Airspace Rules")
        
        # MIN_AIRGAP
        current_min_airgap = config.get_min_airgap()
        new_min_airgap = st.number_input(
            "Min Air Gap [mm]",
            min_value=1.0,
            max_value=10.0,
            value=current_min_airgap,
            step=0.5,
            help="Minimum air gap between glass layers"
        )
        if new_min_airgap != current_min_airgap:
            if st.button("Update Min Air Gap", key="update_min_airgap"):
                config.update_rule("constants.MIN_AIRGAP", new_min_airgap)
                st.success(f"Updated MIN_AIRGAP: {current_min_airgap} → {new_min_airgap}")
                st.rerun()
        
        # QUAD_OA_MIN_INCH
        current_quad_oa_min = config.get_quad_oa_min_inch()
        new_quad_oa_min = st.number_input(
            "Quad OA Minimum [inches]",
            min_value=0.5,
            max_value=1.5,
            value=current_quad_oa_min,
            step=0.125,
            help="Minimum OA for quad configurations"
        )
        if new_quad_oa_min != current_quad_oa_min:
            if st.button("Update Quad OA Min", key="update_quad_oa_min"):
                config.update_rule("constants.QUAD_OA_MIN_INCH", new_quad_oa_min)
                st.success(f"Updated QUAD_OA_MIN_INCH: {current_quad_oa_min} → {new_quad_oa_min}")
                st.rerun()
    
    with col3:
        st.subheader("🏭 Manufacturer Rules")
        
        # Edge manufacturer matching
        edge_matching = config.edges_manufacturer_match_required()
        new_edge_matching = st.checkbox(
            "Require Edge Manufacturer Match",
            value=edge_matching,
            help="Outer and inner glass must be same manufacturer"
        )
        if new_edge_matching != edge_matching:
            if st.button("Update Edge Matching", key="update_edge_matching"):
                config.update_rule("manufacturer_rules.edge_matching.enabled", new_edge_matching)
                st.success(f"Updated edge matching requirement")
                st.rerun()
        
        # Low-E ordering
        lowe_ordering = config.lowe_ordering_required()
        new_lowe_ordering = st.checkbox(
            "Require Low-E Ordering",
            value=lowe_ordering,
            help="parse_lowe_value(outer) >= parse_lowe_value(inner)"
        )
        if new_lowe_ordering != lowe_ordering:
            if st.button("Update Low-E Ordering", key="update_lowe_ordering"):
                config.update_rule("lowe_ordering.enabled", new_lowe_ordering)
                st.success(f"Updated low-E ordering requirement")
                st.rerun()

with tab2:
    st.header("✨ Coating & Surface Rules")
    st.info("🎯 **Critical Fix**: i89 coating placement - Surface 6 (Triple) and Surface 8 (Quad)")
    
    # Surface mapping display
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔷 Triple Surface Map")
        triple_surfaces = config.get_surface_map('triple')
        for surface_num, description in triple_surfaces.items():
            if surface_num == 6:  # Highlight i89 surface
                st.success(f"**Surface {surface_num}**: {description} ← i89 coating")
            elif surface_num in [2, 5]:  # Standard low-E
                st.info(f"Surface {surface_num}: {description} ← Standard low-E")
            elif surface_num == 4:  # Center coating
                st.warning(f"Surface {surface_num}: {description} ← Center coating")
            else:
                st.text(f"Surface {surface_num}: {description}")
    
    with col2:
        st.subheader("🔶 Quad Surface Map")
        quad_surfaces = config.get_surface_map('quad')
        for surface_num, description in quad_surfaces.items():
            if surface_num == 8:  # Highlight i89 surface
                st.success(f"**Surface {surface_num}**: {description} ← i89 coating")
            elif surface_num in [2, 7]:  # Standard low-E
                st.info(f"Surface {surface_num}: {description} ← Standard low-E")
            elif surface_num == 6:  # Center coating
                st.warning(f"Surface {surface_num}: {description} ← Center coating")
            else:
                st.text(f"Surface {surface_num}: {description}")
    
    # Editable coating rules
    st.subheader("🎛️ Edit Coating Placement Rules")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Standard Low-E Surfaces")
        
        # Triple low-E surfaces
        triple_lowe = config.get_standard_lowe_surfaces('triple')
        st.text(f"Triple: {triple_lowe}")
        new_triple_lowe_str = st.text_input(
            "Triple Low-E Surfaces", 
            value=",".join(map(str, triple_lowe)),
            help="Comma-separated surface numbers"
        )
        
        # Quad low-E surfaces  
        quad_lowe = config.get_standard_lowe_surfaces('quad')
        st.text(f"Quad: {quad_lowe}")
        new_quad_lowe_str = st.text_input(
            "Quad Low-E Surfaces",
            value=",".join(map(str, quad_lowe)),
            help="Comma-separated surface numbers"
        )
        
        if st.button("Update Low-E Surfaces"):
            try:
                new_triple_lowe = [int(x.strip()) for x in new_triple_lowe_str.split(',')]
                new_quad_lowe = [int(x.strip()) for x in new_quad_lowe_str.split(',')]
                
                config.update_rule("coating_rules.standard_lowe_surfaces.triple", new_triple_lowe)
                config.update_rule("coating_rules.standard_lowe_surfaces.quad", new_quad_lowe)
                st.success("Updated standard low-E surfaces!")
                st.rerun()
            except ValueError:
                st.error("Invalid format - use comma-separated numbers")
    
    with col2:
        st.subheader("i89 Coating Surfaces")
        
        # Current i89 surfaces
        triple_i89 = config.get_i89_surface('triple')
        quad_i89 = config.get_i89_surface('quad')
        
        st.text(f"Current - Triple: {triple_i89}, Quad: {quad_i89}")
        
        # Edit i89 surfaces
        new_triple_i89 = st.number_input(
            "Triple i89 Surface",
            min_value=1,
            max_value=6,
            value=triple_i89,
            help="Should be 6 (innermost surface)"
        )
        
        new_quad_i89 = st.number_input(
            "Quad i89 Surface", 
            min_value=1,
            max_value=8,
            value=quad_i89,
            help="Should be 8 (innermost surface)"
        )
        
        if st.button("Update i89 Surfaces"):
            config.update_rule("coating_rules.special_coating_rules.i89_coating.triple_surface", new_triple_i89)
            config.update_rule("coating_rules.special_coating_rules.i89_coating.quad_surface", new_quad_i89)
            st.success(f"Updated i89 surfaces: Triple → {new_triple_i89}, Quad → {new_quad_i89}")
            st.rerun()
    
    with col3:
        st.subheader("Center Coating Surfaces")
        
        # Current center surfaces
        triple_center = config.get_center_coating_surfaces('triple')
        quad_center = config.get_center_coating_surfaces('quad')
        
        st.text(f"Triple: {triple_center}")
        st.text(f"Quad: {quad_center}")
        
        # NxLite surfaces
        triple_nxlite = config.get_nxlite_surface('triple')
        quad_nxlite = config.get_nxlite_surface('quad')
        
        st.text(f"NxLite - Triple: {triple_nxlite}, Quad: {quad_nxlite}")

with tab3:
    st.header("🔄 Flipping Logic Configuration")
    st.info("Configure when glass should be flipped to achieve correct coating placement")
    
    # Flipping test interface
    st.subheader("🧪 Test Flipping Logic")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        test_position = st.selectbox(
            "Glass Position",
            options=['outer', 'center', 'quad_inner', 'inner'],
            help="Position of glass in IGU"
        )
    
    with col2:
        test_coating_side = st.selectbox(
            "Coating Side",
            options=['front', 'back', 'none'],
            help="Which side has the coating"
        )
    
    with col3:
        test_coating_name = st.text_input(
            "Coating Name",
            value="",
            help="e.g., 'i89', 'LoE-180', 'NxLite'"
        )
    
    with col4:
        test_igu_type = st.selectbox(
            "IGU Type",
            options=['triple', 'quad'],
            help="Triple or quad configuration"
        )
    
    # Run flipping test
    if st.button("🔄 Test Flipping Logic"):
        should_flip = config.should_flip(
            test_position, 
            test_coating_side, 
            test_coating_name, 
            test_igu_type
        )
        
        if should_flip:
            st.success(f"✅ **FLIP GLASS** - {test_position} position with {test_coating_side} coating")
        else:
            st.info(f"⏹️ **KEEP ORIENTATION** - {test_position} position with {test_coating_side} coating")
        
        # Show reasoning
        if "i89" in test_coating_name.lower():
            target_surface = config.get_i89_surface(test_igu_type)
            st.write(f"💡 **i89 Special Rule**: Must end up on surface {target_surface} (innermost)")
        else:
            st.write(f"💡 **Standard Rule**: Applied for {test_position} position")
    
    # Current flipping rules display
    st.subheader("📋 Current Flipping Rules")
    
    rules = config.get_all_rules()
    flip_logic = rules.get('flipping_rules', {}).get('flip_logic', {})
    
    for position, rule in flip_logic.items():
        with st.expander(f"📍 {position.title()} Position Rules"):
            st.json(rule)

with tab4:
    st.header("🧪 Test & Validate Rules")
    st.subheader("Test Your Rule Changes Against Sample Configurations")
    
    # Create test configurations
    test_configs = [
        {
            'name': 'Valid Triple',
            'igu_type': 'triple',
            'glasses': ['Glass1_NFRC102', 'Glass2_NFRC107', 'Glass3_NFRC102', None],
            'oa_inches': 1.0,
            'gas_type': '95A'
        },
        {
            'name': 'Invalid Triple (has Glass 4)',
            'igu_type': 'triple', 
            'glasses': ['Glass1_NFRC102', 'Glass2_NFRC107', 'Glass3_NFRC102', 'Glass4_NFRC119'],
            'oa_inches': 1.0,
            'gas_type': '95A'
        },
        {
            'name': 'Valid Quad',
            'igu_type': 'quad',
            'glasses': ['Glass1_NFRC102', 'Glass2_NFRC107', 'Glass3_NFRC22720', 'Glass4_NFRC102'],
            'oa_inches': 1.0,
            'gas_type': '90K'
        },
        {
            'name': 'Invalid Quad (OA too small)',
            'igu_type': 'quad',
            'glasses': ['Glass1_NFRC102', 'Glass2_NFRC107', 'Glass3_NFRC22720', 'Glass4_NFRC102'],
            'oa_inches': 0.5,  # Below QUAD_OA_MIN_INCH
            'gas_type': '90K'
        }
    ]
    
    st.subheader("🔍 Rule Validation Results")
    
    for test_config in test_configs:
        with st.expander(f"Test: {test_config['name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.json({
                    'IGU Type': test_config['igu_type'],
                    'Glass Layers': test_config['glasses'],
                    'OA (inches)': test_config['oa_inches'],
                    'Gas Type': test_config['gas_type']
                })
            
            with col2:
                # Run validation
                is_valid, errors = config.validate_igu_configuration(
                    test_config['igu_type'],
                    test_config['glasses']
                )
                
                # Check OA rule for quads
                if test_config['igu_type'] == 'quad':
                    min_oa = config.get_quad_oa_min_inch()
                    if test_config['oa_inches'] <= min_oa:
                        errors.append(f"OA {test_config['oa_inches']}\" ≤ minimum {min_oa}\"")
                        is_valid = False
                
                if is_valid and len(errors) == 0:
                    st.success("✅ **VALID** - Passes all rules")
                else:
                    st.error("❌ **INVALID** - Rule violations:")
                    for error in errors:
                        st.write(f"• {error}")
    
    # Rule constants summary
    st.subheader("📊 Current Rule Constants")
    
    constants = {
        'TOL': config.get_tolerance(),
        'MIN_EDGE_NOMINAL': config.get_min_edge_nominal(),
        'MIN_AIRGAP': config.get_min_airgap(),
        'QUAD_OA_MIN_INCH': config.get_quad_oa_min_inch(),
        'CENTER_MAX_THICKNESS': config.get_center_max_thickness()
    }
    
    df_constants = pd.DataFrame([
        {'Rule': key, 'Value': value, 'Units': 'mm' if 'mm' not in key else ('inches' if 'INCH' in key else 'mm')}
        for key, value in constants.items()
    ])
    
    st.dataframe(df_constants, use_container_width=True)

with tab5:
    st.header("📋 Rule Documentation")
    st.subheader("Complete Reference for All Configurable Rules")
    
    # Show complete rules structure
    all_rules = config.get_all_rules()
    
    st.subheader("🔢 Constants Section")
    with st.expander("View Constants"):
        st.json(all_rules.get('constants', {}))
    
    st.subheader("✨ Coating Rules Section") 
    with st.expander("View Coating Rules"):
        st.json(all_rules.get('coating_rules', {}))
    
    st.subheader("🔄 Flipping Rules Section")
    with st.expander("View Flipping Rules"):
        st.json(all_rules.get('flipping_rules', {}))
    
    st.subheader("💨 Gas Fill Rules Section")
    with st.expander("View Gas Fill Rules"):
        st.json(all_rules.get('gas_fill_rules', {}))
    
    st.subheader("🏭 Manufacturer Rules Section")
    with st.expander("View Manufacturer Rules"):
        st.json(all_rules.get('manufacturer_rules', {}))
    
    # Modification history
    st.subheader("📝 Modification History")
    history = all_rules.get('modification_history', [])
    if history:
        df_history = pd.DataFrame(history)
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("No modifications recorded yet")

# Footer
st.divider()
st.caption("🔧 Live Alpen Rules Editor - Making igu_input_generator.py fully configurable")
st.caption("💡 All hardcoded constants and rules are now editable without code changes")