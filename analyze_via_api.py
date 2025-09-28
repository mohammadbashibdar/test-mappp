#!/usr/bin/env python3
"""
Analyze data types in the my_points table using the API
"""

import urllib.request
import urllib.parse
import json
from collections import Counter

API_BASE = "http://localhost:8000/api/v1"

def get_features():
    """Get all features from my_points table"""
    url = f"{API_BASE}/database/tables/my_points/features"
    params = {
        "minx": 4800000,
        "miny": 1150000, 
        "maxx": 5500000,
        "maxy": 1650000,
        "limit": 1000
    }
    
    url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url_with_params) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        return []

def analyze_data_types():
    """Analyze the data types in my_points table"""
    
    print("🔍 تحلیل انواع داده‌ها در جدول my_points")
    print("=" * 60)
    
    # Get all features
    features = get_features()
    
    if not features:
        print("❌ هیچ داده‌ای یافت نشد")
        return
    
    print(f"تعداد کل رکوردها: {len(features)}")
    print()
    
    # Analyze bcnshp (beacon shape) values
    bcnshp_values = [f.get('bcnshp') for f in features if f.get('bcnshp') is not None]
    bcnshp_counter = Counter(bcnshp_values)
    
    print("📊 انواع فانوس دریایی (bcnshp):")
    for value, count in bcnshp_counter.most_common():
        print(f"  - نوع {value}: {count} مورد")
    print()
    
    # Analyze catspm (category) values
    catspm_values = [f.get('catspm') for f in features if f.get('catspm') is not None]
    catspm_counter = Counter(catspm_values)
    
    if catspm_counter:
        print("📊 دسته‌بندی (catspm):")
        for value, count in catspm_counter.most_common():
            print(f"  - {value}: {count} مورد")
        print()
    
    # Analyze objnam (object name) values
    objnam_values = [f.get('objnam') for f in features if f.get('objnam') is not None]
    objnam_counter = Counter(objnam_values)
    
    if objnam_counter:
        print("📊 نام اشیاء (objnam):")
        for value, count in objnam_counter.most_common():
            print(f"  - {value}: {count} مورد")
        print()
    
    # Analyze txtdsc (text description) values
    txtdsc_values = [f.get('txtdsc') for f in features if f.get('txtdsc') is not None]
    txtdsc_counter = Counter(txtdsc_values)
    
    if txtdsc_counter:
        print("📊 توضیحات متنی (txtdsc):")
        for value, count in txtdsc_counter.most_common():
            print(f"  - {value}: {count} مورد")
        print()
    
    # Show sample records for each bcnshp type
    print("🔍 نمونه رکوردها برای هر نوع:")
    for bcnshp_type in sorted(bcnshp_counter.keys()):
        print(f"\n--- نوع فانوس {bcnshp_type} ---")
        sample_features = [f for f in features if f.get('bcnshp') == bcnshp_type][:3]
        
        for feature in sample_features:
            print(f"  GID {feature.get('gid')}:")
            print(f"    - bcnshp: {feature.get('bcnshp')}")
            print(f"    - catspm: {feature.get('catspm')}")
            print(f"    - objnam: {feature.get('objnam')}")
            print(f"    - txtdsc: {feature.get('txtdsc')}")
            print(f"    - status: {feature.get('status')}")
            print()
    
    # Check if data should be separated
    print("🤔 آیا داده‌ها باید تقسیم شوند؟")
    print("=" * 40)
    
    if len(bcnshp_counter) > 1:
        print("✅ بله! داده‌ها بر اساس bcnshp (نوع فانوس) قابل تقسیم هستند:")
        for value, count in bcnshp_counter.items():
            print(f"  - نوع {value}: {count} مورد")
    else:
        print("❌ خیر، همه داده‌ها از یک نوع هستند")
    
    if len(catspm_counter) > 1:
        print("✅ داده‌ها بر اساس catspm (دسته‌بندی) نیز قابل تقسیم هستند:")
        for value, count in catspm_counter.items():
            print(f"  - {value}: {count} مورد")
    
    # Suggest separation strategy
    print("\n💡 پیشنهاد تقسیم‌بندی:")
    print("=" * 30)
    
    if len(bcnshp_counter) > 1:
        print("1. تقسیم بر اساس bcnshp (نوع فانوس):")
        for value, count in bcnshp_counter.items():
            table_name = f"beacon_type_{int(value)}" if value else "beacon_unknown"
            print(f"   - جدول: {table_name} ({count} مورد)")
    
    if len(catspm_counter) > 1:
        print("2. تقسیم بر اساس catspm (دسته‌بندی):")
        for value, count in catspm_counter.items():
            table_name = f"category_{value.lower().replace(' ', '_')}" if value else "category_unknown"
            print(f"   - جدول: {table_name} ({count} مورد)")

if __name__ == "__main__":
    analyze_data_types()
