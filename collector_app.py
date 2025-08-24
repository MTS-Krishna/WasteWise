import streamlit as st
import requests
from datetime import datetime

# URL of your backend's feedback endpoint
BACKEND_FEEDBACK_URL = "http://127.0.0.1:8000/bin_feedback"

def send_feedback(bin_id, status):
    """Sends a POST request to the backend with the feedback."""
    try:
        response = requests.post(
            BACKEND_FEEDBACK_URL,
            json={
                "bin_id": bin_id,
                "collector_status": status,
                "timestamp": datetime.now().isoformat()
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Get the bin_id from the URL query parameters
query_params = st.query_params

if "bin_id" not in query_params:
    st.warning("Please scan a WasteWise bin QR code to log feedback.")
    st.stop()

# Get the bin_id from the URL
bin_id = query_params["bin_id"]

st.set_page_config(page_title="WasteWise Bin Feedback", page_icon="♻️")

st.header("WasteWise Bin Feedback")
st.markdown("---")
st.info(f"Bin ID: **{bin_id}**")
st.write("Please verify the contents of the bin and provide feedback.")

# Create two columns for the buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Bin is Valid", type="primary"):
        with st.spinner("Submitting feedback..."):
            result = send_feedback(bin_id, "Valid")
            if "error" in result:
                st.error("❌ Failed to submit feedback. Please try again.")
            else:
                st.success("✅ Feedback submitted successfully! Thank you.")
                st.balloons()

with col2:
    if st.button("⚠️ Bin is Contaminated", type="secondary"):
        with st.spinner("Submitting feedback..."):
            result = send_feedback(bin_id, "Contaminated")
            if "error" in result:
                st.error("❌ Failed to submit feedback. Please try again.")
            else:
                st.success("⚠️ Contamination reported. Thank you.")