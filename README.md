# 🔧 ALPENSIMULATOR

**Advanced IGU (Insulated Glass Unit) Configuration Generator and Thermal Performance Simulator**

A comprehensive materials science workflow for generating, configuring, and optimizing insulated glass unit configurations using PyWinCalc thermal simulation engine and IGSDB (International Glazing Speed Database) integration.

## 🎯 Overview

ALPENSIMULATOR follows a **Materials Science Approach**:
```
Ingredients → Rules → Configuration → Simulation → Optimization
```

### Key Features

- **🔶 Unified Glass Catalog**: Multiselect position system for glass types (Outer, QuadInner, Center, Inner)
- **⚙️ Configurable Rules**: YAML-based rule system for coating placement, flipping logic, and validation
- **🚀 Dual Generation**: Fast generator (limited) and full generator (unlimited configurations)
- **🧪 Thermal Simulation**: PyWinCalc integration for U-value, SHGC, and VT calculations
- **📊 Enhanced Results**: Detailed IGU descriptions with glass names and performance metrics
- **🔄 Progress Tracking**: Real-time progress bars and result persistence

## 🛠️ Installation

### Prerequisites
```bash
# Python 3.8+
pip install pandas streamlit pywincalc requests tqdm pyyaml
```

### Quick Setup
```bash
git clone https://github.com/YOUR_USERNAME/ALPENSIMULATOR.git
cd ALPENSIMULATOR
pip install -r requirements.txt
```

## 🚀 Usage

### Launch Workflow App
```bash
streamlit run workflow_app.py
```

### Step-by-Step Process

1. **📦 Ingredient Management**
   - Edit unified glass catalog with position capabilities
   - Configure gas types, OA sizes, and flip logic

2. **⚙️ Rule Configuration** 
   - Modify YAML rules for coating placement
   - Set constants (MIN_AIRGAP, tolerances, etc.)
   - Configure flipping and validation rules

3. **🔧 Generate Configurations**
   - **Fast Generate**: 2000 configs per type for testing
   - **Full Generate**: Unlimited configurations
   - Both triple-pane and quad-pane IGU support

4. **🧪 Run Simulation**
   - Quick Test: 50 rows (~30-60 seconds)
   - Full Simulation: All configurations
   - Real-time progress tracking

5. **📈 Optimize & Filter**
   - Performance-based filtering
   - Export enhanced results with detailed descriptions

## 📁 Project Structure

```
ALPENSIMULATOR/
├── workflow_app.py              # Main Streamlit workflow app
├── igu_input_generator_unified.py    # Unified multiselect generator  
├── igu_input_generator_fast.py       # Fast generation (limited)
├── simulation_small_test.py          # Quick simulation testing
├── Alpen_IGU_Simulation.py          # Full simulation engine
├── configurable_rules.py            # YAML rules system
├── unified_glass_catalog.csv        # Multiselect glass catalog
├── config/
│   └── alpen_igu_rules.yaml        # Configurable rules
└── input_*.csv                     # Input data files
```

## 🔬 Technical Details

### IGU Structure
- **Triple-pane**: [Outer] |gap| [Center] |gap| [Inner] (2 gaps)
- **Quad-pane**: [Outer] |gap| [QuadInner] |gap| [Center] |gap| [Inner] (3 gaps)

### Air Gap Calculation
```
Gap = (Total OA - Sum of Glass Thicknesses) ÷ Gap Count
```

### Glass Position Rules
- **Outer/Inner**: ≥3mm thick, manufacturer matching required
- **Center**: ≤1.1mm thick for optimal thermal performance
- **QuadInner**: ≥3mm thick, special coating rules apply

## 🧪 Key Improvements

### ✅ Recent Enhancements
- **Fixed Quad Generation**: Resolved core bug preventing quad configurations
- **Unified Catalog**: Single multiselect system replacing separate CSV files
- **Progress Bars**: Real-time simulation progress tracking
- **Result Persistence**: Skip to existing results without re-running
- **Enhanced Descriptions**: Full glass names instead of NFRC numbers only

### Example Enhanced Output
```
Quad | OA: 0.88" | 90K | Gap: 3.99mm | G1: Generic Clear 6mm → G2: LoE 272 on 6mm Clear (Flipped) → G3: Generic 1.1mm Clear → G4: i89 on 6mm Clear (Flipped)
```

## 📊 Performance

- **Fast Generation**: 4,000 configs (2K triple + 2K quad) in ~0.7 seconds
- **Simulation**: ~1.2 seconds per configuration (IGSDB API calls)
- **Success Rate**: 100% for valid configurations
- **Memory**: Efficient caching system for IGSDB data

## 🔧 Configuration

### Key Constants (editable via YAML)
```yaml
constants:
  MIN_AIRGAP: 1.0           # Minimum air gap (mm)
  QUAD_OA_MIN_INCH: 0.5     # Minimum OA for quads (inches) 
  TOL: 0.3                  # Thickness tolerance (mm)
  MIN_EDGE_NOMINAL: 3.0     # Minimum edge glass thickness (mm)
```

### Unified Glass Catalog Format
```csv
NFRC_ID,Short_Name,Manufacturer,Can_Outer,Can_QuadInner,Can_Center,Can_Inner,Flip_Outer,Flip_QuadInner,Flip_Center,Flip_Inner
102,Generic Clear 3mm,Generic,True,True,False,True,False,False,False,False
107,Generic 1.1mm Clear,Generic,False,False,True,False,False,False,False,False
```

## 📝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LBNL PyWinCalc**: Thermal simulation engine
- **IGSDB**: International Glazing Speed Database
- **Streamlit**: Web application framework
- **Materials Science Community**: For the systematic approach

## 📧 Contact

For questions, suggestions, or collaboration opportunities, please open an issue or contact the maintainers.

---

**🔬 Built with Materials Science Principles | 🧪 Powered by PyWinCalc | 🚀 Optimized for Performance**