#!/usr/bin/env python3
"""
Demo of Streamlined Rule Builder for ALPENSIMULATOR
Shows how to create rules without any coding or YAML editing
"""

import streamlit as st

def main():
    st.set_page_config(page_title="Rule Builder Demo", layout="wide")
    
    st.title("🔧 Streamlined Rule Builder Demo")
    st.info("See how easy it is to create IGU generation rules!")
    
    # Show the three different approaches
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🎯 Quick Setup")
        st.success("**Best for most users**")
        st.write("Pre-built toggles for common rules:")
        st.write("✅ Same manufacturer required")
        st.write("✅ Emissivity validation")
        st.write("✅ Spacer range constraints")
        st.write("✅ Gas-spacer optimization")
        
        if st.button("Try Quick Setup"):
            st.balloons()
            st.success("Perfect for 80% of use cases!")
    
    with col2:
        st.subheader("🔧 Visual Builder")
        st.info("**For custom requirements**")
        st.write("Point-and-click rule creation:")
        st.write("🎨 No coding required")
        st.write("📝 Plain English conditions")
        st.write("🎯 Visual action builder")
        st.write("🧪 Built-in testing")
        
        if st.button("Try Visual Builder"):
            st.snow()
            st.info("Great for unique business rules!")
    
    with col3:
        st.subheader("⚙️ Advanced YAML")
        st.warning("**Power users only**")
        st.write("Direct YAML editing:")
        st.write("🔧 Full control")
        st.write("📊 Complex conditions")
        st.write("⚡ Batch operations")
        st.write("🚀 Advanced features")
        
        if st.button("Try Advanced Mode"):
            st.error("⚠️ Requires YAML knowledge!")
    
    st.divider()
    
    # Comparison table
    st.subheader("📊 Comparison of Rule Building Methods")
    
    comparison_data = {
        'Feature': [
            'Ease of use',
            'Setup time',
            'Flexibility',
            'Power user features',
            'Error prone',
            'Best for'
        ],
        '🎯 Quick Setup': [
            '⭐⭐⭐⭐⭐',
            '< 2 minutes',
            '⭐⭐⭐',
            '⭐',
            'Very low',
            'Standard workflows'
        ],
        '🔧 Visual Builder': [
            '⭐⭐⭐⭐',
            '< 5 minutes',
            '⭐⭐⭐⭐⭐',
            '⭐⭐⭐',
            'Low',
            'Custom business rules'
        ],
        '⚙️ Advanced YAML': [
            '⭐⭐',
            '10+ minutes',
            '⭐⭐⭐⭐⭐',
            '⭐⭐⭐⭐⭐',
            'High',
            'Complex integrations'
        ]
    }
    
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    st.table(df)
    
    # Examples
    st.divider()
    st.subheader("💡 Example Rules You Can Create")
    
    examples = [
        {
            'title': '🏭 Manufacturer Compatibility',
            'description': 'Ensure structural compatibility between glass types',
            'rule': "When outer manufacturer = Generic AND inner manufacturer ≠ Generic → Show warning",
            'difficulty': 'Quick Setup'
        },
        {
            'title': '⛽ Gas Optimization',
            'description': 'Optimize gas fill for performance',
            'rule': "When IGU type = Quad AND gas type ≠ 95A → Suggest 95A for better performance",
            'difficulty': 'Visual Builder'
        },
        {
            'title': '📏 Spacer Range Validation',
            'description': 'Ensure spacer thickness stays within manufacturing limits',
            'rule': "When spacer thickness < 6mm OR spacer thickness > 20mm → Block configuration",
            'difficulty': 'Visual Builder'
        },
        {
            'title': '🔬 Complex Validation',
            'description': 'Multi-condition performance rules',
            'rule': "When (coating = i89 OR coating = IS-20) AND spacer < 10mm AND OA < 1.0 → Require upgrade",
            'difficulty': 'Advanced YAML'
        }
    ]
    
    for example in examples:
        with st.expander(f"{example['title']} ({example['difficulty']})"):
            st.write(f"**Purpose:** {example['description']}")
            st.code(example['rule'], language='text')
            
            if example['difficulty'] == 'Quick Setup':
                st.success("✅ Available in Quick Setup mode")
            elif example['difficulty'] == 'Visual Builder':
                st.info("🔧 Create with Visual Builder")
            else:
                st.warning("⚙️ Requires Advanced YAML mode")
    
    st.divider()
    st.subheader("🚀 Ready to Get Started?")
    
    st.write("**Recommended approach:**")
    st.write("1. Start with **Quick Setup** for common rules")
    st.write("2. Use **Visual Builder** for your specific needs")
    st.write("3. Only use **Advanced YAML** if you need complex logic")
    
    if st.button("🎯 Go to Main Application", type="primary"):
        st.success("Ready to build your rules! Switch to the main ALPENSIMULATOR app.")

if __name__ == "__main__":
    main()