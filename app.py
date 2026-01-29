# app.py
import streamlit as st
import pandas as pd
import io
from datetime import datetime
import matplotlib.pyplot as plt

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
    upgrade_to_pro,
)

# ---------------- CORE LOGIC ----------------
from utils.excel_cleaner import (
    smart_clean_sheets_from_bytes,
    make_excel_bytes_from_sheets,
)
from utils.ai_insights import generate_ai_insights

# ---------------- INIT ----------------
st.set_page_config(page_title="SheetHub", layout="centered")
init_db()

# ---------------- SESSION INIT (CRITICAL) ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "email" not in st.session_state:
    st.session_state.email = None

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:
    st.title("🔐 Login to SheetHub")

    email = st.text_input("Email address")

    if st.button("Login"):
        if "@" not in email:
            st.error("Please enter a valid email")
        else:
            user_id = get_or_create_user(email)
            st.session_state.user_id = user_id
            st.session_state.email = email
            st.success("Logged in successfully ✅")
            st.rerun()

    st.stop()

user_id = st.session_state.user_id
plan = get_user_plan(user_id)
is_pro = plan == "pro"

# ---------------- UI ----------------
st.title("📊 SheetHub — Smart Excel Cleaner")
st.caption(
    "Upload .xlsx files. Clean data, remove duplicates, generate AI insights, visualize, and download."
)

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### 👤 Account")
st.sidebar.write(st.session_state.email)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------------- DAILY USAGE ----------------
st.sidebar.markdown("### 📊 Daily Usage")

if is_pro:
    st.sidebar.progress(1.0)
    st.sidebar.caption("Unlimited access 🚀")
else:
    remaining = remaining_quota(user_id)
    used = 5 - remaining
    progress = used / 5
    progress = max(0.0, min(progress, 1.0))

    st.sidebar.progress(progress)
    st.sidebar.caption(f"Files remaining today: {remaining} / 5")

    if remaining <= 0:
        st.sidebar.error("🚫 Daily limit reached")

# ---------------- FILE HISTORY ----------------
st.sidebar.markdown("### 🕓 File History")
history = get_file_history(user_id)

if not history:
    st.sidebar.caption("No files yet")
else:
    for name, rows, cols, _ in history:
        st.sidebar.write(f"📄 {name}")
        st.sidebar.caption(f"{rows} rows • {cols} columns")

# ---------------- CLEANING OPTIONS ----------------
st.sidebar.markdown("### 🧹 Cleaning options")
apply_standardize = st.sidebar.checkbox("Standardize column names", True)
remove_summary = st.sidebar.checkbox("Remove summary rows", True)
remove_dupes = st.sidebar.checkbox("Remove duplicates (EmployeeID)", True)
drop_missing = st.sidebar.checkbox("Remove rows with missing values", False)

summary_keywords = st.sidebar.text_input(
    "Summary keywords",
    "total,subtotal,grand total,avg,average,sum"
).split(",")

# ---------------- PLAN ----------------
if not is_pro:
    st.sidebar.warning("Free plan — 5 files/day")
    if st.sidebar.button("🚀 Upgrade to PRO"):
        upgrade_to_pro(user_id)
        st.success("🎉 Upgraded to PRO!")
        st.rerun()
else:
    st.sidebar.success("⭐ PRO User")

# ---------------- HARD BLOCK (FREE USERS) ----------------
if not is_pro and remaining_quota(user_id) <= 0:
    st.warning("🚫 Daily limit reached. Upgrade to PRO for unlimited access.")
    st.stop()

# ---------------- FILE UPLOAD ----------------
uploaded_files = st.file_uploader(
    "Upload Excel files",
    type=["xlsx"],
    accept_multiple_files=True,
)

# ---------------- MAIN PIPELINE ----------------
if uploaded_files:
    for file in uploaded_files:
        if not is_pro and not can_use(user_id):
            st.error("🚫 Daily limit reached")
            st.stop()

        st.markdown(f"## 📄 File: **{file.name}**")

        cleaned = smart_clean_sheets_from_bytes(
            file.read(),
            apply_standardize=apply_standardize,
            remove_summary=remove_summary,
            summary_keywords=summary_keywords,
            remove_dupes=remove_dupes,
            dup_subset_map=None,
            drop_missing=drop_missing,
        )

        increment_usage(user_id)

        st.markdown("### 🧾 Cleaning Summary")
        for sheet, df in cleaned.items():
            st.write(f"• **{sheet}** → {len(df)} rows, {df.shape[1]} columns")

            save_file_history(
                user_id=user_id,
                file_name=file.name,
                rows=len(df),
                columns=df.shape[1],
            )

        # ---------- AI INSIGHTS ----------
        st.markdown("## 🤖 AI Insights")
        for sheet, df in cleaned.items():
            if not df.empty:
                with st.expander(f"Insights for {sheet}", expanded=True):
                    for insight in generate_ai_insights(df):
                        st.write("•", insight)

        # ---------- DOWNLOAD ----------
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button(
            label=f"Download cleaned_{file.name}",
            data=out.getvalue(),
            file_name=f"cleaned_{file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.success("All files processed successfully ✅")
