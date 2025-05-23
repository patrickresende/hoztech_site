from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('hoztech', '0006_remove_pdfdownload_hoztech_pdf_email_s_713d13_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfdownload',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pdf_downloads',
                to='auth.user',
                verbose_name='Usuário que realizou o download'
            ),
        ),
    ] 