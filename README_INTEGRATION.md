# Alpen IGU Simulator - Integrated System

## Overview

The Alpen IGU Simulator has been enhanced with an integrated system that provides:

- **Centralized Data Management**: SQLite database with structured storage
- **Configurable Rules**: YAML-based configuration system  
- **Migration Tools**: Seamless transition from existing CSV workflows
- **Backwards Compatibility**: All existing programs continue to work

## Quick Start

### 1. Initial Setup

```bash
# Install dependencies
pip install -r requirements_integrated.txt

# Initialize the integrated system
python setup_integrated.py
```

This will:
- Create the SQLite database
- Load configuration files  
- Migrate existing data automatically
- Validate the system setup

### 2. Run Existing Programs (No Changes Needed)

Your existing programs continue to work exactly as before:

```bash
# Original Streamlit dashboard
streamlit run Alpen_Advisor_v47.py

# Original simulation engine  
python Alpen_IGU_Simulation.py
```

### 3. Use New Integrated Features (Optional)

```bash
# Migration tools
python legacy/migration_tools.py --help

# Direct database access via Python
python -c "from core.data_manager import DataManager; dm = DataManager(); print(dm.get_database_stats())"
```

## System Architecture

### Directory Structure

```
ALPENSIMULATOR/
├── core/                          # New integrated modules
│   ├── data_manager.py           # Database & file operations
│   ├── rule_engine.py            # Configuration management
│   └── __init__.py
├── config/                        # Configuration files
│   ├── system_defaults.yaml      # Base system rules
│   ├── project_config.yaml       # Project overrides
│   ├── rules_schema.yaml         # Validation schema
│   └── database_schema.sql       # Database structure
├── data/                          # Data storage
│   ├── alpen.db                  # SQLite database
│   ├── igsdb_cache/              # IGSDB API cache
│   └── exports/                  # Export files
├── legacy/                        # Migration tools
│   ├── migration_tools.py        # Data migration utilities
│   └── __init__.py
├── web/                           # Future: Enhanced web interface
│   └── __init__.py
├── [Original Files]               # All your existing .py files
├── requirements_integrated.txt    # Enhanced dependencies
├── setup_integrated.py           # System initialization
└── README_INTEGRATION.md         # This file
```

### Core Components

#### 1. Data Manager (`core/data_manager.py`)
- **SQLite Database**: Structured storage for glass types, configurations, results
- **IGSDB Cache**: Enhanced caching system with automatic cleanup
- **CSV Import/Export**: Maintains compatibility with existing workflows
- **Data Validation**: Ensures data integrity and consistency

#### 2. Rule Engine (`core/rule_engine.py`)
- **YAML Configuration**: Human-readable, version-controllable rules
- **Hierarchical Rules**: System defaults → Project config → User preferences
- **Runtime Overrides**: Dynamic rule updates during optimization
- **Validation System**: Automatic rule consistency checking

#### 3. Migration Tools (`legacy/migration_tools.py`)
- **Automatic Migration**: Seamlessly imports existing CSV and cache data
- **Backwards Export**: Can export database back to legacy CSV format
- **Data Validation**: Verifies migration integrity
- **Command-Line Interface**: Flexible migration options

## Configuration System

### Rule Hierarchy

The system uses a hierarchical configuration approach:

1. **System Defaults** (`config/system_defaults.yaml`) - Base configuration
2. **Project Config** (`config/project_config.yaml`) - Project-specific overrides
3. **User Preferences** (`config/user_preferences.yaml`) - Individual user settings
4. **Runtime Config** - Dynamic overrides during program execution

### Example Configuration

```yaml
# config/project_config.yaml
performance_targets:
  u_value:
    target: 0.18           # More aggressive than system default
    maximum: 0.25
  
  shgc:
    target: 0.30
    range:
      min: 0.25
      max: 0.40

optimization:
  default_weights:
    u_value: 0.45          # Higher emphasis on thermal performance
    shgc: 0.25
    vt: 0.25
    cost: 0.05
```

### Modifying Rules

#### Method 1: Edit YAML Files
```bash
# Edit project configuration
nano config/project_config.yaml

# Reload configuration in Python
from core.rule_engine import RuleEngine
rules = RuleEngine()
rules.reload_configurations()
```

#### Method 2: Runtime Overrides
```python
from core.rule_engine import RuleEngine

rules = RuleEngine()
# Temporarily change optimization weights
rules.set_runtime_config('optimization.default_weights.u_value', 0.5)
```

## Migration Guide

### Automatic Migration

The setup script automatically detects and migrates existing data:

```bash
python setup_integrated.py
```

### Manual Migration

```bash
# Migrate specific files
python legacy/migration_tools.py \
  --input-csv my_configurations.csv \
  --cache-file my_cache.pkl \
  --results-csv my_results.csv

# Validate migration
python legacy/migration_tools.py --validate-only

# Export back to legacy format (for testing)
python legacy/migration_tools.py --export-legacy legacy_export.csv
```

### Migration Process

1. **IGSDB Cache**: Converts pickle cache to new caching system
2. **Configuration Data**: Imports CSV configurations to database  
3. **Results Data**: Imports existing simulation results
4. **Validation**: Checks data integrity and consistency
5. **Reporting**: Provides detailed migration summary

## Database Schema

### Key Tables

- **`glass_types`**: Glass properties from IGSDB
- **`igu_configurations`**: IGU design specifications
- **`simulation_results`**: Performance calculation results
- **`optimization_runs`**: Optimization analysis history
- **`system_config`**: Dynamic system configuration

### Accessing Database

```python
from core.data_manager import DataManager

dm = DataManager()

# Get all glass types
glass_df = dm.get_all_glass_types()

# Get system statistics  
stats = dm.get_database_stats()

# Export results
dm.export_results_to_csv('my_results.csv')
```

## Backwards Compatibility

### Existing Programs Continue Working

- ✅ `Alpen_Advisor_v47.py` - Original Streamlit dashboard
- ✅ `Alpen_IGU_Simulation.py` - Original simulation engine
- ✅ `igsdb_interaction.py` - IGSDB API integration
- ✅ All CSV input/output workflows
- ✅ Existing pickle cache files

### No Breaking Changes

- Same file formats supported
- Same API endpoints  
- Same user interface
- Same command-line usage

### Optional Integration

You can adopt the new features gradually:

1. **Start**: Keep using existing programs
2. **Phase 1**: Use migration tools to explore database features
3. **Phase 2**: Customize rules via YAML configuration  
4. **Phase 3**: Use enhanced optimization capabilities
5. **Future**: Adopt new web interface when ready

## Common Tasks

### Check System Status
```python
from core.data_manager import DataManager
from core.rule_engine import RuleEngine

# Database statistics
dm = DataManager()
print(dm.get_database_stats())

# Rule validation
rules = RuleEngine()
print(rules.validate_rules())
```

### Customize Performance Targets
```yaml
# config/user_preferences.yaml
performance_targets:
  u_value:
    excellent: 0.12    # Stricter than default
    maximum: 0.20      # Lower maximum allowed
```

### Run Custom Optimization
```python
from core.rule_engine import RuleEngine

rules = RuleEngine()

# Set custom weights for this session
rules.set_runtime_config('optimization.default_weights.u_value', 0.6)
rules.set_runtime_config('optimization.default_weights.shgc', 0.2)

# Your optimization code here...

# Clear overrides when done
rules.clear_runtime_config()
```

### Export Data
```python
from core.data_manager import DataManager

dm = DataManager()
dm.export_results_to_csv('current_results.csv')
```

## Troubleshooting

### Setup Issues

1. **Database Creation Fails**
   ```bash
   # Check permissions
   ls -la data/
   
   # Reinitialize
   rm -f data/alpen.db
   python setup_integrated.py
   ```

2. **Configuration Loading Errors**
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('config/system_defaults.yaml'))"
   ```

3. **Migration Issues**
   ```bash
   # Check migration status
   python legacy/migration_tools.py --validate-only
   
   # Re-run specific migration
   python legacy/migration_tools.py --input-csv igu_simulation_input_table.csv
   ```

### Performance Issues

1. **Database Too Large**
   ```python
   # Clean up old data
   dm = DataManager()
   dm.clear_old_cache(hours_old=168)  # 1 week
   dm.vacuum_database()
   ```

2. **Slow Queries**
   ```sql
   -- Check database statistics
   PRAGMA table_info(simulation_results);
   PRAGMA index_list(simulation_results);
   ```

## Support

### Logging

All operations are logged. Check `setup.log` for setup issues.

### Recovery

If something goes wrong, you can always:

1. Delete the integrated system files
2. Continue using your original programs  
3. Re-run setup when ready

### Validation

The system includes comprehensive validation:

```python
from core.rule_engine import RuleEngine
from legacy.migration_tools import MigrationTools

# Validate rules
rules = RuleEngine()
validation = rules.validate_rules()

# Validate data migration
migration = MigrationTools()
migration_status = migration.validate_migration()
```

---

## Next Steps

1. **Try It Out**: Run `python setup_integrated.py`
2. **Explore**: Check database contents and configuration options
3. **Customize**: Modify rules in `config/project_config.yaml` 
4. **Integrate**: Gradually adopt new features while keeping existing workflows

The integrated system is designed to enhance your existing workflow without disrupting it. Take your time to explore the new capabilities!