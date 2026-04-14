import json
import os
import random
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query

APP_NAME = "Demo Tenant API - BauRaum Voltara"
DB_PATH = os.getenv("DEMO_DB_PATH", os.path.join(os.path.dirname(__file__), "demoapi.sqlite3"))
API_KEY = os.getenv("DEMO_API_KEY", "demo-tenant-key")

CHAIN_STORES = [
    "bauraum_berlin_01",
    "bauraum_hamburg_01",
    "bauraum_koeln_01",
    "bauraum_frankfurt_01",
    "bauraum_muenchen_01",
    "bauraum_stuttgart_01",
    "bauraum_essen_01",
    "bauraum_leipzig_01",
]

VOLTARA_CORE_PRODUCTS = [
    ("bohren", "Bohrmaschine", "18V Akku-Bohrschrauber"),
    ("bohren", "Schlagbohrmaschine", "850W Schlagbohrmaschine"),
    ("saegen", "Stichsaege", "Pendelhubs Stichsaege"),
    ("saegen", "Kreissaege", "Handkreissaege 160mm"),
    ("schleifen", "Exzenterschleifer", "Exzenterschleifer 125mm"),
    ("messen", "Laserentfernungsmesser", "Laser-Meter 50m"),
    ("zubehoer", "Akkupack", "18V 4.0Ah Akku"),
    ("zubehoer", "Schnellladegeraet", "18V Schnellladegeraet"),
]

GENERIC_CATEGORIES = [
    ("bohren", "Bohren"),
    ("saegen", "Saegen"),
    ("schrauben", "Schrauben"),
    ("messen", "Messen"),
    ("schleifen", "Schleifen"),
    ("sanitaer", "Sanitaer"),
    ("garten", "Garten"),
    ("elektro", "Elektro"),
    ("farbe", "Farbe"),
    ("werkstatt", "Werkstatt"),
]

GENERIC_BRANDS = ["WerkFox", "ProLine", "Crafton", "BuildStar", "HandWerk", "TopGear", "MetalPro"]

app = FastAPI(title=APP_NAME, version="1.0.0")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_schema() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                barcode TEXT UNIQUE NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category_id TEXT NOT NULL,
                category_name TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                currency TEXT NOT NULL,
                image_url TEXT,
                attributes_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                aisle TEXT NOT NULL,
                shelf TEXT NOT NULL,
                bay TEXT,
                floor_id TEXT NOT NULL,
                x_percent REAL NOT NULL,
                y_percent REAL NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(product_id, store_id),
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            );

            CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
            CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
            CREATE INDEX IF NOT EXISTS idx_inventory_store ON inventory(store_id);
            """
        )


def _ean13_from_number(n: int) -> str:
    base = f"{n:012d}"
    checksum = 0
    for i, ch in enumerate(base):
        d = int(ch)
        checksum += d if i % 2 == 0 else d * 3
    check_digit = (10 - (checksum % 10)) % 10
    return f"{base}{check_digit}"


def build_demo_dataset() -> Dict[str, List[Dict[str, Any]]]:
    """Build deterministic demo catalog + inventory dataset."""
    rng = random.Random(20260414)
    created = now_iso()

    products: List[Dict[str, Any]] = []

    # Create dedicated Voltara line (fantasy Bosch-like contract products).
    seq = 1
    for cat_id, label, variant in VOLTARA_CORE_PRODUCTS:
        product_id = f"voltara_{cat_id}_{seq:03d}"
        products.append(
            {
                "product_id": product_id,
                "barcode": _ean13_from_number(400638100000 + seq),
                "sku": f"VOL-{cat_id[:3].upper()}-{seq:04d}",
                "name": f"Voltara {label} {variant}",
                "brand": "Voltara",
                "category_id": cat_id,
                "category_name": dict(GENERIC_CATEGORIES).get(cat_id, cat_id.title()),
                "price_cents": rng.randint(3999, 29999),
                "currency": "EUR",
                "image_url": f"https://images.demoapi.local/voltara/{product_id}.jpg",
                "attributes": {
                    "line": "Voltara Pro",
                    "warranty_years": 3,
                    "power_source": "akku" if "Akku" in variant else "kabel",
                },
                "created_at": created,
            }
        )
        seq += 1

    # Create large mixed catalog to simulate real tenant API.
    generic_count = 2400
    for i in range(1, generic_count + 1):
        cat_id, cat_name = rng.choice(GENERIC_CATEGORIES)
        brand = rng.choice(GENERIC_BRANDS)
        adjective = rng.choice(["Pro", "Compact", "Max", "Eco", "X", "Ultra", "Smart"])
        noun = rng.choice(
            [
                "Bohrhammer",
                "Akkuschrauber",
                "Hammer",
                "Schraubenset",
                "Saegeblatt",
                "Wasserwaage",
                "Spruehlack",
                "Gartenschere",
                "Verlaengerungskabel",
                "Werkbank",
            ]
        )
        product_id = f"prod_{i:05d}"
        products.append(
            {
                "product_id": product_id,
                "barcode": _ean13_from_number(410000000000 + i),
                "sku": f"{brand[:3].upper()}-{cat_id[:3].upper()}-{i:05d}",
                "name": f"{brand} {adjective} {noun}",
                "brand": brand,
                "category_id": cat_id,
                "category_name": cat_name,
                "price_cents": rng.randint(299, 14999),
                "currency": "EUR",
                "image_url": f"https://images.demoapi.local/catalog/{product_id}.jpg",
                "attributes": {
                    "weight_kg": round(rng.uniform(0.2, 12.0), 2),
                    "color": rng.choice(["schwarz", "rot", "blau", "gruen", "grau"]),
                },
                "created_at": created,
            }
        )

    inventory_rows: List[Dict[str, Any]] = []
    for p in products:
        # Not every product in every store: realistic availability matrix.
        for store in CHAIN_STORES:
            if rng.random() < 0.78:
                inventory_rows.append(
                    {
                        "product_id": p["product_id"],
                        "store_id": store,
                        "quantity": rng.randint(0, 65),
                        "aisle": f"A{rng.randint(1, 18)}",
                        "shelf": f"S{rng.randint(1, 9)}",
                        "bay": f"B{rng.randint(1, 6)}",
                        "floor_id": "eg",
                        "x_percent": round(rng.uniform(8, 92), 2),
                        "y_percent": round(rng.uniform(8, 92), 2),
                        "updated_at": now_iso(),
                    }
                )

    return {"products": products, "inventory_rows": inventory_rows}


def seed_data_if_empty() -> Dict[str, int]:
    init_schema()
    with get_conn() as conn:
        c = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
        if c > 0:
            inv = conn.execute("SELECT COUNT(*) AS c FROM inventory").fetchone()["c"]
            return {"products": int(c), "inventory_rows": int(inv)}

        dataset = build_demo_dataset()
        products = dataset["products"]
        inventory_rows = dataset["inventory_rows"]

        sqlite_products = []
        for p in products:
            sqlite_products.append(
                {
                    **p,
                    "attributes_json": json.dumps(p.get("attributes") or {}),
                }
            )

        conn.executemany(
            """
            INSERT INTO products (
                product_id, barcode, sku, name, brand, category_id, category_name,
                price_cents, currency, image_url, attributes_json, created_at
            ) VALUES (
                :product_id, :barcode, :sku, :name, :brand, :category_id, :category_name,
                :price_cents, :currency, :image_url, :attributes_json, :created_at
            )
            """,
            sqlite_products,
        )

        conn.executemany(
            """
            INSERT INTO inventory (
                product_id, store_id, quantity, aisle, shelf, bay, floor_id,
                x_percent, y_percent, updated_at
            ) VALUES (
                :product_id, :store_id, :quantity, :aisle, :shelf, :bay, :floor_id,
                :x_percent, :y_percent, :updated_at
            )
            """,
            inventory_rows,
        )
        conn.commit()

        return {"products": len(products), "inventory_rows": len(inventory_rows)}


def _auth_guard(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = (x_api_key or "").strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _row_to_product(row: sqlite3.Row) -> Dict[str, Any]:
    attrs = {}
    raw = row["attributes_json"]
    if raw:
        try:
            attrs = json.loads(raw)
        except Exception:
            attrs = {}
    return {
        "product_id": row["product_id"],
        "barcode": row["barcode"],
        "sku": row["sku"],
        "name": row["name"],
        "brand": row["brand"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "price": {"amount": round(row["price_cents"] / 100, 2), "currency": row["currency"]},
        "image_url": row["image_url"],
        "attributes": attrs,
    }


@app.on_event("startup")
def startup() -> None:
    stats = seed_data_if_empty()
    print(f"[demoapi] ready - products={stats['products']} inventory_rows={stats['inventory_rows']} db={DB_PATH}")


@app.get("/health")
def health() -> Dict[str, Any]:
    with get_conn() as conn:
        products = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
        inventory_rows = conn.execute("SELECT COUNT(*) AS c FROM inventory").fetchone()["c"]
    return {
        "ok": True,
        "service": APP_NAME,
        "db_path": DB_PATH,
        "products": products,
        "inventory_rows": inventory_rows,
        "stores": CHAIN_STORES,
    }


@app.get("/v1/products/search")
def product_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=100),
    _: None = Depends(_auth_guard),
) -> Dict[str, Any]:
    pattern = f"%{q.lower()}%"
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM products
            WHERE
                lower(name) LIKE ? OR
                lower(brand) LIKE ? OR
                lower(category_name) LIKE ? OR
                lower(sku) LIKE ? OR
                lower(barcode) LIKE ?
            ORDER BY
                CASE WHEN lower(brand) = 'voltara' THEN 0 ELSE 1 END,
                name ASC
            LIMIT ?
            """,
            (pattern, pattern, pattern, pattern, pattern, limit),
        ).fetchall()

    return {
        "query": q,
        "count": len(rows),
        "items": [_row_to_product(r) for r in rows],
    }


@app.get("/v1/products/barcode/{barcode}")
def product_by_barcode(
    barcode: str,
    _: None = Depends(_auth_guard),
) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"item": _row_to_product(row)}


@app.get("/v1/products/{product_id}")
def product_details(
    product_id: str,
    _: None = Depends(_auth_guard),
) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"item": _row_to_product(row)}


@app.get("/v1/products/{product_id}/availability")
def product_availability(
    product_id: str,
    store_id: str = Query(...),
    _: None = Depends(_auth_guard),
) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT p.product_id, p.name, i.store_id, i.quantity, i.updated_at
            FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id AND i.store_id = ?
            WHERE p.product_id = ?
            """,
            (store_id, product_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    quantity = int(row["quantity"] or 0)
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "store_id": store_id,
        "in_stock": quantity > 0,
        "quantity": quantity,
        "updated_at": row["updated_at"] or now_iso(),
    }


@app.get("/v1/products/{product_id}/location")
def product_location(
    product_id: str,
    store_id: str = Query(...),
    _: None = Depends(_auth_guard),
) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                p.product_id, p.name, p.category_id, p.category_name,
                i.store_id, i.aisle, i.shelf, i.bay, i.floor_id, i.x_percent, i.y_percent
            FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id AND i.store_id = ?
            WHERE p.product_id = ?
            """,
            (store_id, product_id),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    if not row["store_id"]:
        raise HTTPException(status_code=404, detail="Location not found for store")

    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "store_id": row["store_id"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "aisle": row["aisle"],
        "shelf": row["shelf"],
        "bay": row["bay"],
        "floor_id": row["floor_id"],
        "x_percent": row["x_percent"],
        "y_percent": row["y_percent"],
    }


@app.post("/v1/admin/reseed")
def reseed(_: None = Depends(_auth_guard)) -> Dict[str, Any]:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    stats = seed_data_if_empty()
    return {"ok": True, "reseeded": stats}

