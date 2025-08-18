import streamlit as st
import pandas as pd

st.title("🧪 Simple Test App")
st.write("If you can see this, Streamlit is working!")

st.header("Test Data")
test_data = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50],
    'C': ['a', 'b', 'c', 'd', 'e']
})

st.dataframe(test_data)
st.success("✅ Basic Streamlit functionality working!")

st.header("System Info")
st.write(f"Current directory: {st.session_state}")