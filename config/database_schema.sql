-- Alpen IGU Simulator Database Schema
-- SQLite database structure for integrated system

-- Glass Types Table - Store IGSDB glass properties
CREATE TABLE IF NOT EXISTS glass_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nfrc_id INTEGER UNIQUE,
    manufacturer TEXT NOT NULL,
    product_name TEXT,
    coating_name TEXT,
    nominal_thickness_mm REAL,
    actual_thickness_mm REAL,
    thermal_properties JSON,  -- U, SHGC, VT, thermal conductivity, etc.
    optical_properties JSON,  -- Transmittance, reflectance spectra
    igsdb_data JSON,          -- Raw IGSDB API response
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IGU Configurations Table - Store IGU designs
CREATE TABLE IF NOT EXISTS igu_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    igu_type TEXT NOT NULL,  -- 'Triple' or 'Quad'
    outer_airspace_in REAL,  -- Outer airspace in inches
    outer_airspace_mm REAL,  -- Outer airspace in mm
    gas_type TEXT,           -- Gas fill type
    glass_layers JSON,       -- Array of [glass_nfrc_id, flipped_flag]
    air_gaps JSON,           -- Gap specifications with thickness
    configuration_hash TEXT UNIQUE, -- For duplicate detection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simulation Results Table - Store computed performance data
CREATE TABLE IF NOT EXISTS simulation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER,
    u_value_metric REAL,           -- W/m2.K
    u_value_imperial REAL,         -- Btu/hr.ft2.F
    shgc REAL,                     -- Solar Heat Gain Coefficient
    vt REAL,                       -- Visible Transmittance
    temperature_data JSON,         -- Surface temperatures
    environmental_conditions JSON, -- Temperature conditions used
    simulation_metadata JSON,      -- PyWinCalc parameters
    simulation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (config_id) REFERENCES igu_configurations(id)
);

-- Optimization Runs Table - Store optimization analysis
CREATE TABLE IF NOT EXISTS optimization_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    rules_config JSON,       -- Rules used for optimization
    filter_criteria JSON,    -- Applied filters
    results_summary JSON,    -- Statistical summary
    best_configs JSON,       -- Top N configurations with scores
    total_evaluated INTEGER, -- Number of configs evaluated
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT DEFAULT 'system'
);

-- System Configuration Table - Store system settings and rules
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_glass_nfrc ON glass_types(nfrc_id);
CREATE INDEX IF NOT EXISTS idx_config_hash ON igu_configurations(configuration_hash);
CREATE INDEX IF NOT EXISTS idx_config_type ON igu_configurations(igu_type);
CREATE INDEX IF NOT EXISTS idx_results_config ON simulation_results(config_id);
CREATE INDEX IF NOT EXISTS idx_results_timestamp ON simulation_results(simulation_timestamp);
CREATE INDEX IF NOT EXISTS idx_optimization_timestamp ON optimization_runs(run_timestamp);

-- Insert default system configurations
INSERT OR REPLACE INTO system_config (key, value, description) VALUES
('igsdb_api_token', '"0e94db9c8cda032d3eaa083e21984350c17633ca"', 'IGSDB API authentication token'),
('default_weights', '{"u_value": 0.4, "shgc": 0.3, "vt": 0.3}', 'Default optimization weights'),
('performance_thresholds', '{"u_value_max": 0.25, "shgc_min": 0.25, "vt_min": 0.4}', 'Default performance thresholds'),
('preferred_manufacturers', '["Guardian", "Pilkington", "Cardinal"]', 'Preferred glass manufacturers'),
('system_version', '"2.0.0"', 'System version number');