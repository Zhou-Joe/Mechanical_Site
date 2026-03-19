from django.db import models
from oil_records.models import Attraction, Equipment


class FerrographyAttraction(models.Model):
    """铁谱检测景点（独立于油品检测）"""
    name = models.CharField(max_length=100, unique=True, verbose_name="景点名称")
    description = models.TextField(blank=True, verbose_name="描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "铁谱检测景点"
        verbose_name_plural = "铁谱检测景点"
        ordering = ['name']

    def __str__(self):
        return self.name


class FerrographyEquipment(models.Model):
    """铁谱检测设备（独立于油品检测）"""
    attraction = models.ForeignKey(FerrographyAttraction, on_delete=models.CASCADE, verbose_name="所属景点")
    name = models.CharField(max_length=200, verbose_name="设备名称")
    description = models.TextField(blank=True, verbose_name="描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "铁谱检测设备"
        verbose_name_plural = "铁谱检测设备"
        ordering = ['attraction__name', 'name']
        unique_together = ['attraction', 'name']

    def __str__(self):
        return f"{self.attraction.name} - {self.name}"


class FerrographyReport(models.Model):
    """铁谱分析报告模型"""
    equipment = models.ForeignKey(FerrographyEquipment, on_delete=models.CASCADE, verbose_name="检测设备")
    report_date = models.DateField(verbose_name="报告日期")
    sample_date = models.DateField(verbose_name="采样日期")
    report_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="报告编号")
    pdf_file = models.FileField(upload_to='ferrography_reports/', verbose_name="PDF报告文件")
    md_content = models.TextField(blank=True, verbose_name="OCR生成的MD内容")
    processed_data = models.JSONField(default=dict, blank=True, verbose_name="处理后的检测数据")
    is_processed = models.BooleanField(default=False, verbose_name="是否已处理")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "铁谱分析报告"
        verbose_name_plural = "铁谱分析报告"
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.equipment.name} - {self.report_date}"


class FerrographyParticle(models.Model):
    """铁谱颗粒分析模型"""
    report = models.ForeignKey(FerrographyReport, on_delete=models.CASCADE, verbose_name="所属报告")
    particle_type = models.CharField(max_length=100, verbose_name="颗粒类型")
    concentration = models.CharField(max_length=50, verbose_name="浓度")
    size_range = models.CharField(max_length=100, blank=True, verbose_name="尺寸范围")
    morphology = models.TextField(blank=True, verbose_name="形貌描述")
    wear_mechanism = models.CharField(max_length=200, blank=True, verbose_name="磨损机理")
    severity_level = models.CharField(max_length=50, blank=True, verbose_name="严重等级")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "铁谱颗粒"
        verbose_name_plural = "铁谱颗粒"

    def __str__(self):
        return f"{self.report.equipment.name} - {self.particle_type}"


class FerrographyDiagnosis(models.Model):
    """铁谱诊断结论模型"""
    report = models.OneToOneField(FerrographyReport, on_delete=models.CASCADE, verbose_name="所属报告")
    overall_assessment = models.TextField(blank=True, verbose_name="总体评价")
    wear_status = models.CharField(max_length=200, blank=True, verbose_name="磨损状态")
    recommendations = models.TextField(blank=True, verbose_name="建议措施")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "铁谱诊断"
        verbose_name_plural = "铁谱诊断"

    def __str__(self):
        return f"{self.report.equipment.name} 诊断"
