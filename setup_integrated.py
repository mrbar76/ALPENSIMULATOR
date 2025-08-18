"""
Alpen IGU Simulator - Integrated System Setup

Setup script to initialize the integrated system database and configuration.
"""

import os
import sys
import logging
from pathlib import Path

# Add core modules to path
sys.path.append(str(Path(__file__).parent))

from core.data_manager import DataManager
from core.rule_engine import RuleEngine
from legacy.migration_tools import MigrationTools

def setup_logging():
    """Configure logging for setup process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('setup.log')
        ]
    )

def initialize_system():
    """Initialize the integrated system."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== Alpen IGU Simulator - Integrated System Setup ===")
        
        # 1. Initialize DataManager (creates database and schema)
        logger.info("1. Initializing database...")
        data_manager = DataManager()
        logger.info("   ✓ Database initialized successfully")
        
        # 2. Initialize RuleEngine (loads configuration)
        logger.info("2. Loading configuration system...")
        rule_engine = RuleEngine()
        
        # Validate rules
        validation = rule_engine.validate_rules()
        if not validation['valid']:
            logger.warning("   ⚠ Configuration validation issues found:")
            for error in validation['errors']:
                logger.warning(f"     - {error}")
        else:
            logger.info("   ✓ Configuration loaded and validated")
        
        # 3. Check for existing data to migrate
        logger.info("3. Checking for existing data to migrate...")
        
        migration_tools = MigrationTools(data_manager, rule_engine)
        
        # Check for legacy files
        legacy_files = {
            'igsdb_cache': Path('igsdb_layer_cache.pkl'),
            'input_csv': Path('igu_simulation_input_table.csv'),
            'results_csv': None  # Will check for results files
        }
        
        # Look for results CSV files
        for file_path in Path('.').glob('igu_simulation_results_*.csv'):
            legacy_files['results_csv'] = file_path
            break
        
        migration_needed = False
        for file_type, file_path in legacy_files.items():
            if file_path and file_path.exists():
                logger.info(f"   Found {file_type}: {file_path}")
                migration_needed = True
        
        if migration_needed:
            logger.info("4. Migrating existing data...")
            
            migration_summary = migration_tools.full_migration(
                input_csv=str(legacy_files['input_csv']),
                cache_file=str(legacy_files['igsdb_cache']),
                results_csv=str(legacy_files['results_csv']) if legacy_files['results_csv'] else None
            )
            
            if migration_summary['success']:
                logger.info("   ✓ Data migration completed successfully")
                
                # Show migration summary
                cache_mig = migration_summary.get('cache_migration', {})
                config_mig = migration_summary.get('config_migration', {})
                results_mig = migration_summary.get('results_migration', {})
                
                logger.info(f"     - IGSDB cache: {cache_mig.get('migrated', 0)}/{cache_mig.get('total', 0)} entries")
                logger.info(f"     - Configurations: {config_mig.get('migrated', 0)}/{config_mig.get('total', 0)} configs")
                
                if results_mig:
                    logger.info(f"     - Results: {results_mig.get('migrated', 0)}/{results_mig.get('total', 0)} results")
                
            else:
                logger.warning("   ⚠ Data migration completed with issues")
        else:
            logger.info("4. No existing data found to migrate")
        
        # 5. Display system statistics
        logger.info("5. System initialization complete!")
        
        db_stats = data_manager.get_database_stats()
        logger.info("   Database Statistics:")
        for table, count in db_stats.items():
            if table.endswith('_count'):
                table_name = table.replace('_count', '').replace('_', ' ').title()
                logger.info(f"     - {table_name}: {count}")
        
        logger.info(f"   Database Size: {db_stats.get('database_size_mb', 0):.1f} MB")
        
        # 6. Show next steps
        logger.info("\n=== Next Steps ===")
        logger.info("1. Run the integrated dashboard:")
        logger.info("   streamlit run web/main_dashboard.py")
        logger.info("\n2. Or use the migration tools directly:")
        logger.info("   python legacy/migration_tools.py --help")
        logger.info("\n3. Or run the original programs (still compatible):")
        logger.info("   streamlit run Alpen_Advisor_v47.py")
        
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False

def main():
    """Main setup entry point."""
    setup_logging()
    
    # Create necessary directories
    directories = ['data', 'data/exports', 'data/igsdb_cache', 'config']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Run setup
    success = initialize_system()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("📊 You can now run: streamlit run Alpen_Advisor_v47.py")
        print("🔧 Or use the integrated system when ready")
    else:
        print("\n❌ Setup failed. Check setup.log for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()