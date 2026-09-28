# PlantCare Greenhouse Assistant 🌿

An intelligent conversational agent built with the Google Agent Development Kit (ADK) that helps plant enthusiasts manage indoor greenhouse collections, look up plant care guidelines, log watering events, calculate fertilizer dilution and soil volume, generate plant preview images and videos, and render interactive UI cards using Google A2UI.

![PlantCare Greenhouse Agent Demo](demo.gif)

---

## 🚀 Key Features & Capabilities

- **🌱 Plant Catalog & Care Lookup**: Browse indoor and greenhouse plants with care requirements (sunlight, soil type, moisture level, price).
- **💧 Watering History Logging**: Log watering events directly into a persistent database with automatic timestamping.
- **🧪 Soil Volume & Fertilizer Calculator**: Compute exact soil requirements (liters & gallons) for repotting containers and precise fertilizer dilution ratios.
- **🖼️ Plant Image Generation**: Generate realistic visual preview photographs of blooming plants using Vertex AI (`gemini-3.1-flash-lite-image`).
- **🎥 Plant Video Generation**: Generate short preview videos of plants in their greenhouse domain using Google's Omni model (`gemini-omni-flash-preview`).
- **☁️ Real-Time Weather Integration**: Fetch real-time weather and humidity data via Google Maps Weather API.
- **📱 Rich A2UI Component Surface**: Render native UI cards, columns, text, and imagery using Google A2UI v0.8 schema.
- **🐍 Code Execution Sandbox**: Execute Python code safely in the Agent Engine Sandbox environment (`AgentEngineSandboxCodeExecutor`).
- **🧠 Memory Bank Integration**: Persist user preferences, greenhouse environment conditions, and facts across sessions using ADK Memory Bank callbacks.

---

## ☁️ Google Cloud Services Wired Up

- **Google Cloud Agent Runtime / Agent Engine**: Deploys the ADK agent as an A2A service.
- **Google Cloud Firestore**: Stores plant inventory catalog documents and watering history records.
- **Google Cloud Storage (GCS)**: Stores generated plant preview images and video assets in a public bucket (`plantcare-greenhouse-assets-1547cf`).
- **Google Vertex AI GenAI API**: Powers text reasoning (`gemini-2.5-flash`), image generation (`gemini-3.1-flash-lite-image`), and video generation (`gemini-omni-flash-preview`).
- **Google Maps Weather API**: Delivers live local climate and weather metrics for plant care tuning.
- **OpenTelemetry / Cloud Trace**: Captures telemetry and trace spans for agent reasoning steps.

---

## 🛠️ Implemented Tools (`app/agent.py`)

| Tool Function | Description |
| :--- | :--- |
| `list_plants` | Queries Firestore collection `plants` to retrieve all indoor and greenhouse plant inventory. |
| `get_plant_details` | Fetches specific plant document details from Firestore by plant name or ID. |
| `add_plant` | Adds new plant entries to the Firestore inventory database. |
| `log_watering` | Updates watering timestamp and moisture status for plants in Firestore. |
| `calculate_fertilizer_and_soil` | Calculates soil volume requirements and fertilizer dilution ratios. |
| `get_greenhouse_weather` | Fetches weather data via Weather API. |
| `get_google_maps_weather` | Fetches real-time weather data via Google Maps Weather API. |
| `generate_plant_image` | Generates visual plant previews via Vertex AI, saves artifacts, and uploads to GCS. |
| `generate_plant_video` | Generates short plant videos via `gemini-omni-flash-preview` in global region, saves artifacts, and uploads to GCS. |
| `PreloadMemoryTool` | Preloads saved session memories into the agent context at start of turn. |

---

## 📋 Planned / Future Improvements (Not Yet Implemented)

- **Vector Search / Semantic Search**: Automated embeddings for semantic plant disease diagnostic matching (planned, not yet implemented).
- **Automated Irrigation Hardware Hooks**: Direct IoT sensor integration for automatic watering valve control (planned, not yet implemented).

---

## 💻 Local Setup & Run Instructions

### Prerequisites
- Python 3.11+
- `agents-cli` (v1.1.0+)
- Google Cloud SDK (`gcloud`) authenticated with Application Default Credentials (`gcloud auth application-default login`)

### Running the Agent Locally

1. **Install Agent Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Agent in A2A Mode**:
   ```bash
   agents-cli run --mode a2a
   ```

3. **Run Web Frontend Proxy**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   export AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/<location>/reasoningEngines/<id>"
   export AGENT_DIRECTORY="app"
   python main.py
   ```
   Open your browser to port 8080 to interact with the PlantCare Greenhouse Assistant UI.

### Deploying to Agent Platform

```bash
agents-cli deploy --no-confirm-project --update-env-vars GOOGLE_MAPS_API_KEY="<your-api-key>"
```
