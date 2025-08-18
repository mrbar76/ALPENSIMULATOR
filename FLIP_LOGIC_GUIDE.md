# 🔄 Smart Flip Logic Guide

## Overview
The Enhanced ALPENSIMULATOR includes intelligent flip logic that automatically recommends optimal glass orientations based on coating properties and IGU position.

## 🧠 Intelligent Auto-Flip Logic

### Coating Type Detection
The system automatically detects coating types from glass names:

| **Coating Type** | **Keywords** | **Examples** |
|------------------|--------------|--------------|
| **Clear Glass** | clear | Generic Clear 3mm, Clear Float |
| **Hard Coat Low-E** | loe, low-e + 272, 277, 366 | LoE 272, LoE 277 |
| **Soft Coat Low-E** | loe, low-e + 180, 366 | LoE 180, LoE 366 |
| **High Performance** | i89, guardian | Guardian i89, Performance Glass |

### 🎯 Smart Flip Recommendations by Position

#### **Outer Glass (Position 1)**
- **Clear Glass**: No flip needed ❌
- **Hard Coat Low-E**: **FLIP** ✅ (coating faces interior - surface 2)
- **Soft Coat Low-E**: **FLIP** ✅ (coating faces interior - protected position)
- **High Performance**: **FLIP** ✅ (optimal performance orientation)

#### **Quad-Inner Glass (Position 2 in Quad)**
- **Clear Glass**: No flip needed ❌
- **Hard Coat Low-E**: No flip ❌ (coating faces exterior - surface 6/7)
- **Soft Coat Low-E**: No flip ❌ (coating faces exterior in protected position)
- **High Performance**: No flip ❌

#### **Center Glass (Thin glass in air gap)**
- **Clear Glass**: No flip needed ❌
- **Hard Coat Low-E**: No flip ❌ (coating faces air gap)
- **Soft Coat Low-E**: **FLIP** ✅ (coating in protected air gap position)
- **High Performance**: **FLIP** ✅ (protected position)

#### **Inner Glass (Interior surface)**
- **Clear Glass**: No flip needed ❌
- **Hard Coat Low-E**: No flip ❌ (coating faces interior - surface 3/5)
- **Soft Coat Low-E**: No flip ❌ (coating faces interior - protected)
- **High Performance**: No flip ❌

## 🎨 User Interface Features

### ✅ Interactive Catalog Editor
- **Real-time editing**: Click checkboxes to flip glass orientations
- **Visual recommendations**: 🤖 indicators show smart recommendations
- **Color coding**: Green for recommended, gray for not recommended
- **Batch operations**: Apply smart logic to multiple glasses at once

### 🔍 Filtering Options
- **Manufacturer filter**: Focus on specific glass suppliers
- **Coating type filter**: Show only specific coating categories
- **Position filter**: Show glasses available for specific IGU positions

### ⚡ Batch Operations
1. **🤖 Apply Smart Flip Logic**: Auto-set all flips based on coating properties
2. **❌ Clear All Flips**: Reset all flips to False
3. **💾 Save Catalog**: Save current catalog state

## 🔬 Technical Implementation

### Coating Detection Logic
```python
def get_coating_type(glass_name, notes=""):
    name_lower = glass_name.lower()
    
    if 'loe' in name_lower or 'low-e' in name_lower:
        if any(num in name_lower for num in ['272', '277', '366']):
            return 'low_e_hard'  # Hard coat
        else:
            return 'low_e_soft'  # Soft coat
    elif 'i89' in name_lower:
        return 'high_performance'
    elif 'clear' in name_lower:
        return 'clear'
    else:
        return 'unknown'
```

### Smart Recommendation Engine
The system uses a matrix-based approach to determine optimal orientations:

```python
recommendations = {
    'low_e_hard': {
        'outer': True,       # Coating faces interior (surface 2)
        'quad_inner': False, # Coating faces exterior (surface 6/7)
        'center': False,     # Coating faces air gap
        'inner': False       # Coating faces interior (surface 3/5)
    },
    # ... other coating types
}
```

## 🏗️ IGU Surface Numbering Convention

### Triple Pane IGU
```
EXTERIOR | Glass 1 | Air Gap | Glass 2 | Air Gap | Glass 3 | INTERIOR
         Surface 1-2         Surface 3-4         Surface 5-6
```

### Quad Pane IGU
```
EXTERIOR | Glass 1 | Gap | Glass 2 | Gap | Glass 3 | Gap | Glass 4 | INTERIOR
         Surf 1-2        Surf 3-4      Surf 5-6       Surf 7-8
```

## 💡 Best Practices

### For Energy Efficiency
1. **Low-E coatings** should face the interior space when possible
2. **Soft coats** need protected positions (not exposed to weather)
3. **Hard coats** can handle more exposure but still perform better facing interior

### For Durability
1. **Soft coats** must be in protected positions (surfaces 2, 3, 4, 5)
2. **Hard coats** can be on any surface but prefer interior-facing
3. **Clear glass** orientation doesn't affect performance

### For User Experience
1. Use **🤖 Apply Smart Flip Logic** for initial setup
2. **Review recommendations** for special cases
3. **Test different orientations** for performance optimization
4. **Save frequently** to preserve custom settings

## 🚀 Advanced Features

### Custom Rules Integration
The system integrates with the existing rules engine to ensure:
- Flip settings respect coating placement rules
- Surface specifications align with manufacturer recommendations
- Performance targets are met with optimal orientations

### Performance Impact
Proper flip orientation can improve:
- **U-Value**: 5-15% improvement with correct Low-E orientation
- **SHGC**: 10-20% variation based on coating position
- **VT**: Minimal impact but affects glare control
- **Durability**: Significant impact on coating lifespan

## 📊 Quality Assurance

### Validation Checks
The system performs automatic validation:
1. **Coating compatibility**: Ensures coatings are in suitable positions
2. **Performance consistency**: Flags unusual combinations
3. **Manufacturer specs**: Cross-references with glass data
4. **Rules compliance**: Validates against configuration rules

This smart flip management system makes it easy to optimize IGU configurations while ensuring both performance and durability standards are met.