"""
Alpen IGU Simulator - Data Manager

Centralized data persistence layer for the integrated system.
Handles database operations, IGSDB cache management, and CSV import/export.
"""

import sqlite3
import json
import pandas as pd
import hashlib
import pickle
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataManager:
    """
    Centralized data management for the Alpen IGU Simulator.
    Provides database operations, caching, and data persistence.
    """
    
    def __init__(self, db_path: str = "data/alpen.db", schema_path: str = "config/database_schema.sql"):
        """
        Initialize the Data Manager.
        
        Args:
            db_path: Path to SQLite database file
            schema_path: Path to database schema SQL file
        """
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)
        self.cache_dir = Path("data/igsdb_cache")
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"DataManager initialized with database: {self.db_path}")
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Execute schema if it exists
                if self.schema_path.exists():
                    with open(self.schema_path, 'r') as f:
                        schema_sql = f.read()
                    conn.executescript(schema_sql)
                    logger.info("Database schema initialized successfully")
                else:
                    logger.warning(f"Schema file not found: {self.schema_path}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with JSON support."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    # === Glass Types Management ===
    
    def get_glass_type(self, nfrc_id: int) -> Optional[Dict]:
        """Get glass type by NFRC ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM glass_types WHERE nfrc_id = ?", 
                (nfrc_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_glass_type(self, nfrc_id: int, manufacturer: str, 
                       product_name: str = None, coating_name: str = None,
                       nominal_thickness: float = None, actual_thickness: float = None,
                       thermal_properties: Dict = None, optical_properties: Dict = None,
                       igsdb_data: Dict = None) -> int:
        """
        Save or update glass type information.
        
        Returns:
            The glass type ID (primary key)
        """
        with self.get_connection() as conn:
            # Check if exists
            existing = self.get_glass_type(nfrc_id)
            
            if existing:
                # Update existing
                conn.execute("""
                    UPDATE glass_types 
                    SET manufacturer = ?, product_name = ?, coating_name = ?,
                        nominal_thickness_mm = ?, actual_thickness_mm = ?,
                        thermal_properties = ?, optical_properties = ?, 
                        igsdb_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE nfrc_id = ?
                """, (
                    manufacturer, product_name, coating_name,
                    nominal_thickness, actual_thickness,
                    json.dumps(thermal_properties) if thermal_properties else None,
                    json.dumps(optical_properties) if optical_properties else None,
                    json.dumps(igsdb_data) if igsdb_data else None,
                    nfrc_id
                ))
                return existing['id']
            else:
                # Insert new
                cursor = conn.execute("""
                    INSERT INTO glass_types 
                    (nfrc_id, manufacturer, product_name, coating_name,
                     nominal_thickness_mm, actual_thickness_mm,
                     thermal_properties, optical_properties, igsdb_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nfrc_id, manufacturer, product_name, coating_name,
                    nominal_thickness, actual_thickness,
                    json.dumps(thermal_properties) if thermal_properties else None,
                    json.dumps(optical_properties) if optical_properties else None,
                    json.dumps(igsdb_data) if igsdb_data else None
                ))
                return cursor.lastrowid
    
    def get_all_glass_types(self, manufacturer_filter: List[str] = None) -> pd.DataFrame:
        """Get all glass types as DataFrame, optionally filtered by manufacturer."""
        query = "SELECT * FROM glass_types"
        params = []
        
        if manufacturer_filter:
            placeholders = ','.join(['?' for _ in manufacturer_filter])
            query += f" WHERE manufacturer IN ({placeholders})"
            params = manufacturer_filter
        
        query += " ORDER BY manufacturer, nfrc_id"
        
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    # === IGU Configurations Management ===
    
    def _generate_config_hash(self, igu_type: str, outer_airspace_in: float,
                            gas_type: str, glass_layers: List, air_gaps: List) -> str:
        """Generate unique hash for IGU configuration."""
        config_str = f"{igu_type}|{outer_airspace_in}|{gas_type}|{json.dumps(glass_layers, sort_keys=True)}|{json.dumps(air_gaps, sort_keys=True)}"
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def save_igu_configuration(self, name: str, igu_type: str, 
                              outer_airspace_in: float, gas_type: str,
                              glass_layers: List, air_gaps: List) -> int:
        """
        Save IGU configuration.
        
        Args:
            name: Configuration name
            igu_type: 'Triple' or 'Quad'
            outer_airspace_in: Outer airspace in inches
            gas_type: Gas fill type
            glass_layers: List of [nfrc_id, flipped] pairs
            air_gaps: List of gap specifications
        
        Returns:
            Configuration ID
        """
        config_hash = self._generate_config_hash(
            igu_type, outer_airspace_in, gas_type, glass_layers, air_gaps
        )
        
        outer_airspace_mm = outer_airspace_in * 25.4
        
        with self.get_connection() as conn:
            # Check for existing configuration
            cursor = conn.execute(
                "SELECT id FROM igu_configurations WHERE configuration_hash = ?",
                (config_hash,)
            )
            existing = cursor.fetchone()
            
            if existing:
                return existing[0]
            
            # Insert new configuration
            cursor = conn.execute("""
                INSERT INTO igu_configurations 
                (name, igu_type, outer_airspace_in, outer_airspace_mm, 
                 gas_type, glass_layers, air_gaps, configuration_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, igu_type, outer_airspace_in, outer_airspace_mm,
                gas_type, json.dumps(glass_layers), json.dumps(air_gaps),
                config_hash
            ))
            
            return cursor.lastrowid
    
    def get_igu_configuration(self, config_id: int) -> Optional[Dict]:
        """Get IGU configuration by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM igu_configurations WHERE id = ?",
                (config_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse JSON fields
                result['glass_layers'] = json.loads(result['glass_layers'])
                result['air_gaps'] = json.loads(result['air_gaps'])
                return result
            return None
    
    def get_all_igu_configurations(self) -> pd.DataFrame:
        """Get all IGU configurations as DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM igu_configurations ORDER BY created_at DESC",
                conn
            )
    
    # === Simulation Results Management ===
    
    def save_simulation_result(self, config_id: int, u_value_metric: float,
                              u_value_imperial: float, shgc: float, vt: float,
                              temperature_data: Dict = None,
                              environmental_conditions: Dict = None,
                              simulation_metadata: Dict = None) -> int:
        """Save simulation results."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO simulation_results
                (config_id, u_value_metric, u_value_imperial, shgc, vt,
                 temperature_data, environmental_conditions, simulation_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id, u_value_metric, u_value_imperial, shgc, vt,
                json.dumps(temperature_data) if temperature_data else None,
                json.dumps(environmental_conditions) if environmental_conditions else None,
                json.dumps(simulation_metadata) if simulation_metadata else None
            ))
            
            return cursor.lastrowid
    
    def get_simulation_results(self, config_id: int = None, 
                              limit: int = None) -> pd.DataFrame:
        """Get simulation results, optionally filtered by configuration."""
        query = """
            SELECT sr.*, ic.name as config_name, ic.igu_type, ic.gas_type
            FROM simulation_results sr
            LEFT JOIN igu_configurations ic ON sr.config_id = ic.id
        """
        params = []
        
        if config_id:
            query += " WHERE sr.config_id = ?"
            params.append(config_id)
        
        query += " ORDER BY sr.simulation_timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    # === IGSDB Cache Management ===
    
    def get_igsdb_cache(self, nfrc_id: int) -> Optional[bytes]:
        """Get cached IGSDB data for NFRC ID."""
        cache_file = self.cache_dir / f"{nfrc_id}.pkl"
        
        if cache_file.exists():
            # Check if cache is still valid (24 hours)
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age < timedelta(hours=24):
                try:
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load cache for NFRC {nfrc_id}: {e}")
                    cache_file.unlink(missing_ok=True)
        
        return None
    
    def set_igsdb_cache(self, nfrc_id: int, data: bytes) -> None:
        """Cache IGSDB data for NFRC ID."""
        cache_file = self.cache_dir / f"{nfrc_id}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to cache NFRC {nfrc_id}: {e}")
    
    def clear_old_cache(self, hours_old: int = 168) -> int:
        """Clear cache files older than specified hours. Returns count of deleted files."""
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < cutoff_time:
                    cache_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error processing cache file {cache_file}: {e}")
        
        logger.info(f"Cleared {deleted_count} old cache files")
        return deleted_count
    
    # === CSV Import/Export ===
    
    def import_csv_configurations(self, csv_path: str) -> Tuple[int, int]:
        """
        Import IGU configurations from CSV file.
        
        Returns:
            Tuple of (successful_imports, total_rows)
        """
        try:
            df = pd.read_csv(csv_path)
            successful = 0
            total = len(df)
            
            for idx, row in df.iterrows():
                try:
                    # Extract glass layers
                    glass_layers = []
                    nfrc_cols = [c for c in df.columns if 'NFRC ID' in c]
                    flip_cols = [c for c in df.columns if c.startswith('Flip Glass')]
                    
                    for i, nfrc_col in enumerate(nfrc_cols):
                        if pd.notna(row[nfrc_col]):
                            flip_col = flip_cols[i] if i < len(flip_cols) else None
                            flipped = False
                            if flip_col and flip_col in row:
                                flipped = row[flip_col] in [True, 'True', 1]
                            
                            glass_layers.append([int(row[nfrc_col]), flipped])
                    
                    # Build air gaps
                    air_gaps = [{"thickness_mm": row.get('Air Gap (mm)', 12.0)}]
                    
                    # Generate name
                    name = f"{row['IGU Type']}_{row['OA (in)']}in_{row['Gas Type']}_config_{idx}"
                    
                    # Save configuration
                    self.save_igu_configuration(
                        name=name,
                        igu_type=row['IGU Type'],
                        outer_airspace_in=row['OA (in)'],
                        gas_type=row['Gas Type'],
                        glass_layers=glass_layers,
                        air_gaps=air_gaps
                    )
                    
                    successful += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to import row {idx}: {e}")
            
            logger.info(f"Imported {successful}/{total} configurations from CSV")
            return successful, total
            
        except Exception as e:
            logger.error(f"Failed to import CSV file {csv_path}: {e}")
            return 0, 0
    
    def export_results_to_csv(self, file_path: str, 
                             optimization_run_id: int = None) -> bool:
        """Export simulation results to CSV file."""
        try:
            if optimization_run_id:
                # Export specific optimization run
                query = """
                    SELECT sr.*, ic.name as config_name, ic.igu_type, 
                           ic.outer_airspace_in, ic.gas_type
                    FROM simulation_results sr
                    JOIN igu_configurations ic ON sr.config_id = ic.id
                    JOIN optimization_runs_configs orc ON ic.id = orc.config_id
                    WHERE orc.optimization_run_id = ?
                    ORDER BY sr.u_value_imperial
                """
                params = [optimization_run_id]
            else:
                # Export all results
                query = """
                    SELECT sr.*, ic.name as config_name, ic.igu_type,
                           ic.outer_airspace_in, ic.gas_type  
                    FROM simulation_results sr
                    JOIN igu_configurations ic ON sr.config_id = ic.id
                    ORDER BY sr.simulation_timestamp DESC
                """
                params = []
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                df.to_csv(file_path, index=False)
                
            logger.info(f"Exported {len(df)} results to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    # === System Configuration ===
    
    def get_system_config(self, key: str, default: Any = None) -> Any:
        """Get system configuration value."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM system_config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default
    
    def set_system_config(self, key: str, value: Any, 
                         description: str = None, updated_by: str = 'system') -> None:
        """Set system configuration value."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_config (key, value, description, updated_by)
                VALUES (?, ?, ?, ?)
            """, (key, json.dumps(value), description, updated_by))
    
    # === Database Maintenance ===
    
    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space and optimize performance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            logger.info("Database vacuumed successfully")
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        stats = {}
        
        with self.get_connection() as conn:
            # Table counts
            tables = ['glass_types', 'igu_configurations', 'simulation_results', 'optimization_runs']
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Database size
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size") 
            page_size = cursor.fetchone()[0]
            stats['database_size_mb'] = round((page_count * page_size) / 1024 / 1024, 2)
            
            # Last vacuum
            cursor = conn.execute("PRAGMA optimize")
            
        return stats