# ruff: noqa
import datetime
import json
import math
import os
import urllib.request
from zoneinfo import ZoneInfo

from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

# Hardcoded GCP Project ID and Storage Bucket Name as explicitly required
PROJECT_ID = "qwiklabs-gcp-03-1547cf74d462"
BUCKET_NAME = "plantcare-greenhouse-assets-1547cf"

# Load Agent Engine Resource Name from deployment_metadata.json if available
DEPLOYMENT_METADATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json"
)

agent_engine_resource_name = None
if os.path.exists(DEPLOYMENT_METADATA_PATH):
    try:
        with open(DEPLOYMENT_METADATA_PATH, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get(
                "remote_agent_runtime_id"
            )
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Memory-generation callback: saves turn session events to Memory Bank after each agent step."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def _get_db():
    return firestore.Client(project=PROJECT_ID)


def list_plants(category: str = "") -> list[dict]:
    """Lists available plants from the greenhouse Firestore catalog.

    Args:
        category: Optional category filter (e.g. 'Tropical', 'Succulent', 'Flowering').

    Returns:
        List of plant dictionaries containing plant_id, name, category, sunlight, watering_frequency_days, price_usd, stock, and description.
    """
    db = _get_db()
    docs = db.collection("plants").stream()
    plants = []
    for doc in docs:
        data = doc.to_dict()
        if not category or category.lower() in data.get("category", "").lower():
            plants.append(data)
    return plants


def get_plant_details(plant_id: str) -> dict:
    """Gets detailed information for a specific plant from the greenhouse Firestore database.

    Args:
        plant_id: The ID of the plant (e.g. 'monstera-deliciosa', 'snake-plant', 'peace-lily', 'fiddle-leaf-fig').

    Returns:
        Dictionary containing detailed plant information, or an error message if not found.
    """
    db = _get_db()
    doc_ref = db.collection("plants").document(plant_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Plant with ID '{plant_id}' was not found."}


def add_plant(
    plant_id: str,
    name: str,
    category: str,
    sunlight: str,
    watering_frequency_days: int,
    price_usd: float,
    stock: int,
    description: str,
) -> str:
    """Adds a new plant or updates an existing plant item in the greenhouse Firestore database.

    Args:
        plant_id: Unique slug for the plant (e.g. 'pothos-golden').
        name: Common name of the plant.
        category: Category (e.g. 'Tropical', 'Trailing', 'Succulent').
        sunlight: Sunlight requirements (e.g. 'Low Light', 'Bright Indirect').
        watering_frequency_days: Recommended watering interval in days.
        price_usd: Retail price in USD.
        stock: Inventory stock count.
        description: Short description of the plant.

    Returns:
        Confirmation message string.
    """
    db = _get_db()
    plant_data = {
        "plant_id": plant_id,
        "name": name,
        "category": category,
        "sunlight": sunlight,
        "watering_frequency_days": watering_frequency_days,
        "price_usd": price_usd,
        "stock": stock,
        "description": description,
    }
    db.collection("plants").document(plant_id).set(plant_data)
    return f"Successfully added/updated plant '{name}' ({plant_id}) in Firestore database."


def log_watering(plant_id: str, notes: str = "") -> str:
    """Logs a watering event for a plant into the Firestore watering_logs collection.

    Args:
        plant_id: The ID of the plant being watered.
        notes: Optional notes regarding plant condition or care.

    Returns:
        Confirmation message string.
    """
    db = _get_db()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry = {
        "plant_id": plant_id,
        "timestamp": timestamp,
        "notes": notes,
    }
    db.collection("watering_logs").add(log_entry)
    return f"Logged watering event for '{plant_id}' at {timestamp}."


def calculate_fertilizer_and_soil(
    pot_top_diameter_cm: float,
    pot_bottom_diameter_cm: float,
    pot_height_cm: float,
    water_volume_liters: float = 0.0,
    target_dosage_ml_per_l: float = 2.0,
) -> dict:
    """Calculates soil volume needed for repotting and liquid fertilizer dosage requirements.

    Args:
        pot_top_diameter_cm: Diameter of the top of the pot in cm.
        pot_bottom_diameter_cm: Diameter of the bottom of the pot in cm.
        pot_height_cm: Height of the pot in cm.
        water_volume_liters: Amount of water being prepared in liters (optional, default 0.0).
        target_dosage_ml_per_l: Fertilizer dosage rate in mL per Liter of water (default 2.0 mL/L).

    Returns:
        Dictionary containing estimated soil volume in Liters and fertilizer concentrate needed in mL.
    """
    r1 = pot_top_diameter_cm / 2.0
    r2 = pot_bottom_diameter_cm / 2.0
    h = pot_height_cm

    # Volume of frustum of a cone: V = (1/3) * pi * h * (r1^2 + r2^2 + r1*r2) in cm^3
    volume_cm3 = (1.0 / 3.0) * math.pi * h * (r1**2 + r2**2 + r1 * r2)
    soil_volume_liters = round(volume_cm3 / 1000.0, 2)

    fertilizer_needed_ml = round(
        water_volume_liters * target_dosage_ml_per_l, 2
    )

    return {
        "soil_volume_liters": soil_volume_liters,
        "fertilizer_concentrate_ml": fertilizer_needed_ml,
        "water_volume_liters": water_volume_liters,
        "dosage_rate_ml_per_l": target_dosage_ml_per_l,
    }


def get_greenhouse_weather(
    latitude: float = 37.7749, longitude: float = -122.4194
) -> dict:
    """Fetches real-time ambient weather, temperature, humidity, and cloud cover from Open-Meteo API for greenhouse ventilation and watering decisions.

    Args:
        latitude: Latitude coordinate for location (default: 37.7749).
        longitude: Longitude coordinate for location (default: -122.4194).

    Returns:
        Dictionary containing current temperature, relative humidity, cloud cover, and location coordinates.
    """
    api_key = os.environ.get("OPENMETEO_API_KEY", "")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,cloud_cover"
    if api_key:
        url += f"&apikey={api_key}"

    req = urllib.request.Request(
        url, headers={"User-Agent": "PlantCareAgent/1.0"}
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    current = data.get("current", {})
    temp_c = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    cloud_cover = current.get("cloud_cover")

    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature_celsius": temp_c,
        "temperature_fahrenheit": (
            round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None
        ),
        "relative_humidity_percent": humidity,
        "cloud_cover_percent": cloud_cover,
    }


def get_google_maps_weather(
    latitude: float = 37.7749, longitude: float = -122.4194
) -> dict:
    """Fetches real-time weather conditions from the Google Maps Weather REST API using latitude and longitude coordinates.

    Args:
        latitude: Latitude coordinate (default: 37.7749).
        longitude: Longitude coordinate (default: -122.4194).

    Returns:
        Dictionary containing key weather fields: condition, temperature (C & F), feels_like, relative_humidity, uv_index, cloud_cover, and wind_speed.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        try:
            from dotenv import load_dotenv

            load_dotenv()
            api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY environment variable is not set."
        }

    url = f"https://weather.googleapis.com/v1/currentConditions:lookup?location.latitude={latitude}&location.longitude={longitude}&key={api_key}"
    req = urllib.request.Request(
        url, headers={"X-Goog-Api-Key": api_key, "User-Agent": "PlantCare/1.0"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    condition = (
        data.get("weatherCondition", {})
        .get("description", {})
        .get("text", "Unknown")
    )
    temp_c = data.get("temperature", {}).get("degrees")
    feels_c = data.get("feelsLikeTemperature", {}).get("degrees")
    humidity = data.get("relativeHumidity")
    uv_index = data.get("uvIndex")
    cloud_cover = data.get("cloudCover")
    wind_speed = data.get("wind", {}).get("speed", {}).get("value")

    return {
        "condition": condition,
        "temperature_celsius": temp_c,
        "temperature_fahrenheit": (
            round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None
        ),
        "feels_like_celsius": feels_c,
        "relative_humidity_percent": humidity,
        "uv_index": uv_index,
        "cloud_cover_percent": cloud_cover,
        "wind_speed_kmh": wind_speed,
    }


def generate_plant_image(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates a visual image preview for a plant or greenhouse item using the gemini-3.1-flash-lite-image model in the global region. Saves the image with tool_context.save_artifact for Playground Artifacts panel display, uploads the image bytes directly to public Cloud Storage, and returns the public HTTPS URL.

    Args:
        prompt: Description of the plant or greenhouse item image to generate (e.g. 'A vibrant potted Monstera Deliciosa plant with split leaves').

    Returns:
        Public HTTPS URL string (https://storage.googleapis.com/<bucket>/<object>).
    """
    client = genai.Client(
        vertexai=True, project=PROJECT_ID, location="global"
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"Generate a realistic high-quality photograph of: {prompt}",
    )

    if not response.candidates or not response.candidates[0].content.parts:
        return "Error: Image generation failed or produced no content."

    part = response.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/jpeg"

    ext = "png" if "png" in mime_type else "jpg"
    filename = (
        f"plant_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.{ext}"
    )

    # 1. Save artifact with tool_context.save_artifact for Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


def generate_plant_video(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates a short video preview for a plant or greenhouse item using Google's Omni model (gemini-omni-flash-preview) in the global region. Saves the video with tool_context.save_artifact for Playground Artifacts panel display, uploads the video bytes directly to public Cloud Storage, and returns the public HTTPS URL.

    Args:
        prompt: Description of the plant or greenhouse item video to generate (e.g. 'A short video of a blooming Peace Lily in a greenhouse').

    Returns:
        Public HTTPS URL string (https://storage.googleapis.com/plantcare-greenhouse-assets-1547cf/<object>).
    """
    client = genai.Client(
        vertexai=True, project="qwiklabs-gcp-03-1547cf74d462", location="global"
    )
    response = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short video of: {prompt}",
    )

    video_bytes = None
    mime_type = "video/mp4"

    outputs = getattr(response, "output", []) or getattr(response, "outputs", []) or []
    if isinstance(outputs, list):
        for out_content in outputs:
            parts = getattr(out_content, "parts", []) or []
            for part in parts:
                vid = getattr(part, "video", None)
                if vid and getattr(vid, "bytes", None):
                    video_bytes = vid.bytes
                    mime_type = getattr(vid, "mime_type", None) or "video/mp4"
                    break
                elif getattr(part, "bytes", None):
                    video_bytes = part.bytes
                    mime_type = getattr(part, "mime_type", None) or "video/mp4"
                    break
            if video_bytes:
                break

    if not video_bytes:
        return "Error: Video generation produced no video bytes."

    ext = "mp4" if "mp4" in mime_type else "webm"
    filename = (
        f"plant_video_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.{ext}"
    )

    # 1. Save artifact with tool_context.save_artifact for Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project="qwiklabs-gcp-03-1547cf74d462")
    bucket = storage_client.bucket("plantcare-greenhouse-assets-1547cf")
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/plantcare-greenhouse-assets-1547cf/{filename}"
    return public_url


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

try:
    from .a2ui_utils import a2ui_callback
except ImportError:
    from a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the PlantCare Greenhouse Assistant. You help users browse indoor and greenhouse "
        "plants, look up plant care guidelines, add new plant inventory, log watering events, "
        "fetch real-time weather via Google Maps Weather API, calculate soil volume for "
        "repotting as well as fertilizer dilution ratios, generate high-quality plant images "
        "and videos stored in Cloud Storage, execute Python code in a safe sandbox environment, and remember "
        "user preferences and facts across sessions using your tools."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        list_plants,
        get_plant_details,
        add_plant,
        log_watering,
        calculate_fertilizer_and_soil,
        get_greenhouse_weather,
        get_google_maps_weather,
        generate_plant_image,
        generate_plant_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
