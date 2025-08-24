import os
import json
import re
import asyncio
import httpx
import tempfile
import PyPDF2
from PIL import Image
import pytesseract
import docx
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import Dict

# --- Set Tesseract path for local development ---
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = FastAPI()

# URL for your local Ollama instance's API
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Load the Packaging Knowledge Graph
try:
    with open("pack_graph.json", "r") as f:
        PACK_GRAPH = json.load(f)
except FileNotFoundError:
    PACK_GRAPH = {}

# In-memory storage for feedback, simulating a database
feedback_log = []

# New in-memory bin database
bin_data = {
    "bin-A": {"capacity_kg": 25.0, "fill_level_kg": 0.0, "location": (40.71, -74.00)},  # Manhattan
    "bin-B": {"capacity_kg": 25.0, "fill_level_kg": 0.0, "location": (34.05, -118.24)}, # Los Angeles
    "bin-C": {"capacity_kg": 50.0, "fill_level_kg": 0.0, "location": (41.87, -87.62)}, # Chicago
    "bin-D": {"capacity_kg": 50.0, "fill_level_kg": 0.0, "location": (29.76, -95.36)}  # Houston
}

# --- NEW: In-memory user credit database and its persistence ---
user_credits: Dict[str, float] = {}
CREDIT_RATE = 1.0 # 1 credit per kg of plastic

# Load existing user credits from a file on startup
def load_credits_db():
    global user_credits
    if os.path.exists("credits_db.json"):
        with open("credits_db.json", "r") as f:
            user_credits = json.load(f)

# Save user credits to a file
def save_credits_db():
    with open("credits_db.json", "w") as f:
        json.dump(user_credits, f, indent=2)

load_credits_db()

# --- Pydantic models for request bodies ---
class ProcessedData(BaseModel):
    classified_items: list
    bag_recipes: list

class ManifestFeedback(BaseModel):
    manifest_id: str
    collector_status: str
    timestamp: str

class BinFeedback(BaseModel):
    bin_id: str
    collector_status: str
    timestamp: str

class CreditDeposit(BaseModel):
    user_id: str
    waste_type: str
    weight_kg: float
    timestamp: str

class CreditUser(BaseModel):
    user_id: str
    balance: float

# Helper Functions (unchanged, for brevity)
def extract_text(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext in [".jpg", ".jpeg", ".png"]:
        return pytesseract.image_to_string(Image.open(file_path))
    elif ext == ".pdf":
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    elif ext == ".docx":
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif ext == ".txt":
        return open(file_path, "r", encoding="utf-8").read()
    elif ext == ".csv":
        return ""
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data)
    else:
        return ""

def clean_items(raw_text):
    items = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(word in line.lower() for word in ["total", "price", "amount", "subtotal", "tax"]):
            continue
        if re.match(r'^\$?\d+(\.\d+)?$', line):
            continue
        line = re.sub(r'\$?\d+(\.\d+)?(/\w+)?', "", line)
        line = re.sub(r'\b\d+\s*(lbs?|kg|g|dozen|box|pack|bag|cups?|loaves?|gallon|pk)\b', "", line, flags=re.IGNORECASE)
        line = re.sub(r'[^a-zA-Z\s]', " ", line)
        line = re.sub(r'\s+', " ", line).strip()
        if len(line) < 2:
            continue
        items.append(line)
    return list(dict.fromkeys(items))

def generate_bag_recipe(classified_items):
    streams = {}
    for item in classified_items:
        stream = item.get("stream", "Unknown")
        streams.setdefault(stream, []).append(item)
    bag_recipes = []
    for stream, items in streams.items():
        bag_count = max(1, (len(items) + 9) // 10)
        instructions = []
        for itm in items:
            item_name = itm.get("item", "Unknown Item").strip()
            if not item_name:
                item_name = "Unknown Item"
            note = itm.get("note", "Check item before disposal.")
            instructions.append({"item": item_name, "note": note})
        bag_recipes.append({
            "stream": stream,
            "bag_count": bag_count,
            "instructions": instructions
        })
    return bag_recipes

def generate_manifest(classified_items, bag_recipes, bin_id):
    manifest_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    total_weight = sum(item.get('weight_kg', 0) for item in classified_items)
    return {
        "manifest_id": manifest_id,
        "timestamp": timestamp,
        "location": bin_data.get(bin_id, {}).get("location"),
        "total_items": len(classified_items),
        "total_bags": sum(bag['bag_count'] for bag in bag_recipes),
        "total_weight_kg": round(total_weight, 2),
        "bag_recipes": bag_recipes,
        "classified_items": classified_items
    }

async def classify_with_llm(item, client: httpx.AsyncClient):
    prompt = f"""
    You are a strict waste packaging classifier.
    For each input product, respond ONLY in valid JSON.
    Do not add extra text or explanation.
    Schema:
    {{
      "category": "<PET | Glass | Paper | Metal | MLP | Compost | Other>",
      "stream": "<Dry | Wet | Recyclable | None>",
      "recyclability": "<High | Moderate | Low | None>",
      "weight_kg": "<Estimated weight in kilograms as a float>"
    }}
    Input: "{item}"
    """
    try:
        response = await client.post(OLLAMA_API_URL, json={"model": "mistral", "prompt": prompt, "stream": False}, timeout=30.0)
        response.raise_for_status()
        raw_output = response.json().get("response", "").strip()
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON from LLM", "raw": raw_output}
    except httpx.HTTPError as e:
        parsed = {"error": f"HTTP error occurred: {e}"}
    except Exception as e:
        parsed = {"error": f"An unexpected error occurred: {e}"}
    return {"item": item, **parsed}

async def classify_item(item, client):
    item_lower = item.lower().strip()
    
    for key, data in PACK_GRAPH.items():
        if key in item_lower:
            return {
                "item": item,
                "category": data["category"],
                "stream": data["stream"],
                "recyclability": data["recyclability"],
                "note": data["note"],
                "weight_kg": data.get("weight_kg", 0.01)
            }

    llm_result = await classify_with_llm(item, client)
    
    if "error" in llm_result:
        return {
            "item": item,
            "category": "Unknown",
            "stream": "Unknown",
            "recyclability": "None",
            "note": "Classification failed. Check item before disposal.",
            "weight_kg": 0.01
        }
    
    stream = llm_result.get("stream", "Unknown")
    note = "Check item before disposal."
    if stream == "Wet":
        note = "Dispose as wet compost."
    elif stream == "Dry":
        note = "Dispose as dry recyclables."
    elif stream == "Recyclable":
        note = "Rinse & flatten."
    
    weight = llm_result.get("weight_kg")
    if weight is None or not isinstance(weight, (int, float)):
        weight = 0.01
    
    llm_result["note"] = note
    llm_result["weight_kg"] = float(weight)
    
    return llm_result

def calculate_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def solve_tsp(locations):
    if len(locations) < 2:
        return {"path": locations, "distance": 0.0}

    depot = (40.71, -74.00)
    all_locations = [depot] + locations

    manager = pywrapcp.RoutingIndexManager(len(all_locations), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(calculate_distance(all_locations[from_node], all_locations[to_node]) * 1000)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        index = routing.Start(0)
        route = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(all_locations[node_index])
            index = solution.Value(routing.NextVar(index))
        node_index = manager.IndexToNode(index)
        route.append(all_locations[node_index])
        
        total_distance = solution.ObjectiveValue() / 1000
        return {"path": route, "distance": round(total_distance, 2)}
    else:
        return {"path": locations, "distance": -1}

def save_classified_data(data):
    try:
        if os.path.exists("classification_db.json"):
            with open("classification_db.json", "r") as f:
                db = json.load(f)
        else:
            db = []
        db.append(data)
        with open("classification_db.json", "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print(f"Error saving classified data: {e}")

# ---------- API Endpoints ----------
@app.post("/process_file")
async def process_file(file: UploadFile = File(...), bin_id: str = Form(...)):
    if bin_id not in bin_data:
        return JSONResponse({"error": "Invalid bin_id provided."}, status_code=400)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name
    try:
        raw_text = extract_text(temp_path)
        if not raw_text.strip():
            return JSONResponse({"error": "No text found in file"}, status_code=400)
        items = clean_items(raw_text)
        if not items:
            return JSONResponse({"error": "No valid items found after cleaning"}, status_code=400)

        async with httpx.AsyncClient() as client:
            tasks = [classify_item(item, client) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=False)
        
        bag_recipes = generate_bag_recipe(results)
        manifest = generate_manifest(results, bag_recipes, bin_id)
        
        save_classified_data({
            "timestamp": datetime.now().isoformat(),
            "bin_id": bin_id,
            "items": results
        })

        bin_data[bin_id]["fill_level_kg"] += manifest["total_weight_kg"]

        return JSONResponse({"classified_items": results, "bag_recipes": bag_recipes, "manifest": manifest})
    finally:
        os.remove(temp_path)

@app.post("/feedback")
async def receive_feedback(feedback: ManifestFeedback):
    feedback_log.append(feedback.dict())
    print(f"Received feedback for Manifest ID {feedback.manifest_id}: Status is {feedback.collector_status}")
    return {"message": "Feedback received successfully", "manifest_id": feedback.manifest_id}

@app.post("/bin_feedback")
async def receive_bin_feedback(feedback: BinFeedback):
    feedback_log.append(feedback.dict())
    if feedback.collector_status == "Valid" and feedback.bin_id in bin_data:
        bin_data[feedback.bin_id]["fill_level_kg"] = 0.0
    print(f"Received feedback for Bin ID {feedback.bin_id}: Status is {feedback.collector_status}")
    return {"message": "Bin feedback received successfully", "bin_id": feedback.bin_id}

@app.get("/analytics")
async def get_analytics():
    return JSONResponse({"feedback_data": feedback_log, "bin_status": bin_data})

@app.get("/optimize_routes")
async def optimize_routes():
    pickup_locations = []
    for bin_id, data in bin_data.items():
        fill_percentage = (data["fill_level_kg"] / data["capacity_kg"]) * 100
        if fill_percentage >= 75:
            pickup_locations.append(data["location"])
    
    if not pickup_locations:
        return JSONResponse({"message": "No bins are ready for pickup."})
    
    route_result = solve_tsp(pickup_locations)
    
    return JSONResponse({"message": "Pickup route optimized.", "route": route_result})

# --- NEW: Credit System Endpoints ---
@app.post("/deposit_recyclable")
async def deposit_recyclable_plastic(deposit: CreditDeposit):
    if deposit.waste_type.lower() != "recyclable plastics":
        return JSONResponse({"message": "Incorrect waste type. Only 'Recyclable Plastics' are accepted for credits."}, status_code=400)
    
    credits_earned = deposit.weight_kg * CREDIT_RATE
    user_credits[deposit.user_id] = user_credits.get(deposit.user_id, 0.0) + credits_earned
    save_credits_db() # Persist the changes

    return JSONResponse({
        "message": "Deposit successful",
        "user_id": deposit.user_id,
        "credits_earned": credits_earned,
        "new_balance": user_credits[deposit.user_id]
    })

@app.get("/user_balance/{user_id}")
async def get_user_balance(user_id: str):
    balance = user_credits.get(user_id, 0.0)
    return JSONResponse({"user_id": user_id, "balance": balance})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
