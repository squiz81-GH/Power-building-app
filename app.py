import streamlit as st
import pandas as pd
import re
import os

# Set the page configuration
st.set_page_config(page_title="Squiz's Powerbuilding App", page_icon="🏋️", layout="wide")

st.title("🏋️ Squiz's Powerbuilding 3.0 Web App")
st.markdown("Your interactive, customized training program.")

# Define the local file path (must be in the same folder as this script)
file_path = "Squiz's power building program.csv"

# Function to fix RPE dates caused by Excel conversion
def fix_rpe(val):
    v_str = str(val).strip()
    m1 = re.search(r"2022-0(\d)-0(\d)", v_str)
    if m1: return f"{m1.group(1)}-{m1.group(2)}"
    m2 = re.search(r"2022-(\d{2})-(\d{2})", v_str)
    if m2: return f"{int(m2.group(1))}-{int(m2.group(2))}"
    return val

# Check if the file exists in the folder
if os.path.exists(file_path):
    # Read the local CSV
    df = pd.read_csv(file_path, header=None)
    
    # Dynamically find where the actual workout data starts
    try:
        header_row_idx = df[df[1] == 'Exercise'].index[0]
    except IndexError:
        st.error("Could not find the 'Exercise' header. Please ensure the CSV format is correct.")
        st.stop()
        
    # Sidebar for interactive 1 Rep Max Inputs
    st.sidebar.header("🎯 Your Current 1 Rep Maxes")
    st.sidebar.markdown("Update your 1RMs to automatically recalculate your program loads:")
    squat_max = st.sidebar.number_input("Squat Max", value=130.0, step=2.5)
    bench_max = st.sidebar.number_input("Bench Max", value=100.0, step=2.5)
    deadlift_max = st.sidebar.number_input("Deadlift Max", value=100.0, step=2.5)
    ohp_max = st.sidebar.number_input("OHP Max", value=100.0, step=2.5)
    
    # Extract the core workout table
    workout_df = df.iloc[header_row_idx+1:].copy()
    
    # Convert to a standard Python list so we can modify it safely
    raw_columns = list(df.iloc[header_row_idx].values) 
    
    # Name the first column 'Day/Week'
    raw_columns[0] = 'Day/Week'
    workout_df.columns = raw_columns
    
    # Filter out empty/ghost columns from Excel (the 'nan' columns)
    valid_cols = [c for c in workout_df.columns if pd.notna(c) and str(c).strip() != "" and str(c).lower() != "nan"]
    workout_df = workout_df[valid_cols]
    
    # Ensure no exact duplicate column names exist
    workout_df = workout_df.loc[:, ~workout_df.columns.duplicated()]
    
    workout_df.reset_index(drop=True, inplace=True)
    
    # Fix the corrupted RPE column
    if 'RPE' in workout_df.columns:
        workout_df['RPE'] = workout_df['RPE'].apply(fix_rpe)
        
    # Group the workouts by Week to make interactive tabs
    current_week = "Week 1"
    weeks = []
    for idx, row in workout_df.iterrows():
        val = str(row['Day/Week']).strip()
        # Look for week markers
        if 'Week' in val and str(row.get('Exercise', '')).strip() == 'Exercise':
            current_week = val
        elif 'Week' in val and ('deload' in val.lower() or 'taper' in val.lower() or 'testing' in val.lower()):
            current_week = val
        elif 'MAX TESTING' in val:
            current_week = "Max Testing Week"
        weeks.append(current_week)
    workout_df['Week Group'] = weeks
    
    # Helper to map the correct max to the exercise
    def get_max_val(exercise_name):
        if pd.isna(exercise_name): return None
        name = str(exercise_name).lower()
        if 'squat' in name: return squat_max
        if 'bench' in name: return bench_max
        if 'deadlift' in name: return deadlift_max
        if 'overhead press' in name or 'ohp' in name: return ohp_max
        return None

    # Recalculate weights based on parsed percentage
    def calculate_load(max_val, pct_str):
        if pd.isna(pct_str) or str(pct_str).strip().lower() in ['n/a', 'nan', 'none', '']:
            return ""
        pct_str = str(pct_str).strip()
        nums = re.findall(r"[\d\.]+", pct_str)
        if not nums: return ""
        
        loads = []
        for n in nums:
            val = float(n)
            if val > 2.0: # Covert whole numbers into decimals
                val = val / 100.0
            # Calculate load and round to nearest 2.5 increment
            load = round(max_val * val / 2.5) * 2.5
            if load > 0:
                loads.append(f"{load:g}")
        
        unique_loads = list(dict.fromkeys(loads))
        return "-".join(unique_loads)

    # Process and update calculated loads
    updated_loads = []
    for idx, row in workout_df.iterrows():
        ex = row.get('Exercise')
        pct = row.get('%1RM', '')
        m_val = get_max_val(ex)
        
        orig_load = str(row.get('Load', '')) if pd.notna(row.get('Load')) else ''
        
        if m_val is not None and pd.notna(pct):
            new_load = calculate_load(m_val, pct)
            updated_loads.append(new_load if new_load else orig_load)
        else:
            updated_loads.append(orig_load)
            
    if 'Load' in workout_df.columns:
        workout_df['Load'] = updated_loads
    
    # Clean up empty utility rows
    workout_df.dropna(how='all', inplace=True)
    workout_df = workout_df[workout_df['Exercise'] != 'Exercise']
    
    # Convert all data to string to avoid Arrow float64 serialization crashes
    workout_df = workout_df.astype(str)
    # Replace stringified pandas null values with actual empty strings for a clean UI
    workout_df.replace({"nan": "", "NaN": "", "None": "", "<NA>": "", "nat": ""}, inplace=True)
    
    # Create interactive UI tabs for each week
    unique_weeks = [w for w in workout_df['Week Group'].unique() if str(w).strip() != ""]
    if unique_weeks:
        tabs = st.tabs(unique_weeks)
        for i, week in enumerate(unique_weeks):
            with tabs[i]:
                week_data = workout_df[workout_df['Week Group'] == week].drop(columns=['Week Group'])
                st.dataframe(week_data, use_container_width=True, hide_index=True)
    else:
        st.warning("No weeks found to display. Please verify the CSV format.")

else:
    # Error state if the file is missing
    st.error(f"❌ Could not find the file: `{file_path}`")
    st.info("Please make sure your CSV file is in the exact same folder as this `app.py` script and matches the file name exactly.")