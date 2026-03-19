"""
创建缺失的景点和设备数据
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oil_inspection.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from oil_records.models import Attraction, Equipment

def create_missing_data():
    """创建缺失的景点和设备"""
    
    print("=" * 60)
    print("创建缺失的景点和设备")
    print("=" * 60)
    
    # 1. 创建缺失的景点
    attractions_to_create = [
        ('HPS', 'HPS (液压泵站)'),
        ('Pirates', 'Pirates (海盗船)'),
        ('声光塔', '声光塔'),
        ('护城河', '护城河液压站'),
    ]
    
    created_attractions = {}
    for name, description in attractions_to_create:
        attraction, created = Attraction.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        created_attractions[name] = attraction
        if created:
            print(f"✅ 创建景点: {name}")
        else:
            print(f"📌 景点已存在: {name}")
    
    # 2. 创建缺失的设备
    
    # Mine Train HPU
    mine_train = Attraction.objects.filter(name__icontains='mine train').first()
    if mine_train:
        equipment, created = Equipment.objects.get_or_create(
            attraction=mine_train,
            name='HPU',
            defaults={
                'location': 'Mine Train HPU',
                'equipment_type': 'HPU'
            }
        )
        if created:
            print(f"✅ 创建设备: Mine Train - HPU")
        else:
            print(f"📌 设备已存在: Mine Train - HPU")
    
    # Dumbo 轴承油脂
    dumbo = Attraction.objects.filter(name__icontains='dumbo').first()
    if dumbo:
        equipment, created = Equipment.objects.get_or_create(
            attraction=dumbo,
            name='轴承油脂',
            defaults={
                'location': 'Dumbo轴承油脂',
                'equipment_type': '轴承油脂'
            }
        )
        if created:
            print(f"✅ 创建设备: Dumbo - 轴承油脂")
        else:
            print(f"📌 设备已存在: Dumbo - 轴承油脂")
    
    # Carousel 轴承油脂设备
    carousel = Attraction.objects.filter(name__icontains='carousel').first()
    if carousel:
        # 锥齿轴承油脂
        equipment, created = Equipment.objects.get_or_create(
            attraction=carousel,
            name='锥齿轴承油脂',
            defaults={
                'location': 'Carousel轴承油脂（锥齿）#1',
                'equipment_type': '轴承油脂'
            }
        )
        if created:
            print(f"✅ 创建设备: Carousel - 锥齿轴承油脂")
        else:
            print(f"📌 设备已存在: Carousel - 锥齿轴承油脂")
        
        # 大转盘轴承油脂
        equipment, created = Equipment.objects.get_or_create(
            attraction=carousel,
            name='大转盘轴承油脂',
            defaults={
                'location': 'Carousel轴承油脂（大转盘）#2',
                'equipment_type': '轴承油脂'
            }
        )
        if created:
            print(f"✅ 创建设备: Carousel - 大转盘轴承油脂")
        else:
            print(f"📌 设备已存在: Carousel - 大转盘轴承油脂")
    
    # Jetpack 轴承油脂
    jetpack = Attraction.objects.filter(name__icontains='jetpack').first()
    if jetpack:
        equipment, created = Equipment.objects.get_or_create(
            attraction=jetpack,
            name='轴承油脂',
            defaults={
                'location': 'Jetpack轴承油脂',
                'equipment_type': '轴承油脂'
            }
        )
        if created:
            print(f"✅ 创建设备: Jetpack - 轴承油脂")
        else:
            print(f"📌 设备已存在: Jetpack - 轴承油脂")
    
    # HPS 设备
    hps = created_attractions.get('HPS')
    if hps:
        hps_equipments = [
            ('大转盘', 'HPS轴承油脂（大转盘）', '轴承油脂'),
            ('小转盘1', 'HPS轴承油脂（小转盘1）', '轴承油脂'),
            ('小转盘2', 'HPS轴承油脂（小转盘2）', '轴承油脂'),
            ('小转盘3', 'HPS轴承油脂（小转盘3）', '轴承油脂'),
        ]
        
        for name, location, equipment_type in hps_equipments:
            equipment, created = Equipment.objects.get_or_create(
                attraction=hps,
                name=name,
                defaults={
                    'location': location,
                    'equipment_type': equipment_type
                }
            )
            if created:
                print(f"✅ 创建设备: HPS - {name}")
            else:
                print(f"📌 设备已存在: HPS - {name}")
    
    # Pirates HPU
    pirates = created_attractions.get('Pirates')
    if pirates:
        equipment, created = Equipment.objects.get_or_create(
            attraction=pirates,
            name='HPU',
            defaults={
                'location': 'Pirates HPU',
                'equipment_type': 'HPU'
            }
        )
        if created:
            print(f"✅ 创建设备: Pirates - HPU")
        else:
            print(f"📌 设备已存在: Pirates - HPU")
    
    # 声光塔 HPU泵站
    tower = created_attractions.get('声光塔')
    if tower:
        equipment, created = Equipment.objects.get_or_create(
            attraction=tower,
            name='HPU泵站',
            defaults={
                'location': '声光塔HPU泵站',
                'equipment_type': 'HPU'
            }
        )
        if created:
            print(f"✅ 创建设备: 声光塔 - HPU泵站")
        else:
            print(f"📌 设备已存在: 声光塔 - HPU泵站")
    
    # 护城河 HPU泵站
    moat = created_attractions.get('护城河')
    if moat:
        equipment, created = Equipment.objects.get_or_create(
            attraction=moat,
            name='HPU泵站',
            defaults={
                'location': '护城河液压站HPU泵站',
                'equipment_type': 'HPU'
            }
        )
        if created:
            print(f"✅ 创建设备: 护城河 - HPU泵站")
        else:
            print(f"📌 设备已存在: 护城河 - HPU泵站")
    
    # 3. 创建Soaring马达轴承设备
    soaring = Attraction.objects.filter(name__icontains='soaring').first()
    if soaring:
        motor_bearing_equipments = [
            ('马达轴承 - AA前端', 'AA前端'),
            ('马达轴承 - AA后端', 'AA后端'),
            ('马达轴承 - AB前端', 'AB前端'),
            ('马达轴承 - AB后端', 'AB后端'),
            ('马达轴承 - AC前端', 'AC前端'),
            ('马达轴承 - AC后端', 'AC后端'),
            ('马达轴承 - BA前端', 'BA前端'),
            ('马达轴承 - BA后端', 'BA后端'),
            ('马达轴承 - BB前端', 'BB前端'),
            ('马达轴承 - BB后端', 'BB后端'),
            ('马达轴承 - BC前端', 'BC前端'),
            ('马达轴承 - BC后端', 'BC后端'),
        ]
        
        for name, location in motor_bearing_equipments:
            equipment, created = Equipment.objects.get_or_create(
                attraction=soaring,
                name=name,
                defaults={
                    'location': location,
                    'equipment_type': '马达轴承'
                }
            )
            if created:
                print(f"✅ 创建设备: Soaring - {name}")
            else:
                print(f"📌 设备已存在: Soaring - {name}")
    
    print("\n" + "=" * 60)
    print("数据创建完成！")
    print("=" * 60)


if __name__ == "__main__":
    create_missing_data()