import streamlit as st

APP_NAME = "Integrated Professional Selling Lab"
APP_VERSION = "1.0.0"

# Brand colors
COLOR_PRIMARY = "#1B3A6B"
COLOR_SECONDARY = "#2E5FA3"
COLOR_ACCENT = "#4A90D9"
COLOR_SUCCESS = "#27AE60"
COLOR_WARNING = "#F39C12"
COLOR_DANGER = "#E74C3C"
COLOR_LIGHT = "#FAFAFA"
COLOR_DARK = "#0E1117"
COLOR_CARD_BG = "#1A2332"

CHAPTERS = {
    1: {"title": "The Selling Profession", "active": False},
    2: {"title": "Ethics in Sales", "active": False},
    3: {"title": "Buyer Behavior", "active": False},
    4: {"title": "Prospecting", "active": False},
    5: {"title": "Pre-Approach & Planning", "active": False},
    6: {"title": "Approach & Opening", "active": False},
    7: {"title": "Discovery & SPIN Questioning", "active": True},
    8: {"title": "Presentation & Demonstration", "active": False},
    9: {"title": "Objections, Negotiation & Closing", "active": True},
    10: {"title": "Closing the Sale", "active": False},
    11: {"title": "Follow-up & Relationship Management", "active": False},
}


def get_openai_api_key() -> str:
    return st.secrets["OPENAI_API_KEY"]
