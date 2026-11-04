import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "justice_access.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Articles Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS constitution_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_no TEXT UNIQUE,
        part TEXT,
        title_en TEXT,
        title_gu TEXT,
        description_en TEXT,
        description_gu TEXT,
        remedy_gu TEXT
    )
    ''')
    
    # FTS Virtual Table for High Speed Search
    cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS legal_search_index USING fts5(
        article_no, title_en, title_gu, description_en, description_gu, remedy_gu
    )
    ''')
    
    # Clear & seed verified constitutional & criminal laws
    cursor.execute("SELECT count(*) FROM constitution_articles")
    if cursor.fetchone()[0] == 0:
        articles = [
            ("Preamble", "Preamble", "Preamble of Constitution", "ભારતનું બંધારણ - આમુખ",
             "Sovereign Socialist Secular Democratic Republic securing Justice, Liberty, Equality and Fraternity.",
             "સાર્વભૌમ, સમાજવાદી, બિનસાંપ્રદાયિક, લોકશાહી પ્રજાસત્તાક - ન્યાય, સ્વતંત્રતા, સમાનતા અને બંધુતાની ખાતરી.",
             "બંધારણનો આત્મા અને સમગ્ર કાયદાનું માર્ગદર્શક દર્શન."),
             
            ("Article 14", "Part III", "Equality before Law", "કાયદા સમક્ષ સમાનતા",
             "State shall not deny to any person equality before the law or equal protection of laws.",
             "કોઈપણ વ્યક્તિ સાથે કાયદા સમક્ષ ભેદભાવ નહીં થાય, દરેક નાગરિકને કાયદાનું સમાન રક્ષણ મળશે.",
             "જો ભેદભાવ થાય તો હાઇકોર્ટ (Art. 226) અથવા સુપ્રીમ કોર્ટ (Art. 32) માં રિટ કરી શકાય."),
             
            ("Article 19", "Part III", "Right to Freedom of Speech", "વાણી અને અભિવ્યક્તિની સ્વતંત્રતા",
             "Guarantees freedom of speech, assembly, association, movement, residence, and trade.",
             "શાંતિપૂર્ણ રીતે ભેગા થવાની, સંગઠન બનાવવાની, દેશમાં મુક્તપણે ફરવાની અને વ્યવસાય કરવાની સ્વતંત્રતા.",
             "અયોગ્ય પ્રતિબંધ સામે બંધારણીય અધિકાર રક્ષણ."),
             
            ("Article 21", "Part III", "Protection of Life & Personal Liberty", "જીવન અને વ્યક્તિગત સ્વતંત્રતાનું રક્ષણ",
             "No person shall be deprived of his life or personal liberty except according to procedure established by law.",
             "કોઈપણ નાગરિક પાસેથી કાયદાકીય પ્રક્રિયા વિના જીવન અથવા અંગત આઝાદી છીનવી શકાશે નહીં. નિજતાનો અધિકાર (Privacy) પણ સામેલ.",
             "ગેરકાયદે ધરપકડ સામે Habeas Corpus રિટ અરજી."),
             
            ("Article 21A", "Part III", "Right to Education", "મફત અને ફરજિયાત શિક્ષણનો અધિકાર",
             "Free and compulsory education to all children aged 6 to 14 years.",
             "૬ થી ૧૪ વર્ષ સુધીના તમામ બાળકો માટે મફત અને ફરજિયાત પ્રાથમિક શિક્ષણ રાજ્યની જવાબદારી.",
             "શિક્ષણ ન મળવા પર RTE એક્ટ હેઠળ ફરિયાદ."),
             
            ("Article 22", "Part III", "Protection against Arrest & Detention", "ધરપકડ સામે રક્ષણના અધિકારો",
             "Right to be informed of grounds of arrest, right to consult lawyer, must be produced before magistrate within 24 hours.",
             "ધરપકડનું કારણ જાણવાનો હક, વકીલ સાથે સલાહ કરવાનો હક, અને ૨૪ કલાકમાં મેજિસ્ટ્રેટ સમક્ષ હાજર થવાનો હક.",
             "પોલીસ ગેરરીતિ સામે તાત્કાલિક જામીન અને રક્ષણ અરજી."),
             
            ("Article 32", "Part III", "Right to Constitutional Remedies", "બંધારણીય ઉપચારોનો અધિકાર",
             "Right to move Supreme Court for enforcement of fundamental rights via Writs.",
             "મૂળભૂત અધિકારોનું ઉલ્લંઘન થાય ત્યારે સીધા સુપ્રીમ કોર્ટમાં જઈને રિટ (Writs) મેળવવાનો અધિકાર. (બંધારણનું હૃદય).",
             "સુપ્રીમ કોર્ટ સીધો આદેશ જાહેર કરી ન્યાય અપાવે છે."),
             
            ("Article 39A", "Part IV", "Equal Justice & Free Legal Aid", "સમાન ન્યાય અને મફત કાનૂની સહાય",
             "State ensures legal system promotes justice and provides free legal aid to eligible citizens.",
             "ગરીબી કે અસમર્થતાના કારણે કોઈ નાગરિક ન્યાયથી વંચિત ન રહે તે માટે સરકાર મફત વકીલ/કાનૂની સહાય આપશે.",
             "DLSA / NALSA (તાલુકા/જિલ્લા લીગલ સર્વિસ ઓથોરિટી) માંથી મફત વકીલ મેળવી શકાય."),
             
            ("BNS 303 / IPC 379", "Criminal Law", "Theft (ચોરી)", "ચોરી અંગે કાયદાકીય જોગવાઈ",
             "Punishment for theft: Imprisonment up to 3 years or fine or both.",
             "કોઈપણ વ્યક્તિની મંજૂરી વિના અપ્રમાણિક ઇરાદાથી મિલકત લઈ જવી એ ગુનો છે.",
             "નજીકના પોલીસ સ્ટેશનમાં કલમ હેઠળ તાત્કાલિક FIR નોંધાવવી."),
             
            ("BNS 318 / IPC 420", "Criminal Law", "Cheating & Online Fraud", "છેતરપિંડી અને સાયબર ફ્રોડ",
             "Cheating and dishonestly inducing delivery of property. Imprisonment up to 7 years.",
             "ઓનલાઇન કે રૂબરૂ નાણાકીય છેતરપિંડી, ખોટી માહિતી આપીને પૈસા પડાવવા.",
             "cybercrime.gov.in પોર્ટલ અથવા 1930 હેલ્પલાઇન પર ફરિયાદ અને પોલીસ કેસ.")
        ]
        
        for art in articles:
            cursor.execute('''
            INSERT INTO constitution_articles 
            (article_no, part, title_en, title_gu, description_en, description_gu, remedy_gu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', art)
            
            cursor.execute('''
            INSERT INTO legal_search_index 
            (article_no, title_en, title_gu, description_en, description_gu, remedy_gu)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (art[0], art[2], art[3], art[4], art[5], art[6]))
            
    conn.commit()
    conn.close()

def get_all_articles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT article_no, part, title_gu, description_gu, remedy_gu FROM constitution_articles")
    rows = cursor.fetchall()
    conn.close()
    return [{"article_no": r[0], "part": r[1], "title": r[2], "desc": r[3], "remedy": r[4]} for r in rows]

if __name__ == "__main__":
    init_db()
    print("Full Constitution Database created successfully!")
