from flask import Flask, request, jsonify
from flask_cors import CORS
from nlp_engine import extract_handover
from database import init_db, save_analysis, get_recent_handovers, get_dashboard

app=Flask(__name__)
CORS(app)
init_db()

@app.get("/api/health")
def health():
    return jsonify({"status":"success","message":"Hospital Handover API is running"})

@app.post("/api/analyze")
def analyze():
    data=request.get_json(silent=True) or {}
    patient_id=str(data.get("patient_id","")).strip()
    text=str(data.get("handover_text","")).strip()
    if not patient_id or not text:
        return jsonify({"status":"error","message":"Patient ID and handover text are required"}),400
    analysis=extract_handover(text)
    handover_id=save_analysis(patient_id,text,analysis)
    return jsonify({"status":"success","message":"Handover analyzed and saved",
                    "data":{"handover_id":handover_id,"patient_id":patient_id,
                            "handover_text":text,**analysis}})

@app.get("/api/handovers")
def handovers():
    return jsonify({"status":"success","data":get_recent_handovers()})

@app.get("/api/dashboard")
def dashboard():
    return jsonify({"status":"success","data":get_dashboard()})

if __name__=="__main__":
    app.run(debug=True,port=5000)
