# Multimodal Construction Intelligence Platform

![AI Maintained](https://img.shields.io/badge/readme-AI%20maintained-blue)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://construction-intelligence-platform-gules.vercel.app)

**Live Web App:** [https://construction-intelligence-platform-gules.vercel.app](https://construction-intelligence-platform-gules.vercel.app)  
**Developed by:** Santusht Kotai

A multimodal AI platform designed for modern construction intelligence, offering site safety compliance auditing, structural crack triage and diagnostics, cost and materials estimation, and an interactive weather-aware daily site assistant.

## Features
- **Site Safety & PPE Audit:** Upload site photos for visual screening of PPE compliance (helmets, high-visibility vests, steel-toe footwear, safety harnesses) and hazard detection with downloadable JSON audit reports.
- **Crack Diagnostics:** Classify structural and surface defects, assess crack severity and urgency, provide repair recommendations, and export diagnostic logs.
- **Planning & Valuation:** Dynamic planning assumptions for built-up area, CapEx, asset valuation, rough material quantities (cement, steel, sand, aggregate), and progress tracking.
- **Daily Site Assistant & Weather:** Weather-aware construction precautions (high wind, heavy rain, extreme heat) and an interactive conversational assistant powered by Google Gemini.

## Run Locally
Python 3.9+ is recommended.

```bash
# Clone the repository
git clone [https://github.com/santusht06/construction-intelligence-platform.git](https://github.com/santusht06/construction-intelligence-platform.git)
cd construction-intelligence-platform
python -m venv .venv

# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
```

Open the local URL shown by Streamlit in your browser.

## Gemini API Configuration
Enter your Google Gemini API key in the sidebar. The key is used only for requests made during the active session and is never persisted or stored externally.

Without an API key, the safety and crack diagnostic modules operate in interactive demonstration mode with realistic illustrative outputs. The planning module works completely offline with editable parameters.

## Author
- **Santusht Kotai**
