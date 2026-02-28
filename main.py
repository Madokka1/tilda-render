import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# Разрешаем запросы с Тильды
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Читаем переменную из настроек Render
DB_URI = os.getenv("DATABASE_URL")

@app.get("/busy-dates")
async def get_dates():
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT booking_date FROM appointments")
    rows = cur.fetchall()
    dates = [row['booking_date'].strftime('%Y-%m-%d') for row in rows]
    cur.close()
    conn.close()
    return dates

@app.post("/webhook")
async def handle_tilda(
    name: str = Form(None, alias="record-name"),
    phone: str = Form(None, alias="record-phone"),
    calendar: str = Form(None)
):
    try:
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
        return {"status": "error", "detail": str(e)}
