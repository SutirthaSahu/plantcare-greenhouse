"""Seed script for initializing Firestore database with plant items for PlantCare Greenhouse."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-1547cf74d462"
COLLECTION_NAME = "plants"

SEED_PLANTS = [
    {
        "plant_id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "category": "Tropical",
        "sunlight": "Bright Indirect",
        "watering_frequency_days": 7,
        "price_usd": 35.0,
        "stock": 12,
        "description": "Iconic Swiss Cheese Plant with dramatic split leaves. Great for bright indoor spaces.",
    },
    {
        "plant_id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "category": "Succulent",
        "sunlight": "Low to Bright Indirect",
        "watering_frequency_days": 14,
        "price_usd": 24.5,
        "stock": 20,
        "description": "Extremely resilient air-purifying plant. Thrives on minimal watering.",
    },
    {
        "plant_id": "peace-lily",
        "name": "Peace Lily",
        "category": "Flowering",
        "sunlight": "Medium Indirect",
        "watering_frequency_days": 5,
        "price_usd": 28.0,
        "stock": 8,
        "description": "Lush dark foliage with elegant white spathes. Tells you when it needs water by wilting slightly.",
    },
    {
        "plant_id": "fiddle-leaf-fig",
        "name": "Fiddle Leaf Fig",
        "category": "Tree / Tropical",
        "sunlight": "Bright Direct/Indirect",
        "watering_frequency_days": 7,
        "price_usd": 45.0,
        "stock": 5,
        "description": "Stunning centerpiece plant with large, glossy violin-shaped leaves.",
    },
]


def seed():
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection(COLLECTION_NAME)

    print(f"Seeding '{COLLECTION_NAME}' collection in Firestore (Project: {PROJECT_ID})...")
    for plant in SEED_PLANTS:
        doc_ref = plants_ref.document(plant["plant_id"])
        doc_ref.set(plant)
        print(f"  ✓ Seeded: {plant['name']} ({plant['plant_id']})")

    print("Seeding complete!")


if __name__ == "__main__":
    seed()
