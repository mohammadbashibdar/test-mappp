# سیستم احراز هویت - Authentication System

این سیستم احراز هویت برای پروژه Motor Backend FastAPI طراحی شده است و شامل ورود با شماره موبایل و رمز عبور می‌باشد.

## ویژگی‌های سیستم

### 1. ورود کاربر (Login)
- ورود با شماره موبایل و رمز عبور
- اعتبارسنجی شماره موبایل ایرانی (شروع با 09)
- تولید JWT Token
- اعتبارسنجی رمز عبور با bcrypt

### 2. ثبت نام کاربر (Register)
- ثبت نام با اطلاعات کامل
- اعتبارسنجی شماره موبایل و ایمیل
- هش کردن رمز عبور
- پیش‌فرض جنسیت مرد

### 3. مدیریت کاربر فعلی (Current User)
- دریافت اطلاعات کاربر فعلی
- وابستگی‌های FastAPI برای احراز هویت
- مدیریت دسترسی‌ها

## API Endpoints

### 1. ورود کاربر
```
POST /api/v1/auth/login
```

**Request Body:**
```json
{
    "mobile_number": "09123456789",
    "password": "123456"
}
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

### 2. ثبت نام کاربر
```
POST /api/v1/auth/register
```

**Request Body:**
```json
{
    "name": "احمد محمدی",
    "mobile_number": "09123456789",
    "password": "123456",
    "email": "ahmad@example.com",
    "national_code": "1234567890"
}
```

**Response:**
```json
{
    "id": "uuid-string",
    "name": "احمد محمدی",
    "mobile_number": "09123456789",
    "email": "ahmad@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
}
```

### 3. اطلاعات کاربر فعلی
```
GET /api/v1/auth/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "id": "uuid-string",
    "name": "احمد محمدی",
    "mobile_number": "09123456789",
    "email": "ahmad@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
}
```

### 4. اطلاعات پروفایل کاربر
```
GET /api/v1/auth/profile/{user_id}
```

**Response:**
```json
{
    "id": "uuid-string",
    "name": "احمد محمدی",
    "mobile_number": "09123456789",
    "email": "ahmad@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
}
```

## ساختار فایل‌ها

### Core Files
- `app/core/security.py` - توابع امنیتی (هش کردن رمز عبور، JWT)
- `app/core/validation.py` - مدل‌های اعتبارسنجی Pydantic
- `app/core/exeptions.py` - استثناهای سفارشی
- `app/core/dependencies.py` - وابستگی‌های FastAPI
- `app/core/auth.py` - سرویس احراز هویت

### API Endpoints
- `app/api/v1/endpoints/auth.py` - endpoint های احراز هویت

## نحوه استفاده

### 1. نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 2. اجرای سرور
```bash
uvicorn app.main:app --reload
```

### 3. تست سیستم
```bash
python test_auth.py
```

## امنیت

- رمزهای عبور با bcrypt هش می‌شوند
- JWT Token با کلید مخفی امضا می‌شود
- اعتبارسنجی شماره موبایل ایرانی
- مدیریت خطاهای امنیتی

## تنظیمات

تنظیمات در فایل `app/core/config.py`:

```python
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

## مثال استفاده در کد

```python
from fastapi import Depends
from app.core.dependencies import get_current_active_user
from app.models.users import User

@app.get("/protected-route")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {current_user.name}"}
```

## خطاهای ممکن

- `400` - اطلاعات ورودی نامعتبر
- `401` - احراز هویت ناموفق
- `404` - کاربر یافت نشد
- `422` - خطای اعتبارسنجی

## نکات مهم

1. شماره موبایل باید با 09 شروع شود و 11 رقم باشد
2. رمز عبور باید حداقل 6 کاراکتر باشد
3. ایمیل باید فرمت معتبر داشته باشد
4. JWT Token بعد از 30 دقیقه منقضی می‌شود
