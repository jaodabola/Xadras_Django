from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('matchmaking', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='matchmakingqueue',
            name='rating',
            field=models.IntegerField(default=1000, help_text="Player's rating for matchmaking"),
        ),
        migrations.AddField(
            model_name='matchmakingqueue',
            name='joined_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
