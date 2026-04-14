import argparse
import os
from typing import Any, Dict, Iterable, List

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from app import build_demo_dataset


def _chunks(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def seed_atlas(drop_first: bool = False, batch_size: int = 1000) -> Dict[str, int]:
    atlas_uri = _require_env("ATLAS_URI")
    db_name = os.getenv("ATLAS_DB_NAME", "demoapi").strip() or "demoapi"

    client = MongoClient(atlas_uri)
    db = client[db_name]
    products_col: Collection = db["products"]
    inventory_col: Collection = db["inventory"]

    if drop_first:
        products_col.drop()
        inventory_col.drop()

    products_count_before = products_col.count_documents({})
    inventory_count_before = inventory_col.count_documents({})
    if products_count_before > 0 or inventory_count_before > 0:
        return {
            "products_inserted": 0,
            "inventory_inserted": 0,
            "products_existing": int(products_count_before),
            "inventory_existing": int(inventory_count_before),
        }

    dataset = build_demo_dataset()
    products = dataset["products"]
    inventory_rows = dataset["inventory_rows"]

    for batch in _chunks(products, batch_size):
        products_col.insert_many(batch, ordered=False)
    for batch in _chunks(inventory_rows, batch_size):
        inventory_col.insert_many(batch, ordered=False)

    # Indexes for lookup speed and uniqueness guarantees.
    products_col.create_index([("product_id", ASCENDING)], unique=True, name="ux_products_product_id")
    products_col.create_index([("barcode", ASCENDING)], unique=True, name="ux_products_barcode")
    products_col.create_index([("sku", ASCENDING)], unique=True, name="ux_products_sku")
    products_col.create_index([("name", ASCENDING)], name="ix_products_name")
    products_col.create_index([("brand", ASCENDING)], name="ix_products_brand")
    products_col.create_index([("category_id", ASCENDING)], name="ix_products_category")
    inventory_col.create_index([("store_id", ASCENDING)], name="ix_inventory_store")
    inventory_col.create_index(
        [("product_id", ASCENDING), ("store_id", ASCENDING)],
        unique=True,
        name="ux_inventory_product_store",
    )

    return {
        "products_inserted": len(products),
        "inventory_inserted": len(inventory_rows),
        "products_existing": 0,
        "inventory_existing": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Demoapi data into MongoDB Atlas")
    parser.add_argument("--drop-first", action="store_true", help="Drop products/inventory collections before seed")
    parser.add_argument("--batch-size", type=int, default=1000, help="Insert batch size")
    args = parser.parse_args()

    stats = seed_atlas(drop_first=args.drop_first, batch_size=max(args.batch_size, 100))
    print(stats)


if __name__ == "__main__":
    main()

