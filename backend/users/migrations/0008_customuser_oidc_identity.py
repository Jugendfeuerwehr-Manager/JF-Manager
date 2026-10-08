from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0007_add_auth_source")]
    operations = [
        migrations.AddField(
            model_name="customuser",
            name="oidc_issuer",
            field=models.CharField(max_length=500, blank=True, default="", editable=False),
        ),
        migrations.AddField(
            model_name="customuser",
            name="oidc_subject",
            field=models.CharField(max_length=255, blank=True, default="", editable=False),
        ),
        migrations.AddConstraint(
            model_name="customuser",
            constraint=models.UniqueConstraint(
                fields=["oidc_issuer", "oidc_subject"],
                condition=~models.Q(oidc_subject=""),
                name="unique_oidc_identity",
            ),
        ),
    ]
