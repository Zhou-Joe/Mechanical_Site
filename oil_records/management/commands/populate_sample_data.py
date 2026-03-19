from django.core.management.base import BaseCommand
from oil_records.models import Attraction, Equipment

class Command(BaseCommand):
    help = 'Populate the database with sample attractions and equipment based on the PDF files'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate sample data...')
        
        # Create attractions
        attractions_data = [
            {'name': 'Rapids Lift', 'description': '急流升降机'},
            {'name': 'Soaring', 'description': '飞翔项目'},
            {'name': 'Mine Train Lift', 'description': '矿山火车升降机'},
            {'name': 'Dumbo', 'description': '小飞象项目'},
            {'name': 'Carousel', 'description': '旋转木马'},
            {'name': 'Jetpack', 'description': '飞行背包'},
            {'name': 'Slinky Kicker Wheel', 'description': '弹簧踢轮'},
            {'name': 'Woody', 'description': '胡迪牛仔项目'},
            {'name': 'Tron', 'description': '创极速光轮项目'},
        ]
        
        created_attractions = {}
        for attr_data in attractions_data:
            attraction, created = Attraction.objects.get_or_create(
                name=attr_data['name'],
                defaults={'description': attr_data['description']}
            )
            created_attractions[attraction.name] = attraction
            if created:
                self.stdout.write(f'Created attraction: {attraction.name}')
            else:
                self.stdout.write(f'Attraction already exists: {attraction.name}')
        
        # Create equipment based on PDF file names
        equipment_data = [
            # Rapids Lift
            {'attraction': 'Rapids Lift', 'name': '齿轮箱', 'location': 'Rapids lift', 'type': '齿轮箱'},
            
            # Soaring
            {'attraction': 'Soaring', 'name': 'AA设备', 'location': 'SOARING AA', 'type': '飞行设备'},
            {'attraction': 'Soaring', 'name': 'AB设备', 'location': 'Soaring AB', 'type': '飞行设备'},
            {'attraction': 'Soaring', 'name': 'AC设备', 'location': 'Soaring AC', 'type': '飞行设备'},
            {'attraction': 'Soaring', 'name': 'BA设备', 'location': 'SoaringBA', 'type': '飞行设备'},
            {'attraction': 'Soaring', 'name': 'BB设备', 'location': 'Soaring BB', 'type': '飞行设备'},
            {'attraction': 'Soaring', 'name': 'BC设备', 'location': 'Soaring BC', 'type': '飞行设备'},
            
            # Mine Train Lift
            {'attraction': 'Mine Train Lift', 'name': 'A齿轮箱', 'location': 'Mine Train Lift A', 'type': '齿轮箱'},
            {'attraction': 'Mine Train Lift', 'name': 'B齿轮箱', 'location': 'Mine Train Lift B', 'type': '齿轮箱'},
            
            # Dumbo
            {'attraction': 'Dumbo', 'name': '1#齿轮箱', 'location': 'Dumbo齿轮箱（1#）', 'type': '齿轮箱'},
            {'attraction': 'Dumbo', 'name': '2#齿轮箱', 'location': 'Dumbo齿轮箱（2#）', 'type': '齿轮箱'},
            {'attraction': 'Dumbo', 'name': '3#齿轮箱', 'location': 'Dumbo齿轮箱（3#）', 'type': '齿轮箱'},
            {'attraction': 'Dumbo', 'name': '4#齿轮箱', 'location': 'Dumbo齿轮箱（4#）', 'type': '齿轮箱'},
            
            # Carousel
            {'attraction': 'Carousel', 'name': '3#驱动齿轮箱', 'location': 'Carousel驱动齿轮箱#3', 'type': '齿轮箱'},
            {'attraction': 'Carousel', 'name': '4#驱动齿轮箱', 'location': 'Carousel驱动齿轮箱#4', 'type': '齿轮箱'},
            
            # Jetpack
            {'attraction': 'Jetpack', 'name': '1#齿轮箱', 'location': 'Jetpack齿轮箱#1', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '2#齿轮箱', 'location': 'Jetpack齿轮箱#2', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '3#齿轮箱', 'location': 'Jetpack齿轮箱#3', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '4#齿轮箱', 'location': 'Jetpack齿轮箱#4', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '5#齿轮箱', 'location': 'Jetpack齿轮箱#5', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '6#齿轮箱', 'location': 'Jetpack齿轮箱#6', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '7#齿轮箱', 'location': 'Jetpack齿轮箱#7', 'type': '齿轮箱'},
            {'attraction': 'Jetpack', 'name': '8#齿轮箱', 'location': 'Jetpack齿轮箱#8', 'type': '齿轮箱'},
            
            # Slinky Kicker Wheel
            {'attraction': 'Slinky Kicker Wheel', 'name': '1#轮', 'location': 'Slinky Kicker Wheel#1', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '2#轮', 'location': 'Slinky Kicker Wheel#2', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '3#轮', 'location': 'Slinky Kicker Wheel#3', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '4#轮', 'location': 'Slinky Kicker Wheel#4', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '5#轮', 'location': 'Slinky Kicker Wheel#5', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '6#轮', 'location': 'Slinky Kicker Wheel#6', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '7#轮', 'location': 'Slinky Kicker Wheel#7', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '8#轮', 'location': 'Slinky Kicker Wheel#8', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '9#轮', 'location': 'Slinky Kicker Wheel#9', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '10#轮', 'location': 'Slinky Kicker Wheel#10', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '11#轮', 'location': 'Slinky Kicker Wheel#11', 'type': '踢轮'},
            {'attraction': 'Slinky Kicker Wheel', 'name': '12#轮', 'location': 'Slinky Kicker Wheel#12', 'type': '踢轮'},
            
            # Woody
            {'attraction': 'Woody', 'name': '1#齿轮箱', 'location': 'Woody Gearbox#1', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '2#齿轮箱', 'location': 'Woody Gearbox#2', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '3#齿轮箱', 'location': 'Woody Gearbox#3', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '4#齿轮箱', 'location': 'Woody Gearbox#4', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '5#齿轮箱', 'location': 'Woody Gearbox#5', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '6#齿轮箱', 'location': 'Woody Gearbox#6', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '7#齿轮箱', 'location': 'Woody Gearbox#7', 'type': '齿轮箱'},
            {'attraction': 'Woody', 'name': '8#齿轮箱', 'location': 'Woody Gearbox#8', 'type': '齿轮箱'},
            
            # Tron BO系列设备
            {'attraction': 'Tron', 'name': 'BO-Z6-03左', 'location': 'BO-Z6-03 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-Z6-03右', 'location': 'BO-Z6-03 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-Z6-02左', 'location': 'BO-Z6-02 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-Z6-02右', 'location': 'BO-Z6-02 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-Z6-01左', 'location': 'BO-Z6-01 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-Z6-01右', 'location': 'BO-Z6-01 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UB-08左', 'location': 'BO-UB-08 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UB-08右', 'location': 'BO-UB-08 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UB-07左', 'location': 'BO-UB-07 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UB-07右', 'location': 'BO-UB-07 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UA-08左', 'location': 'BO-UA-08 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UA-08右', 'location': 'BO-UA-08 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UA-07左', 'location': 'BO-UA-07 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-UA-07右', 'location': 'BO-UA-07 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-09左', 'location': 'BO-PL-09 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-09右', 'location': 'BO-PL-09 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-08左', 'location': 'BO-PL-08 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-08右', 'location': 'BO-PL-08 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-07左', 'location': 'BO-PL-07 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-PL-07右', 'location': 'BO-PL-07 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H2-02左', 'location': 'BO-H2-02 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H2-02右', 'location': 'BO-H2-02 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H2-01左', 'location': 'BO-H2-01 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H2-01右', 'location': 'BO-H2-01 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H1-02左', 'location': 'BO-H1-02 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H1-02右', 'location': 'BO-H1-02 右', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H1-01左', 'location': 'BO-H1-01 左', 'type': 'BO设备'},
            {'attraction': 'Tron', 'name': 'BO-H1-01右', 'location': 'BO-H1-01 右', 'type': 'BO设备'},
        ]
        
        created_count = 0
        for eq_data in equipment_data:
            attraction = created_attractions.get(eq_data['attraction'])
            if not attraction:
                self.stdout.write(f'Warning: Attraction {eq_data["attraction"]} not found')
                continue
                
            equipment, created = Equipment.objects.get_or_create(
                attraction=attraction,
                name=eq_data['name'],
                location=eq_data['location'],
                defaults={'equipment_type': eq_data['type']}
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created equipment: {equipment.name} - {equipment.location}')
            else:
                self.stdout.write(f'Equipment already exists: {equipment.name} - {equipment.location}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated sample data! '
                f'Created {len(created_attractions)} attractions and {created_count} equipment items.'
            )
        )
