"""
JARVIS AI Justice Access & Navigation System - FastAPI Backend
Developer: Divyesh Bambhaniya (B.Sc. Mathematics, MSU Baroda)
Project: AI-Powered Inclusive Justice Access & Navigation System
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

try:
    from database import init_db, log_query, save_application_draft
except ImportError:
    from .database import init_db, log_query, save_application_draft

app = FastAPI(
    title="JARVIS - AI Justice Access API",
    description="Backend API for multilingual legal service triage, grievance routing and application drafting.",
    version="2.0.0"
)

# Enable CORS for frontend web browser interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = "gu"

class QueryResponse(BaseModel):
    category: str
    summary: str
    steps: List[str]
    authority: str
    helpline: str
    portalUrl: str
    documents: List[str]
    draft: Optional[dict] = None

class DraftRequest(BaseModel):
    applicant_name: str
    phone: str
    authority: str
    subject: str
    body: str
    prayer: str

# Legal Knowledge & Triage Rules
LEGAL_KNOWLEDGE = [
    {
        "id": "cyber",
        "keywords": ["સાયબર", "બેંક", "ઓનલાઇન", "પૈસા", "ઓટીપી", "otp", "cyber", "fraud", "scam", "bank"],
        "category": "સાયબર સુરક્ષા અને નાણાકીય છેતરપિંડી (Cyber Financial Fraud)",
        "summary": "ઓનલાઇન કે બેંકિંગ છેતરપિંડીના કિસ્સામાં શરૂઆતના ૧ થી ૩ કલાક (ગોલ્ડન અવર્સ) સૌથી મહત્વના હોય છે. તરત જ ફરિયાદ કરવાથી નાણાં ટ્રાન્સફર થતા અટકાવી શકાય છે.",
        "steps": [
            "તરત જ ૧૯૩૦ (1930) રાષ્ટ્રીય સાયબર ફ્રોડ હેલ્પલાઇન પર કૉલ કરો અને ટ્રાન્ઝેક્શન વિગત આપો.",
            "તમારી બેંકની શાખા અથવા કસ્ટમર કેરમાં કૉલ કરીને સંબંધિત એકાઉન્ટ/ડેબિટ કાર્ડ તાત્કાલિક બ્લોક કરાવો.",
            "સાયબર ક્રાઈમ સત્તાવાર પોર્ટલ (cybercrime.gov.in) પર ઓનલાઇન ફરિયાદ નોંધાવો.",
            "નજીકના સાયબર ક્રાઈમ પોલીસ સ્ટેશનમાં લેખિત અરજી બેંક સ્ટેટમેન્ટ સાથે જમા કરાવો."
        ],
        "authority": "નેશનલ સાયબર ક્રાઈમ રિપોર્ટિંગ પોર્ટલ & સ્થાનિક સાયબર પોલીસ",
        "helpline": "1930 (National Cyber Fraud Helpline)",
        "portalUrl": "https://cybercrime.gov.in",
        "documents": [
            "બેંક પાસબુક અથવા એકાઉન્ટ સ્ટેટમેન્ટ (ફ્રોડ વ્યવહાર દર્શાવેલ)",
            "છેતરપિંડીના SMS/મેસેજનો સ્ક્રીનશોટ",
            "ઓળખનો પુરાવો (આધાર કાર્ડ/ચૂંટણી કાર્ડ)"
        ],
        "draft": {
            "authority": "પોલીસ ઇન્સ્પેક્ટર શ્રી, સાયબર ક્રાઇમ પોલીસ સ્ટેશન",
            "subject": "ઓનલાઇન અનઅધિકૃત નાણાકીય છેતરપિંડી અંગે કાનૂની તપાસ અને રકમ ફ્રીઝ કરાવવા બાબત",
            "body": "સવિનય જણાવવાનું કે મારા બેંક એકાઉન્ટમાંથી અજાણ્યા સ્ત્રોત દ્વારા અનઅધિકૃત રીતે નાણાં ઉપાડી લેવામાં આવ્યા છે. આ બાબતે ૧૯૩૦ પર પણ જાણ કરેલ છે. કૃપા કરીને તપાસ કરી મારી રકમ પરત અપાવવા યોગ્ય કાનૂની કાર્યવાહી કરશો.",
            "prayer": "આ બનાવ અંગે યોગ્ય ગુનો નોંધી છેતરપિંડી કરનાર એકાઉન્ટ ફ્રીઝ કરી નાણાં પરત અપાવવા નમ્ર વિનંતી છે."
        }
    },
    {
        "id": "land",
        "keywords": ["જમીન", "ખેતર", "માપણી", "સીમા", "પાડોશી", "વિવાદ", "મામલતદાર", "dilr", "land", "survey"],
        "category": "મહેસૂલી બાબતો અને જમીન સીમા વિવાદ (Land & Revenue Dispute)",
        "summary": "ખેતર કે પ્લોટની જમીન સીમા બાબતે પાડોશી સાથે વિવાદ હોય તો DILR કચેરી દ્વારા સરકારી હદ માપણી કરાવવી એ પ્રથમ કાનૂની પગલું છે.",
        "steps": [
            "તમારી જમીનનો ૭/૧૨ અને ૮-અ નો તાજો ઉતારો કઢાવો.",
            "તાલુકા કચેરી / સેવા સદનમાં આવેલી DILR શાખામાં જમીન માપણી માટે નિયત ફી ભરીને અરજી કરો.",
            "સરકારી સર્વેયર દ્વારા માપણીની તારીખે પાડોશી ખાતેદારોને પંચનામા માટે નોટિસ મોકલવામાં આવશે.",
            "જો કોઈ ગેરકાયદેસર રસ્તો રોકતો હોય તો મામલતદાર કોર્ટ એક્ટ હેઠળ મામલતદાર સમક્ષ કેસ દાખલ કરી શકાય છે."
        ],
        "authority": "મામલતદાર કચેરી / DILR (જિલ્લા જમીન દફતર કચેરી)",
        "helpline": "1076 (CM Helpline)",
        "portalUrl": "https://anyror.gujarat.gov.in",
        "documents": [
            "જમીનના ૭/૧૨ અને ૮-અ ના ચાલુ વર્ષના ઉતારા",
            "ગામ નમુનો નં. ૬ (હક્ક પત્રક)",
            "જમીનનો સત્તાવાર નકશો / ટીપણી",
            "અરજદારનું આધાર કાર્ડ"
        ],
        "draft": {
            "authority": "માનનીય મામલતદાર સાહેબશ્રી / DILR કચેરી",
            "subject": "જમીનની હદ માપણી અને સીમા ચિન્હો કાયમ કરવા બાબત",
            "body": "સવિનય જણાવવાનું કે મારી માલિકીની જમીનમાં પાડોશી ખાતેદાર સાથે સીમા બાબતે વિવાદ ઉપસ્થિત થયેલ હોવાથી સરકારી સર્વેયર દ્વારા સ્થળ તપાસ કરી કાયદેસર માપણી કરી આપવા વિનંતી છે.",
            "prayer": "નિયત સરકારી ફી ભરીને આ જમીનની સરકારી માપણી કરી હદ નિશાન કાયમ કરી આપવા હુકમ કરવા વિનંતી."
        }
    },
    {
        "id": "legal_aid",
        "keywords": ["મફત", "વકીલ", "કાનૂની સહાય", "કોર્ટ", "ગરીબ", "legal aid", "lawyer", "nalsa", "free"],
        "category": "મફત કાનૂની સહાય (Free Legal Aid - NALSA / DLSA)",
        "summary": "કાનૂની સેવા સત્તા મંડળ અધિનિયમ (1987) ની કલમ 12 હેઠળ મહિલાઓ, બાળકો, SC/ST અને નબળા વર્ગના નાગરિકોને કોર્ટમાં કેસ લડવા માટે સરકાર તરફથી સંપૂર્ણ મફત વકીલ ફાળવવામાં આવે છે.",
        "steps": [
            "૧૫૧૦૦ (15100) રાષ્ટ્રીય ટોલ-ફ્રી હેલ્પલાઇન પર કૉલ કરીને કાનૂની પરામર્શ મેળવો.",
            "જિલ્લા કોર્ટ અથવા તાલુકા કોર્ટમાં આવેલી DLSA / TLSC કચેરીનો સંપર્ક કરો.",
            "ગ્રામ પંચાયત CSC કેન્દ્ર પરથી Tele-Law પોર્ટલ દ્વારા સરકારી વકીલ સાથે વિડીયો કન્સલ્ટેશન કરો.",
            "સરળ અરજી ફોર્મ સાથે આવક/જાતિ પુરાવો રજૂ કરી પેનલ એડવોકેટ મેળવો."
        ],
        "authority": "જિલ્લા કાનૂની સેવા સત્તા મંડળ (DLSA) / GSLSA",
        "helpline": "15100 (National Legal Aid Toll-Free)",
        "portalUrl": "https://nalsa.gov.in",
        "documents": [
            "આધાર કાર્ડ અથવા ચૂંટણી કાર્ડ",
            "આવકનો દાખલો અથવા જાતિ પ્રમાણપત્ર",
            "કોર્ટ નોટિસ અથવા કેસના કાગળો (જો હોય તો)"
        ],
        "draft": {
            "authority": "માનનીય સચિવશ્રી, જિલ્લા કાનૂની સેવા સત્તા મંડળ (DLSA)",
            "subject": "અદાલતી કાર્યવાહી માટે મફત કાનૂની સહાય (પેનલ વકીલ) ફાળવવા બાબત અરજી",
            "body": "સવિનય રજૂઆત કે હું અરજદાર આર્થિક રીતે નબળા વર્ગમાંથી આવું છું અને ખાનગી વકીલની ફી ચૂકવવા અસમર્થ છું. કાનૂની સેવા સત્તા મંડળ અધિનિયમ ૧૯૮૭ ની કલમ ૧૨ હેઠળ મને સક્ષમ સરકારી વકીલ ફાળવવા વિનંતી છે.",
            "prayer": "ન્યાયના હિતમાં મને મફત કાનૂની સહાય તથા યોગ્ય પેનલ એડવોકેટ નિમી આપવા નમ્ર વિનંતી છે."
        }
    }
]

@app.get("/")
def read_root():
    return {
        "project": "JARVIS AI Justice Access & Navigation System",
        "developer": "Divyesh Bambhaniya",
        "institution": "The Maharaja Sayajirao University of Baroda",
        "status": "Online",
        "version": "2.0.0"
    }

@app.post("/api/query", response_model=QueryResponse)
def process_query(req: QueryRequest):
    q = req.query.lower().strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    matched = None
    max_matches = 0
    for item in LEGAL_KNOWLEDGE:
        matches = sum(1 for kw in item["keywords"] if kw.lower() in q)
        if matches > max_matches:
            max_matches = matches
            matched = item

    if not matched:
        matched = LEGAL_KNOWLEDGE[2]  # Default to Legal Aid

    # Log to SQLite DB
    log_query(req.query, req.language, matched["category"], matched["authority"])

    return QueryResponse(
        category=matched["category"],
        summary=matched["summary"],
        steps=matched["steps"],
        authority=matched["authority"],
        helpline=matched["helpline"],
        portalUrl=matched["portalUrl"],
        documents=matched["documents"],
        draft=matched.get("draft")
    )

@app.post("/api/draft")
def save_draft(req: DraftRequest):
    draft_id = save_application_draft(req.dict())
    return {"status": "success", "draft_id": draft_id, "message": "Draft saved successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
