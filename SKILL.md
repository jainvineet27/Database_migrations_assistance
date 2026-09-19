---
name: database-migration
description: >
  Database migration and data product onboarding skill. Trigger this skill
  whenever a user mentions: data products, SQL Server views, bus scripts,
  engineer onboarding, maestro CSV, schema extraction, column data types,
  grain analysis, flow diagrams for dimension/fact tables, Streamlit dashboards
  for data product documentation, or any workflow involving 23 data products.
  Always use when generating app.py + requirements.txt for a local Streamlit
  data product explorer app, or when setting up source/output folder structures
  for database migration projects. Also triggers when the user wants to validate
  engineer-to-product assignments, connect to a SQL Server or SQLite mock DB,
  or generate any of the 5 standard migration outputs.
---

# Database Migration Skill

End-to-end workflow for onboarding engineers to data products, extracting SQL
views / bus scripts, analysing schema, and displaying results in a 4-tab Streamlit app.

---

## Workflow

```
user_registry.csv    ──► Step 1: Validate name + email + data_product_name
maestro_database.csv ──► Step 2: Fetch bus_script for the matched product
SQL Server / SQLite  ──► Step 3: Connect, extract tables, columns, grain
                               ├─ Output 1: output/01_view_script.sql
                               ├─ Output 2: output/02_tables_used.md
                               ├─ Output 3: output/03_column_datatypes.md
                               ├─ Output 4: output/04_grain_summary.md
                               └─ Output 5: output/05_flow_diagram.md
Streamlit app.py ────────► 4-tab UI: Analysis | Schema | Flow Diagram | History
```

---

## File Structure

```
project/
├── source/
│   ├── user_registry.csv          # name, email, data_product_name (all 23 products)
│   ├── maestro_database.csv       # data_product_name, bus_script
│   └── dummy_sqlserver.db         # SQLite mock DB (run create_mock_db.py once)
├── output/                        # auto-created; all 5 outputs written here
├── app.py                         # Streamlit 4-tab application
├── create_mock_db.py              # one-time DB setup script
└── requirements.txt               # streamlit, pandas, tabulate
```

---

## Source CSV Schemas

### user_registry.csv
One row per engineer ↔ data product assignment (supports many-to-one):
```csv
name,email,data_product_name
Alice Johnson,alice.johnson@company.com,Sales_Daily
Bob Smith,bob.smith@company.com,Customer_360
```

### maestro_database.csv
One row per data product with the full bus script (giant SQL/TSQL block):
```csv
data_product_name,bus_script
Sales_Daily,"SELECT f.sale_id, f.amount, c.customer_name, ...
FROM dbo.fact_sales f
JOIN dbo.dim_customer c ON f.customer_id = c.customer_id
..."
```

---

## Validation Logic (Step 1)

- All three fields (name, email, data_product_name) must match a row in user_registry.csv
- If email found but wrong product: show which products ARE assigned to that email
- If email not found at all: report email not in registry
- Only proceed when all three match exactly (case-insensitive)

---

## SQL Connection

**Demo mode (default):** uses `source/dummy_sqlserver.db` (SQLite — no drivers needed)

**Real SQL Server:** update these constants in `app.py`:
```python
SQL_SERVER   = "PROD-SQL01\\INSTANCE"
SQL_DATABASE = "DataWarehouse"
```
And replace the `sqlite3` connection block with `pyodbc` using Windows Auth:
```python
conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
)
```

---

## 4 Streamlit Tabs

| Tab | Content |
|-----|---------|
| 🔍 Analysis | Name/Email/Product inputs → Run Analysis button → step-by-step status → metric summary → raw SQL view |
| 📐 Schema | Summary dataframe of all tables + expandable per-table column types + grain cards |
| 🔀 Flow Diagram | Mermaid diagram (dimension nodes → fact node, colour-coded) + relationship list |
| 🕑 History | Full session message log (role/content/timestamp dicts), clearable |

---

## Message History Structure

```python
st.session_state.messages = [
    {
        "role": "user",
        "content": "Requested analysis for data product: Sales_Daily",
        "timestamp": "2024-09-19 10:00:00",
        "metadata": {"name": "Alice Johnson", "email": "alice@company.com", "product": "Sales_Daily"}
    },
    {
        "role": "system",
        "content": "Analysis complete for Sales_Daily. 5 tables identified. All outputs saved.",
        "timestamp": "2024-09-19 10:00:05",
        "product": "Sales_Daily"
    }
]
```

---

## Running Locally

```bash
# 1. One-time: create the demo SQLite database
python create_mock_db.py

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Launch the Streamlit app
streamlit run app.py
# → opens at http://localhost:8501
```

---

## Requirements

```
streamlit>=1.35.0
pandas>=2.2.0
tabulate>=0.9.0
```

For real SQL Server (optional):
```
pyodbc>=5.0.1    # also needs: ODBC Driver 17 for SQL Server
```
