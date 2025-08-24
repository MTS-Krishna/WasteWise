# WasteWise: An Intelligent Waste Segregation and Management System ♻️

WasteWise is a full-stack, data-driven prototype that addresses waste management challenges through intelligent waste classification, bin monitoring, and a user credit system. The project's core idea is to move beyond simple recycling education by providing a tangible feedback loop and a direct incentive for users to sort their waste correctly.

## ✨ Key Features

  * **Intelligent Waste Classification:** Automatically classifies items from receipts, menus, or lists using a powerful local **Large Language Model (LLM)** and a custom-built **Packaging Knowledge Graph**.
  * **Bin Monitoring & Route Optimization:** Simulates smart bins with a defined capacity. The system tracks the fill level of each bin and automatically generates an optimized pickup route for bins that are nearing capacity.
  * **User Credit System:** A separate service that rewards users for properly sorting recyclable plastic based on weight. These credits can be tracked and displayed in a dedicated dashboard.
  * **Auditable Collector Feedback:** Waste collectors can scan a static QR code on each bin to provide feedback on waste quality (e.g., "Valid" or "Contaminated"), creating a valuable, auditable dataset.
  * **Real-time Operations Dashboard:** A central dashboard provides managers with live metrics on bin fill levels, contamination rates, and optimized pickup routes.

-----

## 🚀 Installation & User Guide

This guide provides step-by-step instructions for setting up and running the WasteWise system.

### 1\. Install Prerequisites

  * **Ollama:** Download and install Ollama from `https://ollama.com`.
  * **Tesseract OCR:** Download and install Tesseract OCR for your operating system from `https://github.com/UB-Mannheim/tesseract/wiki`.
  * **Python 3.10+:** Download and install Python from `https://www.python.org/downloads/`. Ensure Python and `pip` are added to your system's PATH.

### 2\. Project Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/MTS-Krishna/WasteWise.git
    cd WasteWise-main
    ```
2.  Set up the Python environment:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  Install all Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 3\. Configure and Start Services

You must open a new terminal for each service. All terminals must remain open and running.

  * **Terminal 1: Start Ollama Server**
    ```bash
    # Pull the Mistral model (only needed the first time)
    ollama pull mistral
    # Start the server
    ollama serve
    ```
  * **Terminal 2: Start WasteWise Backend**
    ```bash
    uvicorn app:app --reload
    ```
  * **Terminal 3: Launch Main Dashboard**
    ```bash
    streamlit run dashboard.py
    ```
  * **Terminal 4: Launch Collector Application**
    ```bash
    streamlit run collector_app.py
    ```
  * **Terminal 5: Launch Operations Dashboard**
    ```bash
    streamlit run ops_dashboard.py
    ```
  * **Terminal 6: Launch Credit System Dashboard**
    ```bash
    streamlit run credit_dashboard.py
    ```

### 4\. Generate Bin QR Codes

Run this script once to generate static QR codes for the bins. You'll find the `.png` files in the newly created `bin_qrs` directory.

```bash
python generate_qrs.py
```

-----

## 💡 How to Use the System

1.  **Main Dashboard:** (at `http://localhost:8501`)
      * Select a `bin-id`.
      * Upload a receipt or menu to process a batch of waste. The dashboard will show the classified items and the predicted weight added to the bin.
2.  **Collector App:** (at `http://localhost:8502`)
      * Use the URL from one of the generated QR codes (e.g., `http://localhost:8502/?bin_id=bin-A`).
      * Simulate a collector's feedback by submitting whether the bin's contents are "Valid" or "Contaminated."
3.  **Credit System Dashboard:** (at `http://localhost:8504`)
      * Use this dashboard to simulate depositing recyclable plastics and checking a user's credit balance.
4.  **Operations Dashboard:** (at `http://localhost:8503`)
      * View real-time metrics on bin fill levels and contamination rates.
      * Click the "Optimize Route Now" button to generate a pickup route for bins that are over 75% full.

-----

## 🛠️ Technology Stack

  * **Backend:** Python, FastAPI, Uvicorn
  * **Frontends:** Streamlit
  * **LLM:** Ollama, Mistral
  * **Data Persistence:** `pack_graph.json` and `credits_db.json`
  * **Data Science:** Pandas, Matplotlib
  * **Optimization:** Google OR-Tools
  * **Utilities:** `requests`, `PyPDF2`, `python-docx`, `qrcode`, `pytesseract`

-----

## 🌱 Contributing

We welcome contributions\! Please open issues or submit pull requests for any improvements or bug fixes.
