# مدیریت لایه‌های جغرافیایی - Layer Management

این سند راهنمای استفاده از سیستم مدیریت لایه‌های جغرافیایی است که داده‌های موجود در دیتابیس PostgreSQL را به لایه‌های قابل استفاده تبدیل می‌کند.

## ویژگی‌های اصلی

### 🔍 کشف خودکار لایه‌ها
- شناسایی خودکار جداول جغرافیایی در دیتابیس
- تحلیل اطلاعات هر جدول (نوع هندسه، تعداد ویژگی‌ها، محدوده جغرافیایی)
- پیشنهاد ایجاد لایه برای جداول آماده

### ➕ ایجاد لایه‌ها
- ایجاد لایه از جدول واحد
- ایجاد گروهی لایه‌ها از چندین جدول
- تنظیم خودکار نام و عنوان لایه

### 📊 مدیریت لایه‌ها
- نمایش لیست تمام لایه‌های موجود
- مشاهده اطلاعات تفصیلی هر لایه
- پیش‌نمایش لایه‌ها
- حذف لایه‌ها

## API Endpoints

### 1. کشف لایه‌ها
```http
GET /api/v1/database/layers/discover
```
**پاسخ:**
```json
{
  "total_tables": 5,
  "existing_layers": 2,
  "ready_for_layers": 3,
  "suggestions": [
    {
      "table_name": "buildings",
      "table_info": {...},
      "has_existing_layer": false,
      "suggested_layer_name": "layer_buildings",
      "suggested_title": "لایه buildings",
      "geometry_type": "POLYGON",
      "feature_count": 1500,
      "bounds": {...},
      "srid": 4326,
      "is_ready_for_layer": true
    }
  ],
  "existing_layers_detail": [...]
}
```

### 2. ایجاد لایه از جدول
```http
POST /api/v1/database/tables/{table_name}/create-layer
Content-Type: application/json

{
  "table_name": "buildings",
  "layer_name": "layer_buildings",
  "title": "لایه ساختمان‌ها"
}
```

### 3. ایجاد گروهی لایه‌ها
```http
POST /api/v1/database/layers/bulk-create
Content-Type: application/json

["table1", "table2", "table3"]
```

### 4. لیست لایه‌ها
```http
GET /api/v1/database/layers
```

### 5. اطلاعات تفصیلی لایه
```http
GET /api/v1/database/layers/{layer_id}/info
```

### 6. پیش‌نمایش لایه
```http
GET /api/v1/database/layers/{layer_id}/preview?z=8&x=100&y=50
```

### 7. حذف لایه
```http
DELETE /api/v1/database/layers/{layer_id}
```

## رابط کاربری وب

### صفحه اصلی مدیریت لایه‌ها
رابط کاربری شامل بخش‌های زیر است:

1. **کشف جداول جغرافیایی**
   - دکمه "کشف لایه‌ها" برای شناسایی جداول
   - نمایش کارت‌های جداول با وضعیت آن‌ها
   - دکمه‌های ایجاد لایه برای جداول آماده

2. **لایه‌های موجود**
   - نمایش کارت‌های لایه‌های موجود
   - دکمه‌های پیش‌نمایش، اطلاعات و حذف
   - بروزرسانی لیست لایه‌ها

### وضعیت‌های جداول
- 🟢 **آماده**: جدول دارای داده‌های جغرافیایی و آماده برای ایجاد لایه
- 🔵 **موجود**: لایه از این جدول قبلاً ایجاد شده
- 🔴 **خالی**: جدول فاقد داده‌های جغرافیایی

## نحوه استفاده

### 1. شروع کار
```bash
# اجرای سرور
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# باز کردن مرورگر
http://localhost:8000/static/index.html
```

### 2. کشف لایه‌ها
1. روی دکمه "🔍 کشف لایه‌ها" کلیک کنید
2. جداول جغرافیایی شناسایی و نمایش داده می‌شوند
3. جداول آماده با دکمه "ایجاد لایه" مشخص می‌شوند

### 3. ایجاد لایه‌ها
- **تک لایه**: روی دکمه "ایجاد لایه" در کارت جدول کلیک کنید
- **گروهی**: روی دکمه "ایجاد همه لایه‌های آماده" کلیک کنید

### 4. مدیریت لایه‌ها
- **پیش‌نمایش**: روی دکمه "👁️ پیش‌نمایش" کلیک کنید
- **اطلاعات**: روی دکمه "ℹ️ اطلاعات" کلیک کنید
- **حذف**: روی دکمه "🗑️ حذف" کلیک کنید

## تست عملکرد

### اجرای تست خودکار
```bash
python test_layer_management.py
```

### تست دستی API
```bash
# کشف لایه‌ها
curl http://localhost:8000/api/v1/database/layers/discover

# لیست لایه‌ها
curl http://localhost:8000/api/v1/database/layers

# ایجاد لایه
curl -X POST http://localhost:8000/api/v1/database/tables/buildings/create-layer \
  -H "Content-Type: application/json" \
  -d '{"table_name": "buildings", "layer_name": "layer_buildings", "title": "ساختمان‌ها"}'
```

## ساختار دیتابیس

### جداول مورد نیاز
- `tms_layers`: ذخیره اطلاعات لایه‌های TMS
- `tile_cache`: کش تایل‌های نقشه
- `layer_styles`: استایل‌های لایه‌ها

### جداول جغرافیایی
- هر جدول باید دارای ستون `geom` از نوع `geometry` باشد
- سیستم مختصات پیشنهادی: `EPSG:4326` (WGS84)

## تنظیمات پیشرفته

### تنظیم استایل لایه‌ها
```python
# در app/services/tms_service.py
default_style = {
    "point": {"color": "#FF0000", "size": 4},
    "line": {"color": "#0000FF", "width": 2},
    "polygon": {"fill_color": "#00FF00", "stroke_color": "#000000"}
}
```

### تنظیم محدوده زوم
```python
# در مدل TMSLayer
min_zoom = 0
max_zoom = 18
```

## عیب‌یابی

### مشکلات رایج
1. **خطای اتصال به دیتابیس**: بررسی تنظیمات PostgreSQL
2. **جدول جغرافیایی یافت نشد**: بررسی وجود ستون `geom`
3. **خطای ایجاد لایه**: بررسی مجوزهای دیتابیس

### لاگ‌ها
```bash
# مشاهده لاگ‌های سرور
tail -f logs/app.log

# لاگ‌های دیتابیس
tail -f /var/log/postgresql/postgresql.log
```

## توسعه و سفارشی‌سازی

### افزودن نوع هندسه جدید
1. ویرایش `_draw_*` functions در `tms_service.py`
2. افزودن استایل مناسب در `default_style`
3. تست با داده‌های نمونه

### افزودن فرمت تایل جدید
1. ویرایش `_image_to_bytes` function
2. افزودن پشتیبانی از فرمت جدید
3. بروزرسانی API endpoints

## پشتیبانی

برای گزارش مشکلات یا درخواست ویژگی‌های جدید، لطفاً:
1. مشکل را در GitHub Issues گزارش دهید
2. لاگ‌های مربوطه را ضمیمه کنید
3. مراحل تکرار مشکل را شرح دهید
