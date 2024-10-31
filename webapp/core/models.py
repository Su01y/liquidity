from datetime import datetime
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    class Meta:
        app_label = "core"
        managed = True

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    crypto_wallet_address = models.CharField(max_length=74, blank=True, null=True)
    crypto_wallet_private_key = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Block(models.Model):
    class Meta:
        app_label = "core"
        managed = True

    class BlockState(models.IntegerChoices):
        CLOSED = 0, _("Closed")
        OPEN = 1, _("Open")
        FREEZED = 2, _("Freeze")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.IntegerField(
        choices=BlockState.choices,
        default=BlockState.OPEN,
    )
    block_hash = models.CharField(max_length=64)
    prev_block_hash = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Bet(models.Model):
    class Meta:
        app_label = "core"
        managed = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    bet_size = models.DecimalField(decimal_places=8, max_digits=18)
    bet_percent = models.DecimalField(decimal_places=8, max_digits=18)
    start_matter_price = models.DecimalField(decimal_places=8, max_digits=18)
    start_idea_price = models.DecimalField(decimal_places=8, max_digits=18)
    is_active = models.BooleanField(default=True)
    is_winning = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    bet_ratio = models.DecimalField(null=True, blank=True, decimal_places=8, max_digits=18)

    def soft_delete(self):
        self.deleted_at = datetime.now()
        self.save()


class Transaction(models.Model):
    class Meta:
        app_label = "core"
        managed = True

    class TransactionType(models.IntegerChoices):
        WITHDRAWAL = 0, _("Withdrawal")
        DEPOSIT = 1, _("Deposit")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=8, max_digits=18)
    type = models.IntegerField(
        choices=TransactionType.choices,
        default=TransactionType.DEPOSIT,
    )
    from_wallet = models.CharField(max_length=74)
    to_wallet = models.CharField(max_length=74)
    created_at = models.DateTimeField(auto_now_add=True)
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    bet = models.ForeignKey(Bet, blank=True, null=True, on_delete=models.SET_NULL)
