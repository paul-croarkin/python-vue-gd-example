# Dead Archive

A searchable listening room for Grateful Dead concert recordings in the Internet Archive. Search by song or setlist, show date, and minimum community rating. Open a result to browse its artwork, notes, and playable audio files.

## Run locally

In one terminal, install and start the FastAPI backend:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

In a second terminal, install and start the Vue frontend:

```powershell
cd frontend
npm install
npm run serve
```

Open the Vite URL printed in the frontend terminal (usually `http://localhost:5173`). Vite forwards `/api` requests to FastAPI on port 8000. The app uses Internet Archive's public Advanced Search, metadata, thumbnail, and download endpoints; search and playback require an internet connection.

## Backend tests

```powershell
cd backend
python -m pytest
```