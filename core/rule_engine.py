"""
Alpen IGU Simulator - Rule Engine

Configuration management system for handling rules, constraints, and optimization parameters.
Supports hierarchical configuration with YAML files and runtime rule updates.
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from copy import deepcopy

logger = logging.getLogger(__name__)

@dataclass
class PerformanceTarget:
    """Performance target specification."""
    excellent: float
    very_good: float
    good: float
    maximum: float
    units: str = "Btu/hr.ft2.F"

@dataclass
class OptimizationWeights:
    """Optimization weights for different performance metrics."""
    u_value: float = 0.40
    shgc: float = 0.30
    vt: float = 0.25
    cost: float = 0.05
    
    def normalize(self) -> 'OptimizationWeights':
        """Normalize weights to sum to 1.0."""
        total = self.u_value + self.shgc + self.vt + self.cost
        if total > 0:
            return OptimizationWeights(
                u_value=self.u_value / total,
                shgc=self.shgc / total,
                vt=self.vt / total,
                cost=self.cost / total
            )
        return self

@dataclass
class GlassSelectionRules:
    """Rules for glass type selection and filtering."""
    preferred_manufacturers: List[str]
    excluded_manufacturers: List[str]
    allow_mixed_manufacturers: bool
    min_thickness_mm: float
    max_thickness_mm: float
    preferred_nominal_thicknesses: List[int]
    required_coatings: List[str] = None
    coating_preferences: List[str] = None

class RuleEngine:
    """
    Configuration management system for the Alpen IGU Simulator.
    Handles loading, validation, and hierarchical resolution of rules.
    """
    
    def __init__(self, 
                 system_config_path: str = "config/system_defaults.yaml",
                 project_config_path: str = "config/project_config.yaml",
                 user_config_path: str = "config/user_preferences.yaml"):
        """
        Initialize the Rule Engine.
        
        Args:
            system_config_path: Path to system default configuration
            project_config_path: Path to project-specific configuration  
            user_config_path: Path to user preferences configuration
        """
        self.system_config_path = Path(system_config_path)
        self.project_config_path = Path(project_config_path)
        self.user_config_path = Path(user_config_path)
        
        # Configuration hierarchy (system < project < user)
        self.system_config = {}
        self.project_config = {}
        self.user_config = {}
        
        # Runtime overrides
        self.runtime_config = {}
        
        # Load configurations
        self.reload_configurations()
        
        logger.info("RuleEngine initialized with hierarchical configuration")
    
    def reload_configurations(self) -> None:
        """Reload all configuration files."""
        try:
            # Load system defaults
            if self.system_config_path.exists():
                with open(self.system_config_path, 'r') as f:
                    self.system_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded system config: {self.system_config_path}")
            else:
                logger.warning(f"System config not found: {self.system_config_path}")
            
            # Load project config
            if self.project_config_path.exists():
                with open(self.project_config_path, 'r') as f:
                    self.project_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded project config: {self.project_config_path}")
            
            # Load user config
            if self.user_config_path.exists():
                with open(self.user_config_path, 'r') as f:
                    self.user_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded user config: {self.user_config_path}")
                
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            raise
    
    def _merge_configs(self, *configs: Dict) -> Dict:
        """Recursively merge multiple configuration dictionaries."""
        result = {}
        
        for config in configs:
            if not config:
                continue
                
            for key, value in config.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._merge_configs(result[key], value)
                else:
                    result[key] = deepcopy(value)
        
        return result
    
    def get_config(self, path: str = None, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path (e.g., 'performance_targets.u_value.maximum')
            default: Default value if path not found
        
        Returns:
            Configuration value or default
        """
        # Merge all configurations in priority order
        merged_config = self._merge_configs(
            self.system_config,
            self.project_config, 
            self.user_config,
            self.runtime_config
        )
        
        if path is None:
            return merged_config
        
        # Navigate path
        current = merged_config
        for key in path.split('.'):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_runtime_config(self, path: str, value: Any) -> None:
        """
        Set runtime configuration override.
        
        Args:
            path: Dot-separated path
            value: Value to set
        """
        keys = path.split('.')
        current = self.runtime_config
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set value
        current[keys[-1]] = value
        logger.info(f"Set runtime config: {path} = {value}")
    
    def clear_runtime_config(self) -> None:
        """Clear all runtime configuration overrides."""
        self.runtime_config = {}
        logger.info("Cleared runtime configuration overrides")
    
    # === Performance Rules ===
    
    def get_u_value_target(self) -> PerformanceTarget:
        """Get U-value performance targets."""
        u_config = self.get_config('performance_targets.u_value', {})
        return PerformanceTarget(
            excellent=u_config.get('excellent', 0.15),
            very_good=u_config.get('very_good', 0.20),
            good=u_config.get('good', 0.25),
            maximum=u_config.get('maximum', 0.35),
            units=u_config.get('units', 'Btu/hr.ft2.F')
        )
    
    def get_shgc_range(self, climate_zone: str = None) -> Dict[str, float]:
        """
        Get SHGC performance range.
        
        Args:
            climate_zone: 'hot', 'mixed', 'cold', or None for default
        """
        shgc_config = self.get_config('performance_targets.shgc', {})
        
        if climate_zone and 'climate_zones' in shgc_config:
            zone_config = shgc_config['climate_zones'].get(climate_zone, {})
            if zone_config:
                return zone_config
        
        # Return default range
        return shgc_config.get('default_range', {'min': 0.20, 'max': 0.60})
    
    def get_vt_range(self) -> Dict[str, float]:
        """Get Visible Transmittance performance range."""
        vt_config = self.get_config('performance_targets.vt', {})
        return {
            'minimum': vt_config.get('minimum', 0.35),
            'preferred': vt_config.get('preferred', 0.50),
            'excellent': vt_config.get('excellent', 0.70),
            'maximum': vt_config.get('maximum', 0.85)
        }
    
    # === Glass Selection Rules ===
    
    def get_glass_selection_rules(self) -> GlassSelectionRules:
        """Get glass selection and filtering rules."""
        glass_config = self.get_config('glass_selection', {})
        mfr_config = glass_config.get('manufacturers', {})
        thickness_config = glass_config.get('thickness_constraints', {})
        coating_config = glass_config.get('coating_preferences', {})
        
        return GlassSelectionRules(
            preferred_manufacturers=mfr_config.get('preferred', []),
            excluded_manufacturers=mfr_config.get('excluded', []),
            allow_mixed_manufacturers=mfr_config.get('allow_mixed', True),
            min_thickness_mm=thickness_config.get('min_mm', 3.0),
            max_thickness_mm=thickness_config.get('max_mm', 12.0),
            preferred_nominal_thicknesses=thickness_config.get('preferred_nominal', [4, 5, 6, 8]),
            required_coatings=coating_config.get('required_coatings'),
            coating_preferences=coating_config.get('preferred_coatings')
        )
    
    def get_preferred_manufacturers(self) -> List[str]:
        """Get preferred glass manufacturers."""
        return self.get_config('glass_selection.manufacturers.preferred', [])
    
    def get_excluded_manufacturers(self) -> List[str]:
        """Get excluded glass manufacturers."""
        return self.get_config('glass_selection.manufacturers.excluded', [])
    
    # === IGU Design Rules ===
    
    def get_supported_igu_types(self) -> List[str]:
        """Get supported IGU types."""
        return self.get_config('igu_design.supported_types', ['Triple', 'Quad'])
    
    def get_preferred_igu_type(self) -> str:
        """Get preferred IGU type."""
        return self.get_config('igu_design.preferred_type', 'Triple')
    
    def get_airspace_constraints(self) -> Dict[str, Union[float, List[float]]]:
        """Get airspace design constraints."""
        airspace_config = self.get_config('igu_design.airspace', {})
        return {
            'min_inches': airspace_config.get('min_inches', 0.375),
            'max_inches': airspace_config.get('max_inches', 1.0),
            'preferred_inches': airspace_config.get('preferred_inches', [0.5, 0.625, 0.75])
        }
    
    def get_gas_fill_options(self) -> Dict[str, Any]:
        """Get gas fill options and preferences."""
        gas_config = self.get_config('igu_design.gas_fills', {})
        return {
            'supported': gas_config.get('supported', ['Air', '95A', '90K']),
            'default': gas_config.get('default', '95A'),
            'cost_factors': gas_config.get('cost_factors', {'Air': 1.0, '95A': 1.1, '90K': 1.3})
        }
    
    # === Optimization Rules ===
    
    def get_optimization_weights(self) -> OptimizationWeights:
        """Get optimization weights."""
        weights_config = self.get_config('optimization.default_weights', {})
        weights = OptimizationWeights(
            u_value=weights_config.get('u_value', 0.40),
            shgc=weights_config.get('shgc', 0.30),
            vt=weights_config.get('vt', 0.25),
            cost=weights_config.get('cost', 0.05)
        )
        return weights.normalize()
    
    def get_optimization_constraints(self) -> Dict[str, Any]:
        """Get optimization constraints."""
        return self.get_config('optimization.constraints', {
            'max_results': 50,
            'min_score_threshold': 0.60,
            'diversity_factor': 0.1
        })
    
    def get_optimization_objectives(self) -> Dict[str, List[str]]:
        """Get optimization objectives."""
        return self.get_config('optimization.objectives', {
            'minimize': ['u_value'],
            'maximize': ['shgc', 'vt'],
            'primary': 'u_value'
        })
    
    # === Filter Methods ===
    
    def filter_glass_by_manufacturer(self, glass_df, strict: bool = False) -> Any:
        """
        Filter glass types by manufacturer rules.
        
        Args:
            glass_df: DataFrame of glass types
            strict: If True, only include preferred manufacturers
        """
        rules = self.get_glass_selection_rules()
        
        # Exclude blacklisted manufacturers
        if rules.excluded_manufacturers:
            glass_df = glass_df[~glass_df['manufacturer'].isin(rules.excluded_manufacturers)]
        
        # If strict mode, only include preferred
        if strict and rules.preferred_manufacturers:
            glass_df = glass_df[glass_df['manufacturer'].isin(rules.preferred_manufacturers)]
        
        return glass_df
    
    def filter_glass_by_thickness(self, glass_df) -> Any:
        """Filter glass types by thickness constraints."""
        rules = self.get_glass_selection_rules()
        
        # Filter by thickness range
        mask = ((glass_df['actual_thickness_mm'] >= rules.min_thickness_mm) &
                (glass_df['actual_thickness_mm'] <= rules.max_thickness_mm))
        
        return glass_df[mask]
    
    def score_performance(self, u_value: float, shgc: float, vt: float, 
                         cost_factor: float = 1.0) -> float:
        """
        Calculate performance score based on current rules.
        
        Args:
            u_value: U-value in Btu/hr.ft2.F
            shgc: Solar Heat Gain Coefficient
            vt: Visible Transmittance  
            cost_factor: Cost multiplier
        
        Returns:
            Normalized performance score (0-1)
        """
        weights = self.get_optimization_weights()
        u_target = self.get_u_value_target()
        
        # Normalize metrics (higher is better)
        u_score = max(0, 1 - (u_value - u_target.excellent) / (u_target.maximum - u_target.excellent))
        u_score = min(1, u_score)
        
        # SHGC and VT are context-dependent, so use simple scaling
        shgc_score = min(1, max(0, shgc / 0.6))  # Assume 0.6 as good SHGC
        vt_score = min(1, max(0, vt / 0.8))      # Assume 0.8 as excellent VT
        
        # Cost score (lower cost is better)
        cost_score = max(0, 1 - (cost_factor - 1) / 0.5)  # Assume 50% premium is maximum
        
        # Weighted score
        total_score = (
            weights.u_value * u_score +
            weights.shgc * shgc_score +
            weights.vt * vt_score +
            weights.cost * cost_score
        )
        
        return min(1.0, max(0.0, total_score))
    
    def validate_igu_configuration(self, igu_type: str, airspace_in: float, 
                                  gas_type: str, glass_layers: List) -> Dict[str, Any]:
        """
        Validate IGU configuration against rules.
        
        Returns:
            Dictionary with 'valid' boolean and 'issues' list
        """
        issues = []
        
        # Check IGU type
        if igu_type not in self.get_supported_igu_types():
            issues.append(f"Unsupported IGU type: {igu_type}")
        
        # Check airspace
        airspace_rules = self.get_airspace_constraints()
        if airspace_in < airspace_rules['min_inches']:
            issues.append(f"Airspace too small: {airspace_in}in < {airspace_rules['min_inches']}in")
        elif airspace_in > airspace_rules['max_inches']:
            issues.append(f"Airspace too large: {airspace_in}in > {airspace_rules['max_inches']}in")
        
        # Check gas type
        gas_options = self.get_gas_fill_options()
        if gas_type not in gas_options['supported']:
            issues.append(f"Unsupported gas type: {gas_type}")
        
        # Check glass layer count
        expected_layers = 3 if igu_type == 'Triple' else 4
        if len(glass_layers) != expected_layers:
            issues.append(f"Expected {expected_layers} glass layers for {igu_type}, got {len(glass_layers)}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    # === Configuration Export/Import ===
    
    def export_current_config(self, file_path: str) -> bool:
        """Export current merged configuration to YAML file."""
        try:
            merged_config = self.get_config()
            with open(file_path, 'w') as f:
                yaml.dump(merged_config, f, default_flow_style=False, indent=2)
            logger.info(f"Exported configuration to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def create_user_config(self, overrides: Dict[str, Any], 
                          file_path: str = None) -> bool:
        """Create user configuration file with specified overrides."""
        try:
            if file_path is None:
                file_path = self.user_config_path
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                yaml.dump(overrides, f, default_flow_style=False, indent=2)
            
            # Reload configurations to include new user config
            self.reload_configurations()
            
            logger.info(f"Created user configuration at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create user configuration: {e}")
            return False
    
    # === Rule Validation ===
    
    def validate_rules(self) -> Dict[str, Any]:
        """Validate current rule configuration for consistency."""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check optimization weights sum
            weights = self.get_optimization_weights()
            total_weight = weights.u_value + weights.shgc + weights.vt + weights.cost
            if abs(total_weight - 1.0) > 0.001:
                validation_results['warnings'].append(
                    f"Optimization weights sum to {total_weight:.3f}, not 1.0"
                )
            
            # Check performance target consistency
            u_target = self.get_u_value_target()
            if u_target.excellent > u_target.very_good:
                validation_results['errors'].append(
                    "U-value excellent target should be lower than very_good"
                )
            
            # Check airspace constraints
            airspace = self.get_airspace_constraints()
            if airspace['min_inches'] >= airspace['max_inches']:
                validation_results['errors'].append(
                    "Airspace min_inches should be less than max_inches"
                )
            
            # Check VT range
            vt_range = self.get_vt_range()
            if vt_range['minimum'] > vt_range['preferred']:
                validation_results['errors'].append(
                    "VT minimum should be less than preferred"
                )
            
            validation_results['valid'] = len(validation_results['errors']) == 0
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation failed: {e}")
        
        return validation_results