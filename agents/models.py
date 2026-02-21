from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Agent(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, default='')
    location = models.CharField(max_length=150, blank=True, default='')
    vendor_number = models.CharField(max_length=50, blank=True, default='')
    business_name = models.CharField(max_length=150, blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    performance_votes = models.PositiveIntegerField(default=0)
    float_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ecash_open = models.BooleanField(default=True)
    ecash_min = models.DecimalField(max_digits=12, decimal_places=2, default=100)
    ecash_max = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.get_username()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_agent_profile(sender, instance, created, **kwargs):
    if created:
        Agent.objects.get_or_create(user=instance)
