import streamlit as st
import requests
from datetime import datetime

# URL of your main backend's new credit endpoints
BACKEND_CREDIT_URL = "http://127.0.0.1:8000"

# --- STREAMLIT UI ---
st.set_page_config(page_title="WasteWise Credit System", page_icon="💵", layout="wide")
st.title("💵 WasteWise Credits for Recycling")
st.write("Simulate depositing recyclable plastics and checking your credit balance.")

# Form to simulate a deposit
st.subheader("Simulate a Deposit")
with st.form("deposit_form"):
    deposit_user_id = st.text_input("Your User ID", "user123")
    deposit_weight = st.number_input("Weight of Plastic (kg)", min_value=0.0, step=0.1)
    
    deposit_submitted = st.form_submit_button("Deposit Plastic")
    
    if deposit_submitted:
        payload = {
            "user_id": deposit_user_id,
            "waste_type": "Recyclable Plastics",
            "weight_kg": deposit_weight,
            "timestamp": datetime.now().isoformat()
        }
        try:
            response = requests.post(f"{BACKEND_CREDIT_URL}/deposit_recyclable", json=payload)
            response.raise_for_status()
            
            result = response.json()
            st.success(f"✅ Deposit successful! You earned **{result['credits_earned']:.2f} credits**.")
            st.info(f"Your new balance is: **{result['new_balance']:.2f} credits**")

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Deposit failed: {e}")

st.markdown("---")

# Section to check credit balance
st.subheader("Check Your Credit Balance")
balance_user_id = st.text_input("Enter your User ID to check balance", "user123")

if st.button("Check Balance"):
    try:
        response = requests.get(f"{BACKEND_CREDIT_URL}/user_balance/{balance_user_id}")
        response.raise_for_status()
        
        balance = response.json().get("balance", 0)
        st.success(f"Your current credit balance is: **{balance:.2f} credits**")
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to check balance: {e}")
