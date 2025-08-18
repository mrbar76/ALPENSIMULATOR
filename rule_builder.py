"""
Streamlined Visual Rule Builder for ALPENSIMULATOR
Create and manage IGU generation rules through a simple interface
"""

import streamlit as st
import pandas as pd
import yaml
import os
from datetime import datetime

class RuleBuilder:
    def __init__(self):
        self.rule_types = {
            'constraint': {
                'name': 'Constraint Rule',
                'description': 'Must be true or configuration is rejected',
                'icon': '🚫',
                'examples': ['Spacer thickness 6-20mm', 'Same manufacturer required']
            },
            'preference': {
                'name': 'Preference Rule', 
                'description': 'Generates warning if not followed',
                'icon': '⚠️',
                'examples': ['Quad panes prefer 95A gas', 'Optimal spacer ranges']
            },
            'compatibility': {
                'name': 'Compatibility Rule',
                'description': 'Defines what can work together',
                'icon': '🔗',
                'examples': ['Manufacturer combinations', 'Emissivity relationships']
            },
            'optimization': {
                'name': 'Optimization Rule',
                'description': 'Guides selection for better performance',
                'icon': '⚡',
                'examples': ['Prefer thin glass in center', 'High-performance gas for low U-values']
            }
        }
        
        self.conditions = {
            'glass_property': {
                'name': 'Glass Property',
                'fields': ['thickness', 'manufacturer', 'coating_type', 'position'],
                'operators': ['equals', 'not_equals', 'greater_than', 'less_than', 'in_list']
            },
            'igu_property': {
                'name': 'IGU Property', 
                'fields': ['igu_type', 'oa_size', 'gas_type', 'air_gap'],
                'operators': ['equals', 'not_equals', 'greater_than', 'less_than', 'in_list']
            },
            'performance': {
                'name': 'Performance Target',
                'fields': ['u_value', 'shgc', 'vt'],
                'operators': ['greater_than', 'less_than', 'between']
            },
            'combination': {
                'name': 'Component Combination',
                'fields': ['outer_inner_same', 'coating_emissivity', 'gas_spacer_match'],
                'operators': ['must_match', 'must_not_match', 'compatible']
            }
        }

    def create_rule_builder_interface(self):
        """Main rule builder interface"""
        st.header("🔧 Visual Rule Builder")
        st.info("Build rules with simple point-and-click interface. No YAML editing required!")
        
        # Load existing rules
        if 'custom_rules' not in st.session_state:
            st.session_state.custom_rules = self.load_existing_rules()
        
        # Rule builder tabs
        tab1, tab2, tab3 = st.tabs(["➕ Build New Rule", "📋 Manage Rules", "🧪 Test Rules"])
        
        with tab1:
            self.create_new_rule_interface()
        
        with tab2:
            self.manage_existing_rules()
            
        with tab3:
            self.test_rules_interface()

    def create_new_rule_interface(self):
        """Interface for creating new rules"""
        st.subheader("Create New Rule")
        
        # Step 1: Choose rule type
        st.write("**Step 1: Choose Rule Type**")
        rule_type = st.selectbox(
            "What type of rule do you want to create?",
            options=list(self.rule_types.keys()),
            format_func=lambda x: f"{self.rule_types[x]['icon']} {self.rule_types[x]['name']}",
            help="Different rule types handle violations differently"
        )
        
        with st.expander(f"ℹ️ About {self.rule_types[rule_type]['name']} Rules"):
            st.write(self.rule_types[rule_type]['description'])
            st.write("**Examples:**")
            for example in self.rule_types[rule_type]['examples']:
                st.write(f"• {example}")
        
        # Step 2: Define condition
        st.write("**Step 2: Define When This Rule Applies**")
        condition_type = st.selectbox(
            "What should trigger this rule?",
            options=list(self.conditions.keys()),
            format_func=lambda x: self.conditions[x]['name']
        )
        
        condition_config = self.build_condition_interface(condition_type)
        
        # Step 3: Define action
        st.write("**Step 3: Define What Should Happen**")
        action_config = self.build_action_interface(rule_type, condition_type)
        
        # Step 4: Rule details
        st.write("**Step 4: Rule Details**")
        col1, col2 = st.columns(2)
        with col1:
            rule_name = st.text_input("Rule Name", placeholder="e.g., 'Quad Spacer Minimum'")
        with col2:
            rule_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        
        rule_description = st.text_area(
            "Description (optional)", 
            placeholder="Explain why this rule is important..."
        )
        
        # Step 5: Create rule
        if st.button("🚀 Create Rule", type="primary"):
            if rule_name and condition_config and action_config:
                new_rule = {
                    'id': f"rule_{len(st.session_state.custom_rules) + 1}",
                    'name': rule_name,
                    'type': rule_type,
                    'priority': rule_priority,
                    'description': rule_description,
                    'condition': condition_config,
                    'action': action_config,
                    'enabled': True,
                    'created': datetime.now().isoformat()
                }
                
                st.session_state.custom_rules.append(new_rule)
                st.success(f"✅ Rule '{rule_name}' created successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields")

    def build_condition_interface(self, condition_type):
        """Build interface for rule conditions"""
        condition_info = self.conditions[condition_type]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            field = st.selectbox(
                "Property",
                options=condition_info['fields'],
                key=f"condition_field_{condition_type}"
            )
        
        with col2:
            operator = st.selectbox(
                "Operator", 
                options=condition_info['operators'],
                key=f"condition_operator_{condition_type}"
            )
        
        with col3:
            if operator in ['equals', 'not_equals']:
                if field in ['igu_type']:
                    value = st.selectbox("Value", ["Triple", "Quad"])
                elif field in ['gas_type']:
                    value = st.selectbox("Value", ["Air", "90K", "95A"])
                elif field in ['manufacturer']:
                    value = st.selectbox("Value", ["Cardinal", "Guardian", "Generic"])
                elif field in ['coating_type']:
                    value = st.selectbox("Value", ["clear", "272", "277", "180", "366", "i89"])
                else:
                    value = st.text_input("Value")
            elif operator in ['greater_than', 'less_than']:
                value = st.number_input("Value", min_value=0.0)
            elif operator == 'between':
                min_val = st.number_input("Min Value", min_value=0.0)
                max_val = st.number_input("Max Value", min_value=0.0)
                value = [min_val, max_val]
            elif operator == 'in_list':
                value = st.text_input("Values (comma-separated)", placeholder="A,B,C")
                value = [v.strip() for v in value.split(',') if v.strip()]
            else:
                value = st.text_input("Value")
        
        return {
            'type': condition_type,
            'field': field,
            'operator': operator,
            'value': value
        }

    def build_action_interface(self, rule_type, condition_type):
        """Build interface for rule actions"""
        if rule_type == 'constraint':
            action_type = st.selectbox(
                "Action when violated",
                ["reject_configuration", "require_alternative"]
            )
            message = st.text_input(
                "Error message",
                placeholder="Configuration violates rule requirements"
            )
        elif rule_type == 'preference':
            action_type = st.selectbox(
                "Action when not followed", 
                ["show_warning", "suggest_alternative"]
            )
            message = st.text_input(
                "Warning message",
                placeholder="Consider using alternative for better performance"
            )
        elif rule_type == 'compatibility':
            action_type = st.selectbox(
                "When components incompatible",
                ["reject_combination", "suggest_compatible"]
            )
            message = st.text_input(
                "Incompatibility message", 
                placeholder="These components are not compatible"
            )
        else:  # optimization
            action_type = st.selectbox(
                "Optimization action",
                ["prefer_option", "rank_higher", "suggest_improvement"]
            )
            message = st.text_input(
                "Optimization message",
                placeholder="This option provides better performance"
            )
        
        return {
            'type': action_type,
            'message': message
        }

    def manage_existing_rules(self):
        """Interface for managing existing rules"""
        st.subheader("Manage Existing Rules")
        
        if not st.session_state.custom_rules:
            st.info("No custom rules created yet. Use the 'Build New Rule' tab to create your first rule.")
            return
        
        # Rules summary
        rule_counts = {}
        for rule in st.session_state.custom_rules:
            rule_type = rule['type']
            rule_counts[rule_type] = rule_counts.get(rule_type, 0) + 1
        
        st.write("**Rules Summary:**")
        cols = st.columns(len(self.rule_types))
        for i, (rule_type, info) in enumerate(self.rule_types.items()):
            with cols[i]:
                count = rule_counts.get(rule_type, 0)
                st.metric(f"{info['icon']} {info['name']}", count)
        
        # Rules list
        st.write("**All Rules:**")
        for i, rule in enumerate(st.session_state.custom_rules):
            with st.expander(f"{self.rule_types[rule['type']]['icon']} {rule['name']} ({rule['priority']} priority)"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Type:** {self.rule_types[rule['type']]['name']}")
                    if rule['description']:
                        st.write(f"**Description:** {rule['description']}")
                    st.write(f"**Condition:** {rule['condition']['field']} {rule['condition']['operator']} {rule['condition']['value']}")
                    st.write(f"**Action:** {rule['action']['type']}")
                
                with col2:
                    enabled = st.checkbox("Enabled", value=rule['enabled'], key=f"enable_{rule['id']}")
                    if enabled != rule['enabled']:
                        st.session_state.custom_rules[i]['enabled'] = enabled
                        st.rerun()
                
                with col3:
                    if st.button(f"🗑️ Delete", key=f"delete_{rule['id']}"):
                        st.session_state.custom_rules.pop(i)
                        st.rerun()
        
        # Export/Import
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Export Rules"):
                rules_yaml = yaml.dump({'custom_rules': st.session_state.custom_rules}, default_flow_style=False)
                st.download_button(
                    "📥 Download Rules YAML",
                    rules_yaml,
                    file_name=f"custom_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml",
                    mime="text/yaml"
                )
        
        with col2:
            uploaded_file = st.file_uploader("📤 Import Rules", type=['yaml', 'yml'])
            if uploaded_file:
                try:
                    imported_rules = yaml.safe_load(uploaded_file)
                    if 'custom_rules' in imported_rules:
                        st.session_state.custom_rules.extend(imported_rules['custom_rules'])
                        st.success(f"✅ Imported {len(imported_rules['custom_rules'])} rules")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error importing rules: {e}")

    def test_rules_interface(self):
        """Interface for testing rules"""
        st.subheader("Test Rules")
        
        if not st.session_state.custom_rules:
            st.info("No rules to test. Create some rules first.")
            return
        
        # Quick test with sample configurations
        test_configs = [
            {
                'name': 'Standard Triple',
                'igu_type': 'Triple',
                'outer_glass': {'thickness': 3, 'manufacturer': 'Generic', 'coating': 'clear'},
                'inner_glass': {'thickness': 3, 'manufacturer': 'Cardinal', 'coating': '272'},
                'air_gap': 12,
                'gas_type': '90K'
            },
            {
                'name': 'High-Performance Quad',
                'igu_type': 'Quad', 
                'outer_glass': {'thickness': 6, 'manufacturer': 'Guardian', 'coating': '366'},
                'inner_glass': {'thickness': 3, 'manufacturer': 'Guardian', 'coating': '180'},
                'air_gap': 10,
                'gas_type': '95A'
            }
        ]
        
        for config in test_configs:
            st.write(f"**Testing: {config['name']}**")
            violations = self.test_configuration_against_rules(config)
            
            if violations:
                for violation in violations:
                    if violation['severity'] == 'error':
                        st.error(f"❌ {violation['message']}")
                    else:
                        st.warning(f"⚠️ {violation['message']}")
            else:
                st.success("✅ Passes all rules")
            st.write("---")

    def test_configuration_against_rules(self, config):
        """Test a configuration against all rules"""
        violations = []
        
        for rule in st.session_state.custom_rules:
            if not rule['enabled']:
                continue
                
            if self.evaluate_rule_condition(rule['condition'], config):
                severity = 'error' if rule['type'] == 'constraint' else 'warning'
                violations.append({
                    'rule_name': rule['name'],
                    'message': rule['action']['message'],
                    'severity': severity
                })
        
        return violations

    def evaluate_rule_condition(self, condition, config):
        """Evaluate if a rule condition is met"""
        # Simple evaluation - in real implementation, this would be more sophisticated
        field = condition['field']
        operator = condition['operator']
        value = condition['value']
        
        # Get actual value from config
        if field == 'igu_type':
            actual = config.get('igu_type')
        elif field == 'gas_type':
            actual = config.get('gas_type')
        elif field == 'air_gap':
            actual = config.get('air_gap')
        elif field == 'thickness':
            actual = config.get('outer_glass', {}).get('thickness')
        else:
            return False
        
        # Evaluate condition
        if operator == 'equals':
            return actual == value
        elif operator == 'not_equals':
            return actual != value
        elif operator == 'greater_than':
            return actual > value
        elif operator == 'less_than':
            return actual < value
        elif operator == 'between':
            return value[0] <= actual <= value[1]
        elif operator == 'in_list':
            return actual in value
        
        return False

    def load_existing_rules(self):
        """Load existing custom rules"""
        # In real implementation, load from file or database
        return []

# Streamlit interface
def main():
    st.set_page_config(page_title="ALPENSIMULATOR Rule Builder", layout="wide")
    
    builder = RuleBuilder()
    builder.create_rule_builder_interface()

if __name__ == "__main__":
    main()