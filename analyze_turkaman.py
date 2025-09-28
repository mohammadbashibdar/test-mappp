#!/usr/bin/env python3
"""
Analyze data types in the turkaman_map table using the API
"""

import urllib.request
import urllib.parse
import json
from collections import Counter

API_BASE = "http://localhost:8000/api/v1"

def get_features(table_name, limit=1000):
    """Get features from a table"""
    url = f"{API_BASE}/database/tables/{table_name}/features"
    params = {
        "minx": 50.0,
        "miny": 30.0, 
        "maxx": 70.0,
        "maxy": 45.0,
        "limit": limit
    }
    
    url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url_with_params) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        return []

def analyze_turkaman_data():
    """Analyze the data types in turkaman_map table"""
    
    print("🔍 تحلیل انواع داده‌ها در جدول turkaman_map")
    print("=" * 60)
    
    # Get features
    features = get_features("turkaman_map", 2000)  # Get more samples
    
    if not features:
        print("❌ هیچ داده‌ای یافت نشد")
        return
    
    print(f"تعداد نمونه رکوردها: {len(features)}")
    print()
    
    # Analyze fclass (feature class) values
    fclass_values = [f.get('fclass') for f in features if f.get('fclass') is not None]
    fclass_counter = Counter(fclass_values)
    
    print("📊 انواع خطوط (fclass):")
    for value, count in fclass_counter.most_common():
        print(f"  - {value}: {count} مورد")
    print()
    
    # Analyze code values
    code_values = [f.get('code') for f in features if f.get('code') is not None]
    code_counter = Counter(code_values)
    
    if code_counter:
        print("📊 کدهای خطوط (code):")
        for value, count in code_counter.most_common():
            print(f"  - {value}: {count} مورد")
        print()
    
    # Analyze name values
    name_values = [f.get('name') for f in features if f.get('name') is not None]
    name_counter = Counter(name_values)
    
    if name_counter:
        print("📊 نام‌های خطوط (name) - 10 مورد اول:")
        for value, count in name_counter.most_common(10):
            print(f"  - {value}: {count} مورد")
        print()
    
    # Show sample records for each fclass type
    print("🔍 نمونه رکوردها برای هر نوع:")
    for fclass_type in sorted(fclass_counter.keys())[:5]:  # Show first 5 types
        print(f"\n--- نوع خط {fclass_type} ---")
        sample_features = [f for f in features if f.get('fclass') == fclass_type][:2]
        
        for feature in sample_features:
            print(f"  GID {feature.get('gid')}:")
            print(f"    - fclass: {feature.get('fclass')}")
            print(f"    - code: {feature.get('code')}")
            print(f"    - name: {feature.get('name')}")
            print(f"    - ref: {feature.get('ref')}")
            print(f"    - oneway: {feature.get('oneway')}")
            print()
    
    # Check if data should be separated
    print("🤔 آیا داده‌ها باید تقسیم شوند؟")
    print("=" * 40)
    
    if len(fclass_counter) > 1:
        print("✅ بله! داده‌ها بر اساس fclass (نوع خط) قابل تقسیم هستند:")
        for value, count in fclass_counter.items():
            print(f"  - {value}: {count} مورد")
    else:
        print("❌ خیر، همه داده‌ها از یک نوع هستند")
    
    # Suggest separation strategy
    print("\n💡 پیشنهاد تقسیم‌بندی:")
    print("=" * 30)
    
    if len(fclass_counter) > 1:
        print("1. تقسیم بر اساس fclass (نوع خط):")
        for value, count in fclass_counter.items():
            table_name = f"line_{value.lower().replace(' ', '_')}" if value else "line_unknown"
            print(f"   - جدول: {table_name} ({count} مورد)")
    
    # Show what each fclass represents
    print("\n📚 توضیح انواع خطوط:")
    print("=" * 25)
    
    fclass_descriptions = {
        'primary': 'جاده‌های اصلی',
        'secondary': 'جاده‌های فرعی', 
        'tertiary': 'جاده‌های محلی',
        'trunk': 'جاده‌های شریانی',
        'motorway': 'اتوبان',
        'residential': 'جاده‌های مسکونی',
        'unclassified': 'جاده‌های طبقه‌بندی نشده',
        'track': 'مسیرهای خاکی',
        'path': 'پیاده‌روها',
        'footway': 'مسیرهای پیاده',
        'cycleway': 'مسیرهای دوچرخه',
        'river': 'رودخانه‌ها',
        'stream': 'جوی‌ها',
        'canal': 'کانال‌ها',
        'railway': 'خطوط راه‌آهن',
        'coastline': 'خطوط ساحلی'
    }
    
    for fclass_type in fclass_counter.keys():
        description = fclass_descriptions.get(fclass_type, 'نوع نامشخص')
        count = fclass_counter[fclass_type]
        print(f"  - {fclass_type}: {description} ({count} مورد)")

if __name__ == "__main__":
    analyze_turkaman_data()
