from django.core.management.base import BaseCommand
from ferrography_reports.models import FerrographyReport, FerrographyParticle, FerrographyDiagnosis
from ferrography_reports.ferrography_data_extraction import extract_ferrography_data_from_md


class Command(BaseCommand):
    help = '更新铁谱报告的颗粒和诊断数据'
    
    def add_arguments(self, parser):
        parser.add_argument('--report-id', type=int, help='指定报告ID')
        parser.add_argument('--all', action='store_true', help='更新所有报告')
    
    def handle(self, *args, **options):
        report_id = options.get('report_id')
        update_all = options.get('all')
        
        if report_id:
            reports = FerrographyReport.objects.filter(id=report_id)
        elif update_all:
            reports = FerrographyReport.objects.all()
        else:
            self.stdout.write(self.style.ERROR('请指定 --report-id 或 --all'))
            return
        
        updated = 0
        for report in reports:
            if not report.md_content:
                self.stdout.write(self.style.WARNING(f'报告 {report.id} 没有MD内容，跳过'))
                continue
            
            self.stdout.write(f'处理报告 {report.id}...')
            
            # 提取数据
            extracted_data = extract_ferrography_data_from_md(report.md_content)
            
            # 更新processed_data
            report.processed_data = extracted_data
            report.save()
            
            # 删除旧的颗粒数据
            FerrographyParticle.objects.filter(report=report).delete()
            
            # 保存新的颗粒数据
            particles = extracted_data.get('particles', [])
            for particle_data in particles:
                FerrographyParticle.objects.create(
                    report=report,
                    particle_type=particle_data.get('particle_type', ''),
                    concentration=particle_data.get('concentration', ''),
                    size_range=particle_data.get('size_range', ''),
                    morphology=particle_data.get('morphology', ''),
                    wear_mechanism=particle_data.get('wear_mechanism', ''),
                    severity_level=particle_data.get('severity_level', ''),
                )
            
            # 删除旧的诊断数据
            FerrographyDiagnosis.objects.filter(report=report).delete()
            
            # 保存新的诊断数据
            diagnosis_data = extracted_data.get('diagnosis', {})
            if diagnosis_data and isinstance(diagnosis_data, dict):
                FerrographyDiagnosis.objects.create(
                    report=report,
                    overall_assessment=diagnosis_data.get('overall_assessment', ''),
                    wear_status=diagnosis_data.get('wear_status', ''),
                    recommendations=diagnosis_data.get('recommendations', ''),
                )
            
            updated += 1
            self.stdout.write(self.style.SUCCESS(f'报告 {report.id} 更新完成'))
        
        self.stdout.write(self.style.SUCCESS(f'共更新 {updated} 个报告'))