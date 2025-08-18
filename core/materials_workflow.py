"""
Alpen IGU Simulator - Materials Science Workflow Engine

Implements the proper IGU design workflow:
A) Ingredient Management → B) Rule Checking → C) Simulation → D) Optimization
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from pathlib import Path

from .data_manager import DataManager
from .igu_rule_validator import IGUConfigurationValidator, ValidationResult

logger = logging.getLogger(__name__)

class WorkflowStage(Enum):
    """Workflow stages for IGU design process."""
    INGREDIENT_SELECTION = "ingredient_selection"
    RULE_VALIDATION = "rule_validation" 
    SIMULATION_READY = "simulation_ready"
    SIMULATION_COMPLETE = "simulation_complete"
    OPTIMIZATION_READY = "optimization_ready"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    SELECTION_READY = "selection_ready"

@dataclass
class IGUIngredients:
    """Container for IGU material ingredients."""
    glass_layers: List[Dict[str, Any]] = field(default_factory=list)
    gas_fills: List[str] = field(default_factory=list)
    airspace_dimensions: List[float] = field(default_factory=list)
    spacer_materials: List[str] = field(default_factory=list)
    edge_seals: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if all required ingredients are specified."""
        return (len(self.glass_layers) >= 2 and 
                len(self.gas_fills) > 0 and
                len(self.airspace_dimensions) > 0)

@dataclass 
class IGUConfiguration:
    """Complete IGU configuration ready for simulation."""
    config_id: Optional[int] = None
    ingredients: Optional[IGUIngredients] = None
    igu_type: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    stage: WorkflowStage = WorkflowStage.INGREDIENT_SELECTION
    simulation_results: Optional[Dict[str, float]] = None
    optimization_score: Optional[float] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration passed validation."""
        return (self.validation_result is not None and 
                self.validation_result.valid)

class MaterialsWorkflowEngine:
    """
    Materials science workflow engine for IGU design.
    
    Manages the complete workflow from ingredient selection through
    optimization following proper materials science principles.
    """
    
    def __init__(self, data_manager: DataManager = None):
        """Initialize workflow engine."""
        self.data_manager = data_manager or DataManager()
        self.rule_validator = IGUConfigurationValidator()
        
        # Active workflow state
        self.active_configurations: List[IGUConfiguration] = []
        self.ingredient_library = self._load_ingredient_library()
        
        logger.info("Materials Workflow Engine initialized")
    
    def _load_ingredient_library(self) -> Dict[str, Any]:
        """Load available materials ingredient library."""
        try:
            # Get available materials from database
            glass_types = self.data_manager.get_all_glass_types()
            
            library = {
                'glass_substrates': self._organize_glass_substrates(glass_types),
                'coatings': self._extract_coating_options(glass_types),
                'gas_fills': self._get_available_gas_fills(),
                'spacer_systems': self._get_spacer_options(),
                'thickness_options': self._get_thickness_options(glass_types)
            }
            
            logger.info(f"Loaded ingredient library with {len(library)} categories")
            return library
            
        except Exception as e:
            logger.error(f"Failed to load ingredient library: {e}")
            return self._get_default_library()
    
    def _organize_glass_substrates(self, glass_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Organize glass types by substrate categories."""
        substrates = {
            'clear': [],
            'low_iron': [],
            'tinted': [],
            'reflective': []
        }
        
        for _, glass in glass_df.iterrows():
            glass_info = {
                'id': glass['id'],
                'name': glass['name'],
                'manufacturer': glass['manufacturer'],
                'thickness_mm': glass['nominal_thickness_mm'],
                'thermal_properties': {
                    'conductivity': glass.get('thermal_conductivity'),
                    'emissivity': glass.get('ir_transmittance_front', 0.84)  # Default glass emissivity
                }
            }
            
            # Categorize by name/properties
            glass_name = glass['name'].lower()
            if 'clear' in glass_name or 'starphire' in glass_name:
                substrates['clear'].append(glass_info)
            elif 'tint' in glass_name or 'gray' in glass_name or 'bronze' in glass_name:
                substrates['tinted'].append(glass_info)
            elif 'reflect' in glass_name:
                substrates['reflective'].append(glass_info)
            else:
                substrates['clear'].append(glass_info)  # Default category
        
        return substrates
    
    def _extract_coating_options(self, glass_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Extract coating options from glass database."""
        coatings = {
            'low_e': [],
            'solar_control': [],
            'specialty': []
        }
        
        for _, glass in glass_df.iterrows():
            if pd.notna(glass.get('coating_name')):
                coating_info = {
                    'name': glass['coating_name'],
                    'glass_id': glass['id'],
                    'emissivity': glass.get('ir_transmittance_front', 0.84),
                    'solar_transmittance': glass.get('solar_transmittance_front'),
                    'visible_transmittance': glass.get('visible_transmittance_front')
                }
                
                coating_name = str(glass['coating_name']).lower()
                if 'loe' in coating_name or 'low-e' in coating_name:
                    coatings['low_e'].append(coating_info)
                elif 'solar' in coating_name or 'sun' in coating_name:
                    coatings['solar_control'].append(coating_info)
                else:
                    coatings['specialty'].append(coating_info)
        
        return coatings
    
    def _get_available_gas_fills(self) -> List[Dict[str, Any]]:
        """Get available gas fill options."""
        return [
            {
                'name': 'Air',
                'description': 'Standard air fill (78% N2, 21% O2)',
                'thermal_conductivity': 0.024,  # W/m·K
                'cost_factor': 1.0,
                'availability': 'universal'
            },
            {
                'name': '95A',
                'description': '95% Argon, 5% Air',
                'thermal_conductivity': 0.016,  # W/m·K
                'cost_factor': 1.1,
                'availability': 'standard'
            },
            {
                'name': '90K',
                'description': '90% Krypton, 10% Air',
                'thermal_conductivity': 0.009,  # W/m·K
                'cost_factor': 1.35,
                'availability': 'premium'
            }
        ]
    
    def _get_spacer_options(self) -> List[Dict[str, Any]]:
        """Get available spacer system options."""
        return [
            {
                'name': 'Aluminum',
                'thermal_conductivity': 160.0,  # W/m·K
                'cost_factor': 1.0,
                'standard_widths': [0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
            },
            {
                'name': 'Warm Edge',
                'thermal_conductivity': 0.2,  # W/m·K (typical warm edge)
                'cost_factor': 1.2,
                'standard_widths': [0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
            }
        ]
    
    def _get_thickness_options(self, glass_df: pd.DataFrame) -> List[float]:
        """Get available glass thickness options."""
        if len(glass_df) > 0:
            return sorted(glass_df['nominal_thickness_mm'].dropna().unique())
        return [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]
    
    def _get_default_library(self) -> Dict[str, Any]:
        """Return default ingredient library if loading fails."""
        return {
            'glass_substrates': {'clear': [], 'low_iron': [], 'tinted': [], 'reflective': []},
            'coatings': {'low_e': [], 'solar_control': [], 'specialty': []},
            'gas_fills': self._get_available_gas_fills(),
            'spacer_systems': self._get_spacer_options(),
            'thickness_options': [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]
        }
    
    # === PHASE A: INGREDIENT MANAGEMENT ===
    
    def get_ingredient_library(self) -> Dict[str, Any]:
        """Get the complete ingredient library for selection."""
        return self.ingredient_library
    
    def validate_ingredient_compatibility(self, ingredients: IGUIngredients) -> Dict[str, Any]:
        """
        Validate material compatibility before configuration.
        
        Args:
            ingredients: Selected IGU ingredients
            
        Returns:
            Compatibility validation results
        """
        compatibility = {
            'compatible': True,
            'issues': [],
            'recommendations': []
        }
        
        # Check glass layer count
        layer_count = len(ingredients.glass_layers)
        if layer_count < 2:
            compatibility['compatible'] = False
            compatibility['issues'].append('Minimum 2 glass layers required for IGU')
        elif layer_count > 4:
            compatibility['compatible'] = False
            compatibility['issues'].append('Maximum 4 glass layers supported')
        
        # Check airspace count matches glass layers
        expected_airspaces = layer_count - 1
        if len(ingredients.airspace_dimensions) != expected_airspaces:
            compatibility['compatible'] = False
            compatibility['issues'].append(
                f'Need {expected_airspaces} airspaces for {layer_count} glass layers, got {len(ingredients.airspace_dimensions)}'
            )
        
        # Check gas fill count
        if len(ingredients.gas_fills) == 0:
            compatibility['compatible'] = False
            compatibility['issues'].append('At least one gas fill must be specified')
        elif len(ingredients.gas_fills) > 1:
            compatibility['recommendations'].append('Multiple gas fills will create configuration variants')
        
        return compatibility
    
    def create_configurations_from_ingredients(self, ingredients: IGUIngredients) -> List[IGUConfiguration]:
        """
        Create IGU configurations from selected ingredients.
        
        Phase A → Phase B transition: Generate all valid combinations.
        """
        configurations = []
        
        # Validate ingredient compatibility first
        compatibility = self.validate_ingredient_compatibility(ingredients)
        if not compatibility['compatible']:
            logger.error(f"Ingredient compatibility issues: {compatibility['issues']}")
            return configurations
        
        try:
            # Generate configuration combinations
            layer_count = len(ingredients.glass_layers)
            igu_type = 'Triple' if layer_count == 3 else 'Quad' if layer_count == 4 else 'Unknown'
            
            # For each gas fill option
            for gas_fill in ingredients.gas_fills:
                # For each airspace combination (if multiple options provided)
                for airspace_set in self._generate_airspace_combinations(ingredients.airspace_dimensions):
                    config = IGUConfiguration(
                        ingredients=ingredients,
                        igu_type=igu_type,
                        stage=WorkflowStage.INGREDIENT_SELECTION
                    )
                    configurations.append(config)
            
            logger.info(f"Generated {len(configurations)} configurations from ingredients")
            
        except Exception as e:
            logger.error(f"Failed to create configurations from ingredients: {e}")
        
        return configurations
    
    def _generate_airspace_combinations(self, airspace_dims: List[float]) -> List[List[float]]:
        """Generate airspace dimension combinations."""
        # For now, return as single combination
        # In future, could generate multiple combinations for optimization
        return [airspace_dims]
    
    # === PHASE B: RULE VALIDATION ===
    
    def validate_configurations(self, configurations: List[IGUConfiguration]) -> List[IGUConfiguration]:
        """
        Validate IGU configurations against rules.
        
        Phase B: Check each configuration against materials science rules.
        """
        validated_configs = []
        
        for config in configurations:
            try:
                # Convert to format expected by rule validator
                config_data = self._convert_to_validation_format(config)
                
                # Run validation
                validation_result = self.rule_validator.validate_igu_configuration(config_data)
                
                # Update configuration
                config.validation_result = validation_result
                config.stage = WorkflowStage.RULE_VALIDATION
                
                if validation_result.valid:
                    config.stage = WorkflowStage.SIMULATION_READY
                    logger.info(f"Configuration {config.config_id} passed validation")
                else:
                    logger.warning(f"Configuration {config.config_id} failed validation: {len(validation_result.errors)} errors")
                
                validated_configs.append(config)
                
            except Exception as e:
                logger.error(f"Validation failed for configuration {config.config_id}: {e}")
                config.stage = WorkflowStage.RULE_VALIDATION
                validated_configs.append(config)
        
        return validated_configs
    
    def _convert_to_validation_format(self, config: IGUConfiguration) -> Dict[str, Any]:
        """Convert IGUConfiguration to format expected by validator."""
        if not config.ingredients:
            return {}
        
        # Build validation data structure
        validation_data = {
            'igu_type': config.igu_type,
            'outer_airspace_in': config.ingredients.airspace_dimensions[0] if config.ingredients.airspace_dimensions else 0.5,
            'gas_type': config.ingredients.gas_fills[0] if config.ingredients.gas_fills else 'Air'
        }
        
        # Add glass layers
        for i, glass_layer in enumerate(config.ingredients.glass_layers, 1):
            validation_data[f'glass_{i}_id'] = glass_layer.get('id', i)
        
        return validation_data
    
    # === PHASE C: SIMULATION TRIGGER ===
    
    def trigger_simulations(self, configurations: List[IGUConfiguration]) -> List[IGUConfiguration]:
        """
        Trigger PyWinCalc simulations for valid configurations.
        
        Phase C: Run thermal and optical simulations.
        """
        simulation_ready = [c for c in configurations if c.stage == WorkflowStage.SIMULATION_READY]
        
        logger.info(f"Triggering simulations for {len(simulation_ready)} configurations")
        
        # In the real implementation, this would:
        # 1. Convert configurations to PyWinCalc format
        # 2. Run thermal simulation (U-value, SHGC)
        # 3. Run optical simulation (VT, color)
        # 4. Store results back to configuration
        
        # For now, mark as simulation complete
        for config in simulation_ready:
            config.stage = WorkflowStage.SIMULATION_COMPLETE
            config.simulation_results = {
                'u_value': 0.15,  # Placeholder
                'shgc': 0.35,     # Placeholder
                'vt': 0.55        # Placeholder
            }
        
        return configurations
    
    # === PHASE D: OPTIMIZATION ===
    
    def run_optimization(self, configurations: List[IGUConfiguration], 
                        objectives: Dict[str, float] = None) -> List[IGUConfiguration]:
        """
        Run multi-objective optimization on simulated configurations.
        
        Phase D: Optimize configurations based on performance objectives.
        """
        simulation_complete = [c for c in configurations 
                             if c.stage == WorkflowStage.SIMULATION_COMPLETE and c.simulation_results]
        
        if not simulation_complete:
            logger.warning("No configurations available for optimization")
            return configurations
        
        # Default objectives if not provided
        if objectives is None:
            objectives = {
                'u_value': 0.4,    # Minimize U-value (40% weight)
                'shgc': 0.3,       # Context-dependent SHGC (30% weight)
                'vt': 0.25,        # Maximize VT (25% weight) 
                'cost': 0.05       # Minimize cost (5% weight)
            }
        
        logger.info(f"Running optimization for {len(simulation_complete)} configurations")
        
        # Calculate optimization scores
        for config in simulation_complete:
            score = self._calculate_optimization_score(config.simulation_results, objectives)
            config.optimization_score = score
            config.stage = WorkflowStage.OPTIMIZATION_COMPLETE
        
        # Sort by optimization score (highest first)
        optimized_configs = sorted(simulation_complete, 
                                 key=lambda c: c.optimization_score or 0, 
                                 reverse=True)
        
        return configurations
    
    def _calculate_optimization_score(self, results: Dict[str, float], 
                                    objectives: Dict[str, float]) -> float:
        """Calculate weighted optimization score."""
        # Normalize metrics (higher is better for score)
        u_score = max(0, 1 - (results.get('u_value', 0.3) - 0.1) / 0.3)  # Lower U-value is better
        shgc_score = min(1, max(0, results.get('shgc', 0.3) / 0.6))        # Context-dependent
        vt_score = min(1, max(0, results.get('vt', 0.5) / 0.8))            # Higher VT is better
        cost_score = 0.8  # Placeholder cost score
        
        # Weighted total
        total_score = (
            objectives.get('u_value', 0) * u_score +
            objectives.get('shgc', 0) * shgc_score +
            objectives.get('vt', 0) * vt_score +
            objectives.get('cost', 0) * cost_score
        )
        
        return min(1.0, max(0.0, total_score))
    
    # === WORKFLOW MANAGEMENT ===
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status summary."""
        status = {
            'total_configurations': len(self.active_configurations),
            'by_stage': {},
            'validation_summary': {'passed': 0, 'failed': 0},
            'simulation_summary': {'complete': 0, 'pending': 0},
            'optimization_summary': {'complete': 0, 'pending': 0}
        }
        
        for config in self.active_configurations:
            stage = config.stage.value
            status['by_stage'][stage] = status['by_stage'].get(stage, 0) + 1
            
            if config.validation_result:
                if config.validation_result.valid:
                    status['validation_summary']['passed'] += 1
                else:
                    status['validation_summary']['failed'] += 1
            
            if config.simulation_results:
                status['simulation_summary']['complete'] += 1
            else:
                status['simulation_summary']['pending'] += 1
            
            if config.optimization_score is not None:
                status['optimization_summary']['complete'] += 1
            else:
                status['optimization_summary']['pending'] += 1
        
        return status
    
    def run_complete_workflow(self, ingredients: IGUIngredients, 
                            objectives: Dict[str, float] = None) -> List[IGUConfiguration]:
        """
        Run complete workflow from ingredients to optimized results.
        
        A → B → C → D: Full materials science workflow.
        """
        logger.info("Starting complete IGU design workflow")
        
        # Phase A: Create configurations from ingredients
        configurations = self.create_configurations_from_ingredients(ingredients)
        if not configurations:
            logger.error("No configurations generated from ingredients")
            return []
        
        # Phase B: Validate configurations
        configurations = self.validate_configurations(configurations)
        valid_configs = [c for c in configurations if c.is_valid]
        logger.info(f"{len(valid_configs)}/{len(configurations)} configurations passed validation")
        
        # Phase C: Run simulations
        configurations = self.trigger_simulations(configurations)
        simulated_configs = [c for c in configurations if c.simulation_results]
        logger.info(f"{len(simulated_configs)} configurations completed simulation")
        
        # Phase D: Run optimization
        configurations = self.run_optimization(configurations, objectives)
        optimized_configs = [c for c in configurations if c.optimization_score is not None]
        logger.info(f"{len(optimized_configs)} configurations completed optimization")
        
        # Store as active configurations
        self.active_configurations = configurations
        
        logger.info("Complete IGU design workflow finished")
        return configurations