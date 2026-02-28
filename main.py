import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# Улучшенный CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URI = os.getenv("DATABASE_URL")

@app.get("/busy-dates")
async def get_dates():
    try:
        if not DB_URI:
            print("ОШИБКА: DATABASE_URL не настроена в Render")
            return []

        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT TO_CHAR(booking_date, 'YYYY-MM-DD HH24:MI') as slot FROM appointments WHERE booking_date IS NOT NULL")
        
        rows = cur.fetchall()
        dates = [row['slot'] for row in rows]
        
        cur.close()
        conn.close()
        return dates
    except Exception as e:
        print(f"ОШИБКА БАЗЫ: {e}")
        return []

@app.post("/webhook")
async def handle_tilda(
    name: str = Form(None, alias="record-name"),
    phone: str = Form(None, alias="record-phone"),
    calendar: str = Form(None)
):
    try:
        if not calendar:
            return {"status": "error", "message": "No date provided"}
            
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO appointments (name, phone, booking_date) VALUES (%s, %s, %s)",
            (name, phone, calendar)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        print(f"ОШИБКА WEBHOOK: {e}")
        return {"status": "error", "detail": str(e)}
