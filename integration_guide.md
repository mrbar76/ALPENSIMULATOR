# Integration Guide: Making Your Alpen System Fully Configurable

## 🎯 What's Been Created

### 1. **Configurable Rules System**
- `config/alpen_igu_rules.yaml` - All rules in editable YAML format
- `configurable_rules.py` - Python interface to load/modify rules
- `live_rules_editor.py` - Web interface to edit rules (http://localhost:8505)

### 2. **Updated Generator**
- `igu_input_generator_configurable.py` - Uses configurable rules instead of hardcoded values

### 3. **Key Fixes Applied**
- ✅ **i89 coating**: Fixed to Surface 6 (Triple) and Surface 8 (Quad)
- ✅ **All constants**: Now configurable (TOL, MIN_EDGE_NOMINAL, etc.)
- ✅ **Flipping logic**: Uses configurable coating placement rules
- ✅ **Validation rules**: All IGU validation now configurable

## 🚀 How to Integrate

### Option A: Replace Your Current Files
```bash
# Backup your original files
cp igu_input_generator.py igu_input_generator_original.py
cp Alpen_IGU_Simulation.py Alpen_IGU_Simulation_original.py

# Use the configurable versions
cp igu_input_generator_configurable.py igu_input_generator.py
```

### Option B: Gradual Integration
Keep your original files and test the new system:

```bash
# Test the configurable version
python3 igu_input_generator_configurable.py

# Compare results with original
python3 igu_input_generator.py  # Original hardcoded version
```

## 🔧 Using the Configurable System

### 1. **Edit Rules Without Code Changes**
- Open: http://localhost:8505 (Live Rules Editor)
- Change any constant (TOL, MIN_EDGE_NOMINAL, etc.)
- Test new coating placement rules
- Save changes instantly

### 2. **Key Configuration Areas**

#### **Constants Tab**: Edit hardcoded values
- TOL (thickness tolerance)
- MIN_EDGE_NOMINAL (minimum edge glass thickness)
- MIN_AIRGAP (minimum air gap)
- QUAD_OA_MIN_INCH (minimum OA for quads)
- CENTER_MAX_THICKNESS (maximum center glass thickness)

#### **Coating & Surface Tab**: Fix coating placement
- i89 surfaces: 6 (triple), 8 (quad) ✅ CORRECTED
- Standard low-E surfaces: 2,5 (triple), 2,7 (quad)
- Center coating surfaces: 4 (triple), 6 (quad)

#### **Flipping Logic Tab**: Test coating orientation
- Test any glass position + coating combination
- See exactly when glass gets flipped
- Verify i89 ends up on correct surface

### 3. **Programming Interface**

Replace hardcoded values in your code:

```python
# OLD WAY (hardcoded)
TOL = 0.3
MIN_EDGE_NOMINAL = 3.0
QUAD_OA_MIN_INCH = 0.75

def should_flip(position, coating_side, coating_name):
    # Hardcoded logic...
    
# NEW WAY (configurable)
from configurable_rules import AlpenRulesConfig
config = AlpenRulesConfig()

TOL = config.get_tolerance()
MIN_EDGE_NOMINAL = config.get_min_edge_nominal() 
QUAD_OA_MIN_INCH = config.get_quad_oa_min_inch()

def should_flip(position, coating_side, coating_name, igu_type):
    return config.should_flip(position, coating_side, coating_name, igu_type)
```

## 🧪 Testing Your Changes

### 1. **Rule Validation**
The Live Rules Editor includes a "Test & Validate" tab:
- Tests sample configurations against your rules
- Shows which rules pass/fail
- Validates i89 coating placement
- Checks OA minimums for quads

### 2. **Before/After Comparison**
```bash
# Generate with original hardcoded rules
python3 igu_input_generator.py
mv igu_simulation_input_table.csv input_table_original.csv

# Generate with configurable rules  
python3 igu_input_generator_configurable.py
mv igu_simulation_input_table.csv input_table_configurable.csv

# Compare results
python3 -c "
import pandas as pd
orig = pd.read_csv('input_table_original.csv')
new = pd.read_csv('input_table_configurable.csv')
print(f'Original: {len(orig)} configs')
print(f'Configurable: {len(new)} configs')
print(f'Triple split: {orig[\"IGU Type\"].value_counts()}')
print(f'Configurable split: {new[\"IGU Type\"].value_counts()}')
"
```

### 3. **Coating Placement Verification**
Use the flipping test in the Live Rules Editor:
- Test: position="inner", coating_side="back", coating_name="i89", igu_type="triple"
- Should show: **KEEP ORIENTATION** (i89 ends up on surface 6)
- Test: position="inner", coating_side="front", coating_name="i89", igu_type="triple"  
- Should show: **FLIP GLASS** (i89 ends up on surface 6)

## 📊 Benefits of Configurable System

### 1. **No More Code Changes for Rule Updates**
- Change thickness tolerances → Edit in web interface
- Adjust OA minimums → Edit in web interface  
- Fix coating placement → Edit in web interface
- Test new rules → Real-time validation

### 2. **Auditable Rule Changes**
- All changes logged with timestamps
- Rule modification history tracked
- Easy to revert bad changes
- Document why rules were changed

### 3. **Expert Knowledge Capture**
- Rules documented with descriptions
- Surface numbering clearly explained
- Coating placement requirements explicit
- Materials science rationale preserved

### 4. **Easier Collaboration**
- Subject matter experts can edit rules directly
- No need to understand Python code
- Visual interface for complex logic
- Test changes before applying

## 🔄 Workflow Integration

### Current Workflow:
1. Edit CSV ingredients → 2. Run hardcoded generator → 3. Run simulation → 4. Optimize

### New Configurable Workflow:
1. Edit CSV ingredients → 2. **Configure rules via web interface** → 3. Run configurable generator → 4. Run simulation → 5. Optimize

The new step 2 allows you to:
- Adjust rules based on new requirements
- Fix issues without code changes  
- Test rule variations quickly
- Document rule changes for compliance

## 🎉 Next Steps

1. **Test the configurable system**: Run `igu_input_generator_configurable.py`
2. **Open the Live Rules Editor**: http://localhost:8505
3. **Verify i89 placement**: Check coating placement tab
4. **Test rule changes**: Use the test & validate tab
5. **Compare results**: Ensure configurable system matches your expectations
6. **Integrate gradually**: Replace hardcoded values one at a time

## 💡 Pro Tips

- **Start with small changes**: Test one rule at a time
- **Use the validation tab**: Always test before generating thousands of configs
- **Document your changes**: Add modification notes in the rules editor
- **Keep backups**: Original files saved as `*_original.py`
- **Monitor results**: Compare configuration counts before/after rule changes

The configurable system maintains 100% compatibility with your existing workflow while making every rule editable!