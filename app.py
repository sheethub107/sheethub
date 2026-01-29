import streamlit as st
import pandas as pd
import io

# ---------------- CONFIG ----------------
FREE_DAILY_LIMIT = 5

# ---------------- DB ----------------
from utils.db import (
    init_db,
    get_or_create_user,
    can_use,
    increment_usage,
    remaining_quota,
    save_file_history,
    get_file_history,
    get_user_plan,
)

# ---------------- CORE ----------------
from utils.excel_cleaner import (
    smart_clean_sheets_from_bytes,
    make_excel_bytes_from_sheets,
)
from utils.ai_insights import generate_ai_insights

# ---------------- INIT ----------------
st.set_page_config(page_title="SheetHub", layout="centered")
init_db()

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:
    st.title("🔐 Login to SheetHub")
    email = st.text_input("Email address")

    if st.button("Login"):
        if "@" not in email:
            st.error("Please enter a valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.success("Logged in successfully ✅")
            st.rerun()

    st.stop()

user_id = st.session_state.user_id
is_pro = get_user_plan(user_id) == "pro"

# ---------------- UI ----------------
st.title("📊 SheetHub — Smart Excel Cleaner")
st.caption("Clean Excel files safely. No formulas. No data loss.")

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### 👤 Account")
st.sidebar.write(st.session_state.email)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- PLAN ----------------
st.sidebar.markdown("### 💳 Plan")
if is_pro:
    st.sidebar.success("PRO 🚀")
else:
    st.sidebar.info("Free plan")

# ---------------- USAGE ----------------
st.sidebar.markdown("### 📊 Daily Usage")

if is_pro:
    st.sidebar.success("Unlimited files")
else:
    remaining = remaining_quota(user_id)
    st.sidebar.progress((FREE_DAILY_LIMIT - remaining) / FREE_DAILY_LIMIT)
    st.sidebar.caption(f"{remaining} / {FREE_DAILY_LIMIT} files left today")

# ---------------- FILE HISTORY ----------------
st.sidebar.markdown("### 🕓 Recent Files")
for name, r, c, _ in get_file_history(user_id):
    st.sidebar.caption(f"{name} — {r}×{c}")

# ---------------- OPTIONS ----------------
st.sidebar.markdown("### 🧹 Cleaning Options")
apply_standardize = st.sidebar.checkbox("Standardize column names", True)
remove_summary = st.sidebar.checkbox("Remove summary rows", True)
remove_dupes = st.sidebar.checkbox("Remove duplicates (EmployeeID)", True)
drop_missing = st.sidebar.checkbox("Remove rows with missing values", False)

if drop_missing:
    st.sidebar.warning(
        "⚠️ This may remove many rows. "
        "Enable only if you need fully complete records."
    )

summary_keywords = st.sidebar.text_input(
    "Summary keywords",
    "total,subtotal,grand total,avg,average,sum"
).split(",")

# ---------------- PRO CTA ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🚀 PRO Coming Soon")
st.sidebar.caption(
    "• Unlimited files\n"
    "• Larger uploads\n"
    "• Faster processing\n"
    "• Priority fixes"
)

if st.sidebar.button("Notify me when PRO launches"):
    st.sidebar.success("✅ You’ll be notified!")

# ---------------- HARD LIMIT ----------------
if not is_pro and remaining_quota(user_id) <= 0:
    st.warning(
        "🚫 Free plan limit reached (5 files/day).\n\n"
        "PRO will unlock unlimited files."
    )
    st.stop()

# ---------------- UPLOAD ----------------
files = st.file_uploader(
    "Upload Excel files (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not is_pro:
    st.caption("Free plan: 5 files/day • PRO coming soon")

# ---------------- PIPELINE ----------------
any_success = False

if files:
    for file in files:
        if not is_pro and not can_use(user_id):
            st.error("🚫 Free plan limit reached.")
            break

        file_bytes = file.read()

        # Read raw safely
        try:
            raw_sheets = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=None,
                engine="openpyxl",
            )
            original_rows = {k: len(v) for k, v in raw_sheets.items()}
        except Exception:
            st.error(
                "❌ This Excel file is corrupted or exported incorrectly.\n\n"
                "Fix: Open it in Excel → Save As → Excel Workbook (.xlsx)"
            )
            continue

        # Clean
        try:
            cleaned = smart_clean_sheets_from_bytes(
                file_bytes,
                apply_standardize,
                remove_summary,
                summary_keywords,
                remove_dupes,
                None,
                drop_missing,
            )
        except Exception as e:
            st.error(f"❌ {str(e)}")
            continue

        # Success
        any_success = True
        increment_usage(user_id)

        st.markdown("### 🧾 Cleaning Summary")
        for sheet, df in cleaned.items():
            removed = original_rows.get(sheet, 0) - len(df)
            st.write(
                f"• **{sheet}** → "
                f"Original: {original_rows.get(sheet)} | "
                f"Removed: {removed} | "
                f"Final: {len(df)} rows × {df.shape[1]} columns"
            )
            save_file_history(user_id, file.name, len(df), df.shape[1])

        # ---------------- AI INSIGHTS (FREE) ----------------
        st.markdown("## 🤖 AI Insights (Auto-generated)")
        for sheet, df in cleaned.items():
            if not df.empty:
                with st.expander(f"Insights for {sheet}", expanded=True):
                    for insight in generate_ai_insights(df):
                        st.write("•", insight)

        # Download
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button(
            f"Download cleaned_{file.name}",
            out.getvalue(),
            f"cleaned_{file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if any_success:
    st.success("All valid files processed successfully ✅")
