"""
批量导入ECR_Record目录中的所有Excel文件
"""
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from ecr.views import import_ecr_from_excel


class Command(BaseCommand):
    help = 'Import all ECR Excel files from ECR_Record directory'

    def handle(self, *args, **options):
        # ECR_Record 目录路径
        ecr_directory = Path(__file__).resolve().parent.parent.parent.parent / 'ECR_Record'
        
        if not ecr_directory.exists():
            self.stdout.write(self.style.ERROR(f'Directory not found: {ecr_directory}'))
            return
        
        # 查找所有Excel文件
        excel_files = list(ecr_directory.glob('*.xlsx')) + list(ecr_directory.glob('*.xls'))
        
        if not excel_files:
            self.stdout.write(self.style.WARNING(f'No Excel files found in {ecr_directory}'))
            return
        
        self.stdout.write(f'Found {len(excel_files)} Excel files')
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for file_path in excel_files:
            self.stdout.write(f'Processing: {file_path.name}')
            
            try:
                record, error = import_ecr_from_excel(file_path)
                
                if record:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Imported ECR #{record.form_number}'))
                    success_count += 1
                elif error:
                    if '已存在' in error:
                        self.stdout.write(self.style.WARNING(f'  ⚠ {error}'))
                        skip_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f'  ✗ {error}'))
                        error_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                error_count += 1
        
        # 总结
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Success: {success_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skip_count}'))
        self.stdout.write(self.style.ERROR(f'Failed: {error_count}'))
        self.stdout.write('='*50)
