# ⚖️ NYAYMITRA-AI (ન્યાયમિત્ર-AI) 🇮🇳
> **"તમારો હક, તમારો અવાજ — જ્યાં સુધી ન્યાય દેશના છેવાડાના નાગરિકની પોતાની ભાષામાં સુલભ ન બને, ત્યાં સુધી લોકશાહી અધૂરી છે. આધુનિક ટેકનોલોજી દ્વારા દરેક ભારતીય માટે સમાન, સત્વરે અને પારદર્શક ન્યાય."**  
> *(Your Rights, Your Voice — Until justice becomes accessible to the last citizen of our nation in their own mother tongue, true equality is incomplete. Empowering every Indian with inclusive, transparent, and timely justice.)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3.4.17-38bdf8.svg)](https://tailwindcss.com/)
[![Web Speech API](https://img.shields.io/badge/Speech%20API-Multilingual-emerald.svg)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)

---

## 👨‍💻 Created by Developer
* **Lead Developer & Innovator:** **Bambhaniya Divyesh Nonghanbhai (દિવ્યેશ બંભણીયા)**
* **Hometown:** Dhundhvana, Khambha Taluka, Amreli District, Gujarat, India
* **Institution:** The Maharaja Sayajirao University of Baroda (MSU), Gujarat
* **Program:** First-Year B.Sc. Mathematics
* **Inspiration:** HackIndia – AI for Lawyers Hackathon (*Problem Statement 02: Access to Justice*)

---

## 🌟 The Vision: Access to Justice for Every Indian
In India, millions of citizens in rural and semi-urban areas face substantial barriers in reaching the appropriate administrative departments, legal aid mechanisms, and grievance redressal cells:
1. **Language & Literacy Barriers:** Complex legal terminology and English/Hindi-dominated digital portals make it intimidating for local language speakers (e.g., Gujarati).
2. **Uncertainty of Next Steps:** Ordinary citizens do not know whether a dispute requires the Mamlatdar Court, DILR (Land Survey), Cybercrime Police, or Consumer Commission.
3. **Difficulty in Drafting Applications:** Drafting a formal legal grievance requires hiring private deed writers or advocates that many economically weaker citizens cannot afford.

**NYAYMITRA-AI** solves this by providing a **multilingual, voice-first AI assistant** that listens to citizens in their everyday language, triages the problem, connects them to official government portals (NALSA, Tele-Law, CPGRAMS, AnyRoR), and drafts formatted official complaints ready to print or submit.

---

## 🎨 Design & Key Modules
1. **🎙️ Voice Assistant:** Multilingual real-time speech recognition (Web Speech API) supporting Gujarati, Hindi, and English.
2. **💬 Text Assistant:** Direct legal triage for cyber financial fraud, land disputes, free legal aid, consumer grievances, and welfare schemes.
3. **📚 Constitution Library:** Citizen-friendly explorer for key Articles of the Constitution of India (Articles 14, 21, 39A, 32, 226).
4. **📝 Application & Complaint Drafter:** Formal letterhead generator with 1-click copy and print-ready PDF export.
5. **📞 Emergency Helplines Directory:** Direct dialing for 15100 (NALSA / Tele-Law), 1930 (Cyber Fraud), 181 (Abhayam Women Helpline), 1076 (CM Helpline), and 112 (National Emergency).

---

## ⚡ Quick Start & Deployment

### Option 1: Live Web App (No Server Needed)
Simply open `frontend/index.html` in any browser or enable **GitHub Pages**:
- Repository Settings -> **Pages** -> Source: `Deploy from a branch` -> `main` -> `/frontend` (or root) -> Save.

### Option 2: Full-Stack (FastAPI + SQLite)
```bash
cd backend
pip install -r requirements.txt
python main.py
```
Open `http://127.0.0.1:8000/docs` for API specs.

---

## ⚖️ Ethical Principle & Disclaimer
NYAYMITRA-AI does not act as a judge, render final judicial decrees, or replace licensed advocates. It is an independent student innovation designed to democratize legal literacy, service discovery, and administrative assistance.
