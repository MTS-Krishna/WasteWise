import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# URL of your backend's analytics endpoint
BACKEND_ANALYTICS_URL = "http://127.0.0.1:8000/analytics"
BACKEND_OPTIMIZE_URL = "http://127.0.0.1:8000/optimize_routes"

def get_analytics_data():
    """Fetches analytics data from the backend."""
    try:
        response = requests.get(BACKEND_ANALYTICS_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to fetch analytics data from backend: {e}")
        return {}

def optimize_routes():
    """Triggers the route optimization on the backend."""
    try:
        response = requests.get(BACKEND_OPTIMIZE_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Route optimization failed: {e}")
        return {"message": "Optimization failed."}

# --- STREAMLIT UI ---
st.set_page_config(page_title="WasteWise Ops Dashboard", page_icon="📊", layout="wide")
st.title("📊 WasteWise Operations Dashboard")
st.markdown("---")

st.write("This dashboard provides an overview of waste segregation performance and bin status.")

# Fetch the data
data = get_analytics_data()
feedback_data = data.get("feedback_data", [])
bin_data = data.get("bin_status", {})

# --- BIN STATUS SECTION ---
st.subheader("🗑️ Bin Status & Fill Levels")
if not bin_data:
    st.warning("No bin data available.")
else:
    for bin_id, details in bin_data.items():
        fill_level = details["fill_level_kg"]
        capacity = details["capacity_kg"]
        fill_percentage = (fill_level / capacity) if capacity > 0 else 0
        fill_percentage_display = min(fill_percentage, 1.0) # Cap at 100%
        
        st.write(f"**{bin_id}** - {details['location']} (Capacity: {capacity} kg)")
        st.progress(fill_percentage_display)
        st.text(f"Fill Level: {round(fill_level, 2)} kg / {capacity} kg")

# --- ROUTE OPTIMIZATION SECTION ---
st.markdown("---")
st.subheader("🚛 Pickup Route Optimization")
st.write("Run the route optimizer to find the most efficient path for bins nearing full capacity (>= 75%).")

if st.button("Optimize Route Now", type="primary"):
    with st.spinner("Optimizing..."):
        route_result = optimize_routes()
        if "route" in route_result:
            path = route_result["route"]["path"]
            distance = route_result["route"]["distance"]
            
            st.success("✅ Route optimization successful!")
            st.write(f"**Total Distance:** {distance} units (simulated km)")
            st.write(f"**Optimized Route:** {path}")
            st.map(pd.DataFrame(path, columns=['lat', 'lon']))
        else:
            st.warning(route_result.get("message", "No bins are ready for pickup."))

# --- FEEDBACK ANALYTICS (Existing Code) ---
st.markdown("---")
if not feedback_data:
    st.warning("No feedback data available yet. Please submit some feedback via the collector app.")
else:
    df = pd.DataFrame(feedback_data)
    st.subheader("📈 Feedback Analytics")
    
    col1, col2, col3 = st.columns(3)
    total_submissions = len(df)
    valid_count = len(df[df['collector_status'] == 'Valid'])
    contaminated_count = len(df[df['collector_status'] == 'Contaminated'])
    contamination_rate = (contaminated_count / total_submissions) * 100 if total_submissions > 0 else 0
    
    with col1:
        st.metric(label="Total Submissions", value=total_submissions)
    with col2:
        st.metric(label="Valid Bags", value=valid_count)
    with col3:
        st.metric(label="Contaminated Bags", value=contaminated_count)
    
    st.markdown("---")
    
    st.subheader("Feedback Status Distribution")
    plot_col, _ = st.columns([1, 2])
    with plot_col:
        fig, ax = plt.subplots(figsize=(4, 4))
        status_counts = df['collector_status'].value_counts()
        ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        fig.tight_layout()
        st.pyplot(fig)

    st.markdown("---")
    st.subheader("Raw Feedback Data")
    st.dataframe(df)