# Generated manually for ECR app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ECRRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_number', models.IntegerField(unique=True, verbose_name='表格序号')),
                ('progress', models.CharField(blank=True, max_length=50, verbose_name='状态')),
                ('completion_date', models.DateField(blank=True, null=True, verbose_name='完成日期')),
                ('requestor', models.CharField(blank=True, max_length=100, verbose_name='需求者')),
                ('contact', models.CharField(blank=True, max_length=50, verbose_name='联系方式')),
                ('request_date', models.DateField(blank=True, null=True, verbose_name='请求日期')),
                ('expected_completion_date', models.DateField(blank=True, null=True, verbose_name='预期完成日期')),
                ('doc_number', models.CharField(blank=True, max_length=50, verbose_name='文件号')),
                ('rev_number', models.CharField(blank=True, max_length=50, verbose_name='版本号')),
                ('title', models.CharField(blank=True, max_length=200, verbose_name='标题')),
                ('attraction_or_location', models.CharField(blank=True, max_length=200, verbose_name='景点或地点')),
                ('engineering_change_type', models.CharField(blank=True, max_length=100, verbose_name='工程变更类型')),
                ('detail_description', models.TextField(blank=True, verbose_name='详细描述')),
                ('before_change', models.TextField(blank=True, verbose_name='变更前')),
                ('after_change', models.TextField(blank=True, verbose_name='变更后')),
                ('justification', models.TextField(blank=True, verbose_name='变更理由')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'ECR记录',
                'verbose_name_plural': 'ECR记录',
                'ordering': ['-form_number'],
            },
        ),
    ]
