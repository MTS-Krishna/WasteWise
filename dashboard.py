import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from io import BytesIO

# Assuming the backend is running at this URL
BACKEND_URL = "http://127.0.0.1:8000"

# --- STREAMLIT UI ---
st.set_page_config(page_title="WasteWise ♻️", page_icon="♻️", layout="wide")
st.title("♻️ WasteWise: Smart Waste Classifier")
st.write("Upload a receipt or menu to classify waste and update a bin's fill level.")

# --- User selects a bin before uploading a file ---
bin_options = ["bin-A", "bin-B", "bin-C", "bin-D"]
selected_bin = st.selectbox("Select a waste bin for this upload:", bin_options)

uploaded_file = st.file_uploader(
    "Upload a file",
    type=["jpg", "jpeg", "png", "pdf", "docx", "txt", "csv", "json"]
)

if uploaded_file is not None:
    st.subheader("📜 File Uploaded")
    st.info(f"File Name: {uploaded_file.name} | Target Bin: **{selected_bin}**")

    with st.spinner("Processing file and classifying items..."):
        try:
            files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {'bin_id': selected_bin}
            
            res = requests.post(f"{BACKEND_URL}/process_file", files=files, data=data)
            res.raise_for_status()
            resp_data = res.json()
            
            classified_items = resp_data.get("classified_items", [])
            bag_recipes = resp_data.get("bag_recipes", [])
            manifest = resp_data.get("manifest", {})

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Backend communication failed: {e}")
            classified_items = []
            bag_recipes = []
            manifest = {}
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")
            classified_items = []
            bag_recipes = []
            manifest = {}

    if classified_items:
        # --- Display the results and their impact on the bin ---
        if manifest:
            st.markdown("---")
            st.subheader(f"✅ Waste Processed for Bin **{selected_bin}**")
            
            total_weight = manifest.get("total_weight_kg", 0)
            
            # Display a success metric for the processed waste
            st.metric(
                label=f"Predicted Waste Weight Added to **{selected_bin}**",
                value=f"{total_weight} kg"
            )

        df = pd.DataFrame(classified_items)
        st.subheader("📋 Classification Results")
        st.dataframe(df)

        col_plot1, col_plot2 = st.columns([1, 1])

        with col_plot1:
            st.subheader("📊 Recyclability Breakdown")
            fig, ax = plt.subplots(figsize=(5, 5))
            df["recyclability"].value_counts().plot.pie(ax=ax, autopct="%1.1f%%", startangle=90)
            ax.set_ylabel("")
            fig.tight_layout()
            st.pyplot(fig)

        with col_plot2:
            st.subheader("📊 Waste Stream Distribution")
            fig2, ax2 = plt.subplots(figsize=(5, 5))
            df["stream"].value_counts().plot.bar(ax=ax2)
            fig2.tight_layout()
            ax2.set_ylabel("Count")
            st.pyplot(fig2)

        if bag_recipes:
            st.subheader("🛍️ Smart Bag Recipes")
            color_map = {
                "Wet": "#1f78b4",
                "Dry": "#33a02c",
                "Recyclable": "#e31a1c",
                "Unknown": "#ff7f00",
                "Compost": "#6a3d9a",
                "None": "#b15928"
            }
            for bag in bag_recipes:
                stream_name = bag['stream']
                st.markdown(f"**Stream:** {stream_name} | **Bags Needed:** {bag['bag_count']}")
                df_bag = pd.DataFrame(bag["instructions"])
                df_bag.rename(columns={"item": "Item", "note": "Instruction"}, inplace=True)
                st.dataframe(df_bag.style.set_properties(**{'background-color': color_map.get(stream_name,"#ffffff")}), use_container_width=True)
    else:
        st.warning("⚠ No valid items found or classification failed.")