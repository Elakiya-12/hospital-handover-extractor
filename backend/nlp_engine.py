import re
from datetime import datetime
import spacy

nlp = spacy.blank("en")
ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})

PATTERNS = [
    {"label":"SYMPTOM","pattern":p} for p in [
        "chest pain","chest discomfort","shortness of breath","difficulty breathing",
        "headache","dizziness","fever","cough","nausea","vomiting","abdominal pain",
        "fatigue","weakness","pain","swelling"
    ]
] + [
    {"label":"MEDICATION","pattern":p} for p in [
        "Paracetamol","Ibuprofen","Aspirin","Amoxicillin","Metformin",
        "Insulin","Salbutamol","Omeprazole","Atorvastatin","Ceftriaxone"
    ]
] + [
    {"label":"INVESTIGATION","pattern":p} for p in [
        "ECG","blood test","blood tests","X-ray","CT scan","MRI","ultrasound",
        "urine test","echocardiogram","echo","CBC","blood pressure"
    ]
] + [
    {"label":"PROCEDURE","pattern":p} for p in [
        "surgery","operation","intubation","catheterization","dressing",
        "dialysis","biopsy","injection"
    ]
] + [
    {"label":"BODY_PART","pattern":p} for p in [
        "chest","abdomen","head","arm","leg","left arm","right arm",
        "left leg","right leg","back","abdomen","throat"
    ]
] + [
    {"label":"VITAL","pattern":p} for p in [
        "BP","blood pressure","heart rate","pulse","oxygen saturation",
        "SpO2","temperature","respiratory rate"
    ]
] + [
    {"label":"DIAGNOSIS","pattern":p} for p in [
        "diabetes","hypertension","pneumonia","asthma","infection",
        "anemia","hypotension","sepsis"
    ]
] + [
    {"label":"WARD","pattern":[{"LOWER":"ward"},{"IS_DIGIT":True}]},
    {"label":"DOCTOR","pattern":[{"LOWER":{"IN":["dr","dr."]}},{"IS_ALPHA":True}]},
    {"label":"DOSAGE","pattern":[
        {"TEXT":{"REGEX":r"^\d+(?:\.\d+)?$"}},
        {"LOWER":{"IN":["mg","mcg","g","ml","units","unit","%"]}}
    ]},
]
ruler.add_patterns(PATTERNS)

def preprocess_text(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text

def extract_entities(text):
    cleaned = preprocess_text(text)
    doc = nlp(cleaned)
    entities = []
    seen = set()
    for ent in doc.ents:
        key=(ent.start_char, ent.end_char, ent.label_)
        if key not in seen:
            seen.add(key)
            entities.append({"text":ent.text, "type":ent.label_,
                             "start":ent.start_char, "end":ent.end_char})
    # Regex entities that are better treated as exact clinical patterns.
    regex_patterns = [
        ("TIME", r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:AM|PM|am|pm)\b"),
        ("DATE", r"\b(?:today|tomorrow|yesterday|tonight|overnight)\b"),
        ("DOSAGE", r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|units?|%)\b"),
        ("VITAL_VALUE", r"\b(?:BP|blood pressure)\s*(?:is|was|:)?\s*\d{2,3}/\d{2,3}\b"),
        ("VITAL_VALUE", r"\b(?:SpO2|oxygen saturation)\s*(?:is|was|:)?\s*\d{2,3}%\b"),
        ("VITAL_VALUE", r"\b(?:heart rate|pulse)\s*(?:is|was|:)?\s*\d{2,3}\b"),
        ("VITAL_VALUE", r"\b(?:temperature)\s*(?:is|was|:)?\s*\d{2,3}(?:\.\d+)?\b"),
    ]
    for label, pattern in regex_patterns:
        for m in re.finditer(pattern, cleaned, re.I):
            key=(m.start(),m.end(),label)
            if key not in seen:
                seen.add(key)
                entities.append({"text":m.group(), "type":label,
                                 "start":m.start(), "end":m.end()})
    return sorted(entities, key=lambda x:(x["start"], x["end"]))

def extract_times(text):
    cleaned=preprocess_text(text)
    results=[]
    patterns=[
        ("CLOCK_TIME", r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:AM|PM|am|pm)\b"),
        ("RELATIVE_TIME", r"\b(?:today|tomorrow|yesterday|tonight|overnight|this morning|this afternoon|this evening|last night)\b"),
    ]
    for kind,pat in patterns:
        for m in re.finditer(pat,cleaned,re.I):
            results.append({"text":m.group(),"type":kind,"start":m.start(),"end":m.end()})
    return sorted(results,key=lambda x:x["start"])

def _sentence_for(text, start, end):
    for m in re.finditer(r"[^.!?]+[.!?]?", text):
        if m.start() <= start < m.end() or m.start() < end <= m.end():
            return m.group().strip()
    return text.strip()

def extract_events(text, entities, times):
    events=[]
    sentences=re.split(r"(?<=[.!?])\s+", preprocess_text(text))
    patterns=[
        ("TRANSFER", r"\b(?:shifted|transferred|moved|admitted)\b"),
        ("SYMPTOM_REPORTED", r"\b(?:complained of|reported|experiencing|developed)\b"),
        ("INVESTIGATION_ORDERED", r"\b(?:ordered|requested|sent for)\b"),
        ("MEDICATION_GIVEN", r"\b(?:given|administered|received|started)\b"),
        ("MEDICATION_STOPPED", r"\b(?:stopped|discontinued|held)\b"),
        ("REVIEW", r"\b(?:reviewed|review|consultation|consult)\b"),
        ("PROCEDURE", r"\b(?:underwent|performed|completed|scheduled)\b"),
        ("DISCHARGE", r"\b(?:discharged|discharge planned)\b"),
    ]
    for sent in sentences:
        if not sent: continue
        lower=sent.lower()
        status=None
        if re.search(r"\b(pending|awaiting|to be done|not yet)\b",lower): status="PENDING"
        elif re.search(r"\b(completed|done|finished)\b",lower): status="COMPLETED"
        elif re.search(r"\b(ordered|requested)\b",lower): status="ORDERED"
        elif re.search(r"\b(given|administered)\b",lower): status="GIVEN"
        elif re.search(r"\b(stopped|discontinued|held)\b",lower): status="STOPPED"
        elif re.search(r"\b(stable|normal|resolved)\b",lower): status="STABLE"
        for event_type,pat in patterns:
            m=re.search(pat,sent,re.I)
            if m:
                event={"type":event_type,"text":sent,"status":status or "DOCUMENTED"}
                # attach entities occurring in this sentence
                start_global=text.find(sent)
                related=[e for e in entities if start_global >= 0 and start_global <= e["start"] < start_global+len(sent)]
                event["entities"]=[{"text":e["text"],"type":e["type"]} for e in related]
                local_times=[t for t in times if start_global >= 0 and start_global <= t["start"] < start_global+len(sent)]
                event["time"]=local_times[0]["text"] if local_times else None
                events.append(event)
                break
    return events

def extract_handover(text):
    cleaned=preprocess_text(text)
    entities=extract_entities(cleaned)
    times=extract_times(cleaned)
    events=extract_events(cleaned,entities,times)
    pending=[]
    for e in events:
        if e["status"]=="PENDING":
            # Prefer a concise pending clinical task over the entire sentence.
            match = re.search(r"([A-Za-z][A-Za-z -]{1,50}?)\s+review\s+is\s+pending", e["text"], re.I)
            if match:
                task = f"{match.group(1).strip()} review"
            elif e.get("entities"):
                task = e["entities"][-1]["text"]
            else:
                task = e["text"]
            pending.append({"task":task,"time":e["time"],"status":"PENDING"})
    return {"cleaned_text":cleaned,"entities":entities,"times":times,
            "events":events,"pending_tasks":pending}
