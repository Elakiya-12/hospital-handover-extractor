# Hospital Handover Extractor - Streamlit Version

The UI has been changed from React to Streamlit.

## Structure

- `streamlit_app.py` - complete Streamlit UI
- `backend/nlp_engine.py` - NLP/entity/event/time/status extraction
- `backend/database.py` - SQLite storage and dashboard queries
- `backend/app.py` - original Flask REST API, kept unchanged
- `backend/requirements.txt` - Python dependencies
- `run_streamlit.bat` - starts the Streamlit UI
- `run_backend.bat` - starts the original Flask API

The NLP and database files remain separate from the UI.

## Run Streamlit

Open PowerShell in this project folder:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
$env:PYTHONPATH = "$PWD\backend"
streamlit run streamlit_app.py
```

Then open the URL Streamlit shows, normally `http://localhost:8501`.

You do NOT need to run the Flask server for the Streamlit UI because Streamlit directly calls the existing NLP and database modules.

## Important

This is a student prototype. Use synthetic/de-identified patient information, not real patient data.
