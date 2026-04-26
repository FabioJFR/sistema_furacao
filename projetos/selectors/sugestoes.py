from django.contrib.auth.models import User


def listar_emails_superusers():
    emails = list(
        User.objects.filter(
            is_superuser=True,
            is_active=True,
        )
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .values_list("email", flat=True)
        .distinct()
    )
    return emails

