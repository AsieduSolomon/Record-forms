"""
Duayaw Nkwanta COP Child Development Centre
HOME VISITATION FORM — Data Collection App

Run locally with:
    streamlit run app.py

This single file contains the whole app. A requirements.txt file
is provided alongside it — just place both files in the same folder
(or same GitHub repo) and deploy to Streamlit Community Cloud.
"""

import os
import io
import csv
from datetime import date, datetime

import streamlit as st
from fpdf import FPDF

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
CENTRE_NAME = "St. Anselm's Anglican Child Development Centre"
LOG_FILE = "home_visitation_records.csv"

st.set_page_config(page_title="Home Visitation Form", page_icon="🏠", layout="centered")

HYGIENE_ITEMS = [
    "Sponge (personal)",
    "Towel (personal)",
    "Mattress",
    "House attire (at least 8)",
    "Church attire (at least 4)",
    "Bowl/ cup/ spoon",
    "Source for light learning",
    "Others (please specify)",
]
HYGIENE_STATUSES = ["Available", "Manageable", "Need Replacement", "Not Available"]


# --------------------------------------------------------------------------
# PDF GENERATION — recreates the paper form layout
# --------------------------------------------------------------------------
class VisitationPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 7, CENTRE_NAME, ln=1, align="C")
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 7, "HOME VISITATION FORM", ln=1, align="C")
        self.ln(2)

    def section_title(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 6, text, ln=1, fill=True)
        self.ln(1)

    def field_line(self, label, value):
        self.set_font("Helvetica", "B", 9)
        self.cell(48, 6, label, border=0)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, str(value) if value else "-")

    def checklist_line(self, label, options, selected):
        self.set_font("Helvetica", "B", 9)
        self.cell(48, 6, label, border=0)
        self.set_font("Helvetica", "", 9)
        parts = []
        for opt in options:
            mark = "[X]" if opt in selected else "[ ]"
            parts.append(f"{mark} {opt}")
        self.multi_cell(0, 6, "   ".join(parts))


def generate_pdf(data: dict) -> bytes:
    pdf = VisitationPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Basic info -------------------------------------------------
    pdf.field_line("Date of Visit:", data["date_of_visit"])
    pdf.field_line("Child's Name:", data["child_name"])
    pdf.field_line("Child's No.:", data["child_no"])
    pdf.ln(1)

    pdf.checklist_line(
        "Reason(s) for visit:",
        ["Regular Home Visit", "Health", "Behavior/Attitude At Home",
         "Absent from project", "Others"],
        data["reasons"],
    )
    if "Others" in data["reasons"] and data["reason_other"]:
        pdf.field_line("   (Specify):", data["reason_other"])

    pdf.checklist_line(
        "How was visit conducted:",
        ["Face To Face Visit", "Third Party Visit", "Others"],
        [data["visit_conducted"]],
    )
    if data["visit_conducted"] == "Others" and data["visit_conducted_other"]:
        pdf.field_line("   (Specify):", data["visit_conducted_other"])

    pdf.checklist_line(
        "Who was available:",
        ["Parent", "Guardian", "Siblings", "Others"],
        data["available_persons"],
    )
    if "Others" in data["available_persons"] and data["available_other"]:
        pdf.field_line("   (Specify):", data["available_other"])

    pdf.checklist_line(
        "Child's whereabouts:",
        ["At Home", "Travelled", "Errand", "Others"],
        [data["whereabouts"]],
    )
    if data["whereabouts"] == "Others" and data["whereabouts_other"]:
        pdf.field_line("   (Specify):", data["whereabouts_other"])

    pdf.ln(2)

    # --- Personal hygiene table --------------------------------------
    pdf.section_title("Personal Hygiene at Home")
    col_item_w = 60
    col_status_w = (190 - col_item_w) / len(HYGIENE_STATUSES)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(col_item_w, 6, "Item", border=1)
    for status in HYGIENE_STATUSES:
        pdf.cell(col_status_w, 6, status, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for item in HYGIENE_ITEMS:
        pdf.cell(col_item_w, 6, item, border=1)
        chosen = data["hygiene"].get(item, "")
        for status in HYGIENE_STATUSES:
            mark = "X" if status == chosen else ""
            pdf.cell(col_status_w, 6, mark, border=1, align="C")
        pdf.ln()
    pdf.ln(2)

    # --- Child's condition --------------------------------------------
    pdf.section_title("Child's Condition")
    pdf.checklist_line("Appearance:", ["Neat", "Not neat"], [data["appearance"]])
    pdf.checklist_line("Mood:", ["Happy", "Sad"], [data["mood"]])
    pdf.checklist_line("Time to learn after school:", ["Yes", "No"], [data["time_to_learn"]])
    if data["time_to_learn"] == "No" and data["time_to_learn_reason"]:
        pdf.field_line("   Reason:", data["time_to_learn_reason"])

    pdf.checklist_line(
        "Behavior at home:",
        ["Portrays a Christ-like character", "Good personality",
         "Well-behaved", "Not well-behaved"],
        data["behavior"],
    )

    pdf.field_line("Chores assigned to child:", data["chores"])

    pdf.checklist_line("Exposed to child abuse:", ["Yes", "No"], [data["abuse"]])
    if data["abuse"] == "Yes" and data["abuse_narration"]:
        pdf.field_line("   Narrate:", data["abuse_narration"])

    pdf.checklist_line(
        "Need for another immediate home visit:", ["Yes", "No"], [data["need_revisit"]]
    )
    if data["need_revisit"] == "Yes":
        pdf.field_line("   Reason:", data["revisit_reason"])
        pdf.field_line("   Next date for visit:", data["next_visit_date"])

    pdf.ln(2)

    # --- Comments / Recommendation -------------------------------------
    pdf.section_title("Comment and Observation of the Visit")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, data["comments"] if data["comments"] else "-")
    pdf.ln(1)

    pdf.section_title("Recommendation (in order of priority)")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, data["recommendation"] if data["recommendation"] else "-")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, f"Name of CDW/Volunteer: {data['cdw_name']}", ln=1)
    pdf.cell(0, 6, "Signature: ______________________________", ln=1)

    # fpdf2 returns a bytearray with dest="S"
    return bytes(pdf.output(dest="S"))


# --------------------------------------------------------------------------
# CSV LOGGING (keeps a running record of every submission)
# --------------------------------------------------------------------------
def log_to_csv(data: dict):
    file_exists = os.path.isfile(LOG_FILE)
    flat = {
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "date_of_visit": data["date_of_visit"],
        "child_name": data["child_name"],
        "child_no": data["child_no"],
        "reasons": ", ".join(data["reasons"]),
        "visit_conducted": data["visit_conducted"],
        "available_persons": ", ".join(data["available_persons"]),
        "whereabouts": data["whereabouts"],
        "appearance": data["appearance"],
        "mood": data["mood"],
        "time_to_learn": data["time_to_learn"],
        "behavior": ", ".join(data["behavior"]),
        "chores": data["chores"],
        "abuse": data["abuse"],
        "need_revisit": data["need_revisit"],
        "next_visit_date": data.get("next_visit_date", ""),
        "comments": data["comments"],
        "recommendation": data["recommendation"],
        "cdw_name": data["cdw_name"],
    }
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(flat)


# --------------------------------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------------------------------
st.title("🏠 Home Visitation Form")
st.caption(CENTRE_NAME)
st.info("Fill in one child's details, submit to generate & download their PDF, "
         "then the form clears automatically so you can log the next child.")

if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
    st.session_state.last_filename = None
    st.session_state.last_child = None

with st.form("visitation_form", clear_on_submit=True):
    st.subheader("Basic Information")
    c1, c2 = st.columns(2)
    with c1:
        date_of_visit = st.date_input("Date of Visit", value=date.today())
        child_name = st.text_input("Child's Name")
    with c2:
        child_no = st.text_input("Child's No.", value="GH ")

    st.subheader("Reason(s) for Visit")
    reasons = st.multiselect(
        "Select all that apply",
        ["Regular Home Visit", "Health", "Behavior/Attitude At Home",
         "Absent from project", "Others"],
    )
    reason_other = ""
    if "Others" in reasons:
        reason_other = st.text_input("Specify other reason")

    st.subheader("Visit Details")
    visit_conducted = st.radio(
        "How was the visit conducted?",
        ["Face To Face Visit", "Third Party Visit", "Others"],
        horizontal=True,
    )
    visit_conducted_other = ""
    if visit_conducted == "Others":
        visit_conducted_other = st.text_input("Specify how visit was conducted")

    available_persons = st.multiselect(
        "Who was available for the visit?",
        ["Parent", "Guardian", "Siblings", "Others"],
    )
    available_other = ""
    if "Others" in available_persons:
        available_other = st.text_input("Specify other person available")

    whereabouts = st.radio(
        "Child's Whereabouts?",
        ["At Home", "Travelled", "Errand", "Others"],
        horizontal=True,
    )
    whereabouts_other = ""
    if whereabouts == "Others":
        whereabouts_other = st.text_input("Specify child's whereabouts")

    st.subheader("Personal Hygiene at Home")
    hygiene = {}
    for item in HYGIENE_ITEMS:
        hygiene[item] = st.radio(item, HYGIENE_STATUSES, horizontal=True, key=f"hyg_{item}")

    st.subheader("Child's Condition")
    c3, c4 = st.columns(2)
    with c3:
        appearance = st.radio("Appearance", ["Neat", "Not neat"], horizontal=True)
    with c4:
        mood = st.radio("Mood", ["Happy", "Sad"], horizontal=True)

    time_to_learn = st.radio(
        "Does the child have time to learn after school?", ["Yes", "No"], horizontal=True
    )
    time_to_learn_reason = ""
    if time_to_learn == "No":
        time_to_learn_reason = st.text_input("If no, reason")

    behavior = st.multiselect(
        "Behavior at home",
        ["Portrays a Christ-like character", "Good personality",
         "Well-behaved", "Not well-behaved"],
    )

    chores = st.text_area("Chores assigned to this child (comma-separated)")

    abuse = st.radio(
        "Has the child been exposed to any abuse at home/school/community?",
        ["Yes", "No"], horizontal=True,
    )
    abuse_narration = ""
    if abuse == "Yes":
        abuse_narration = st.text_area("If yes, narrate")

    need_revisit = st.radio(
        "Is there a need for another immediate home visit?", ["Yes", "No"], horizontal=True
    )
    revisit_reason, next_visit_date = "", ""
    if need_revisit == "Yes":
        revisit_reason = st.text_input("Reason")
        next_visit_date = st.date_input("Next date for visit", value=date.today())

    st.subheader("Comments & Recommendation")
    comments = st.text_area("Comment and observation of the visit")
    recommendation = st.text_area(
        "Recommendation — domestic assistance required, in order of priority"
    )

    cdw_name = st.text_input("Name of CDW / Volunteer")

    submitted = st.form_submit_button("Submit & Generate Report")

if submitted:
    if not child_name or not cdw_name:
        st.error("Please fill in at least the Child's Name and CDW/Volunteer Name.")
    else:
        form_data = {
            "date_of_visit": date_of_visit.strftime("%d-%m-%Y"),
            "child_name": child_name,
            "child_no": child_no,
            "reasons": reasons,
            "reason_other": reason_other,
            "visit_conducted": visit_conducted,
            "visit_conducted_other": visit_conducted_other,
            "available_persons": available_persons,
            "available_other": available_other,
            "whereabouts": whereabouts,
            "whereabouts_other": whereabouts_other,
            "hygiene": hygiene,
            "appearance": appearance,
            "mood": mood,
            "time_to_learn": time_to_learn,
            "time_to_learn_reason": time_to_learn_reason,
            "behavior": behavior,
            "chores": chores,
            "abuse": abuse,
            "abuse_narration": abuse_narration,
            "need_revisit": need_revisit,
            "revisit_reason": revisit_reason,
            "next_visit_date": next_visit_date.strftime("%d-%m-%Y") if need_revisit == "Yes" else "",
            "comments": comments,
            "recommendation": recommendation,
            "cdw_name": cdw_name,
        }

        pdf_bytes = generate_pdf(form_data)
        log_to_csv(form_data)

        file_label = f"{child_name.replace(' ', '_')}_{form_data['date_of_visit']}.pdf"
        st.session_state.last_pdf = pdf_bytes
        st.session_state.last_filename = file_label
        st.session_state.last_child = child_name

# Shown outside the form so it survives reruns (e.g. clicking Download itself
# triggers a rerun — without this, the button would vanish before you could use it)
if st.session_state.last_pdf:
    st.success(f"Report generated for {st.session_state.last_child}. "
               f"The form above has cleared — ready for the next child.")
    st.download_button(
        f"📄 Download {st.session_state.last_child}'s Report (PDF)",
        data=st.session_state.last_pdf,
        file_name=st.session_state.last_filename,
        mime="application/pdf",
        key="download_last_pdf",
    )

# --------------------------------------------------------------------------
# Records viewer / export (all submissions so far, this session's server)
# --------------------------------------------------------------------------
st.divider()
with st.expander("📊 View / export all saved records"):
    if os.path.isfile(LOG_FILE):
        with open(LOG_FILE, "rb") as f:
            csv_bytes = f.read()
        st.download_button(
            "Download all records (CSV)",
            data=csv_bytes,
            file_name="home_visitation_records.csv",
            mime="text/csv",
        )
        import pandas as pd
        st.dataframe(pd.read_csv(LOG_FILE))
    else:
        st.info("No records saved yet on this server.")
