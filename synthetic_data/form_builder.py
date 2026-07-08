"""
Generates synthetic EHR intake form HTML across 4 layouts with randomised:
- field selection and order
- label wording (real-world variants per field)
- color scheme
- optional modal, alert banner, loading spinner

Every interactive widget element carries a data-widget-class attribute —
this is what renderer.py queries after rendering to auto-extract ground-truth
bounding boxes, so no manual annotation is needed.
"""

import random

# ---------------------------------------------------------------------------
# Color schemes — enough visual variety to prevent the model from memorising
# a single look
# ---------------------------------------------------------------------------

COLOR_SCHEMES = [
    {"bg": "#f4f6f8", "card": "#ffffff", "primary": "#2563eb",
     "text": "#1e293b", "label": "#374151", "border": "#d1d5db"},
    {"bg": "#1e293b", "card": "#334155", "primary": "#38bdf8",
     "text": "#f1f5f9", "label": "#94a3b8", "border": "#475569"},
    {"bg": "#f0fdf4", "card": "#ffffff", "primary": "#16a34a",
     "text": "#14532d", "label": "#166534", "border": "#bbf7d0"},
    {"bg": "#f5f3ff", "card": "#ffffff", "primary": "#7c3aed",
     "text": "#3b0764", "label": "#5b21b6", "border": "#ddd6fe"},
    {"bg": "#fff7ed", "card": "#ffffff", "primary": "#ea580c",
     "text": "#7c2d12", "label": "#9a3412", "border": "#fed7aa"},
]

# ---------------------------------------------------------------------------
# Label variants — same semantic field, different wording across EHR vendors
# ---------------------------------------------------------------------------

LABEL_VARIANTS = {
    "patient_name":      ["Patient Name", "Full Name", "Patient Full Name",
                          "Name (Last, First)", "Legal Name", "Name"],
    "dob":               ["Date of Birth", "DOB", "Birth Date",
                          "Date of Birth (MM/DD/YYYY)", "Patient DOB", "Birthdate"],
    "sex":               ["Sex", "Gender", "Biological Sex",
                          "Sex at Birth", "Gender Identity"],
    "insurance_id":      ["Insurance ID", "Member ID", "Insurance Member ID",
                          "Policy Number", "Subscriber ID", "Member Number"],
    "address":           ["Address", "Street Address", "Home Address",
                          "Address Line 1", "Residential Address"],
    "phone":             ["Phone Number", "Phone", "Primary Phone",
                          "Contact Number", "Mobile Number"],
    "email":             ["Email", "Email Address", "Patient Email", "Contact Email"],
    "emergency_contact": ["Emergency Contact", "Emergency Contact Name",
                          "Next of Kin", "Emergency Contact (Name)"],
    "blood_type":        ["Blood Type", "Blood Group", "ABO Blood Type"],
    "allergies":         ["Known Allergies", "Allergies",
                          "Drug Allergies", "Allergy List"],
    "consent":           ["I consent to treatment", "Patient Consent",
                          "Agree to Terms", "I agree to the terms of treatment"],
}

FORM_TITLES = [
    "Patient Demographics", "Patient Registration", "Patient Intake Form",
    "Patient Information", "New Patient Form", "Patient Record Update",
    "Clinical Intake",
]

MODAL_TYPES = [
    {
        "title": "Session Timeout Warning",
        "body": "Your session will expire in 5 minutes due to inactivity.",
        "buttons": ["Continue Session", "Log Out"],
    },
    {
        "title": "Please Verify Your Identity",
        "body": "Enter the last 4 digits of the patient's SSN to continue.",
        "buttons": ["Verify", "Cancel"],
    },
    {
        "title": "Privacy Policy Update",
        "body": "Our privacy policy has been updated. Please review and acknowledge.",
        "buttons": ["I Acknowledge", "View Policy"],
    },
    {
        "title": "Unsaved Changes",
        "body": "You have unsaved changes. Do you want to save before leaving?",
        "buttons": ["Save", "Discard", "Cancel"],
    },
]

ALERT_MESSAGES = [
    "&#9888; Please review all fields before submitting.",
    "&#8505; Required fields are marked with an asterisk (*).",
    "&#10003; Patient record loaded successfully.",
    "&#9888; Some required fields are incomplete.",
]

# ---------------------------------------------------------------------------
# Field pool
# Each entry: (field_key, widget_class, html_input_type, options_list|None)
# ---------------------------------------------------------------------------

# These are always available for random selection
BASE_FIELDS = [
    ("patient_name",      "TEXT_FIELD", "text",  None),
    ("insurance_id",      "TEXT_FIELD", "text",  None),
    ("address",           "TEXT_FIELD", "text",  None),
    ("phone",             "TEXT_FIELD", "tel",   None),
    ("email",             "TEXT_FIELD", "email", None),
    ("emergency_contact", "TEXT_FIELD", "text",  None),
    ("allergies",         "TEXT_FIELD", "text",  None),
]


def _sex_field():
    """Sex is either a DROPDOWN or RADIO_BUTTON — chosen randomly."""
    if random.random() < 0.6:
        return ("sex", "DROPDOWN", "select",
                ["-- Select --", "Male", "Female", "Other", "Prefer not to say"])
    return ("sex", "RADIO_BUTTON", "radio", ["Male", "Female", "Other"])


def _dob_field():
    """DOB is either a plain text field or a calendar control — chosen randomly."""
    if random.random() < 0.5:
        return ("dob", "TEXT_FIELD", "text", None)
    return ("dob", "CALENDAR_CONTROL", "date", None)


def _blood_type_field():
    return ("blood_type", "DROPDOWN", "select",
            ["-- Select --", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])


def _consent_field():
    return ("consent", "CHECKBOX", "checkbox", None)


# ---------------------------------------------------------------------------
# Public: build a random config dict for one form generation
# ---------------------------------------------------------------------------

def build_random_config() -> dict:
    """
    Returns a config dict that generate_form() consumes.
    Every call produces a different combination of layout, fields,
    labels, color scheme, and optional overlays.
    """
    # pick a random subset of optional fields, always include patient_name
    optional = [f for f in BASE_FIELDS if f[0] != "patient_name"]
    random.shuffle(optional)
    n = random.randint(3, len(optional))
    fields = [next(f for f in BASE_FIELDS if f[0] == "patient_name")] + optional[:n]

    # add typed fields with their own widget-class variation
    fields.append(_dob_field())
    fields.append(_sex_field())
    if random.random() < 0.5:
        fields.append(_blood_type_field())
    if random.random() < 0.4:
        fields.append(_consent_field())

    random.shuffle(fields)  # order varies across forms

    return {
        "layout":       random.randint(1, 4),
        "fields":       fields,
        "color_scheme": random.choice(COLOR_SCHEMES),
        "title":        random.choice(FORM_TITLES),
        "submit_label": random.choice(["Save", "Submit", "Save & Continue", "Update Record"]),
        "add_modal":    random.random() < 0.25,
        "modal_config": random.choice(MODAL_TYPES),
        "add_alert":    random.random() < 0.30,
        "add_spinner":  random.random() < 0.10,
    }


# ---------------------------------------------------------------------------
# HTML helpers — one function per widget type, per layout style
# ---------------------------------------------------------------------------

def _uid(key):
    return f"{key}_{random.randint(1000, 9999)}"


def _input_html(uid, widget_class, input_type, key, cs):
    placeholder = ' placeholder="MM/DD/YYYY"' if (input_type == "text" and key == "dob") else ""
    return (f'<input type="{input_type}" id="{uid}" name="{uid}" '
            f'data-widget-class="{widget_class}"{placeholder} '
            f'style="width:100%;padding:8px;font-size:14px;box-sizing:border-box;'
            f'border:1px solid {cs["border"]};border-radius:4px;'
            f'background:{cs["card"]};color:{cs["text"]};">')


def _select_html(uid, options, cs):
    opts = "\n".join(f'<option value="{o}">{o}</option>' for o in options)
    return (f'<select id="{uid}" name="{uid}" data-widget-class="DROPDOWN" '
            f'style="width:100%;padding:8px;font-size:14px;box-sizing:border-box;'
            f'border:1px solid {cs["border"]};border-radius:4px;'
            f'background:{cs["card"]};color:{cs["text"]};">'
            f'\n{opts}\n</select>')


def _radio_html(uid, options, cs):
    radios = ""
    for opt in options:
        oid = f"{uid}_{opt.lower().replace(' ', '_')}"
        radios += (f'<label style="display:inline-flex;align-items:center;gap:4px;'
                   f'margin-right:12px;font-weight:normal;color:{cs["text"]};cursor:pointer;">'
                   f'<input type="radio" id="{oid}" name="{uid}" value="{opt}" '
                   f'data-widget-class="RADIO_BUTTON"> {opt}</label>')
    return f'<div style="margin-top:4px;">{radios}</div>'


def _checkbox_html(uid, label, cs):
    return (f'<div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
            f'<input type="checkbox" id="{uid}" name="{uid}" data-widget-class="CHECKBOX" '
            f'style="width:16px;height:16px;">'
            f'<label for="{uid}" style="margin:0;font-weight:normal;color:{cs["text"]};">'
            f'{label}</label></div>')


def _button_html(label, cs, extra_style=""):
    return (f'<button type="button" data-widget-class="BUTTON" '
            f'style="padding:10px 20px;background:{cs["primary"]};color:#fff;'
            f'border:none;border-radius:4px;font-size:14px;cursor:pointer;{extra_style}">'
            f'{label}</button>')


def _modal_html(cs, modal_config):
    buttons = " ".join(_button_html(b, cs, "margin-right:8px;")
                       for b in modal_config["buttons"])
    # data-widget-class on the inner dialog box — that's the meaningful detection target,
    # not the full-screen translucent overlay
    return f"""
<div style="position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,0.5);z-index:1000;
            display:flex;align-items:center;justify-content:center;">
  <div data-widget-class="MODAL_DIALOG"
       style="background:{cs["card"]};padding:32px;border-radius:8px;
              max-width:440px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.3);">
    <h3 style="margin-top:0;color:{cs["text"]};">{modal_config["title"]}</h3>
    <p style="color:{cs["text"]};margin-bottom:24px;">{modal_config["body"]}</p>
    <div>{buttons}</div>
  </div>
</div>"""


def _alert_html(cs):
    msg = random.choice(ALERT_MESSAGES)
    return (f'<div data-widget-class="ALERT_BANNER" '
            f'style="background:#fef9c3;border:1px solid #fde047;color:#713f12;'
            f'padding:10px 16px;border-radius:6px;margin-bottom:16px;font-size:13px;">'
            f'{msg}</div>')


def _spinner_html():
    return """
<div style="position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(255,255,255,0.7);z-index:999;
            display:flex;align-items:center;justify-content:center;">
  <div data-widget-class="LOADING_SPINNER"
       style="width:48px;height:48px;border:5px solid #e2e8f0;
              border-top-color:#2563eb;border-radius:50%;
              animation:spin 0.8s linear infinite;"></div>
</div>
<style>@keyframes spin { to { transform:rotate(360deg); } }</style>"""


# ---------------------------------------------------------------------------
# Per-layout field renderers
# ---------------------------------------------------------------------------

def _field_single_column(key, widget_class, input_type, options, label, cs):
    uid = _uid(key)
    label_style = (f'display:block;margin-bottom:4px;font-weight:600;'
                   f'font-size:14px;color:{cs["label"]};')

    if widget_class == "CHECKBOX":
        return (f'<div style="margin-top:16px;">'
                f'<label style="{label_style}">{label}</label>'
                f'{_checkbox_html(uid, label, cs)}</div>')

    if widget_class == "RADIO_BUTTON":
        return (f'<div style="margin-top:16px;">'
                f'<label style="{label_style}">{label}</label>'
                f'{_radio_html(uid, options, cs)}</div>')

    if widget_class == "DROPDOWN":
        return (f'<div style="margin-top:16px;">'
                f'<label for="{uid}" style="{label_style}">{label}</label>'
                f'{_select_html(uid, options, cs)}</div>')

    # TEXT_FIELD / CALENDAR_CONTROL
    return (f'<div style="margin-top:16px;">'
            f'<label for="{uid}" style="{label_style}">{label}</label>'
            f'{_input_html(uid, widget_class, input_type, key, cs)}</div>')


def _field_two_column(key, widget_class, input_type, options, label, cs, full_row=False):
    uid = _uid(key)
    col_span = "grid-column:1/-1;" if full_row else ""
    label_style = f'display:block;margin-bottom:4px;font-weight:600;font-size:13px;color:{cs["label"]};'
    wrapper = f'<div style="{col_span}">'

    if widget_class == "CHECKBOX":
        return wrapper + f'<label style="{label_style}">{label}</label>{_checkbox_html(uid, label, cs)}</div>'
    if widget_class == "RADIO_BUTTON":
        return wrapper + f'<label style="{label_style}">{label}</label>{_radio_html(uid, options, cs)}</div>'
    if widget_class == "DROPDOWN":
        return wrapper + f'<label for="{uid}" style="{label_style}">{label}</label>{_select_html(uid, options, cs)}</div>'
    return wrapper + f'<label for="{uid}" style="{label_style}">{label}</label>{_input_html(uid, widget_class, input_type, key, cs)}</div>'


def _field_inline(key, widget_class, input_type, options, label, cs):
    uid = _uid(key)
    label_style = (f'min-width:160px;font-weight:600;font-size:13px;'
                   f'color:{cs["label"]};text-align:right;flex-shrink:0;')
    wrapper = (f'<div style="display:flex;align-items:center;'
               f'margin-top:14px;gap:12px;">'
               f'<label for="{uid}" style="{label_style}">{label}</label>')

    if widget_class == "CHECKBOX":
        return (wrapper +
                f'<input type="checkbox" id="{uid}" name="{uid}" '
                f'data-widget-class="CHECKBOX" style="width:16px;height:16px;"></div>')
    if widget_class == "RADIO_BUTTON":
        return wrapper + _radio_html(uid, options, cs) + "</div>"
    if widget_class == "DROPDOWN":
        s = _select_html(uid, options, cs)
        # override width for inline layout — flex handles sizing
        s = s.replace("width:100%;", "flex:1;")
        return wrapper + s + "</div>"

    i = _input_html(uid, widget_class, input_type, key, cs)
    i = i.replace("width:100%;", "flex:1;")
    return wrapper + i + "</div>"


# ---------------------------------------------------------------------------
# Layout builders — each returns a complete HTML document string
# ---------------------------------------------------------------------------

FULL_ROW_KEYS = {"patient_name", "address", "allergies", "emergency_contact"}


def _layout_single_column(config):
    cs, fields = config["color_scheme"], config["fields"]
    title, submit = config["title"], config["submit_label"]

    body = ""
    if config["add_alert"]:
        body += _alert_html(cs)
    for key, widget_class, input_type, options in fields:
        label = random.choice(LABEL_VARIANTS.get(key, [key.replace("_", " ").title()]))
        body += _field_single_column(key, widget_class, input_type, options, label, cs)
    body += f'<div style="margin-top:24px;">{_button_html(submit, cs)}</div>'

    modal  = _modal_html(cs, config["modal_config"]) if config["add_modal"] else ""
    spinner = _spinner_html() if config["add_spinner"] else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family:Arial,sans-serif;background:{cs["bg"]};padding:40px;margin:0;">
  <div style="background:{cs["card"]};max-width:480px;margin:auto;padding:30px;
              border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.15);">
    <h2 style="margin-top:0;color:{cs["text"]};">{title}</h2>
    {body}
  </div>
  {modal}{spinner}
</body></html>"""


def _layout_two_column(config):
    cs, fields = config["color_scheme"], config["fields"]
    title, submit = config["title"], config["submit_label"]

    body = ""
    if config["add_alert"]:
        body += _alert_html(cs)
    grid_items = ""
    for key, widget_class, input_type, options in fields:
        label = random.choice(LABEL_VARIANTS.get(key, [key.replace("_", " ").title()]))
        grid_items += _field_two_column(key, widget_class, input_type, options, label, cs,
                                        full_row=(key in FULL_ROW_KEYS))

    body += (f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px 24px;">'
             f'{grid_items}</div>')
    body += f'<div style="margin-top:24px;">{_button_html(submit, cs)}</div>'

    modal   = _modal_html(cs, config["modal_config"]) if config["add_modal"] else ""
    spinner = _spinner_html() if config["add_spinner"] else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:{cs["bg"]};padding:40px;margin:0;">
  <div style="background:{cs["card"]};max-width:640px;margin:auto;padding:32px;
              border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">
    <h2 style="margin-top:0;color:{cs["text"]};">{title}</h2>
    {body}
  </div>
  {modal}{spinner}
</body></html>"""


def _layout_inline(config):
    cs, fields = config["color_scheme"], config["fields"]
    title, submit = config["title"], config["submit_label"]

    body = ""
    if config["add_alert"]:
        body += _alert_html(cs)
    for key, widget_class, input_type, options in fields:
        label = random.choice(LABEL_VARIANTS.get(key, [key.replace("_", " ").title()]))
        body += _field_inline(key, widget_class, input_type, options, label, cs)
    body += (f'<div style="margin-top:24px;margin-left:172px;">'
             f'{_button_html(submit, cs)}</div>')

    modal   = _modal_html(cs, config["modal_config"]) if config["add_modal"] else ""
    spinner = _spinner_html() if config["add_spinner"] else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family:Georgia,serif;background:{cs["bg"]};padding:40px;margin:0;">
  <div style="background:{cs["card"]};max-width:560px;margin:auto;padding:30px;
              border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,0.12);">
    <h2 style="margin-top:0;color:{cs["text"]};border-bottom:2px solid {cs["primary"]};
               padding-bottom:8px;">{title}</h2>
    {body}
  </div>
  {modal}{spinner}
</body></html>"""


def _layout_tabbed(config):
    cs, fields = config["color_scheme"], config["fields"]
    title, submit = config["title"], config["submit_label"]

    mid = max(1, len(fields) // 2)
    tab1_fields, tab2_fields = fields[:mid], fields[mid:]

    tab1_name = random.choice(["Demographics", "Personal Info", "Basic Info"])
    tab2_name = random.choice(["Insurance", "Contact Details", "Medical Info"])

    def _tab_fields_html(flist):
        html = ""
        for key, widget_class, input_type, options in flist:
            label = random.choice(LABEL_VARIANTS.get(key, [key.replace("_", " ").title()]))
            html += _field_single_column(key, widget_class, input_type, options, label, cs)
        return html

    tab1_html = _tab_fields_html(tab1_fields)
    tab2_html = _tab_fields_html(tab2_fields)
    alert = _alert_html(cs) if config["add_alert"] else ""
    modal   = _modal_html(cs, config["modal_config"]) if config["add_modal"] else ""
    spinner = _spinner_html() if config["add_spinner"] else ""

    tab_btn_base = (f'flex:1;padding:12px;border:none;font-size:14px;'
                    f'cursor:pointer;font-weight:600;')

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title>
<style>
  .tab-content {{ display:none; padding:24px; }}
  .tab-content.active {{ display:block; }}
  .tab-btn {{ {tab_btn_base} background:transparent;color:{cs["label"]}; }}
  .tab-btn.active {{ background:{cs["card"]};color:{cs["primary"]};
                     border-bottom:2px solid {cs["primary"]}; }}
</style>
</head>
<body style="font-family:Arial,sans-serif;background:{cs["bg"]};padding:40px;margin:0;">
  <div style="background:{cs["card"]};max-width:500px;margin:auto;
              border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.15);overflow:hidden;">
    <div style="display:flex;background:{cs["bg"]};border-bottom:2px solid {cs["border"]};">
      <button class="tab-btn active" onclick="showTab(0)"
              data-widget-class="BUTTON">{tab1_name}</button>
      <button class="tab-btn" onclick="showTab(1)"
              data-widget-class="BUTTON">{tab2_name}</button>
    </div>
    <div class="tab-content active">
      {alert}{tab1_html}
      <div style="margin-top:20px;">{_button_html(submit, cs)}</div>
    </div>
    <div class="tab-content">
      {tab2_html}
      <div style="margin-top:20px;">{_button_html(submit, cs)}</div>
    </div>
  </div>
  {modal}{spinner}
  <script>
    function showTab(n) {{
      document.querySelectorAll('.tab-content').forEach((el,i) =>
        el.classList.toggle('active', i===n));
      document.querySelectorAll('.tab-btn').forEach((el,i) =>
        el.classList.toggle('active', i===n));
    }}
  </script>
</body></html>"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_form(config: dict) -> str:
    """
    Generate a complete HTML document string from a config dict.
    config is produced by build_random_config() or built manually for testing.
    """
    layout = config["layout"]
    if layout == 1:
        return _layout_single_column(config)
    elif layout == 2:
        return _layout_two_column(config)
    elif layout == 3:
        return _layout_inline(config)
    elif layout == 4:
        return _layout_tabbed(config)
    raise ValueError(f"Unknown layout: {layout}")
