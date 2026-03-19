from django.db import models
from django.contrib.auth.models import User
import json

# Create your models here.

class Attraction(models.Model):
    """景点模型"""
    name = models.CharField(max_length=200, verbose_name="景点名称")
    description = models.TextField(blank=True, verbose_name="景点描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "景点"
        verbose_name_plural = "景点"

    def __str__(self):
        return self.name

class Equipment(models.Model):
    """设备/点位模型"""
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE, verbose_name="所属景点")
    name = models.CharField(max_length=200, verbose_name="设备名称")
    location = models.CharField(max_length=200, verbose_name="位置/编号")
    equipment_type = models.CharField(max_length=100, verbose_name="设备类型")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "设备"
        verbose_name_plural = "设备"

    def __str__(self):
        return f"{self.attraction.name} - {self.name}"

class OilInspectionReport(models.Model):
    """油品检测报告模型"""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name="检测设备")
    report_date = models.DateField(verbose_name="报告日期")
    sample_date = models.DateField(verbose_name="采样日期")
    report_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="报告编号")
    pdf_file = models.FileField(upload_to='oil_reports/', verbose_name="PDF报告文件")
    md_content = models.TextField(blank=True, verbose_name="OCR生成的MD内容")
    processed_data = models.JSONField(default=dict, blank=True, verbose_name="处理后的检测数据")
    is_processed = models.BooleanField(default=False, verbose_name="是否已处理")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "油品检测报告"
        verbose_name_plural = "油品检测报告"
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.equipment.name} - {self.report_date}"

class OilParameter(models.Model):
    """油品参数模型"""
    report = models.ForeignKey(OilInspectionReport, on_delete=models.CASCADE, verbose_name="检测报告")
    parameter_name = models.CharField(max_length=100, verbose_name="参数名称")
    parameter_value = models.FloatField(verbose_name="参数值")
    unit = models.CharField(max_length=50, verbose_name="单位")
    standard_range = models.CharField(max_length=100, blank=True, verbose_name="标准范围")
    is_normal = models.BooleanField(default=True, verbose_name="是否正常")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "油品参数"
        verbose_name_plural = "油品参数"

    def __str__(self):
        return f"{self.report.equipment.name} - {self.parameter_name}: {self.parameter_value} {self.unit}"

class UploadedFile(models.Model):
    """上传文件记录模型"""
    file = models.FileField(upload_to='uploads/', verbose_name="上传文件")
    original_filename = models.CharField(max_length=255, verbose_name="原始文件名")
    file_type = models.CharField(max_length=50, verbose_name="文件类型")
    file_size = models.BigIntegerField(verbose_name="文件大小(字节)")
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    processed = models.BooleanField(default=False, verbose_name="是否已处理")
    processing_status = models.CharField(max_length=100, default="pending", verbose_name="处理状态")
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    class Meta:
        verbose_name = "上传文件"
        verbose_name_plural = "上传文件"

    def __str__(self):
        return self.original_filename
