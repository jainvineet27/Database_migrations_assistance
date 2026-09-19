"""
Database Migration — Data Product Explorer
==========================================
Fully integrated app combining Points 1, 2 & 3:

  POINT 1 — Mermaid diagram rendered via ES-module iframe (guaranteed to work in Streamlit)
  POINT 2 — Sidebar SQL Server config with Windows Auth; auto-overrides SQLite demo
             when valid server + database are provided and connection test passes
  POINT 3 — Complete integrated app.py merging all previous work into one coherent file

4 tabs: Analysis | Schema | Flow Diagram | History
"""

import re
import sqlite3
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Optional: pyodbc for real SQL Server ─────────────────────────────────────
try:
    import pyodbc
    PYODBC_OK = True
except ImportError:
    PYODBC_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
SOURCE_DIR = Path("source")
OUTPUT_DIR = Path("output")
REGISTRY_CSV = SOURCE_DIR / "user_registry.csv"
MAESTRO_CSV = SOURCE_DIR / "maestro_database.csv"
SQLITE_DB = SOURCE_DIR / "dummy_sqlserver.db"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DB Migration — Data Product Explorer",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 10px; }
.stTabs [data-baseweb="tab"]      { padding: 8px 20px; border-radius: 8px 8px 0 0;
                                    font-weight: 600; font-size: .95rem; }
/* Metric cards */
div[data-testid="metric-container"] {
    background: #f0f4ff; border-radius: 10px; padding: 10px 14px; }
/* Grain / summary cards */
.grain-card {
    background: #e8f5e9; border-left: 4px solid #43a047;
    padding: 10px 14px; border-radius: 4px; margin-bottom: 8px;
    font-size: .88rem; line-height: 1.5; }
/* Connection status badges */
.badge-demo { display:inline-block; background:#607d8b; color:#fff;
              padding: 4px 12px; border-radius: 14px; font-size: .78rem; }
.badge-live { display:inline-block; background:#2e7d32; color:#fff;
              padding: 4px 12px; border-radius: 14px; font-size: .78rem; }
.badge-fail { display:inline-block; background:#c62828; color:#fff;
              padding: 4px 12px; border-radius: 14px; font-size: .78rem; }
/* Step progress rows */
.step-row { padding: 4px 0; font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════
_defaults = {
    "messages":     [],      # List[dict] — full message history
    "last_run":     {},      # outputs from most recent successful pipeline run
    "conn_mode":    "demo",  # "demo" | "live"
    "win_auth_ok":  False,   # True once live connection tested successfully
    "sql_server":   "",
    "sql_db":       "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — SQL Server Configuration (POINT 2)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ SQL Server Config")

    st.markdown("""
    **Demo mode** (default): uses a local SQLite mock database — no drivers needed.

    **Live mode**: enter your SQL Server details below, click *Test Connection*,
    and Windows Authentication will be used automatically.
    """)

    sb_server = st.text_input(
        "🖥️ Server Name",
        value=st.session_state.sql_server,
        placeholder="PROD-SQL01\\INSTANCE",
        help="Hostname or IP\\InstanceName of your SQL Server",
    )
    sb_db = st.text_input(
        "🗄️ Database Name",
        value=st.session_state.sql_db,
        placeholder="DataWarehouse",
    )

    both_filled = sb_server.strip() != "" and sb_db.strip() != ""

    if both_filled:
        # Show live-mode UI
        st.markdown('<span class="badge-live">🟢 Live SQL Server mode</span>',
                    unsafe_allow_html=True)
        st.caption("Windows Authentication (Trusted Connection) will be used.")

        if not PYODBC_OK:
            st.error("`pyodbc` not installed.\n\n`pip install pyodbc`")

        test_btn = st.button("🔐 Test Windows Auth Connection",
                             use_container_width=True, type="primary")
        if test_btn:
            if not PYODBC_OK:
                st.error("Install `pyodbc` first.")
            else:
                try:
                    _cs = (
                        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                        f"SERVER={sb_server.strip()};"
                        f"DATABASE={sb_db.strip()};"
                        f"Trusted_Connection=yes;"
                    )
                    _tc = pyodbc.connect(_cs, timeout=8)
                    _tc.close()
                    # Persist to session and switch mode
                    st.session_state.sql_server = sb_server.strip()
                    st.session_state.sql_db = sb_db.strip()
                    st.session_state.conn_mode = "live"
                    st.session_state.win_auth_ok = True
                    st.success("✅ Connected via Windows Auth!")
                    st.rerun()
                except Exception as _e:
                    st.session_state.win_auth_ok = False
                    st.session_state.conn_mode = "demo"
                    st.error(f"❌ Connection failed:\n\n`{_e}`")

        # Allow reverting to demo
        if st.session_state.win_auth_ok:
            st.markdown('<span class="badge-live">✅ Windows Auth active</span>',
                        unsafe_allow_html=True)
            if st.button("↩️ Switch back to Demo mode", use_container_width=True):
                st.session_state.conn_mode = "demo"
                st.session_state.win_auth_ok = False
                st.session_state.sql_server = ""
                st.session_state.sql_db = ""
                st.rerun()
    else:
        # Demo mode
        st.markdown('<span class="badge-demo">⚪ Demo mode — SQLite</span>',
                    unsafe_allow_html=True)
        st.caption(f"Using: `{SQLITE_DB}`")
        st.session_state.conn_mode = "demo"
        st.session_state.win_auth_ok = False

    st.divider()
    st.markdown("**📁 Folder paths**")
    st.caption(f"Source → `{SOURCE_DIR}/`")
    st.caption(f"Output → `{OUTPUT_DIR}/`")

    st.divider()
    st.markdown("**🧪 Demo credentials**")
    with st.container(border=True):
        st.caption("Name: `Alice Johnson`")
        st.caption("Email: `alice.johnson@company.com`")
        st.caption("Product: `Sales_Daily`")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def push_msg(role: str, content: str, **extra):
    """Append a structured message to session history."""
    st.session_state.messages.append({
        "role":      role,
        "content":   content,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **extra,
    })


def ensure_dirs():
    SOURCE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def save_output(filename: str, text: str) -> Path:
    ensure_dirs()
    p = OUTPUT_DIR / filename
    p.write_text(text, encoding="utf-8")
    return p


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Validate user against registry CSV
# ══════════════════════════════════════════════════════════════════════════════

def validate_user(name: str, email: str, product: str) -> tuple[bool, str]:
    if not REGISTRY_CSV.exists():
        return False, f"❌ `{REGISTRY_CSV}` not found. Run `python create_mock_db.py` first."

    df = pd.read_csv(REGISTRY_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"name", "email", "data_product_name"}
    if not required.issubset(df.columns):
        return False, f"❌ `user_registry.csv` must have columns: {required}. Found: {set(df.columns)}"

    df["_n"] = df["name"].str.strip().str.lower()
    df["_e"] = df["email"].str.strip().str.lower()
    df["_p"] = df["data_product_name"].str.strip().str.lower()

    match = df[
        (df["_n"] == name.strip().lower()) &
        (df["_e"] == email.strip().lower()) &
        (df["_p"] == product.strip().lower())
    ]

    if not match.empty:
        return True, f"✅ Validated — **{name}** ({email}) is assigned to **{product}**"

    # Helpful fallback messages
    email_rows = df[df["_e"] == email.strip().lower()]
    if email_rows.empty:
        return False, f"❌ Email **{email}** not found in user registry."

    assigned = email_rows["data_product_name"].tolist()
    return False, (
        f"❌ **{product}** is not assigned to **{email}**.\n\n"
        f"Products assigned to this email: `{'`, `'.join(assigned)}`"
    )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Fetch bus script from Maestro CSV
# ══════════════════════════════════════════════════════════════════════════════

def get_bus_script(product: str) -> tuple[str | None, str]:
    if not MAESTRO_CSV.exists():
        return None, f"❌ `{MAESTRO_CSV}` not found."

    df = pd.read_csv(MAESTRO_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "data_product_name" not in df.columns or "bus_script" not in df.columns:
        return None, "❌ `maestro_database.csv` must have `data_product_name` and `bus_script` columns."

    row = df[df["data_product_name"].str.strip().str.lower() ==
             product.strip().lower()]
    if row.empty:
        available = df["data_product_name"].tolist()
        return None, (f"❌ No bus script found for **{product}**.\n\n"
                      f"Available products: `{'`, `'.join(available)}`")

    script = str(row.iloc[0]["bus_script"]).strip()
    return script, f"✅ Bus script retrieved ({len(script):,} characters)"


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Database connection (live SQL Server OR SQLite demo)
# ══════════════════════════════════════════════════════════════════════════════

def get_db_connection():
    """
    Returns (connection, mode_str) where mode_str is 'live' or 'demo'.
    Automatically picks live if Windows Auth was validated, else falls back to demo.
    """
    if st.session_state.conn_mode == "live" and st.session_state.win_auth_ok and PYODBC_OK:
        try:
            cs = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={st.session_state.sql_server};"
                f"DATABASE={st.session_state.sql_db};"
                f"Trusted_Connection=yes;"
            )
            return pyodbc.connect(cs, timeout=10), "live"
        except Exception as e:
            st.warning(
                f"⚠️ Live connection failed (`{e}`). Falling back to demo database.")

    # Demo / fallback
    if not SQLITE_DB.exists():
        st.error(f"❌ Demo database not found at `{SQLITE_DB}`.\n\n"
                 "Run: `python create_mock_db.py`")
        return None, "demo"
    return sqlite3.connect(SQLITE_DB), "demo"


def list_tables(conn, mode: str) -> list[str]:
    if mode == "live":
        cur = conn.cursor()
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
        return [r[0] for r in cur.fetchall()]
    else:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in cur.fetchall()]


def get_columns(conn, table: str, mode: str) -> pd.DataFrame:
    try:
        if mode == "live":
            q = f"""
                SELECT COLUMN_NAME        AS [Column],
                       DATA_TYPE          AS [Data Type],
                       COALESCE(CAST(CHARACTER_MAXIMUM_LENGTH AS VARCHAR(20)), '') AS [Max Len],
                       COALESCE(CAST(NUMERIC_PRECISION AS VARCHAR(10)), '')        AS [Precision],
                       COALESCE(CAST(NUMERIC_SCALE AS VARCHAR(10)), '')            AS [Scale],
                       IS_NULLABLE        AS [Nullable]
                FROM   INFORMATION_SCHEMA.COLUMNS
                WHERE  TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """
            return pd.read_sql(q, conn)
        else:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows, columns=["cid", "name", "type", "notnull", "dflt", "pk"])
            df["Nullable"] = df["notnull"].map({0: "YES", 1: "NO"})
            df["PK"] = df["pk"].map({0: "", 1: "✅"})
            return df[["name", "type", "Nullable", "PK"]].rename(
                columns={"name": "Column", "type": "Data Type"})
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# SQL PARSING
# ══════════════════════════════════════════════════════════════════════════════

def extract_tables_from_sql(sql: str) -> list[dict]:
    """Extract all table references from FROM / JOIN clauses."""
    pattern = re.compile(
        r'\b(?:FROM|JOIN)\s+(?:\[?(\w+)\]?\.\[?(\w+)\]?|\[?(\w+)\]?)',
        re.IGNORECASE,
    )
    seen, result = set(), []
    for m in pattern.finditer(sql):
        if m.group(1) and m.group(2):
            schema, tbl = m.group(1), m.group(2)
        elif m.group(3):
            schema, tbl = "dbo", m.group(3)
        else:
            continue
        key = f"{schema}.{tbl}"
        if key not in seen:
            seen.add(key)
            result.append({"schema": schema, "table": tbl})
    return result


def infer_role(table_name: str) -> str:
    n = table_name.lower()
    if n.startswith("fact_"):
        return "Fact"
    if n.startswith("dim_"):
        return "Dimension"
    if n.startswith("agg_"):
        return "Aggregate"
    if n.startswith("bridge_"):
        return "Bridge"
    return "Unknown"


# ══════════════════════════════════════════════════════════════════════════════
# GRAIN / SUMMARY KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

_GRAIN = {
    "fact_sales":           ("One row per sale transaction per customer, product, store and date",
                             "Central fact table capturing all sales transactions. Links customer, "
                             "product, store and date dimensions. Key measures: amount, quantity, "
                             "discount. Primary source for revenue and sales performance reporting."),
    "fact_inventory":       ("One row per item per warehouse per weekly snapshot date",
                             "Weekly inventory snapshot tracking on-hand, reserved and available "
                             "stock per item-warehouse combination. Drives replenishment and "
                             "supply-chain analytics."),
    "fact_gl_transactions": ("One row per general ledger posting",
                             "All financial transactions posted to the GL, each linked to an "
                             "account, cost centre and legal entity. Feeds P&L, balance sheet "
                             "and management reporting."),
    "dim_customer":         ("One row per unique customer",
                             "Customer master with demographic, segmentation and active-status "
                             "attributes. SCD Type 1 — always reflects the latest record."),
    "dim_product":          ("One row per unique product SKU",
                             "Product master including category hierarchy and list price. "
                             "Referenced by sales and inventory fact tables."),
    "dim_date":             ("One row per calendar date",
                             "Standard date dimension covering calendar attributes, fiscal periods "
                             "and quarters. Joins to all time-variant fact tables."),
    "dim_store":            ("One row per physical store location",
                             "Store master with city and country attributes, used to slice "
                             "sales performance by geography."),
    "dim_address":          ("One row per address record",
                             "Normalised address dimension shared by customer and employee tables."),
    "dim_loyalty":          ("One row per customer loyalty record",
                             "Stores loyalty tier and point balance per customer, refreshed "
                             "daily from the CRM system."),
    "agg_order_stats":      ("One row per customer (pre-aggregated lifetime stats)",
                             "Pre-computed aggregate: lifetime order count, total spend, average "
                             "order value and last order date. Improves Customer-360 query speed."),
    "dim_item":             ("One row per inventory item / SKU",
                             "Item master for the supply-chain domain including SKU and UPC codes. "
                             "Distinct from dim_product which covers sellable products."),
    "dim_warehouse":        ("One row per warehouse / distribution centre",
                             "Warehouse master with regional classification, referenced by "
                             "inventory fact and supplier tables."),
    "dim_supplier":         ("One row per supplier",
                             "Supplier master for procurement and inventory analytics."),
    "dim_account":          ("One row per chart-of-accounts entry",
                             "Financial account master: code, name and type "
                             "(Income / Expense / Asset / Liability)."),
    "dim_cost_center":      ("One row per cost centre",
                             "Organisational cost centre dimension used in financial reporting."),
    "dim_entity":           ("One row per legal entity",
                             "Legal entity dimension enabling multi-entity financial consolidation."),
    "dim_employee":         ("One row per employee",
                             "Employee master with job, department and location. Covers active "
                             "and on-leave staff."),
    "dim_department":       ("One row per department",
                             "Organisational department dimension with division hierarchy."),
    "dim_job":              ("One row per job code",
                             "Job dimension: title, level and family for HR analytics."),
    "dim_location":         ("One row per office location",
                             "Office / site dimension used by employee and operational tables."),
}


def get_grain(table: str) -> tuple[str, str]:
    entry = _GRAIN.get(table.lower())
    if entry:
        return entry
    role = infer_role(table)
    return (
        f"One row per unique record in {table}",
        f"This {role} table stores attributes relevant to the data product. "
        f"Participates in the dimensional model via foreign key relationships.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# MERMAID DIAGRAM
# Root cause of previous failure: Streamlit's sandboxed iframe blocks
# type="module" ES imports from external CDNs entirely.
# Fix: use the UMD bundle via a plain <script src> tag + <pre class="mermaid">
# with startOnLoad:true — the only approach that works inside st.components.v1.html()
# ══════════════════════════════════════════════════════════════════════════════

def build_mermaid(tables: list[dict]) -> str:
    """
    Build clean Mermaid graph LR syntax.
    Dimension / Aggregate nodes point TO the fact node (many → one).
    Node IDs use only alphanumeric chars to avoid Mermaid parse errors.
    """
    facts = [t for t in tables if infer_role(t["table"]) == "Fact"]
    others = [t for t in tables if infer_role(t["table"]) != "Fact"]

    # Fallback: treat first table as the hub if no fact_ prefix found
    if not facts:
        facts, others = tables[:1], tables[1:]

    fact_node = facts[0]["table"] if facts else "central"

    lines = ["graph LR"]

    # Each dimension/agg gets its own line: DimNode -->|FK label| FactNode
    for t in others:
        role = infer_role(t["table"])
        colour = {"Dimension": "#1565c0", "Aggregate": "#2e7d32",
                  "Bridge":    "#6a1b9a"}.get(role, "#37474f")
        n = t["table"]
        # Use square brackets for dim nodes, round for fact
        lines.append(f'    {n}["{n}"] -->|FK| {fact_node}(("{fact_node}"))')

    # If only a fact table (no dims parsed), still render it
    if not others:
        lines.append(f'    {fact_node}(("{fact_node}"))')

    # Colour styles — must come AFTER all node declarations
    lines.append(
        f'    style {fact_node} fill:#e64a19,color:#fff,stroke:#bf360c,stroke-width:3px'
    )
    for t in others:
        role = infer_role(t["table"])
        colour = {"Dimension": "#1565c0", "Aggregate": "#2e7d32",
                  "Bridge":    "#6a1b9a"}.get(role, "#37474f")
        lines.append(
            f'    style {t["table"]} fill:{colour},color:#fff,stroke:#0d47a1,stroke-width:1px'
        )

    return "\n".join(lines)


def render_mermaid(mermaid_code: str, height: int = 500):
    """
    Render a Mermaid diagram inside Streamlit using st.components.v1.html().

    WHY THIS APPROACH:
    - type="module" ES imports are blocked by Streamlit's sandboxed iframe CSP.
    - The UMD bundle loaded via a plain <script src> tag is NOT blocked.
    - <pre class="mermaid"> + mermaid.initialize({startOnLoad:true}) is the
      canonical way to use the UMD bundle — Mermaid scans the DOM on load
      and converts all .mermaid elements to SVG automatically.
    - We pin mermaid@10.6.1 (stable, widely cached on jsDelivr).
    """
    # Escape any back-ticks or template-literal chars that could break
    # the HTML string — the diagram goes inside a <pre>, so it is safe as-is,
    # but guard against accidental </pre> in generated text.
    safe_code = mermaid_code.replace("</pre>", "&lt;/pre&gt;")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #f8f9fb;
      font-family: 'Segoe UI', Arial, sans-serif;
      padding: 20px;
    }}

    #wrap {{
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 2px 14px rgba(0,0,0,.09);
      padding: 28px 24px 20px;
      overflow-x: auto;
    }}

    /* Make the rendered SVG fill the container */
    #wrap svg {{
      width: 100% !important;
      max-width: 100%;
      height: auto !important;
      display: block;
    }}

    #legend {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      font-size: 12px;
      color: #546e7a;
      padding-left: 4px;
    }}

    .dot {{
      display: inline-block;
      width: 11px;
      height: 11px;
      border-radius: 50%;
      margin-right: 5px;
      vertical-align: middle;
    }}

    #err {{
      display: none;
      margin-top: 14px;
      padding: 10px 14px;
      background: #ffebee;
      color: #b71c1c;
      border-radius: 8px;
      font-size: 13px;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>

  <div id="wrap">
    <!--
      KEY: <pre class="mermaid"> is the correct element for the UMD bundle.
           Mermaid's startOnLoad scans for this class and converts it to SVG.
           Do NOT use <div class="mermaid"> with the UMD bundle — it requires
           the ESM API which is blocked in Streamlit iframes.
    -->
    <pre class="mermaid">{safe_code}</pre>
    <div id="err"></div>
  </div>

  <div id="legend">
    <span><span class="dot" style="background:#e64a19"></span><b>Fact Table</b> (hub)</span>
    <span><span class="dot" style="background:#1565c0"></span>Dimension Table</span>
    <span><span class="dot" style="background:#2e7d32"></span>Aggregate Table</span>
    <span style="color:#888">— Arrows: dimension → fact (many-to-one FK)</span>
  </div>

  <!--
    UMD bundle: loaded as a classic script, not type="module".
    This is the ONLY script loading strategy that works in Streamlit's iframe.
  -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
  <script>
    // Initialize BEFORE the DOM has fully painted — startOnLoad:true means
    // Mermaid will process .mermaid elements once DOMContentLoaded fires.
    mermaid.initialize({{
      startOnLoad:   true,
      theme:         'base',
      securityLevel: 'loose',
      themeVariables: {{
        primaryColor:        '#1565c0',
        primaryTextColor:    '#ffffff',
        primaryBorderColor:  '#0d47a1',
        lineColor:           '#546e7a',
        edgeLabelBackground: '#eceff1',
        fontSize:            '14px',
      }},
      flowchart: {{
        curve:        'basis',
        rankSpacing:  80,
        nodeSpacing:  55,
        useMaxWidth:  true,
        htmlLabels:   true,
      }},
    }});

    // Catch any render errors and surface them visibly
    window.addEventListener('error', function(e) {{
      var el = document.getElementById('err');
      el.style.display = 'block';
      el.textContent   = 'Render error: ' + e.message;
    }});
  </script>
</body>
</html>"""

    st.components.v1.html(html, height=height, scrolling=True)


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT FILE WRITERS
# ══════════════════════════════════════════════════════════════════════════════

def write_output1(script: str, product: str) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"-- Data Product : {product}\n-- Generated   : {ts}\n\n{script}"


def write_output2(tables: list[dict], product: str) -> str:
    lines = [f"# Tables Used in: {product}\n",
             "| # | Schema | Table Name | Role |",
             "|---|--------|------------|------|"]
    for i, t in enumerate(tables, 1):
        lines.append(
            f"| {i} | {t['schema']} | {t['table']} | {infer_role(t['table'])} |")
    return "\n".join(lines)


def write_output3(col_data: dict) -> str:
    lines = ["# Column Data Types\n"]
    for tbl, df in col_data.items():
        lines.append(f"## {tbl}\n")
        lines.append(df.to_markdown(index=False)
                     if df is not None and not df.empty else "_No column info available._")
        lines.append("")
    return "\n".join(lines)


def write_output4(tables: list[dict]) -> str:
    lines = ["# Grain & Table Summaries\n"]
    for t in tables:
        g, s = get_grain(t["table"])
        lines += [f"## {t['schema']}.{t['table']}",
                  f"**Grain:** {g}", f"\n**Summary:** {s}\n", "---\n"]
    return "\n".join(lines)


def write_output5(mermaid_code: str, product: str) -> str:
    return f"# Flow Diagram — {product}\n\n```mermaid\n{mermaid_code}\n```\n"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE — runs all 5 steps in sequence
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(name: str, email: str, product: str) -> dict | None:
    """
    Runs all 5 pipeline steps inside an already-open st.status() context.
    Returns the outputs dict on success, None on any failure.
    """
    outputs = {}

    # ── STEP 1 ────────────────────────────────────────────────────────────────
    st.markdown('<p class="step-row">📋 <b>Step 1</b> — Validating user in registry…</p>',
                unsafe_allow_html=True)
    ok, msg = validate_user(name, email, product)
    (st.success if ok else st.error)(msg)
    if not ok:
        push_msg("system", f"FAILED at Step 1: {msg}", product=product)
        return None

    # ── STEP 2 ────────────────────────────────────────────────────────────────
    st.markdown('<p class="step-row">📜 <b>Step 2</b> — Fetching bus script from Maestro…</p>',
                unsafe_allow_html=True)
    bus_script, msg2 = get_bus_script(product)
    (st.success if bus_script else st.error)(msg2)
    if not bus_script:
        push_msg("system", f"FAILED at Step 2: {msg2}", product=product)
        return None
    outputs["bus_script"] = bus_script

    # ── STEP 3 ────────────────────────────────────────────────────────────────
    mode_label = ("Live SQL Server (Windows Auth)"
                  if (st.session_state.conn_mode == "live" and st.session_state.win_auth_ok)
                  else "SQLite demo database")
    st.markdown(f'<p class="step-row">🔌 <b>Step 3</b> — Connecting ({mode_label})…</p>',
                unsafe_allow_html=True)

    conn, actual_mode = get_db_connection()
    if conn is None:
        push_msg(
            "system", "FAILED at Step 3: database connection error.", product=product)
        return None

    server_label = (
        f"{st.session_state.sql_server} / {st.session_state.sql_db}"
        if actual_mode == "live"
        else f"SQLite demo ({SQLITE_DB.name})"
    )
    st.success(f"✅ Connected → `{server_label}`")
    outputs["conn_mode"] = actual_mode

    all_db_tables = list_tables(conn, actual_mode)

    # ── OUTPUT 1 — raw bus script ─────────────────────────────────────────────
    save_output("01_view_script.sql", write_output1(bus_script, product))
    outputs["view_script"] = bus_script
    st.write("📄 **Output 1** saved → `output/01_view_script.sql`")

    # ── OUTPUT 2 — table list ─────────────────────────────────────────────────
    tables = extract_tables_from_sql(bus_script)
    missing = [t["table"] for t in tables
               if t["table"].lower() not in [x.lower() for x in all_db_tables]]
    if missing:
        st.info(f"ℹ️ Some tables are in the script but not in the demo DB "
                f"(normal for demo mode): `{'`, `'.join(missing)}`")
    save_output("02_tables_used.md", write_output2(tables, product))
    outputs["tables"] = tables
    st.write(
        f"📋 **Output 2** saved → `output/02_tables_used.md`  ({len(tables)} tables found)")

    # ── OUTPUT 3 — column data types ─────────────────────────────────────────
    col_data = {}
    for t in tables:
        real = next((x for x in all_db_tables if x.lower()
                    == t["table"].lower()), None)
        col_data[f"{t['schema']}.{t['table']}"] = (
            get_columns(conn, real, actual_mode) if real else pd.DataFrame()
        )
    save_output("03_column_datatypes.md", write_output3(col_data))
    outputs["columns"] = col_data
    st.write("🗂️  **Output 3** saved → `output/03_column_datatypes.md`")

    # ── OUTPUT 4 — grain & summary ────────────────────────────────────────────
    save_output("04_grain_summary.md", write_output4(tables))
    outputs["grain"] = {t["table"]: get_grain(t["table"]) for t in tables}
    st.write("📝 **Output 4** saved → `output/04_grain_summary.md`")

    # ── OUTPUT 5 — flow diagram ───────────────────────────────────────────────
    mermaid_code = build_mermaid(tables)
    save_output("05_flow_diagram.md", write_output5(mermaid_code, product))
    outputs["flow_diagram"] = mermaid_code
    st.write("🔀 **Output 5** saved → `output/05_flow_diagram.md`")

    conn.close()
    return outputs


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("🗄️ Database Migration — Data Product Explorer")

# Dynamic connection status badge below title
if st.session_state.conn_mode == "live" and st.session_state.win_auth_ok:
    _badge = (f'<span class="badge-live">🟢 Live SQL Server — '
              f'{st.session_state.sql_server} / {st.session_state.sql_db} '
              f'(Windows Auth active)</span>')
else:
    _badge = '<span class="badge-demo">⚪ Demo mode — SQLite mock database</span>'
st.markdown(_badge, unsafe_allow_html=True)
st.caption("Use the sidebar to configure a live SQL Server, or run in demo mode with the test credentials shown there.")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_analysis, tab_schema, tab_flow, tab_history = st.tabs(
    ["🔍 Analysis", "📐 Schema", "🔀 Flow Diagram", "🕑 History"]
)


# ════════════════════════════════════════════
# TAB 1 — ANALYSIS
# ════════════════════════════════════════════
with tab_analysis:
    st.subheader("Engineer Onboarding — Data Product Analysis")
    st.caption(
        "Enter your details below. All three fields must match the user registry.")

    c1, c2, c3 = st.columns(3)
    inp_name = c1.text_input(
        "👤 Full Name",         placeholder="Alice Johnson")
    inp_email = c2.text_input(
        "📧 Email",             placeholder="alice.johnson@company.com")
    inp_product = c3.text_input(
        "📦 Data Product Name", placeholder="Sales_Daily")

    run_btn = st.button("🚀 Run Analysis", type="primary",
                        use_container_width=True)

    if run_btn:
        if not all([inp_name.strip(), inp_email.strip(), inp_product.strip()]):
            st.warning("⚠️ Please fill in all three fields.")
        else:
            push_msg(
                "user",
                f"Requested analysis for data product: **{inp_product}**",
                metadata={"name": inp_name, "email": inp_email,
                          "product": inp_product},
            )

            with st.status("⏳ Running pipeline…", expanded=True) as status:
                result = run_pipeline(inp_name, inp_email, inp_product)

            if result:
                st.session_state.last_run = {
                    **result,
                    "product": inp_product,
                    "name":    inp_name,
                    "email":   inp_email,
                }
                status.update(
                    label="✅ Analysis complete — all 5 outputs saved!", state="complete")

                push_msg(
                    "system",
                    f"Analysis complete for **{inp_product}**. "
                    f"{len(result.get('tables', []))} tables identified. "
                    f"All outputs written to `{OUTPUT_DIR}/`.",
                    product=inp_product,
                )

                st.divider()
                tables = result.get("tables", [])
                facts = [t for t in tables if infer_role(t["table"]) == "Fact"]
                dims = [t for t in tables if infer_role(t["table"]) != "Fact"]

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Tables",      len(tables))
                m2.metric("Fact Tables",       len(facts))
                m3.metric("Dimension / Agg",   len(dims))
                m4.metric("Script Length",
                          f"{len(result.get('bus_script', ''))} chars")

                st.divider()
                with st.expander("📄 View raw bus script (Output 1)", expanded=False):
                    st.code(result.get("bus_script", ""), language="sql")

                st.info(
                    "👉 Switch to the **Schema** and **Flow Diagram** tabs to explore all outputs.")
            else:
                status.update(
                    label="❌ Pipeline failed — see errors above.", state="error")

    lr = st.session_state.last_run
    if lr and not run_btn:
        st.info(
            f"Last run: **{lr.get('product')}** by {lr.get('name')} "
            f"({len(lr.get('tables', []))} tables). "
            f"Switch to other tabs to explore outputs."
        )


# ════════════════════════════════════════════
# TAB 2 — SCHEMA
# ════════════════════════════════════════════
with tab_schema:
    st.subheader("📐 Column Data Types & Grain Summaries")
    lr = st.session_state.last_run

    if not lr:
        st.info("Run an analysis in the **Analysis** tab first.")
    else:
        tables = lr.get("tables", [])
        col_data = lr.get("columns", {})
        grain = lr.get("grain", {})

        # Overview table
        summary_rows = []
        for t in tables:
            g, _ = grain.get(t["table"], ("—", "—"))
            df_c = col_data.get(f"{t['schema']}.{t['table']}", pd.DataFrame())
            n_cols = len(df_c) if df_c is not None and not df_c.empty else "—"
            summary_rows.append({
                "Table":   t["table"],
                "Role":    infer_role(t["table"]),
                "Columns": n_cols,
                "Grain":   g,
            })
        st.dataframe(pd.DataFrame(summary_rows),
                     use_container_width=True, hide_index=True)
        st.divider()

        # Per-table expandable detail cards
        for t in tables:
            role = infer_role(t["table"])
            emoji = {"Fact": "🟠", "Dimension": "🔵",
                     "Aggregate": "🟢"}.get(role, "⚪")
            key = f"{t['schema']}.{t['table']}"

            with st.expander(f"{emoji} **{key}**  —  *{role}*", expanded=False):
                df_c = col_data.get(key)
                g_text, s_text = grain.get(t["table"], ("—", "—"))

                left, right = st.columns([3, 2])
                with left:
                    st.markdown("**Column Schema**")
                    if df_c is not None and not df_c.empty:
                        st.dataframe(
                            df_c, use_container_width=True, hide_index=True)
                    else:
                        st.caption(
                            "_Column info unavailable (table not in database)._")
                with right:
                    st.markdown("**Grain**")
                    st.markdown(f"<div class='grain-card'>🔑 {g_text}</div>",
                                unsafe_allow_html=True)
                    st.markdown("**Objective**")
                    st.markdown(f"<div class='grain-card'>{s_text}</div>",
                                unsafe_allow_html=True)


# ════════════════════════════════════════════
# TAB 3 — FLOW DIAGRAM  (POINT 1 fix)
# ════════════════════════════════════════════
with tab_flow:
    st.subheader("🔀 Table Relationship Flow Diagram")
    lr = st.session_state.last_run

    if not lr:
        st.info("Run an analysis in the **Analysis** tab first.")
    else:
        tables = lr.get("tables", [])
        diagram = lr.get("flow_diagram", "")
        product = lr.get("product", "")

        facts = [t for t in tables if infer_role(t["table"]) == "Fact"]
        dims = [t for t in tables if infer_role(t["table"]) != "Fact"]

        lc1, lc2, lc3 = st.columns([1, 1, 3])
        lc1.markdown("🟠 **Fact** (hub)")
        lc2.markdown("🔵 **Dimension** (leaf)")
        lc3.caption(
            f"Product: **{product}**  |  {len(facts)} fact · {len(dims)} dimension/agg")

        st.divider()

        # ── Mermaid rendered via ES-module iframe (POINT 1) ───────────────────
        render_mermaid(diagram, height=520)

        st.divider()

        with st.expander("📋 Relationship details", expanded=False):
            fact_name = facts[0]["table"] if facts else "?"
            for d in dims:
                st.markdown(
                    f"- **{d['table']}** `→` **{fact_name}**"
                    f"  *(many-to-one FK,  role: {infer_role(d['table'])})*"
                )

        with st.expander("🧾 Mermaid source code", expanded=False):
            st.code(diagram, language="text")


# ════════════════════════════════════════════
# TAB 4 — HISTORY
# ════════════════════════════════════════════
with tab_history:
    st.subheader("🕑 Session Message History")
    msgs = st.session_state.messages

    if not msgs:
        st.info("No history yet — run an analysis to start logging.")
    else:
        st.caption(f"{len(msgs)} message(s) recorded in this session.")

        for i, msg in enumerate(reversed(msgs)):
            role = msg["role"]
            icon = "👤" if role == "user" else "🤖"
            ts = msg.get("timestamp", "")
            snip = msg["content"][:75].replace("\n", " ")

            with st.expander(
                f"{icon} **{role.upper()}** — {ts}  |  {snip}…",
                expanded=(i == 0),
            ):
                ca, cb = st.columns([1, 3])
                with ca:
                    st.markdown(f"**Role:** `{role}`")
                    st.markdown(f"**Time:** `{ts}`")
                    meta = msg.get("metadata", {})
                    if meta:
                        st.markdown("**Metadata:**")
                        for k, v in meta.items():
                            st.markdown(f"- `{k}` : {v}")
                with cb:
                    st.markdown("**Content:**")
                    st.markdown(msg["content"])

        st.divider()
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.messages = []
            st.session_state.last_run = {}
            st.rerun()
