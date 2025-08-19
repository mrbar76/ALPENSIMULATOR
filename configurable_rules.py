"""
Configurable Rules System for Alpen IGU Generator

Replaces hardcoded constants and rules in igu_input_generator.py 
with configurable YAML-based rules that can be edited without code changes.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AlpenRulesConfig:
    """
    Configurable rules system that replaces hardcoded constants
    from igu_input_generator.py with editable YAML configuration.
    """
    
    def __init__(self, config_file: str = "config/alpen_igu_rules.yaml"):
        """Initialize with rules configuration file."""
        self.config_file = Path(config_file)
        self.rules = {}
        self.load_rules()
        
    def load_rules(self) -> None:
        """Load rules from YAML configuration file."""
        try:
            if not self.config_file.exists():
                logger.error(f"Rules config file not found: {self.config_file}")
                self.rules = self._get_default_rules()
                return
                
            with open(self.config_file, 'r') as f:
                self.rules = yaml.safe_load(f) or {}
                
            logger.info(f"Loaded Alpen IGU rules from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load rules config: {e}")
            self.rules = self._get_default_rules()
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Return default rules if config file fails to load."""
        return {
            'constants': {
                'TOL': 0.3,
                'MIN_EDGE_NOMINAL': 3.0,
                'MIN_AIRGAP': 6.0,
                'QUAD_OA_MIN_INCH': 0.75,
                'CENTER_MAX_THICKNESS': 1.1
            }
        }
    
    # === CONSTANTS (replacements for hardcoded values) ===
    
    def get_tolerance(self) -> float:
        """Get TOL constant."""
        return self.rules.get('constants', {}).get('TOL', 0.3)
    
    def get_min_edge_nominal(self) -> float:
        """Get MIN_EDGE_NOMINAL constant."""
        return self.rules.get('constants', {}).get('MIN_EDGE_NOMINAL', 3.0)
    
    def get_min_airgap(self) -> float:
        """Get MIN_AIRGAP constant."""
        return self.rules.get('constants', {}).get('MIN_AIRGAP', 3.0)
    
    def get_quad_oa_min_inch(self) -> float:
        """Get QUAD_OA_MIN_INCH constant."""
        return self.rules.get('constants', {}).get('QUAD_OA_MIN_INCH', 0.75)
    
    def get_center_max_thickness(self) -> float:
        """Get center glass maximum thickness."""
        return self.rules.get('constants', {}).get('CENTER_MAX_THICKNESS', 1.1)
    
    # === SURFACE DEFINITIONS ===
    
    def get_surface_map(self, igu_type: str) -> Dict[int, str]:
        """Get surface number to description mapping."""
        igu_key = igu_type.lower()
        surface_map = self.rules.get('surface_validation', {}).get(f'{igu_key}_surface_map', {})
        return {int(k): v for k, v in surface_map.items()}
    
    def get_surface_count(self, igu_type: str) -> int:
        """Get total surface count for IGU type."""
        igu_key = igu_type.lower()
        return self.rules.get('igu_types', {}).get(igu_key, {}).get('surface_count', 6)
    
    # === COATING PLACEMENT RULES ===
    
    def get_standard_lowe_surfaces(self, igu_type: str) -> List[int]:
        """Get standard low-E coating surface positions."""
        igu_key = igu_type.lower()
        return self.rules.get('coating_rules', {}).get('standard_lowe_surfaces', {}).get(igu_key, [])
    
    def get_center_coating_surfaces(self, igu_type: str) -> List[int]:
        """Get center coating surface positions."""
        igu_key = igu_type.lower()
        return self.rules.get('coating_rules', {}).get('center_coating_surfaces', {}).get(igu_key, [])
    
    def get_i89_surface(self, igu_type: str) -> int:
        """Get i89 coating surface position."""
        igu_key = igu_type.lower()
        i89_rules = self.rules.get('coating_rules', {}).get('special_coating_rules', {}).get('i89_coating', {})
        return i89_rules.get(f'{igu_key}_surface', 6 if igu_key == 'triple' else 8)
    
    def get_nxlite_surface(self, igu_type: str) -> int:
        """Get NxLite coating surface position."""
        igu_key = igu_type.lower()
        nxlite_rules = self.rules.get('coating_rules', {}).get('special_coating_rules', {}).get('nxlite_coating', {})
        return nxlite_rules.get(f'{igu_key}_surface', 4 if igu_key == 'triple' else 6)
    
    # === FLIPPING RULES ===
    
    def should_flip(self, position: str, coating_side: str, coating_name: str = '', igu_type: str = 'triple') -> bool:
        """
        Configurable version of should_flip function.
        
        Args:
            position: Glass position ('outer', 'center', 'quad_inner', 'inner')
            coating_side: Coating side ('front', 'back', 'none')
            coating_name: Name of coating (for special rules)
            igu_type: IGU type ('triple', 'quad')
        """
        
        # Special handling for i89 coating
        if position == "inner" and "i89" in coating_name.lower():
            return self._should_flip_i89(coating_side, igu_type)
        
        # Get standard flipping rules
        flip_rules = self.rules.get('flipping_rules', {}).get('flip_logic', {})
        position_rule = flip_rules.get(position, {})
        
        if not position_rule:
            logger.warning(f"No flip rule found for position: {position}")
            return False
        
        # Check if we should flip based on coating side
        flip_if = position_rule.get('flip_if_coating_side')
        keep_if = position_rule.get('keep_if_coating_side')
        
        if coating_side == flip_if:
            return True
        elif coating_side == keep_if:
            return False
        else:
            return False
    
    def _should_flip_i89(self, coating_side: str, igu_type: str) -> bool:
        """Special flipping logic for i89 coatings."""
        igu_key = igu_type.lower()
        i89_flip_rules = self.rules.get('flipping_rules', {}).get('special_flip_rules', {}).get('i89_coating', {})
        igu_rules = i89_flip_rules.get(igu_key, {})
        
        flip_if = igu_rules.get('flip_if_coating_side', 'front')
        keep_if = igu_rules.get('keep_if_coating_side', 'back')
        
        if coating_side == flip_if:
            return True
        elif coating_side == keep_if:
            return False
        else:
            return False
    
    # === GLASS LAYER RULES ===
    
    def center_allowed(self, thickness_mm: float, coating_side: str, igu_type: str) -> bool:
        """
        Configurable version of center_allowed function.
        
        Args:
            thickness_mm: Glass thickness
            coating_side: Coating side
            igu_type: IGU type
        """
        max_thickness = self.get_center_max_thickness()
        tolerance = self.get_tolerance()
        
        # Check thickness
        if thickness_mm > max_thickness + tolerance:
            return False
        
        # Quad special rule: inner center must be uncoated if center is coated
        if igu_type.lower() == "quad":
            quad_rules = self.rules.get('glass_rules', {}).get('center_glass', {}).get('quad_special_rules', {})
            if quad_rules.get('quad_inner_uncoated_if_center_coated', False):
                if coating_side != "none":
                    return False
        
        return True
    
    def quad_center_rule(self, thickness_mm: float) -> bool:
        """Configurable version of quad_center_rule."""
        max_thickness = self.get_center_max_thickness()
        tolerance = self.get_tolerance()
        return thickness_mm <= max_thickness + tolerance
    
    def edges_manufacturer_match_required(self) -> bool:
        """Check if edge glass manufacturer matching is required."""
        return self.rules.get('manufacturer_rules', {}).get('edge_matching', {}).get('enabled', True)
    
    def lowe_ordering_required(self) -> bool:
        """Check if low-E ordering rule is required."""
        return self.rules.get('lowe_ordering', {}).get('enabled', True)
    
    # === GAS FILL RULES ===
    
    def get_gas_configuration(self, gas_type: str) -> Dict[str, Any]:
        """Get gas fill configuration for simulation."""
        gas_rules = self.rules.get('gas_fill_rules', {}).get('supported_gases', {})
        return gas_rules.get(gas_type, {})
    
    def get_gap_count(self, igu_type: str) -> int:
        """Get number of gaps for IGU type."""
        igu_key = igu_type.lower()
        return self.rules.get('gas_fill_rules', {}).get('gap_count_by_igu_type', {}).get(igu_key, 2)
    
    # === VALIDATION RULES ===
    
    def validate_igu_configuration(self, igu_type: str, glass_layers: List[Any]) -> Tuple[bool, List[str]]:
        """
        Validate IGU configuration against rules.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        igu_key = igu_type.lower()
        igu_rules = self.rules.get('igu_types', {}).get(igu_key, {})
        
        if not igu_rules:
            errors.append(f"Unsupported IGU type: {igu_type}")
            return False, errors
        
        # Check glass count
        expected_count = igu_rules.get('glass_count', 3)
        actual_count = len([g for g in glass_layers if g is not None])
        
        if actual_count != expected_count:
            errors.append(f"{igu_type} requires {expected_count} glass layers, found {actual_count}")
        
        # Check validation rules
        validation_rules = igu_rules.get('validation_rules', [])
        
        for rule in validation_rules:
            if isinstance(rule, dict):
                for rule_name, rule_value in rule.items():
                    if rule_name == 'glass_4_must_be_empty' and rule_value:
                        if len(glass_layers) > 3 and glass_layers[3] is not None:
                            errors.append("Triple-pane cannot have Glass 4")
                    
                    elif rule_name == 'all_required_glasses_present' and isinstance(rule_value, list):
                        for pos in rule_value:
                            if pos > len(glass_layers) or glass_layers[pos-1] is None:
                                errors.append(f"Missing required glass in position {pos}")
        
        return len(errors) == 0, errors
    
    # === RULE MODIFICATION ===
    
    def update_rule(self, path: str, value: Any) -> bool:
        """
        Update a rule value and save to file.
        
        Args:
            path: Dot-separated path to rule (e.g., 'constants.TOL')
            value: New value
        """
        try:
            # Navigate to rule location
            keys = path.split('.')
            current = self.rules
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Update value
            current[keys[-1]] = value
            
            # Save to file
            return self.save_rules()
            
        except Exception as e:
            logger.error(f"Failed to update rule {path}: {e}")
            return False
    
    def save_rules(self) -> bool:
        """Save current rules to YAML file."""
        try:
            # Create backup
            backup_path = Path(str(self.config_file) + '.backup')
            if self.config_file.exists():
                backup_path.write_text(self.config_file.read_text())
            
            # Add modification entry
            if 'modification_history' not in self.rules:
                self.rules['modification_history'] = []
            
            from datetime import datetime
            self.rules['modification_history'].append({
                'date': datetime.now().isoformat(),
                'author': 'user',
                'description': 'Rule updated via configuration system'
            })
            
            # Save rules
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self.rules, f, default_flow_style=False, indent=2)
            
            logger.info(f"Rules saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            return False
    
    def get_all_rules(self) -> Dict[str, Any]:
        """Get complete rules configuration."""
        return self.rules.copy()
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """Get summary of current rule configuration."""
        return {
            'config_file': str(self.config_file),
            'constants_count': len(self.rules.get('constants', {})),
            'igu_types': list(self.rules.get('igu_types', {}).keys()),
            'supported_gases': list(self.rules.get('gas_fill_rules', {}).get('supported_gases', {}).keys()),
            'surface_validation_enabled': 'surface_validation' in self.rules,
            'coating_rules_defined': 'coating_rules' in self.rules,
            'flipping_rules_defined': 'flipping_rules' in self.rules
        }


# === INTEGRATION HELPERS ===

def create_configurable_igu_generator():
    """
    Create a wrapper that replaces hardcoded values in igu_input_generator.py
    with configurable rules.
    
    Usage:
        # Replace hardcoded constants
        config = AlpenRulesConfig()
        
        # Instead of: TOL = 0.3
        TOL = config.get_tolerance()
        
        # Instead of: MIN_EDGE_NOMINAL = 3.0  
        MIN_EDGE_NOMINAL = config.get_min_edge_nominal()
        
        # Instead of: should_flip(position, coating_side, coating_name)
        should_flip = config.should_flip(position, coating_side, coating_name, igu_type)
    """
    return AlpenRulesConfig()


if __name__ == "__main__":
    # Test the configuration system
    config = AlpenRulesConfig()
    
    print("=== Alpen Rules Configuration Test ===")
    print(f"Tolerance (TOL): {config.get_tolerance()}")
    print(f"Min Edge Nominal: {config.get_min_edge_nominal()}")
    print(f"Quad OA Min: {config.get_quad_oa_min_inch()}")
    
    print(f"\nTriple i89 surface: {config.get_i89_surface('triple')}")
    print(f"Quad i89 surface: {config.get_i89_surface('quad')}")
    
    print(f"\nTriple standard low-E surfaces: {config.get_standard_lowe_surfaces('triple')}")
    print(f"Quad standard low-E surfaces: {config.get_standard_lowe_surfaces('quad')}")
    
    # Test flipping
    print(f"\nFlip test - i89 on inner, coating_side='front': {config.should_flip('inner', 'front', 'i89', 'triple')}")
    print(f"Flip test - i89 on inner, coating_side='back': {config.should_flip('inner', 'back', 'i89', 'triple')}")
    
    print(f"\nRule summary: {config.get_rule_summary()}")