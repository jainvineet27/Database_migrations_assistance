"""
create_mock_db.py
Generates source/dummy_sqlserver.db  — a local SQLite database that mimics
the SQL Server environment for demo purposes.

Run once:  python create_mock_db.py
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path("source/dummy_sqlserver.db")

DDL = """
-- ── dim_customer ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id       INTEGER PRIMARY KEY,
    customer_name     TEXT    NOT NULL,
    email             TEXT    NOT NULL,
    phone             TEXT,
    date_of_birth     TEXT,
    registration_date TEXT,
    segment           TEXT,
    address_id        INTEGER,
    is_active         INTEGER DEFAULT 1
);

-- ── dim_address ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_address (
    address_id    INTEGER PRIMARY KEY,
    address_line1 TEXT,
    city          TEXT,
    state         TEXT,
    zip_code      TEXT,
    country       TEXT
);

-- ── dim_product ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_product (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT,
    sub_category TEXT,
    unit_price   REAL
);

-- ── dim_date ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    date_key      INTEGER PRIMARY KEY,
    calendar_date TEXT,
    month_name    TEXT,
    quarter       INTEGER,
    fiscal_year   INTEGER
);

-- ── dim_store ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_store (
    store_id   INTEGER PRIMARY KEY,
    store_name TEXT,
    city       TEXT,
    country    TEXT
);

-- ── fact_sales ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id      INTEGER PRIMARY KEY,
    sale_date    TEXT,
    customer_id  INTEGER,
    product_id   INTEGER,
    date_key     INTEGER,
    store_id     INTEGER,
    amount       REAL,
    quantity     INTEGER,
    discount_pct REAL,
    is_deleted   INTEGER DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (product_id)  REFERENCES dim_product(product_id),
    FOREIGN KEY (date_key)    REFERENCES dim_date(date_key),
    FOREIGN KEY (store_id)    REFERENCES dim_store(store_id)
);

-- ── agg_order_stats ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agg_order_stats (
    customer_id     INTEGER PRIMARY KEY,
    total_orders    INTEGER,
    total_spend     REAL,
    avg_order_value REAL,
    last_order_date TEXT
);

-- ── dim_loyalty ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_loyalty (
    customer_id    INTEGER PRIMARY KEY,
    loyalty_tier   TEXT,
    loyalty_points INTEGER
);

-- ── dim_item ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_item (
    item_id   INTEGER PRIMARY KEY,
    item_name TEXT,
    sku       TEXT,
    upc_code  TEXT
);

-- ── dim_warehouse ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_warehouse (
    warehouse_id   INTEGER PRIMARY KEY,
    warehouse_name TEXT,
    region         TEXT
);

-- ── dim_supplier ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_supplier (
    supplier_id   INTEGER PRIMARY KEY,
    supplier_name TEXT
);

-- ── fact_inventory ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_inventory (
    inventory_id       INTEGER PRIMARY KEY,
    item_id            INTEGER,
    warehouse_id       INTEGER,
    supplier_id        INTEGER,
    quantity_on_hand   INTEGER,
    quantity_reserved  INTEGER,
    quantity_available INTEGER,
    reorder_level      INTEGER,
    reorder_quantity   INTEGER,
    unit_cost          REAL,
    snapshot_date      TEXT,
    FOREIGN KEY (item_id)      REFERENCES dim_item(item_id),
    FOREIGN KEY (warehouse_id) REFERENCES dim_warehouse(warehouse_id),
    FOREIGN KEY (supplier_id)  REFERENCES dim_supplier(supplier_id)
);

-- ── dim_account ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_account (
    account_id   INTEGER PRIMARY KEY,
    account_code TEXT,
    account_name TEXT,
    account_type TEXT
);

-- ── dim_cost_center ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_cost_center (
    cost_center_id   INTEGER PRIMARY KEY,
    cost_center_name TEXT,
    department       TEXT
);

-- ── dim_entity ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_entity (
    entity_id    INTEGER PRIMARY KEY,
    entity_name  TEXT,
    legal_entity TEXT
);

-- ── fact_gl_transactions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_gl_transactions (
    ledger_id        INTEGER PRIMARY KEY,
    transaction_date TEXT,
    amount           REAL,
    debit_credit_flag TEXT,
    description      TEXT,
    account_id       INTEGER,
    cost_center_id   INTEGER,
    entity_id        INTEGER,
    FOREIGN KEY (account_id)     REFERENCES dim_account(account_id),
    FOREIGN KEY (cost_center_id) REFERENCES dim_cost_center(cost_center_id),
    FOREIGN KEY (entity_id)      REFERENCES dim_entity(entity_id)
);

-- ── dim_employee ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_employee (
    employee_id       INTEGER PRIMARY KEY,
    first_name        TEXT,
    last_name         TEXT,
    email             TEXT,
    hire_date         TEXT,
    termination_date  TEXT,
    employment_status TEXT,
    department_id     INTEGER,
    job_id            INTEGER,
    location_id       INTEGER,
    FOREIGN KEY (department_id) REFERENCES dim_department(department_id),
    FOREIGN KEY (job_id)        REFERENCES dim_job(job_id),
    FOREIGN KEY (location_id)   REFERENCES dim_location(location_id)
);

-- ── dim_department ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_department (
    department_id   INTEGER PRIMARY KEY,
    department_name TEXT,
    division        TEXT
);

-- ── dim_job ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_job (
    job_id     INTEGER PRIMARY KEY,
    job_title  TEXT,
    job_level  TEXT,
    job_family TEXT
);

-- ── dim_location ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_location (
    location_id INTEGER PRIMARY KEY,
    office_name TEXT,
    city        TEXT,
    country     TEXT
);
"""

SAMPLE_DATA = """
INSERT OR IGNORE INTO dim_address VALUES (1,'123 Main St','New York','NY','10001','USA');
INSERT OR IGNORE INTO dim_address VALUES (2,'456 Oak Ave','Los Angeles','CA','90001','USA');
INSERT OR IGNORE INTO dim_address VALUES (3,'789 Pine Rd','Chicago','IL','60601','USA');

INSERT OR IGNORE INTO dim_customer VALUES (1,'John Doe','john@acme.com','555-0101','1985-03-15','2020-01-10','Premium',1,1);
INSERT OR IGNORE INTO dim_customer VALUES (2,'Jane Smith','jane@acme.com','555-0102','1990-07-22','2021-05-18','Standard',2,1);
INSERT OR IGNORE INTO dim_customer VALUES (3,'Bob Lee','bob@acme.com','555-0103','1978-11-08','2019-09-01','VIP',3,1);

INSERT OR IGNORE INTO dim_product VALUES (1,'Laptop Pro 15','Electronics','Computers',1299.99);
INSERT OR IGNORE INTO dim_product VALUES (2,'Wireless Mouse','Electronics','Accessories',29.99);
INSERT OR IGNORE INTO dim_product VALUES (3,'Desk Chair','Furniture','Seating',349.99);
INSERT OR IGNORE INTO dim_product VALUES (4,'Monitor 27"','Electronics','Displays',549.99);

INSERT OR IGNORE INTO dim_date VALUES (20240101,'2024-01-01','January',1,2024);
INSERT OR IGNORE INTO dim_date VALUES (20240201,'2024-02-01','February',1,2024);
INSERT OR IGNORE INTO dim_date VALUES (20240301,'2024-03-01','March',1,2024);
INSERT OR IGNORE INTO dim_date VALUES (20240901,'2024-09-01','September',3,2024);

INSERT OR IGNORE INTO dim_store VALUES (1,'NYC Flagship','New York','USA');
INSERT OR IGNORE INTO dim_store VALUES (2,'LA Store','Los Angeles','USA');
INSERT OR IGNORE INTO dim_store VALUES (3,'Chicago Hub','Chicago','USA');

INSERT OR IGNORE INTO fact_sales VALUES (1001,'2024-09-18',1,1,20240901,1,1299.99,1,0.0,0);
INSERT OR IGNORE INTO fact_sales VALUES (1002,'2024-09-18',2,2,20240901,2,29.99,3,0.05,0);
INSERT OR IGNORE INTO fact_sales VALUES (1003,'2024-09-18',3,3,20240901,1,349.99,2,0.10,0);
INSERT OR IGNORE INTO fact_sales VALUES (1004,'2024-09-17',1,4,20240901,3,549.99,1,0.0,0);

INSERT OR IGNORE INTO agg_order_stats VALUES (1,15,12450.50,830.03,'2024-09-18');
INSERT OR IGNORE INTO agg_order_stats VALUES (2,8,1240.20,155.03,'2024-09-15');
INSERT OR IGNORE INTO agg_order_stats VALUES (3,32,48200.00,1506.25,'2024-09-18');

INSERT OR IGNORE INTO dim_loyalty VALUES (1,'Gold',4500);
INSERT OR IGNORE INTO dim_loyalty VALUES (2,'Silver',800);
INSERT OR IGNORE INTO dim_loyalty VALUES (3,'Platinum',12000);

INSERT OR IGNORE INTO dim_item VALUES (1,'Office Paper A4','SKU-001','UPC-001');
INSERT OR IGNORE INTO dim_item VALUES (2,'Ballpoint Pens Box','SKU-002','UPC-002');
INSERT OR IGNORE INTO dim_item VALUES (3,'Stapler Heavy Duty','SKU-003','UPC-003');

INSERT OR IGNORE INTO dim_warehouse VALUES (1,'East Coast DC','East');
INSERT OR IGNORE INTO dim_warehouse VALUES (2,'West Coast DC','West');

INSERT OR IGNORE INTO dim_supplier VALUES (1,'OfficeMax Supply Co');
INSERT OR IGNORE INTO dim_supplier VALUES (2,'Paper World Inc');

INSERT OR IGNORE INTO fact_inventory VALUES (1,1,1,1,500,50,450,100,200,4.99,'2024-09-12');
INSERT OR IGNORE INTO fact_inventory VALUES (2,2,2,2,1200,100,1100,200,500,0.89,'2024-09-12');
INSERT OR IGNORE INTO fact_inventory VALUES (3,3,1,1,80,10,70,20,50,8.49,'2024-09-12');

INSERT OR IGNORE INTO dim_account VALUES (1,'4000','Revenue','Income');
INSERT OR IGNORE INTO dim_account VALUES (2,'5000','COGS','Expense');
INSERT OR IGNORE INTO dim_account VALUES (3,'6000','Operating Expenses','Expense');

INSERT OR IGNORE INTO dim_cost_center VALUES (1,'CC-SALES','Sales');
INSERT OR IGNORE INTO dim_cost_center VALUES (2,'CC-MKT','Marketing');
INSERT OR IGNORE INTO dim_cost_center VALUES (3,'CC-OPS','Operations');

INSERT OR IGNORE INTO dim_entity VALUES (1,'ACME Corp US','ACME-US LLC');
INSERT OR IGNORE INTO dim_entity VALUES (2,'ACME Corp EU','ACME-EU GmbH');

INSERT OR IGNORE INTO fact_gl_transactions VALUES (1,'2024-08-15',50000.00,'CR','Monthly Revenue',1,1,1);
INSERT OR IGNORE INTO fact_gl_transactions VALUES (2,'2024-08-15',30000.00,'DR','Cost of Goods',2,1,1);
INSERT OR IGNORE INTO fact_gl_transactions VALUES (3,'2024-08-20',12000.00,'DR','Marketing Spend',3,2,1);

INSERT OR IGNORE INTO dim_department VALUES (1,'Engineering','Technology');
INSERT OR IGNORE INTO dim_department VALUES (2,'Sales','Revenue');
INSERT OR IGNORE INTO dim_department VALUES (3,'HR','People');

INSERT OR IGNORE INTO dim_job VALUES (1,'Software Engineer','L4','Engineering');
INSERT OR IGNORE INTO dim_job VALUES (2,'Account Executive','L3','Sales');
INSERT OR IGNORE INTO dim_job VALUES (3,'HR Business Partner','L3','HR');

INSERT OR IGNORE INTO dim_location VALUES (1,'HQ New York','New York','USA');
INSERT OR IGNORE INTO dim_location VALUES (2,'London Office','London','UK');

INSERT OR IGNORE INTO dim_employee VALUES (1,'Alice','Johnson','alice@company.com','2020-03-01',NULL,'Active',1,1,1);
INSERT OR IGNORE INTO dim_employee VALUES (2,'Bob','Smith','bob@company.com','2019-07-15',NULL,'Active',2,2,1);
INSERT OR IGNORE INTO dim_employee VALUES (3,'Carol','White','carol@company.com','2021-01-10',NULL,'On Leave',3,3,2);
"""


def create_db():
    Path("source").mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for stmt in DDL.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    for stmt in SAMPLE_DATA.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except Exception as e:
                print(f"  skip: {e}")
    con.commit()
    con.close()
    print(f"✅ Mock database created at: {DB_PATH}")
    print("   Tables:", ", ".join([
        "fact_sales","fact_inventory","fact_gl_transactions",
        "dim_customer","dim_product","dim_date","dim_store",
        "dim_address","dim_loyalty","agg_order_stats",
        "dim_item","dim_warehouse","dim_supplier",
        "dim_account","dim_cost_center","dim_entity",
        "dim_employee","dim_department","dim_job","dim_location"
    ]))


if __name__ == "__main__":
    create_db()
