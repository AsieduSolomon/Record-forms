"""
ST. ANSELM'S ANGLICAN CHILD DEVELOPMENT CENTRE - SUNYANI
Home Visitation Form — Digital Data Collection + PDF Report Generator
(Mobile-friendly edition: single-column layout, everything is a plain
checkbox — no dropdown / multiselect widgets — so it's easy to fill on a phone.)

Run locally with:  streamlit run app.py
Deploy on Streamlit Community Cloud by pushing this folder to a GitHub repo
(app.py AND logo.png together) and pointing Streamlit Cloud at app.py
(see README.md for details).
"""

import io
import os
import sqlite3
import uuid
from datetime import date, datetime

import streamlit as st
from fpdf import FPDF
from PIL import Image

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
ORG_NAME = "ST. ANSELM'S ANGLICAN CHILD DEVELOPMENT CENTRE - SUNYANI"
FORM_TITLE = "HOME VISITATION FORM"
DB_PATH = "visitation_records.db"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")

st.set_page_config(page_title="St. Anselm's Home Visitation Form", page_icon="📋", layout="centered")


def load_logo_bytes():
    try:
        with open(LOGO_PATH, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


LOGO_BYTES = load_logo_bytes()

# --------------------------------------------------------------------------
# DATABASE (lightweight local storage so past reports can be re-downloaded)
# NOTE: Streamlit Cloud's filesystem is NOT permanently persistent — it can
# reset when the app restarts/redeploys. This local SQLite store is a
# convenience so reports stay available for the current running session.
# For guaranteed long-term storage, see the "Persistence" note in README.md
# (e.g. connect to Google Sheets or a hosted database instead).
# --------------------------------------------------------------------------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            child_name TEXT,
            child_no TEXT,
            date_of_visit TEXT,
            cdw_name TEXT,
            data_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_record(record_id, data):
    import json

    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO visits (id, created_at, child_name, child_no, date_of_visit, cdw_name, data_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            record_id,
            datetime.now().isoformat(timespec="seconds"),
            data.get("child_name", ""),
            data.get("child_no", ""),
            str(data.get("date_of_visit", "")),
            data.get("cdw_name", ""),
            json.dumps(data, default=str),
        ),
    )
    conn.commit()
    conn.close()


def fetch_all_records():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at, child_name, child_no, date_of_visit, cdw_name FROM visits ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def fetch_record(record_id):
    import json

    conn = get_conn()
    row = conn.execute("SELECT data_json FROM visits WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


init_db()

# --------------------------------------------------------------------------
# PDF GENERATION
# --------------------------------------------------------------------------

NAVY = (26, 43, 76)
GOLD = (176, 141, 87)
LIGHT_GREY = (245, 246, 248)
DARK_TEXT = (35, 35, 40)


class VisitationPDF(FPDF):
    def header(self):
        pass  # custom header drawn manually per page for full control

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}  |  Page {self.page_no()}", align="C")


def checkbox(pdf: FPDF, checked: bool, size=4.2):
    """Draw a small checkbox at the current x,y and advance x."""
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(90, 90, 90)
    pdf.set_line_width(0.3)
    pdf.rect(x, y + 1, size, size)
    if checked:
        pdf.set_draw_color(*NAVY)
        pdf.set_line_width(0.6)
        pdf.line(x + 0.6, y + 1 + size / 2, x + size / 2, y + 1 + size - 0.6)
        pdf.line(x + size / 2, y + 1 + size - 0.6, x + size - 0.6, y + 1.2)
        pdf.set_draw_color(90, 90, 90)
        pdf.set_line_width(0.3)
    pdf.set_xy(x + size + 2, y)


def section_title(pdf: FPDF, text):
    pdf.ln(2)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7.5, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*DARK_TEXT)
    pdf.ln(1.5)


def field_row(pdf: FPDF, label, value, label_w=55):
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(label_w, 6, label)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(20, 20, 20)
    value = value if value else "-"
    pdf.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def checklist_grid(pdf: FPDF, items, cols=2, col_width=None):
    """items: list of (label, bool). Lays out in a grid of `cols` columns."""
    if col_width is None:
        col_width = (pdf.w - pdf.l_margin - pdf.r_margin) / cols
    pdf.set_font("Helvetica", "", 9.5)
    start_x = pdf.get_x()
    for i, (label, checked) in enumerate(items):
        col = i % cols
        if col == 0:
            pdf.set_x(start_x)
        checkbox(pdf, checked)
        pdf.set_font("Helvetica", "" if not checked else "B", 9.5)
        pdf.set_text_color(*DARK_TEXT)
        avail_w = col_width - 8
        pdf.multi_cell(avail_w, 5.6, label, new_x="RIGHT" if col < cols - 1 else "LMARGIN",
                        new_y="TOP" if col < cols - 1 else "NEXT")
        if col < cols - 1:
            pdf.set_xy(start_x + (col + 1) * col_width, pdf.get_y())
        if col == cols - 1:
            pass
    if len(items) % cols != 0:
        pdf.ln(6)
    pdf.ln(1)


def build_pdf(data, logo_bytes=None) -> bytes:
    pdf = VisitationPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(14, 14, 14)

    # ----- Header -----
    # Logo is stacked centered ABOVE the org name (rather than in a corner)
    # so it never collides with the long centered title text.
    y_cursor = 12
    if logo_bytes:
        try:
            logo_w = 24
            with Image.open(io.BytesIO(logo_bytes)) as im:
                logo_h = logo_w * (im.height / im.width)
            logo_x = (pdf.w - logo_w) / 2
            pdf.image(io.BytesIO(logo_bytes), x=logo_x, y=y_cursor, w=logo_w)
            y_cursor += logo_h + 3
        except Exception:
            pass

    pdf.set_xy(14, y_cursor)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, ORG_NAME, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 7, FORM_TITLE, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.8)
    pdf.line(14, pdf.get_y() + 1, pdf.w - 14, pdf.get_y() + 1)
    pdf.ln(5)

    # ----- Identification -----
    section_title(pdf, "CHILD & VISIT IDENTIFICATION")
    col_w = (pdf.w - 28) / 2
    y0 = pdf.get_y()
    pdf.set_xy(14, y0)
    field_row(pdf, "Child's Name:", data.get("child_name", ""), label_w=32)
    pdf.set_xy(14 + col_w, y0)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(32, 6, "Child's No:")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 6, data.get("child_no", "-"), new_x="LMARGIN", new_y="NEXT")

    y0 = pdf.get_y()
    pdf.set_xy(14, y0)
    field_row(pdf, "Date of Visit:", str(data.get("date_of_visit", "")), label_w=32)
    pdf.set_xy(14 + col_w, y0)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(32, 6, "CDW / Volunteer:")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 6, data.get("cdw_name", "-"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ----- Reason for visit -----
    section_title(pdf, "REASON(S) FOR VISIT")
    reasons = []
    if data.get("reason_absent"):
        detail = data.get("reason_absent_date", "")
        reasons.append(("Absent from project" + (f" on {detail}" if detail else ""), True))
    if data.get("reason_health"):
        detail = data.get("reason_health_detail", "")
        reasons.append(("Health" + (f" — {detail}" if detail else ""), True))
    if data.get("reason_other"):
        detail = data.get("reason_other_detail", "")
        reasons.append(("Other" + (f" — {detail}" if detail else ""), True))
    if not reasons:
        reasons = [("No specific reason recorded", False)]
    for label, checked in reasons:
        checkbox(pdf, checked)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.multi_cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ----- How conducted -----
    section_title(pdf, "HOW THE VISIT WAS CONDUCTED")
    checklist_grid(pdf, [
        ("Telephone call", data.get("visit_method") == "Telephone call"),
        ("Went to child's home", data.get("visit_method") == "Went to child's home"),
    ], cols=2)
    field_row(pdf, "Who was available:", data.get("who_available", ""), label_w=48)
    field_row(pdf, "Child's whereabouts:", data.get("child_whereabouts", ""), label_w=48)
    pdf.ln(1)

    # ----- Reason for not coming (only if relevant) -----
    not_coming = data.get("reason_not_coming", [])
    if not_coming:
        section_title(pdf, "REASON FOR NOT COMING TO PROJECT")
        all_options = ["Sick at home", "Went for Extra classes", "Child did not feel like coming",
                        "Was sent on an errand", "Travelled", "Others"]
        checklist_grid(pdf, [(o, o in not_coming) for o in all_options], cols=2)
        if "Travelled" in not_coming:
            field_row(pdf, "Travelled to:", data.get("travel_where", ""), label_w=48)
            field_row(pdf, "Date of return:", data.get("date_of_return", ""), label_w=48)
        if "Others" in not_coming:
            field_row(pdf, "Others (specify):", data.get("others_specify", ""), label_w=48)
        pdf.ln(1)

    # ----- Ready for next meeting -----
    section_title(pdf, "IS CHILD READY TO COME TO PROJECT NEXT MEETING?")
    ready = data.get("ready_next_meeting", "")
    checklist_grid(pdf, [
        ("Yes", ready == "Yes"), ("No", ready == "No"), ("Not Sure", ready == "Not Sure"),
    ], cols=3)

    # ----- Personal basic items -----
    section_title(pdf, "PERSONAL BASIC ITEMS")
    all_personal = ["Sponge / towel", "Bag for clothes", "Mat / mattress (may not be personal)",
                     "Toothbrush / paste", "Cup / spoon / plate", "Slipper / shoe"]
    sel = data.get("personal_items", [])
    checklist_grid(pdf, [(o, o in sel) for o in all_personal], cols=2)

    # ----- Learning condition -----
    section_title(pdf, "LEARNING CONDITION OF THE CHILD")
    all_learning = ["Light source", "Reading books", "Child is able to do his/her homework",
                     "Child is able to learn on his/her own", "Child's academic condition has improved"]
    sel = data.get("learning_aids", [])
    checklist_grid(pdf, [(o, o in sel) for o in all_learning], cols=2)

    # ----- Living condition -----
    section_title(pdf, "LIVING CONDITION OF THE CHILD")
    all_living = ["Eats at least 3 times a day", "Has good social behavior (i.e. respect)",
                  "Child has been a change in the family", "Child has access to TV in and around home",
                  "Child is able to do house chores"]
    sel = data.get("living_condition", [])
    checklist_grid(pdf, [(o, o in sel) for o in all_living], cols=2)

    # ----- Compassion items -----
    section_title(pdf, "COMPASSION ITEMS CHECK")
    all_compassion = ["Sponsor letters", "Sponsor gift items", "Compassion Bible", "Mosquito net"]
    sel = data.get("compassion_items", [])
    checklist_grid(pdf, [(o, o in sel) for o in all_compassion], cols=2)

    # ----- Follow up -----
    section_title(pdf, "IS THERE A NEED FOR ANOTHER FOLLOW-UP VISIT?")
    fu = data.get("followup_needed", "")
    checklist_grid(pdf, [("Yes", fu == "Yes"), ("No", fu == "No")], cols=2)

    # ----- Comments -----
    section_title(pdf, "ANY OTHER COMMENTS")
    pdf.set_font("Helvetica", "", 9.5)
    comments = data.get("comments", "") or "-"
    pdf.set_fill_color(*LIGHT_GREY)
    y_before = pdf.get_y()
    pdf.multi_cell(0, 6, comments, border=0, fill=True)
    pdf.ln(2)

    # ----- Signature -----
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(50, 6, "CDW / Volunteer Signature:")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 6, data.get("signature", "") or "________________________", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    return bytes(out)


# --------------------------------------------------------------------------
# STREAMLIT UI  (single-column layout, plain checkboxes — no dropdowns —
# so it's comfortable to fill on a phone)
# --------------------------------------------------------------------------

if LOGO_BYTES:
    st.image(LOGO_BYTES, width=110)
else:
    st.warning("Logo not found. Place a file named **logo.png** in the same folder as app.py.")

st.title("📋 Home Visitation Form")
st.caption(ORG_NAME)

tab_new, tab_history = st.tabs(["🆕 New Visit Report", "🗂️ Past Reports"])

with tab_new:
    st.markdown("Fill in the details collected during the home visit below, then generate the PDF report.")

    with st.form("visitation_form", clear_on_submit=False):
        st.subheader("Child & Visit Identification")
        child_name = st.text_input("Child's Name *")
        child_no = st.text_input("Child's No", value="GH 0761000")
        date_of_visit = st.date_input("Date of Visit *", value=date.today())
        cdw_name = st.text_input("Name of CDW / Volunteer *")

        st.divider()
        st.subheader("Reason(s) for Visit")
        st.caption("Tick all that apply")
        reason_absent = st.checkbox("Absent from project")
        reason_absent_date = st.text_input("Absent date(s)", disabled=not reason_absent, key="rad")
        reason_health = st.checkbox("Health")
        reason_health_detail = st.text_input("Health details", disabled=not reason_health, key="rhd")
        reason_other = st.checkbox("Any other")
        reason_other_detail = st.text_input("Other details", disabled=not reason_other, key="rod")

        st.divider()
        st.subheader("How Was the Visit Conducted?")
        visit_method = st.radio("Method", ["Telephone call", "Went to child's home"],
                                 label_visibility="collapsed")
        who_available = st.text_input("Who was available for the visit?")
        child_whereabouts = st.text_input("Child's whereabouts")

        st.divider()
        st.subheader("Reason for Not Coming to Project")
        st.caption("Tick all that apply (leave blank if not relevant)")
        nc_options = ["Sick at home", "Went for Extra classes", "Child did not feel like coming",
                      "Was sent on an errand", "Travelled", "Others"]
        reason_not_coming = [opt for opt in nc_options if st.checkbox(opt, key=f"nc_{opt}")]
        travel_where = st.text_input("If travelled, to where?")
        date_of_return = st.text_input("Date of return")
        others_specify = st.text_input("Others — specify")

        st.divider()
        st.subheader("Is Child Ready to Come to Project Next Meeting?")
        ready_next_meeting = st.radio("Ready?", ["Yes", "No", "Not Sure"], label_visibility="collapsed")

        st.divider()
        st.subheader("Personal Basic Items Present")
        st.caption("Tick all that apply")
        personal_options = ["Sponge / towel", "Bag for clothes", "Mat / mattress (may not be personal)",
                             "Toothbrush / paste", "Cup / spoon / plate", "Slipper / shoe"]
        personal_items = [opt for opt in personal_options if st.checkbox(opt, key=f"pi_{opt}")]

        st.divider()
        st.subheader("Learning Condition of the Child")
        st.caption("Tick all that apply")
        learning_options = ["Light source", "Reading books", "Child is able to do his/her homework",
                             "Child is able to learn on his/her own", "Child's academic condition has improved"]
        learning_aids = [opt for opt in learning_options if st.checkbox(opt, key=f"la_{opt}")]

        st.divider()
        st.subheader("Living Condition of the Child")
        st.caption("Tick all that apply")
        living_options = ["Eats at least 3 times a day", "Has good social behavior (i.e. respect)",
                           "Child has been a change in the family", "Child has access to TV in and around home",
                           "Child is able to do house chores"]
        living_condition = [opt for opt in living_options if st.checkbox(opt, key=f"lc_{opt}")]

        st.divider()
        st.subheader("Compassion Items Check")
        st.caption("Tick all that apply")
        compassion_options = ["Sponsor letters", "Sponsor gift items", "Compassion Bible", "Mosquito net"]
        compassion_items = [opt for opt in compassion_options if st.checkbox(opt, key=f"ci_{opt}")]

        st.divider()
        st.subheader("Is There a Need for Another Follow-up Visit?")
        followup_needed = st.radio("Follow-up", ["Yes", "No"], label_visibility="collapsed")

        st.divider()
        st.subheader("Comments & Signature")
        comments = st.text_area("Any other comments (e.g. child's condition, appearance, behavior at home)")
        signature = st.text_input("CDW / Volunteer signature (type full name)")

        submitted = st.form_submit_button("Generate Report ➜", use_container_width=True)

    if submitted:
        if not child_name or not cdw_name:
            st.error("Please fill in at least the Child's Name and CDW/Volunteer Name before generating a report.")
        else:
            data = dict(
                child_name=child_name, child_no=child_no, date_of_visit=date_of_visit, cdw_name=cdw_name,
                reason_absent=reason_absent, reason_absent_date=reason_absent_date,
                reason_health=reason_health, reason_health_detail=reason_health_detail,
                reason_other=reason_other, reason_other_detail=reason_other_detail,
                visit_method=visit_method, who_available=who_available, child_whereabouts=child_whereabouts,
                reason_not_coming=reason_not_coming, travel_where=travel_where, date_of_return=date_of_return,
                others_specify=others_specify, ready_next_meeting=ready_next_meeting,
                personal_items=personal_items, learning_aids=learning_aids, living_condition=living_condition,
                compassion_items=compassion_items, followup_needed=followup_needed,
                comments=comments, signature=signature,
            )
            pdf_bytes = build_pdf(data, logo_bytes=LOGO_BYTES)

            record_id = str(uuid.uuid4())
            save_record(record_id, data)

            st.success(f"Report generated for **{child_name}**.")
            fname = f"{child_name.replace(' ', '_')}_{date_of_visit}.pdf"
            st.download_button("⬇️ Download PDF Report", data=pdf_bytes, file_name=fname,
                                mime="application/pdf", use_container_width=True)

with tab_history:
    st.markdown("Reports generated during this session are listed below and can be re-downloaded.")
    st.info(
        "⚠️ **Persistence note:** this history is stored locally on the app's server. "
        "Streamlit Community Cloud can reset this storage when the app restarts or redeploys, "
        "so treat this list as a convenience, not permanent backup. Download each PDF and keep it "
        "in the child's physical/digital file right after generating it. See README.md for options "
        "to connect a permanent database (e.g. Google Sheets) if needed."
    )
    records = fetch_all_records()
    if not records:
        st.write("No reports generated yet.")
    else:
        for rid, created_at, cname, cno, dov, cdw in records:
            with st.expander(f"{cname} — {dov}  (recorded {created_at})"):
                st.write(f"**Child's No:** {cno}")
                st.write(f"**CDW/Volunteer:** {cdw}")
                if st.button("Regenerate PDF", key=f"regen_{rid}"):
                    data = fetch_record(rid)
                    pdf_bytes = build_pdf(data, logo_bytes=LOGO_BYTES)
                    fname = f"{cname.replace(' ', '_')}_{dov}.pdf"
                    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=fname,
                                        mime="application/pdf", key=f"dl_{rid}")
