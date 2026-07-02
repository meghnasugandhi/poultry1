import re


UI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "dashboard": "Dashboard",
        "inventory": "Inventory",
        "documents": "Documents",
        "finance": "Finance",
        "reports": "Reports",
        "calculator": "Calculator",
        "assistant": "AI Assistant",
        "notifications": "Notifications",
        "settings": "Settings",
        "voice": "Voice Assistant",
        "login": "Login",
        "register": "Register",
        "logout": "Logout",
        "welcome": "Welcome back",
        "total_birds": "Total Birds",
        "feed_stock": "Feed Stock",
        "medicine_stock": "Medicine Stock",
        "vaccine_stock": "Vaccine Stock",
        "monthly_revenue": "Monthly Revenue",
        "monthly_expenses": "Monthly Expenses",
        "profit_loss": "Profit/Loss",
        "ai_summary_card": "AI Summary Card",
        "add_stock": "Add Stock",
        "upload_document": "Upload Document",
        "save": "Save",
        "cancel": "Cancel",
    },
    "kn": {
        "dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "inventory": "ದಾಸ್ತಾನು",
        "documents": "ದಾಖಲೆಗಳು",
        "finance": "ಹಣಕಾಸು",
        "reports": "ವರದಿಗಳು",
        "calculator": "ಕ್ಯಾಲ್ಕುಲೇಟರ್",
        "assistant": "AI ಸಹಾಯಕ",
        "notifications": "ಅಧಿಸೂಚನೆಗಳು",
        "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "voice": "ಧ್ವನಿ ಸಹಾಯಕ",
        "login": "ಲಾಗಿನ್",
        "register": "ನೋಂದಣಿ",
        "logout": "ಲಾಗ್ ಔಟ್",
        "welcome": "ಮರಳಿ ಸ್ವಾಗತ",
        "total_birds": "ಒಟ್ಟು ಪಕ್ಷಿಗಳು",
        "feed_stock": "ಆಹಾರ ಸ್ಟಾಕ್",
        "medicine_stock": "ಔಷಧಿ ಸ್ಟಾಕ್",
        "vaccine_stock": "ರೋಗನಿರೋಧಕ ಸ್ಟಾಕ್",
        "monthly_revenue": "ಮಾಸಿಕ ಆದಾಯ",
        "monthly_expenses": "ಮಾಸಿಕ ಖರ್ಚು",
        "profit_loss": "ಲಾಭ/ನಷ್ಟ",
        "ai_summary_card": "AI ಸಾರಾಂಶ ಕಾರ್ಡ್",
        "add_stock": "ಸ್ಟಾಕ್ ಸೇರಿಸಿ",
        "upload_document": "ದಾಖಲೆ ಅಪ್‌ಲೋಡ್",
        "save": "ಉಳಿಸಿ",
        "cancel": "ರದ್ದು",
    },
    "hi": {
        "dashboard": "डैशबोर्ड",
        "inventory": "इन्वेंटरी",
        "documents": "दस्तावेज़",
        "finance": "वित्त",
        "reports": "रिपोर्ट",
        "calculator": "कैलकुलेटर",
        "assistant": "AI सहायक",
        "notifications": "सूचनाएं",
        "settings": "सेटिंग्स",
        "voice": "वॉयस असिस्टेंट",
        "login": "लॉगिन",
        "register": "पंजीकरण",
        "logout": "लॉगआउट",
        "welcome": "वापसी पर स्वागत",
        "total_birds": "कुल पक्षी",
        "feed_stock": "चारा स्टॉक",
        "medicine_stock": "दवा स्टॉक",
        "vaccine_stock": "टीका स्टॉक",
        "monthly_revenue": "मासिक आय",
        "monthly_expenses": "मासिक खर्च",
        "profit_loss": "लाभ/हानि",
        "ai_summary_card": "AI सारांश कार्ड",
        "add_stock": "स्टॉक जोड़ें",
        "upload_document": "दस्तावेज़ अपलोड",
        "save": "सहेजें",
        "cancel": "रद्द करें",
    },
    "te": {
        "dashboard": "డాష్‌బోర్డ్",
        "inventory": "ఇన్వెంటరీ",
        "documents": "పత్రాలు",
        "finance": "ఆర్థికం",
        "reports": "నివేదికలు",
        "calculator": "కాలిక్యులేటర్",
        "assistant": "AI అసిస్టెంట్",
        "notifications": "నోటిఫికేషన్లు",
        "settings": "సెట్టింగ్‌లు",
        "voice": "వాయిస్ అసిస్టెంట్",
        "login": "లాగిన్",
        "register": "నమోదు",
        "logout": "లాగ్ అవుట్",
        "welcome": "తిరిగి స్వాగతం",
        "total_birds": "మొత్తం పక్షులు",
        "feed_stock": "(feed) స్టాక్",
        "profit_loss": "లాభం/నష్టం",
        "add_stock": "స్టాక్ జోడించండి",
        "upload_document": "పత్రం అప్‌లోడ్",
        "save": "సేవ్",
        "cancel": "రద్దు",
    },
    "ta": {
        "dashboard": "டாஷ்போர்டு",
        "inventory": "சரக்கு",
        "documents": "ஆவணங்கள்",
        "finance": "நிதி",
        "reports": "அறிக்கைகள்",
        "calculator": "கணிப்பான்",
        "assistant": "AI உதவியாளர்",
        "notifications": "அறிவிப்புகள்",
        "settings": "அமைப்புகள்",
        "voice": "குரல் உதவியாளர்",
        "login": "உள்நுழை",
        "register": "பதிவு",
        "logout": "வெளியேறு",
        "welcome": "மீண்டும் வரவேற்கிறோம்",
        "total_birds": "மொத்த பறவைகள்",
        "feed_stock": "(feed) இருப்பு",
        "profit_loss": "லாபம்/நஷ்டம்",
        "add_stock": "இருப்பு சேர்",
        "upload_document": "ஆவணம் பதிவேற்று",
        "save": "சேமி",
        "cancel": "ரத்து",
    },
    "ml": {
        "dashboard": "ഡാഷ്‌ബോർഡ്",
        "inventory": "ഇൻവെന്ററി",
        "documents": "രേഖകൾ",
        "finance": "ധനകാര്യം",
        "reports": "റിപ്പോർട്ടുകൾ",
        "calculator": "കാൽക്കുലേറ്റർ",
        "assistant": "AI അസിസ്റ്റന്റ്",
        "notifications": "അറിയിപ്പുകൾ",
        "settings": "ക്രമീകരണങ്ങൾ",
        "voice": "വോയിസ് അസിസ്റ്റന്റ്",
        "login": "ലോഗിൻ",
        "register": "രജിസ്റ്റർ",
        "logout": "ലോഗൗട്ട്",
        "welcome": "തിരികെ സ്വാഗതം",
        "total_birds": "ആകെ പക്ഷികൾ",
        "feed_stock": "(feed) സ്റ്റോക്ക്",
        "profit_loss": "ലാഭം/നഷ്ടം",
        "add_stock": "സ്റ്റോക്ക് ചേർക്കുക",
        "upload_document": "രേഖ അപ്‌ലോഡ്",
        "save": "സേവ്",
        "cancel": "റദ്ദാക്കുക",
    },
    "mr": {
        "dashboard": "डॅशबोर्ड",
        "inventory": "इन्व्हेंटरी",
        "documents": "कागदपत्रे",
        "finance": " finance",
        "reports": "अहवाल",
        "calculator": "कॅल्क्युलेटर",
        "assistant": "AI सहाय्यक",
        "notifications": "सूचना",
        "settings": "सेटिंग्ज",
        "voice": "व्हॉइस असिस्टंट",
        "login": "लॉगिन",
        "register": "नोंदणी",
        "logout": "लॉगआउट",
        "welcome": "परत स्वागत",
        "total_birds": "एकूण पक्षी",
        "feed_stock": "(feed) स्टॉक",
        "profit_loss": "नफा/तोटा",
        "add_stock": "स्टॉक जोडा",
        "upload_document": "कागदपत्र अपलोड",
        "save": "जतन करा",
        "cancel": "रद्द",
    },
}

RESPONSE_PHRASES: dict[str, dict[str, str]] = {
    "kn": {
        "no items": "ಯಾವುದೇ ವಸ್ತುಗಳಿಲ್ಲ.",
        "healthy stock": "ಎಲ್ಲಾ ಸ್ಟಾಕ್‌ಗಳು ಚೆನ್ನಾಗಿವೆ.",
    },
    "hi": {
        "no items": "कोई आइटम नहीं।",
        "healthy stock": "सभी स्टॉक स्तर स्वस्थ हैं।",
    },
}

RESPONSE_PHRASES["hi"].update(
    {
        "no items": "कोई आइटम नहीं।",
        "healthy stock": "सभी स्टॉक स्तर ठीक हैं।",
        "operations look steady. no urgent issues detected.": "कामकाज स्थिर है। कोई जरूरी समस्या नहीं मिली।",
        "keep monitoring feed consumption and expense trends.": "चारा खपत और खर्च के रुझान पर नजर रखें।",
        "ai summary ready.": "AI सारांश तैयार है।",
        "feed stock is low": "चारा स्टॉक कम है",
        "stock may last only a few days.": "स्टॉक केवल कुछ दिनों तक चल सकता है।",
        "feed stock is moderate": "चारा स्टॉक मध्यम है",
        "monitor usage closely.": "उपयोग पर ध्यान से नजर रखें।",
        "medicine stock is critically low": "दवा स्टॉक बहुत कम है",
        "pending bills need attention.": "लंबित बिलों पर ध्यान देने की जरूरत है।",
        "medicine expenses are unusually high this period.": "इस अवधि में दवा खर्च असामान्य रूप से ज्यादा है।",
        "low stock alert": "कम स्टॉक अलर्ट",
        "vaccination schedule reminders are pending.": "टीकाकरण शेड्यूल रिमाइंडर लंबित हैं।",
        "mortality alerts require attention.": "मृत्यु दर अलर्ट पर ध्यान देने की जरूरत है।",
        "action: reorder feed immediately and review recent consumption.": "कार्य: तुरंत चारा मंगाएं और हाल की खपत देखें।",
        "action: restock medical supplies and check expiry dates.": "कार्य: दवाओं का स्टॉक भरें और एक्सपायरी तारीखें जांचें।",
        "action: review unpaid bills and prioritize payments.": "कार्य: बकाया बिल देखें और भुगतान को प्राथमिकता दें।",
        "action: compare recent medicine purchases with the last cycle and verify vendor costs.": "कार्य: हाल की दवा खरीद की पिछले चक्र से तुलना करें और विक्रेता लागत जांचें।",
        "action: follow the vaccination schedule and mark the next batch as completed.": "कार्य: टीकाकरण शेड्यूल का पालन करें और अगली बैच को पूरा चिह्नित करें।",
        "action: inspect flock conditions and review recent feed and medicine changes.": "कार्य: झुंड की स्थिति जांचें और हाल के चारा व दवा बदलाव देखें।",
    }
)


def translate_ui(key: str, language: str) -> str:
    if language == "en":
        return UI_TRANSLATIONS["en"].get(key, key)
    return UI_TRANSLATIONS.get(language, UI_TRANSLATIONS["en"]).get(
        key, UI_TRANSLATIONS["en"].get(key, key)
    )


def get_ui_bundle(language: str) -> dict[str, str]:
    base = UI_TRANSLATIONS["en"].copy()
    if language != "en" and language in UI_TRANSLATIONS:
        base.update(UI_TRANSLATIONS[language])
    return base


def translate_text(text: str, target_language: str) -> str:
    if target_language == "en":
        return text
    phrases = RESPONSE_PHRASES.get(target_language, {})
    translated_text = text
    for en_phrase, translated in phrases.items():
        if en_phrase in translated_text.lower():
            translated_text = re.sub(re.escape(en_phrase), translated, translated_text, flags=re.I)
    return translated_text
