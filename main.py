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
        # Проверка: установлена ли переменная
        if not DB_URI:
            return {"error": "DATABASE_URL is not set"}
            
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT booking_date FROM appointments WHERE booking_date IS NOT NULL")
        rows = cur.fetchall()
        
        # Форматируем даты, проверяя, что они существуют
        dates = []
        for row in rows:
            if row['booking_date']:
                dates.append(row['booking_date'].strftime('%Y-%m-%d'))
        
        cur.close()
        conn.close()
        return dates
    except Exception as e:
        print(f"ОШИБКА БАЗЫ: {e}") # Это отобразится в логах Render
        return [] # Возвращаем пустой список вместо падения сервера (500)

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
