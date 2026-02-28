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
            return {"status": "error", "message": "Данные не полные"}

        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()

        # 1. Находим или создаем пользователя
        cur.execute("""
            INSERT INTO users (name, phone) 
            VALUES (%s, %s) 
            ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (name, phone))
        user_id = cur.fetchone()[0]

        # 2. Логика ПЕРЕНОСА: 
        # Если у этого пользователя уже есть запись — обновляем её на новую дату.
        # Если нет — создаем новую.
        cur.execute("""
            INSERT INTO appointments (user_id, booking_date)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
            SET booking_date = EXCLUDED.booking_date
        """, (user_id, calendar))

        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "message": "Запись успешно обновлена/создана"}
    except Exception as e:
        print(f"Ошибка: {e}")
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
