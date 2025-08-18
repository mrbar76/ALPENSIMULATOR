"""
Create a fixed version with correct indentation
"""

# Copy the problematic section and fix it
fixed_section = '''
        # Process results if generation succeeded
        if 'result' in locals() and result.returncode == 0:
            # Show detailed results
            try:
                df = pd.read_csv('igu_simulation_input_table.csv')
                st.success(f"✅ Generated {len(df):,} IGU configurations")
                
                # Load glass catalogs for name mapping
                try:
                    glass_io_df = pd.read_csv('input_glass_catalog_inner_outer.csv')
                    glass_center_df = pd.read_csv('input_glass_catalog_center.csv')
                    
                    # Create NFRC to name mapping
                    nfrc_to_name = {}
                    for _, row in glass_io_df.iterrows():
                        nfrc_to_name[row['NFRC_ID']] = row['Short_Name']
                    for _, row in glass_center_df.iterrows():
                        nfrc_to_name[row['NFRC_ID']] = row['Short_Name']
                except Exception as e:
                    nfrc_to_name = {}
                    st.warning(f"Could not load glass names: {e}")
                
                # Configuration Summary
                st.subheader("📊 Configuration Summary")
                igu_counts = df['IGU Type'].value_counts()
                gas_counts = df['Gas Type'].value_counts()
                oa_counts = df['OA (in)'].value_counts()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Triple Configs", f"{igu_counts.get('Triple', 0):,}")
                with col2:
                    st.metric("Quad Configs", f"{igu_counts.get('Quad', 0):,}")
                with col3:
                    st.metric("Gas Types", len(gas_counts))
                    for gas, count in gas_counts.items():
                        st.text(f"• {gas}: {count:,}")
                with col4:
                    st.metric("OA Sizes", len(oa_counts))
                    st.text(f"Range: {oa_counts.index.min():.3f}\" - {oa_counts.index.max():.3f}\"")
                
                st.divider()
                
                # Ready for simulation
                st.session_state.configurations_generated = True
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success("🎉 Configurations ready for simulation!")
                with col2:
                    if st.button("Proceed to Step 4: Run Simulation", type="primary"):
                        st.session_state.workflow_step = 4
                        st.rerun()
                
            except Exception as e:
                st.error(f"Could not load generated configurations: {e}")
'''

print("Fixed section created - need to manually apply this")