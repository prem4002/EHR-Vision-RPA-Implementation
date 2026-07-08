WIDGET_CLASSES = [
    "TEXT_FIELD",
    "DROPDOWN",
    "CHECKBOX",
    "RADIO_BUTTON",
    "BUTTON",
    "CALENDAR_CONTROL",
    "MODAL_DIALOG",
    "ALERT_BANNER",
    "LOADING_SPINNER",
]

# maps class name to integer index for DETR training
CLASS_TO_IDX = {cls: idx for idx, cls in enumerate(WIDGET_CLASSES)}
IDX_TO_CLASS = {idx: cls for cls, idx in CLASS_TO_IDX.items()}

NUM_CLASSES = len(WIDGET_CLASSES)