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
        if not calendar or not phone:
            return {"status": "error", "message": "Missing data"}

        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()

        # 1. Пытаемся найти пользователя по телефону или создать нового
        # SQL запрос: если телефон есть - вернуть ID, если нет - вставить и вернуть ID
        cur.execute("""
            INSERT INTO users (name, phone) 
            VALUES (%s, %s) 
            ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (name, phone))
        
        user_id = cur.fetchone()[0]

        # 2. Создаем саму запись, привязанную к этому user_id
        cur.execute(
            "INSERT INTO appointments (user_id, booking_date) VALUES (%s, %s)",
            (user_id, calendar)
        )

        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "user_id": user_id}
    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/busy-dates")
async def get_dates():
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Нам всё еще нужно просто отдавать список занятых слотов для календаря
        cur.execute("SELECT TO_CHAR(booking_date, 'YYYY-MM-DD HH24:MI') as slot FROM appointments")
        rows = cur.fetchall()
        dates = [row['slot'] for row in rows]
        cur.close()
        conn.close()
        return dates
    except Exception as e:
        return []

@app.get("/user-appointments")
async def get_user_appts(phone: str):
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Ищем все даты записей для конкретного телефона
        cur.execute("""
            SELECT TO_CHAR(a.booking_date, 'YYYY-MM-DD HH24:MI') as slot 
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE u.phone = %s
        """, (phone,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [row['slot'] for row in rows]
    except:
        return []
