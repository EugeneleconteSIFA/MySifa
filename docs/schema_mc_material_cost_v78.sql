-- MySifa v78 — Calcul des coûts matières (référence SQL)
-- Appliqué automatiquement via app/core/database.py (_migrate version 78)
-- Préfixe mc_ pour ne pas confondre avec MyDevis (matiere_params, matiere_base, …)

CREATE TABLE IF NOT EXISTS mc_setting (
    key TEXT PRIMARY KEY NOT NULL,
    value_decimal REAL NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mc_supplier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE IF NOT EXISTS mc_material_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE
        CHECK(code IN ('FRONTAL', 'ADHESIF', 'SILICONE', 'GLASSINE', 'AUTRE')),
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mc_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    appellation_code TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES mc_material_category(id),
    supplier_id INTEGER REFERENCES mc_supplier(id),
    weight_per_m2 REAL NOT NULL DEFAULT 0,
    weight_gsm INTEGER,
    price_currency TEXT NOT NULL DEFAULT 'EUR' CHECK(price_currency IN ('EUR', 'USD')),
    unit_price REAL NOT NULL DEFAULT 0,
    price_basis TEXT NOT NULL DEFAULT 'PER_KG' CHECK(price_basis IN ('PER_KG', 'PER_M2')),
    tax_incidence REAL NOT NULL DEFAULT 1.0,
    is_imported INTEGER NOT NULL DEFAULT 0,
    container_kg REAL,
    container_cost_usd REAL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE IF NOT EXISTS mc_material_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES mc_material(id),
    unit_price REAL NOT NULL,
    price_currency TEXT NOT NULL CHECK(price_currency IN ('EUR', 'USD')),
    tax_incidence REAL NOT NULL DEFAULT 1.0,
    effective_date TEXT NOT NULL,
    source TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE IF NOT EXISTS mc_product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    frontal_id INTEGER REFERENCES mc_material(id),
    adhesif_id INTEGER REFERENCES mc_material(id),
    silicone_id INTEGER REFERENCES mc_material(id),
    glassine_id INTEGER REFERENCES mc_material(id),
    custom_margin_eur_m2 REAL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE IF NOT EXISTS mc_product_extra_material (
    product_id INTEGER NOT NULL REFERENCES mc_product(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES mc_material(id),
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (product_id, material_id)
);

CREATE INDEX IF NOT EXISTS idx_mc_material_appellation ON mc_material(appellation_code);
CREATE INDEX IF NOT EXISTS idx_mc_material_category ON mc_material(category_id);
CREATE INDEX IF NOT EXISTS idx_mc_material_active ON mc_material(is_active);
CREATE INDEX IF NOT EXISTS idx_mc_material_price_history_material
    ON mc_material_price_history(material_id, effective_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mc_product_code ON mc_product(code COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_mc_product_active ON mc_product(is_active);
CREATE INDEX IF NOT EXISTS idx_mc_supplier_active ON mc_supplier(is_active);

-- Seeds
INSERT OR IGNORE INTO mc_material_category (code, label, sort_order) VALUES
    ('FRONTAL', 'Frontal', 1),
    ('ADHESIF', 'Adhésif', 2),
    ('SILICONE', 'Silicone', 3),
    ('GLASSINE', 'Glassine', 4),
    ('AUTRE', 'Autre', 5);

INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES
    ('eur_usd_rate', 0.85),
    ('default_container_cost_usd', 4000.0),
    ('default_container_kg', 26000.0),
    ('default_margin_eur_m2', 0.06);
