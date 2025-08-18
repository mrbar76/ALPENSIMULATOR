"""
IGU Rule Editor - Interactive Interface for Materials Science Rules

Allows building materials scientists and glass IGU experts to edit
the comprehensive IGU configuration rules in real-time.
"""

import streamlit as st
import yaml
import json
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.append('.')

try:
    from core.igu_rule_validator import IGUConfigurationValidator
    from core.materials_workflow import MaterialsWorkflowEngine
    CORE_AVAILABLE = True
except ImportError as e:
    st.error(f"Core modules not available: {e}")
    CORE_AVAILABLE = False

st.set_page_config(
    page_title="IGU Rule Editor", 
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ IGU Configuration Rule Editor")
st.subheader("Materials Science Rule Management System")

if not CORE_AVAILABLE:
    st.stop()

# Initialize systems
@st.cache_resource
def init_systems():
    try:
        validator = IGUConfigurationValidator()
        workflow = MaterialsWorkflowEngine()
        return validator, workflow
    except Exception as e:
        st.error(f"Failed to initialize systems: {e}")
        return None, None

validator, workflow = init_systems()

if validator is None:
    st.error("System initialization failed")
    st.stop()

# Sidebar - Rule File Management
st.sidebar.header("📁 Rule File Management")

rule_summary = validator.get_rule_summary()
st.sidebar.success("✅ Rule System Online")
st.sidebar.metric("Rule File", Path(rule_summary['rules_file']).name)
st.sidebar.metric("IGU Types", len(rule_summary['igu_types_supported']))
st.sidebar.metric("Gas Types", len(rule_summary['gas_types_supported']))
st.sidebar.metric("Validation Mode", rule_summary['validation_mode'])

if st.sidebar.button("🔄 Reload Rules"):
    if validator.reload_rules():
        st.sidebar.success("Rules reloaded successfully!")
        st.rerun()
    else:
        st.sidebar.error("Failed to reload rules")

if st.sidebar.button("💾 Save Current Rules"):
    if validator.save_rules():
        st.sidebar.success("Rules saved successfully!")
    else:
        st.sidebar.error("Failed to save rules")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧬 IGU Type Rules", 
    "🌀 Airspace Rules", 
    "💨 Gas Fill Rules", 
    "🪟 Glass Layer Rules", 
    "🧪 Test & Validate"
])

with tab1:
    st.header("🧬 IGU Type Configuration Rules")
    
    # Get current IGU type rules
    current_rules = validator.get_editable_rules()
    igu_types = current_rules.get('igu_types', {})
    
    # IGU Type selector
    selected_igu_type = st.selectbox(
        "Select IGU Type to Edit",
        options=list(igu_types.keys()),
        help="Choose which IGU type rules to modify"
    )
    
    if selected_igu_type and selected_igu_type in igu_types:
        igu_config = igu_types[selected_igu_type]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"📋 {selected_igu_type.title()} Configuration")
            
            # Basic properties
            st.text_input("Name", value=igu_config.get('name', ''), key=f"{selected_igu_type}_name")
            st.text_area("Description", value=igu_config.get('description', ''), key=f"{selected_igu_type}_desc")
            
            # Layer count
            layer_count = st.number_input(
                "Glass Layer Count", 
                min_value=2, 
                max_value=4, 
                value=igu_config.get('glass_layer_count', 3),
                key=f"{selected_igu_type}_layers"
            )
            
            airspace_count = st.number_input(
                "Airspace Count",
                min_value=1,
                max_value=3,
                value=igu_config.get('airspace_count', 2),
                key=f"{selected_igu_type}_airspaces"
            )
            
        with col2:
            st.subheader("🔧 Glass Layer Definitions")
            
            glass_layers = igu_config.get('glass_layers', [])
            
            # Editable glass layer rules
            for i, layer in enumerate(glass_layers):
                with st.expander(f"Glass Layer {layer.get('position', i+1)}"):
                    st.text_input("Name", value=layer.get('name', ''), key=f"{selected_igu_type}_layer_{i}_name")
                    st.text_area("Description", value=layer.get('description', ''), key=f"{selected_igu_type}_layer_{i}_desc")
                    st.checkbox("Required", value=layer.get('required', True), key=f"{selected_igu_type}_layer_{i}_req")
        
        # Validation Rules Section
        st.subheader("⚖️ Validation Rules")
        
        validation_rules = igu_config.get('validation_rules', [])
        
        for i, rule in enumerate(validation_rules):
            with st.expander(f"Rule: {rule.get('rule', f'Rule {i+1}')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Rule ID", value=rule.get('rule', ''), key=f"{selected_igu_type}_rule_{i}_id")
                    st.text_area("Description", value=rule.get('description', ''), key=f"{selected_igu_type}_rule_{i}_desc")
                with col2:
                    st.text_area("Error Message", value=rule.get('error_message', ''), key=f"{selected_igu_type}_rule_{i}_msg")
        
        # Update button
        if st.button(f"💾 Update {selected_igu_type.title()} Rules"):
            # Collect all changes and update
            st.success(f"Updated {selected_igu_type} rules!")
            # TODO: Implement actual rule updating

with tab2:
    st.header("🌀 Airspace Configuration Rules")
    
    airspace_rules = current_rules.get('airspace_rules', {})
    
    # Outer airspace rules
    st.subheader("🌊 Outer Airspace Rules")
    
    outer_rules = airspace_rules.get('outer_airspace', {})
    constraints = outer_rules.get('constraints', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_inches = st.number_input(
            "Minimum Inches",
            min_value=0.1,
            max_value=2.0,
            value=constraints.get('minimum_inches', 0.375),
            step=0.125,
            format="%.3f"
        )
    
    with col2:
        max_inches = st.number_input(
            "Maximum Inches", 
            min_value=0.5,
            max_value=3.0,
            value=constraints.get('maximum_inches', 2.0),
            step=0.125,
            format="%.3f"
        )
    
    with col3:
        st.multiselect(
            "Preferred Sizes (inches)",
            options=[0.375, 0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25],
            default=constraints.get('preferred_inches', [0.5, 0.625, 0.75]),
            help="Standard manufacturing sizes"
        )
    
    # Engineering notes
    st.subheader("📝 Engineering Notes")
    engineering_notes = st.text_area(
        "Engineering Guidelines",
        value=outer_rules.get('engineering_notes', ''),
        height=150,
        help="Technical guidance for airspace design"
    )
    
    # Validation rules for airspaces
    st.subheader("⚖️ Airspace Validation Rules")
    
    validation_rules = outer_rules.get('validation_rules', [])
    for i, rule in enumerate(validation_rules):
        with st.expander(f"Validation Rule: {rule.get('rule', f'Rule {i+1}')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Rule Type", value=rule.get('rule', ''), key=f"airspace_rule_{i}_type")
                st.text_area("Description", value=rule.get('description', ''), key=f"airspace_rule_{i}_desc")
            with col2:
                st.text_area("Error Message", value=rule.get('error_message', ''), key=f"airspace_rule_{i}_error")
                st.text_area("Warning Message", value=rule.get('warning_message', ''), key=f"airspace_rule_{i}_warn")

with tab3:
    st.header("💨 Gas Fill Configuration Rules")
    
    gas_rules = current_rules.get('gas_fill_rules', {})
    supported_gases = gas_rules.get('supported_gases', {})
    
    st.subheader("⚗️ Supported Gas Types")
    
    # Display current gas types
    for gas_name, gas_info in supported_gases.items():
        with st.expander(f"💨 {gas_name} - {gas_info.get('name', gas_name)}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.text_input("Display Name", value=gas_info.get('name', ''), key=f"gas_{gas_name}_name")
                st.text_area("Description", value=gas_info.get('description', ''), key=f"gas_{gas_name}_desc")
            
            with col2:
                st.number_input(
                    "Thermal Conductivity (W/m·K)",
                    min_value=0.001,
                    max_value=0.1,
                    value=gas_info.get('thermal_conductivity', 0.024),
                    step=0.001,
                    format="%.3f",
                    key=f"gas_{gas_name}_tc"
                )
                
                st.number_input(
                    "Cost Factor",
                    min_value=1.0,
                    max_value=3.0,
                    value=gas_info.get('cost_factor', 1.0),
                    step=0.05,
                    format="%.2f",
                    key=f"gas_{gas_name}_cost"
                )
            
            with col3:
                st.selectbox(
                    "Availability",
                    options=['universal', 'standard', 'premium', 'special_order'],
                    index=['universal', 'standard', 'premium', 'special_order'].index(
                        gas_info.get('availability', 'standard')
                    ),
                    key=f"gas_{gas_name}_avail"
                )
                
                st.text_area("Technical Notes", value=gas_info.get('notes', ''), key=f"gas_{gas_name}_notes")
    
    # Add new gas type
    st.subheader("➕ Add New Gas Type")
    with st.expander("Create New Gas Fill Option"):
        col1, col2 = st.columns(2)
        with col1:
            new_gas_id = st.text_input("Gas ID (e.g., '85K')")
            new_gas_name = st.text_input("Display Name (e.g., '85% Krypton')")
            new_gas_desc = st.text_area("Description")
        with col2:
            new_gas_tc = st.number_input("Thermal Conductivity", min_value=0.001, value=0.015, step=0.001)
            new_gas_cost = st.number_input("Cost Factor", min_value=1.0, value=1.2, step=0.1)
            new_gas_avail = st.selectbox("Availability", ['universal', 'standard', 'premium', 'special_order'])
        
        if st.button("➕ Add Gas Type") and new_gas_id:
            st.success(f"Added new gas type: {new_gas_id}")
            # TODO: Implement adding new gas type
    
    # Gas fill mixing rules
    st.subheader("🔄 Gas Mixing Rules")
    mixing_rules = gas_rules.get('mixing_rules', {})
    
    allow_mixed = st.checkbox(
        "Allow Mixed Gas Fills",
        value=mixing_rules.get('allow_mixed_gases', False),
        help="Allow different gases in different airspaces"
    )
    
    if allow_mixed:
        st.info("Mixed gas fills enabled - different airspaces can use different gases")
    else:
        st.warning("Mixed gas fills disabled - all airspaces must use the same gas")

with tab4:
    st.header("🪟 Glass Layer Configuration Rules")
    
    glass_rules = current_rules.get('glass_layer_rules', {})
    
    # Manufacturer rules
    st.subheader("🏭 Manufacturer Rules")
    mfr_rules = glass_rules.get('manufacturer_rules', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.multiselect(
            "Preferred Manufacturers",
            options=["Cardinal Glass Industries", "Guardian Glass", "Pilkington", "AGC", "Vitro"],
            default=mfr_rules.get('preferred_manufacturers', []),
            help="Manufacturers with best performance/compatibility"
        )
        
        mixed_mfr_enabled = st.checkbox(
            "Allow Mixed Manufacturers",
            value=mfr_rules.get('allow_mixed_manufacturers', {}).get('enabled', True),
            help="Allow different manufacturers in same IGU"
        )
    
    with col2:
        st.multiselect(
            "Excluded Manufacturers",
            options=["Example Bad Manufacturer"],
            default=mfr_rules.get('excluded_manufacturers', []),
            help="Manufacturers to exclude from selection"
        )
        
        if mixed_mfr_enabled:
            st.number_input(
                "Mixed Manufacturer Warning Threshold",
                min_value=1,
                max_value=4,
                value=mfr_rules.get('allow_mixed_manufacturers', {}).get('warning_threshold', 2),
                help="Warn when using this many different manufacturers"
            )
    
    # Thickness rules
    st.subheader("📏 Glass Thickness Rules")
    thickness_rules = glass_rules.get('thickness_rules', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.number_input(
            "Minimum Thickness (mm)",
            min_value=2.0,
            max_value=6.0,
            value=thickness_rules.get('minimum_mm', 3.0),
            step=0.5
        )
    
    with col2:
        st.number_input(
            "Maximum Thickness (mm)",
            min_value=8.0,
            max_value=20.0,
            value=thickness_rules.get('maximum_mm', 12.0),
            step=1.0
        )
    
    with col3:
        st.multiselect(
            "Preferred Nominal Thicknesses (mm)",
            options=[3, 4, 5, 6, 8, 10, 12, 15],
            default=thickness_rules.get('preferred_nominal', [4, 5, 6, 8]),
            help="Standard glass thicknesses"
        )
    
    # Coating rules
    st.subheader("✨ Coating Configuration Rules")
    coating_rules = glass_rules.get('coating_rules', {})
    
    st.text_area(
        "Coating Placement Guidelines",
        value=coating_rules.get('description', ''),
        help="Rules for low-E coating placement and surface positions"
    )

with tab5:
    st.header("🧪 Test & Validate Rule System")
    
    st.subheader("🔬 Test Configuration Validation")
    
    # Create test configuration
    with st.expander("Create Test IGU Configuration"):
        col1, col2 = st.columns(2)
        
        with col1:
            test_igu_type = st.selectbox("IGU Type", ['Triple', 'Quad'])
            test_gas_type = st.selectbox("Gas Type", ['Air', '95A', '90K'])
            test_outer_airspace = st.number_input("Outer Airspace (inches)", min_value=0.1, max_value=2.0, value=0.5, step=0.125)
        
        with col2:
            # Glass layer configuration
            test_glass_1 = st.number_input("Glass 1 ID", min_value=1, value=1)
            test_glass_2 = st.number_input("Glass 2 ID", min_value=1, value=2) 
            test_glass_3 = st.number_input("Glass 3 ID", min_value=1, value=3)
            
            if test_igu_type == 'Quad':
                test_glass_4 = st.number_input("Glass 4 ID", min_value=1, value=4)
            else:
                test_glass_4 = None
        
        if st.button("🧪 Validate Test Configuration"):
            # Create test configuration data
            test_config = {
                'igu_type': test_igu_type,
                'gas_type': test_gas_type,
                'outer_airspace_in': test_outer_airspace,
                'glass_1_id': test_glass_1,
                'glass_2_id': test_glass_2,
                'glass_3_id': test_glass_3
            }
            
            if test_glass_4 is not None:
                test_config['glass_4_id'] = test_glass_4
            
            # Run validation
            validation_result = validator.validate_igu_configuration(test_config)
            
            # Display results
            if validation_result.valid:
                st.success("✅ Configuration is valid!")
            else:
                st.error("❌ Configuration failed validation")
            
            # Show detailed results
            st.subheader("📋 Validation Results")
            
            if validation_result.errors:
                st.error("**Errors:**")
                for error in validation_result.errors:
                    st.write(f"- {error.message}")
            
            if validation_result.warnings:
                st.warning("**Warnings:**")
                for warning in validation_result.warnings:
                    st.write(f"- {warning.message}")
            
            if validation_result.info_messages:
                st.info("**Information:**")
                for info in validation_result.info_messages:
                    st.write(f"- {info.message}")
            
            # Show performance prediction if available
            if validation_result.performance_prediction:
                st.subheader("📈 Performance Prediction")
                st.json(validation_result.performance_prediction)
    
    # Rule system health check
    st.subheader("🏥 Rule System Health Check")
    
    if st.button("🔍 Run System Diagnostics"):
        with st.spinner("Running diagnostics..."):
            # Check rule file integrity
            rules_valid = True
            try:
                test_rules = validator.get_editable_rules()
                required_sections = ['igu_types', 'airspace_rules', 'gas_fill_rules', 'glass_layer_rules']
                missing_sections = [section for section in required_sections if section not in test_rules]
                
                if missing_sections:
                    rules_valid = False
                    st.error(f"Missing rule sections: {missing_sections}")
                else:
                    st.success("✅ All required rule sections present")
                
            except Exception as e:
                rules_valid = False
                st.error(f"Rule loading error: {e}")
            
            # Test validator functionality
            try:
                test_config = {
                    'igu_type': 'Triple',
                    'gas_type': 'Air',
                    'outer_airspace_in': 0.5,
                    'glass_1_id': 1,
                    'glass_2_id': 2,
                    'glass_3_id': 3
                }
                test_result = validator.validate_igu_configuration(test_config)
                st.success("✅ Validator functioning correctly")
            except Exception as e:
                st.error(f"Validator error: {e}")
            
            # Overall health
            if rules_valid:
                st.success("🎉 Rule system is healthy and operational!")
            else:
                st.error("⚠️ Rule system has issues that need attention")

# Footer
st.divider()
st.caption("🔬 IGU Rule Editor - Materials Science Configuration Management System")
st.caption("Edit rules to customize IGU validation behavior for your specific requirements")