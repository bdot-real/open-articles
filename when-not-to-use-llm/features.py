"""Feature definitions, in one place so the generator and the models agree."""

COLUMNS = [
    "lead_days",          # days between booking and appointment
    "prior_noshows",
    "prior_attended",
    "age",
    "hour",               # hour of day, 8 to 17
    "dow",                # weekday, 0 = Monday
    "sms_reminder",
    "distance_km",
    "is_new_patient",
    "reschedules",
    "copay",
    "slot_minutes",
    "hist_noshow_rate",   # prior_noshows / (prior_noshows + prior_attended)
]

# Appended by hybrid/extract.py when free-text notes are available.
HYBRID_COLUMNS = ["transport_difficulty", "anxiety_signal", "caregiver_dependent"]
