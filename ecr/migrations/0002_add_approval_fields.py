# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecr', '0001_initial'),
    ]

    operations = [
        # LOB Manager fields
        migrations.AddField(
            model_name='ecrrecord',
            name='lob_manager_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='LOB Manager姓名'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='lob_manager_approval',
            field=models.CharField(blank=True, max_length=10, verbose_name='LOB Manager审批'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='lob_manager_review_date',
            field=models.DateField(blank=True, null=True, verbose_name='LOB Manager审批日期'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='lob_manager_comments',
            field=models.TextField(blank=True, verbose_name='LOB Manager注解'),
        ),
        # QE Engineer fields
        migrations.AddField(
            model_name='ecrrecord',
            name='qe_engineer_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='QE Engineer姓名'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='qe_engineer_approval',
            field=models.CharField(blank=True, max_length=10, verbose_name='QE Engineer审批'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='qe_engineer_review_date',
            field=models.DateField(blank=True, null=True, verbose_name='QE Engineer审批日期'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='qe_engineer_comments',
            field=models.TextField(blank=True, verbose_name='QE Engineer注解'),
        ),
        # ME Engineer fields
        migrations.AddField(
            model_name='ecrrecord',
            name='me_engineer_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='ME Engineer姓名'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='me_engineer_approval',
            field=models.CharField(blank=True, max_length=10, verbose_name='ME Engineer审批'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='me_engineer_review_date',
            field=models.DateField(blank=True, null=True, verbose_name='ME Engineer审批日期'),
        ),
        migrations.AddField(
            model_name='ecrrecord',
            name='me_engineer_comments',
            field=models.TextField(blank=True, verbose_name='ME Engineer注解'),
        ),
    ]
