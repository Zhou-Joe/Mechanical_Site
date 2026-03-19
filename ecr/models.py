from django.db import models


class ECRRecord(models.Model):
    """工程变更请求记录"""
    
    # 基本信息
    form_number = models.IntegerField(unique=True, verbose_name='表格序号')
    progress = models.CharField(max_length=50, blank=True, verbose_name='状态')
    completion_date = models.DateField(null=True, blank=True, verbose_name='完成日期')
    
    # 请求信息
    requestor = models.CharField(max_length=100, blank=True, verbose_name='需求者')
    contact = models.CharField(max_length=50, blank=True, verbose_name='联系方式')
    request_date = models.DateField(null=True, blank=True, verbose_name='请求日期')
    expected_completion_date = models.DateField(null=True, blank=True, verbose_name='预期完成日期')
    
    # 文档信息
    doc_number = models.CharField(max_length=50, blank=True, verbose_name='文件号')
    rev_number = models.CharField(max_length=50, blank=True, verbose_name='版本号')
    title = models.CharField(max_length=200, blank=True, verbose_name='标题')
    
    # 位置信息
    attraction_or_location = models.CharField(max_length=200, blank=True, verbose_name='景点或地点')
    engineering_change_type = models.CharField(max_length=100, blank=True, verbose_name='工程变更类型')
    
    # 详细描述
    detail_description = models.TextField(blank=True, verbose_name='详细描述')
    
    # 变更内容
    before_change = models.TextField(blank=True, verbose_name='变更前')
    after_change = models.TextField(blank=True, verbose_name='变更后')
    before_change_image = models.ImageField(upload_to='ecr/before_change/%Y/%m/', blank=True, null=True, verbose_name='变更前图片')
    after_change_image = models.ImageField(upload_to='ecr/after_change/%Y/%m/', blank=True, null=True, verbose_name='变更后图片')
    
    # 变更理由
    justification = models.TextField(blank=True, verbose_name='变更理由')
    
    # 审批信息 - LOB Manager
    lob_manager_name = models.CharField(max_length=100, blank=True, verbose_name='LOB Manager姓名')
    lob_manager_approval = models.CharField(max_length=10, blank=True, verbose_name='LOB Manager审批')
    lob_manager_review_date = models.DateField(null=True, blank=True, verbose_name='LOB Manager审批日期')
    lob_manager_comments = models.TextField(blank=True, verbose_name='LOB Manager注解')
    
    # 审批信息 - QE Engineer
    qe_engineer_name = models.CharField(max_length=100, blank=True, verbose_name='QE Engineer姓名')
    qe_engineer_approval = models.CharField(max_length=10, blank=True, verbose_name='QE Engineer审批')
    qe_engineer_review_date = models.DateField(null=True, blank=True, verbose_name='QE Engineer审批日期')
    qe_engineer_comments = models.TextField(blank=True, verbose_name='QE Engineer注解')
    
    # 审批信息 - ME Engineer
    me_engineer_name = models.CharField(max_length=100, blank=True, verbose_name='ME Engineer姓名')
    me_engineer_approval = models.CharField(max_length=10, blank=True, verbose_name='ME Engineer审批')
    me_engineer_review_date = models.DateField(null=True, blank=True, verbose_name='ME Engineer审批日期')
    me_engineer_comments = models.TextField(blank=True, verbose_name='ME Engineer注解')
    
    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'ECR记录'
        verbose_name_plural = 'ECR记录'
        ordering = ['-form_number']
    
    def __str__(self):
        return f"ECR #{self.form_number} - {self.title or 'Untitled'}"
