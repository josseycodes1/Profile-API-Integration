from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_url",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="github_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="last_login_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
