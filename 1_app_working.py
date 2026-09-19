"""
Database Migration — Data Product Explorer
==========================================
4-tab Streamlit app for data product onboarding.

Tabs:
  1. 🔍 Analysis    — enter name/email/product, validate, run pipeline
  2. 📐 Schema      — column data types per table
  3. 🔀 Flow Diagram — dimension→fact relationship diagram
  4. 🕑 History     — full session message history

Validation flow:
  Step 1 → check user_registry.csv   (name + email + product must match)
  Step 2 → check maestro_database.csv (bus script for that product)
  Step 3 → connect to local SQLite DB (dummy_sqlserver.db) and query tables
"""

import re
import sqlite3
import datetime
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE_DIR   = Path("source")
OUTPUT_DIR   = Path("output")
REGISTRY_CSV = SOURCE_DIR / "user_registry.csv"
MAESTRO_CSV  = SOURCE_DIR / "maestro_database.csv"
DB_PATH      = SOURCE_DIR / "dummy_sqlserver.db"

# Demo server / database labels shown in the UI
DEMO_SERVER   = "localhost\\SQLEXPRESS (SQLite demo)"
DEMO_DATABASE = "dummy_sqlserver"

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DB Migration — Data Product Explorer",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { gap: 12px; }
.stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 8px 8px 0 0; font-weight: 600; }
div[data-testid="metric-container"] { background:#f0f4ff; border-radius:10px; padding:10px; }
.output-card { background:#f8f9fa; border-left:4px solid #4e73df;
               padding:12px 16px; border-radius:4px; margin-bottom:12px; }
.grain-card  { background:#e8f5e9; border-left:4px solid #43a047;
               padding:10px 14px; border-radius:4px; margin-bottom:8px;
               font-size:0.9rem; }
.fact-badge  { background:#ff7043; color:white; padding:2px 8px;
               border-radius:10px; font-size:0.75rem; }
.dim-badge   { background:#42a5f5; color:white; padding:2px 8px;
               border-radius:10px; font-size:0.75rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    # List[Dict] with keys: role, content, timestamp, metadata (optional)
    st.session_state.messages: list[dict] = []

if "last_run" not in st.session_state:
    st.session_state.last_run: dict = {}   # stores outputs of most-recent analysis


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def push_msg(role: str, content: str, **extra):
    """Append a message to the session history."""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **extra,
    })


def ensure_dirs():
    SOURCE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def save(filename: str, text: str) -> Path:
    ensure_dirs()
    p = OUTPUT_DIR / filename
    p.write_text(text, encoding="utf-8")
    return p


# ── Step 1: User Registry Validation ─────────────────────────────────────────

def validate_user(name: str, email: str, product: str) -> tuple[bool, str]:
    """
    Returns (ok, message).
    Checks that name + email + data_product_name all exist together
    in user_registry.csv.
    """
    if not REGISTRY_CSV.exists():
        return False, f"❌ `{REGISTRY_CSV}` not found. Run `python create_mock_db.py` first."

    df = pd.read_csv(REGISTRY_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    needed = {"name", "email", "data_product_name"}
    if not needed.issubset(df.columns):
        return False, f"❌ user_registry.csv must have columns: {needed}"

    # Normalise for comparison
    df["email_n"]   = df["email"].str.strip().str.lower()
    df["product_n"] = df["data_product_name"].str.strip().str.lower()
    df["name_n"]    = df["name"].str.strip().str.lower()

    row = df[
        (df["email_n"]   == email.strip().lower()) &
        (df["product_n"] == product.strip().lower()) &
        (df["name_n"]    == name.strip().lower())
    ]

    if row.empty:
        # Give a more helpful hint
        email_match = df[df["email_n"] == email.strip().lower()]
        if email_match.empty:
            return False, f"❌ Email **{email}** not found in user registry."
        products_for_user = email_match["data_product_name"].tolist()
        return False, (
            f"❌ **{product}** is not assigned to **{email}**.\n\n"
            f"Assigned product(s): `{'`, `'.join(products_for_user)}`"
        )

    return True, f"✅ Validated: **{name}** ({email}) → **{product}**"


# ── Step 2: Bus Script Lookup ─────────────────────────────────────────────────

def get_bus_script(product: str) -> tuple[str | None, str]:
    """Returns (bus_script | None, message)."""
    if not MAESTRO_CSV.exists():
        return None, f"❌ `{MAESTRO_CSV}` not found."

    df = pd.read_csv(MAESTRO_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    row = df[df["data_product_name"].str.strip().str.lower() == product.strip().lower()]
    if row.empty:
        available = df["data_product_name"].tolist()
        return None, (
            f"❌ No bus script found for **{product}**.\n\n"
            f"Available: `{'`, `'.join(available)}`"
        )

    script = row.iloc[0]["bus_script"]
    return script, f"✅ Bus script found for **{product}** ({len(script)} chars)"


# ── Step 3: SQLite connection (mocking SQL Server) ───────────────────────────

def get_connection() -> sqlite3.Connection | None:
    if not DB_PATH.exists():
        st.error(
            f"❌ Database not found at `{DB_PATH}`.\n\n"
            "Run:  `python create_mock_db.py`  to create the demo database."
        )
        return None
    return sqlite3.connect(DB_PATH)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


# ── Parse tables from SQL ─────────────────────────────────────────────────────

def extract_tables_from_sql(sql: str) -> list[dict]:
    """Pull schema.table or table references from FROM / JOIN clauses."""
    # Match  [schema].[table]  or  schema.table  or bare table
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
    if n.startswith("fact_"):       return "Fact"
    if n.startswith("dim_"):        return "Dimension"
    if n.startswith("agg_"):        return "Aggregate"
    if n.startswith("bridge_"):     return "Bridge"
    return "Unknown"


# ── Column info ───────────────────────────────────────────────────────────────

def get_columns(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["cid","name","type","notnull","dflt_value","pk"])
        df["nullable"] = df["notnull"].apply(lambda x: "NO" if x else "YES")
        df["primary_key"] = df["pk"].apply(lambda x: "✅" if x else "")
        return df[["name","type","nullable","primary_key"]].rename(columns={
            "name": "Column", "type": "Data Type",
            "nullable": "Nullable", "primary_key": "PK"
        })
    except Exception:
        return pd.DataFrame()


# ── Grain / summary heuristics ────────────────────────────────────────────────

GRAIN_MAP = {
    "fact_sales":         ("One row per sale transaction per customer per product per date",
                           "Central fact table capturing all sales transactions. Each record "
                           "represents a single sale event linking customer, product, store, "
                           "and date dimensions. Key measures include amount, quantity, and "
                           "discount. Used for revenue and sales performance reporting."),
    "fact_inventory":     ("One row per item per warehouse per snapshot date",
                           "Weekly inventory snapshot fact table. Tracks stock levels, "
                           "reserved quantities, and reorder thresholds per item-warehouse "
                           "combination. Drives replenishment and supply-chain analytics."),
    "fact_gl_transactions":("One row per general ledger transaction",
                            "Stores all financial transactions posted to the general ledger. "
                            "Each entry is linked to an account, cost center, and legal entity. "
                            "Used for P&L, balance sheet, and management reporting."),
    "dim_customer":       ("One row per unique customer",
                           "Master dimension for all customers. Contains demographic, "
                           "segmentation, and status attributes. Slowly Changing Dimension "
                           "Type 1 — latest record only."),
    "dim_product":        ("One row per unique product SKU",
                           "Product master dimension including category hierarchy and "
                           "list price. Used across sales and inventory fact tables."),
    "dim_date":           ("One row per calendar date",
                           "Standard date dimension covering calendar attributes, fiscal "
                           "periods, and quarters. Joins to all time-variant fact tables."),
    "dim_store":          ("One row per physical store location",
                           "Store master dimension with city and country attributes. "
                           "Used to analyse sales by geography."),
    "dim_address":        ("One row per address record",
                           "Normalised address dimension used by customer and employee tables."),
    "dim_loyalty":        ("One row per customer loyalty record",
                           "Stores loyalty tier and point balance per customer. "
                           "Refreshed daily from the CRM system."),
    "agg_order_stats":    ("One row per customer (pre-aggregated)",
                           "Pre-computed aggregate table summarising lifetime order count, "
                           "total spend, average order value, and last order date per customer. "
                           "Improves Customer-360 query performance."),
    "dim_item":           ("One row per inventory item / SKU",
                           "Item master for the supply-chain domain, including SKU and UPC. "
                           "Distinct from dim_product (which covers sellable products)."),
    "dim_warehouse":      ("One row per warehouse / distribution centre",
                           "Warehouse master with regional classification. "
                           "Used by inventory fact and supplier tables."),
    "dim_supplier":       ("One row per supplier",
                           "Supplier master dimension for procurement analytics."),
    "dim_account":        ("One row per chart-of-accounts entry",
                           "Financial account master with account code, name, and type "
                           "(Income / Expense / Asset / Liability)."),
    "dim_cost_center":    ("One row per cost centre",
                           "Organisational cost centre dimension used in financial reporting."),
    "dim_entity":         ("One row per legal entity",
                           "Legal entity dimension for multi-entity consolidation."),
    "dim_employee":       ("One row per employee",
                           "Employee master dimension including job, department, and location. "
                           "Tracks current and historical employment status."),
    "dim_department":     ("One row per department",
                           "Organisational department dimension with division hierarchy."),
    "dim_job":            ("One row per job code",
                           "Job dimension capturing title, level, and job family."),
    "dim_location":       ("One row per office location",
                           "Office / site dimension used by employee and operational tables."),
}

def get_grain_summary(table: str) -> tuple[str, str]:
    t = table.lower()
    if t in GRAIN_MAP:
        return GRAIN_MAP[t]
    role = infer_role(table)
    return (
        f"One row per unique record in {table}",
        f"This {role} table stores attributes relevant to the data product. "
        f"Participates in the dimensional model via key relationships."
    )


# ── Flow diagram ──────────────────────────────────────────────────────────────

def build_mermaid(tables: list[dict]) -> str:
    facts = [t for t in tables if infer_role(t["table"]) == "Fact"]
    dims  = [t for t in tables if infer_role(t["table"]) != "Fact"]

    if not facts:
        facts, dims = tables[:1], tables[1:]

    fact_node = facts[0]["table"]
    lines = ["graph LR"]
    for d in dims:
        lines.append(f"    {d['table']}([{d['table']}]) -->|FK| {fact_node}[/{fact_node}/]")
    if not dims:
        lines.append(f"    {fact_node}[/{fact_node}/]")

    # style nodes
    lines.append(f"    style {fact_node} fill:#ff7043,color:#fff,stroke:#e64a19")
    for d in dims:
        lines.append(f"    style {d['table']} fill:#42a5f5,color:#fff,stroke:#1976d2")

    return "\n".join(lines)


def render_mermaid(code: str):
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <div class="mermaid" style="background:transparent">
    {code}
    </div>
    <script>mermaid.initialize({{startOnLoad:true, theme:'base',
      themeVariables:{{primaryColor:'#42a5f5', edgeLabelBackground:'#fff'}}}});</script>
    """
    st.components.v1.html(html, height=420, scrolling=False)


# ── Output file writers ───────────────────────────────────────────────────────

def write_output1(script: str, product: str) -> str:
    return f"-- View / Bus Script for: {product}\n-- Generated: {datetime.datetime.now()}\n\n{script}"


def write_output2(tables: list[dict], product: str) -> str:
    lines = [f"# Tables Used in {product}\n"]
    lines.append("| # | Schema | Table | Role |")
    lines.append("|---|--------|-------|------|")
    for i, t in enumerate(tables, 1):
        lines.append(f"| {i} | {t['schema']} | {t['table']} | {infer_role(t['table'])} |")
    return "\n".join(lines)


def write_output3(col_data: dict) -> str:
    lines = ["# Column Data Types\n"]
    for tbl, df in col_data.items():
        lines.append(f"## {tbl}\n")
        if df is not None and not df.empty:
            lines.append(df.to_markdown(index=False))
        else:
            lines.append("_No column info available._")
        lines.append("")
    return "\n".join(lines)


def write_output4(tables: list[dict]) -> str:
    lines = ["# Grain & Table Summaries\n"]
    for t in tables:
        grain, summary = get_grain_summary(t["table"])
        lines.append(f"## {t['schema']}.{t['table']}")
        lines.append(f"**Grain:** {grain}")
        lines.append(f"\n**Summary:** {summary}\n")
        lines.append("---\n")
    return "\n".join(lines)


def write_output5(mermaid_code: str, product: str) -> str:
    return f"# Flow Diagram — {product}\n\n```mermaid\n{mermaid_code}\n```\n"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(name: str, email: str, product: str) -> dict | None:
    """
    Executes all 5 steps. Returns outputs dict on success, None on failure.
    Writes progress to st.status() context already open by caller.
    """
    outputs = {}

    # ── Step 1 ─────────────────────────────────────────────────────────────────
    st.write("**Step 1** — Validating user in registry…")
    ok, msg = validate_user(name, email, product)
    if ok:
        st.success(msg)
    else:
        st.error(msg)
        push_msg("system", f"FAILED (Step 1): {msg}", product=product)
        return None

    # ── Step 2 ─────────────────────────────────────────────────────────────────
    st.write("**Step 2** — Fetching bus script from Maestro…")
    bus_script, msg2 = get_bus_script(product)
    if bus_script:
        st.success(msg2)
    else:
        st.error(msg2)
        push_msg("system", f"FAILED (Step 2): {msg2}", product=product)
        return None
    outputs["bus_script"] = bus_script

    # ── Step 3 ─────────────────────────────────────────────────────────────────
    st.write(f"**Step 3** — Connecting to `{DEMO_SERVER}` / `{DEMO_DATABASE}`…")
    conn = get_connection()
    if not conn:
        push_msg("system", "FAILED (Step 3): DB connection failed.", product=product)
        return None
    st.success(f"✅ Connected to local demo database (`{DB_PATH.name}`)")

    all_db_tables = list_tables(conn)

    # ── Output 1: save raw bus script ─────────────────────────────────────────
    script_text = write_output1(bus_script, product)
    save("01_view_script.sql", script_text)
    outputs["view_script"] = bus_script
    st.write("📄 Output 1 saved → `output/01_view_script.sql`")

    # ── Output 2: table list ──────────────────────────────────────────────────
    tables = extract_tables_from_sql(bus_script)
    # Keep only tables that actually exist in the DB
    tables_in_db = [t for t in tables if t["table"].lower() in
                    [x.lower() for x in all_db_tables]]
    # Warn about any that are missing
    missing = [t["table"] for t in tables if t not in tables_in_db]
    if missing:
        st.info(f"ℹ️ Tables in script not in demo DB (expected): {missing}")

    save("02_tables_used.md", write_output2(tables, product))
    outputs["tables"] = tables
    outputs["tables_in_db"] = tables_in_db
    st.write(f"📋 Output 2 saved → `output/02_tables_used.md`  ({len(tables)} tables)")

    # ── Output 3: column data types ───────────────────────────────────────────
    col_data = {}
    for t in tables:
        tbl_lower = t["table"].lower()
        # find real table name (case-insensitive)
        real = next((x for x in all_db_tables if x.lower() == tbl_lower), None)
        if real:
            col_data[f"{t['schema']}.{t['table']}"] = get_columns(conn, real)
        else:
            col_data[f"{t['schema']}.{t['table']}"] = pd.DataFrame()

    save("03_column_datatypes.md", write_output3(col_data))
    outputs["columns"] = col_data
    st.write("🗂️  Output 3 saved → `output/03_column_datatypes.md`")

    # ── Output 4: grain & summary ─────────────────────────────────────────────
    save("04_grain_summary.md", write_output4(tables))
    outputs["grain"] = {t["table"]: get_grain_summary(t["table"]) for t in tables}
    st.write("📝 Output 4 saved → `output/04_grain_summary.md`")

    # ── Output 5: flow diagram ────────────────────────────────────────────────
    mermaid_code = build_mermaid(tables)
    save("05_flow_diagram.md", write_output5(mermaid_code, product))
    outputs["flow_diagram"] = mermaid_code
    st.write("🔀 Output 5 saved → `output/05_flow_diagram.md`")

    conn.close()
    return outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

st.title("🗄️ Database Migration — Data Product Explorer")
st.caption(
    f"Server: `{DEMO_SERVER}`  |  Database: `{DEMO_DATABASE}`  |  "
    f"Source: `{SOURCE_DIR}/`  |  Output: `{OUTPUT_DIR}/`"
)

tab_analysis, tab_schema, tab_flow, tab_history = st.tabs(
    ["🔍 Analysis", "📐 Schema", "🔀 Flow Diagram", "🕑 History"]
)


# ── TAB 1: ANALYSIS ──────────────────────────────────────────────────────────
with tab_analysis:
    st.subheader("Engineer Onboarding — Data Product Analysis")

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        inp_name = st.text_input("👤 Full Name", placeholder="e.g. Alice Johnson")
    with col2:
        inp_email = st.text_input("📧 Email", placeholder="e.g. alice.johnson@company.com")
    with col3:
        inp_product = st.text_input("📦 Data Product Name", placeholder="e.g. Sales_Daily")

    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    if run_btn:
        if not all([inp_name.strip(), inp_email.strip(), inp_product.strip()]):
            st.warning("⚠️ Please fill in all three fields.")
        else:
            # Log user request
            push_msg(
                "user",
                f"Requested analysis for data product: **{inp_product}**",
                metadata={"name": inp_name, "email": inp_email, "product": inp_product},
            )

            with st.status("⏳ Running pipeline…", expanded=True) as status:
                result = run_pipeline(inp_name, inp_email, inp_product)

            if result:
                st.session_state.last_run = {**result, "product": inp_product,
                                              "name": inp_name, "email": inp_email}
                status.update(label="✅ Analysis complete!", state="complete")

                push_msg(
                    "system",
                    f"Analysis complete for **{inp_product}**. "
                    f"{len(result.get('tables', []))} tables identified. "
                    f"All outputs saved to `{OUTPUT_DIR}/`.",
                    product=inp_product,
                )

                st.divider()
                # Quick summary metrics
                tables = result.get("tables", [])
                facts = [t for t in tables if infer_role(t["table"]) == "Fact"]
                dims  = [t for t in tables if infer_role(t["table"]) != "Fact"]

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Tables", len(tables))
                m2.metric("Fact Tables", len(facts))
                m3.metric("Dimension/Agg Tables", len(dims))
                m4.metric("Bus Script Size", f"{len(result.get('bus_script',''))} chars")

                st.divider()
                st.subheader("📄 Bus Script (Output 1)")
                with st.expander("View raw SQL", expanded=False):
                    st.code(result.get("bus_script", ""), language="sql")

                st.info("👉 Switch to the **Schema** and **Flow Diagram** tabs to explore the outputs.")
            else:
                status.update(label="❌ Pipeline failed — see errors above", state="error")

    # Always show last-run summary if available
    lr = st.session_state.last_run
    if lr and not run_btn:
        st.info(
            f"Last analysis: **{lr.get('product')}** by {lr.get('name')} "
            f"({len(lr.get('tables', []))} tables) — switch to other tabs to explore."
        )


# ── TAB 2: SCHEMA ─────────────────────────────────────────────────────────────
with tab_schema:
    st.subheader("📐 Column Data Types & Grain Summaries")
    lr = st.session_state.last_run

    if not lr:
        st.info("Run an analysis in the **Analysis** tab first.")
    else:
        tables   = lr.get("tables", [])
        col_data = lr.get("columns", {})
        grain    = lr.get("grain", {})

        # Summary table at top
        summary_rows = []
        for t in tables:
            g, s = grain.get(t["table"], ("—", "—"))
            df_c = col_data.get(f"{t['schema']}.{t['table']}", pd.DataFrame())
            summary_rows.append({
                "Table": t["table"],
                "Role": infer_role(t["table"]),
                "Columns": len(df_c) if df_c is not None and not df_c.empty else "—",
                "Grain": g,
            })

        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        st.divider()

        # Detailed expandable cards per table
        for t in tables:
            role  = infer_role(t["table"])
            badge = "🟠 Fact" if role == "Fact" else ("🔵 Dimension" if role == "Dimension" else "🟢 " + role)
            key   = f"{t['schema']}.{t['table']}"

            with st.expander(f"{badge}  **{key}**", expanded=False):
                df_c = col_data.get(key)

                col_left, col_right = st.columns([3, 2])
                with col_left:
                    st.markdown("**Column Schema**")
                    if df_c is not None and not df_c.empty:
                        st.dataframe(df_c, use_container_width=True, hide_index=True)
                    else:
                        st.caption("_No column info (table not in demo DB)._")

                with col_right:
                    g, s = grain.get(t["table"], ("—", "—"))
                    st.markdown("**Grain**")
                    st.markdown(f"<div class='grain-card'>🔑 {g}</div>", unsafe_allow_html=True)
                    st.markdown("**Objective**")
                    st.markdown(f"<div class='grain-card'>{s}</div>", unsafe_allow_html=True)


# ── TAB 3: FLOW DIAGRAM ───────────────────────────────────────────────────────
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
        dims  = [t for t in tables if infer_role(t["table"]) != "Fact"]

        st.caption(
            f"Data product: **{product}**  |  "
            f"🟠 {len(facts)} Fact table(s)   🔵 {len(dims)} Dimension/Agg table(s)"
        )

        # Legend
        lcol1, lcol2, _ = st.columns([1, 1, 4])
        lcol1.markdown("🟠 **Fact Table** (central node)")
        lcol2.markdown("🔵 **Dimension** (leaf nodes)")

        st.divider()
        render_mermaid(diagram)

        with st.expander("📋 Relationship details"):
            for d in dims:
                st.markdown(f"- **{d['table']}** → `{facts[0]['table'] if facts else '?'}`  (many-to-one FK)")

        with st.expander("🧾 Mermaid source"):
            st.code(diagram, language="text")


# ── TAB 4: HISTORY ────────────────────────────────────────────────────────────
with tab_history:
    st.subheader("🕑 Session Message History")

    msgs = st.session_state.messages
    if not msgs:
        st.info("No history yet. Run an analysis to start logging.")
    else:
        st.caption(f"{len(msgs)} message(s) in this session")

        for i, msg in enumerate(reversed(msgs)):
            role = msg["role"]
            icon = "👤" if role == "user" else "🤖"
            ts   = msg.get("timestamp", "")

            with st.expander(
                f"{icon} **{role.upper()}** — {ts}  |  {msg['content'][:70]}…",
                expanded=(i == 0),
            ):
                cols = st.columns([1, 3])
                with cols[0]:
                    st.markdown(f"**Role:** `{role}`")
                    st.markdown(f"**Time:** `{ts}`")
                    meta = msg.get("metadata", {})
                    if meta:
                        st.markdown("**Metadata:**")
                        for k, v in meta.items():
                            st.markdown(f"- `{k}`: {v}")
                with cols[1]:
                    st.markdown("**Content:**")
                    st.markdown(msg["content"])

        st.divider()
        if st.button("🗑️  Clear History", type="secondary"):
            st.session_state.messages = []
            st.session_state.last_run = {}
            st.rerun()
