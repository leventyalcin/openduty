__author__ = 'deathowl'

import uuid
import hmac
from hashlib import sha1

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.auth.models import User
from oauth2client.django_orm import CredentialsField
from uuidfield import UUIDField
from django.core.exceptions import ValidationError
from schedule.models import Calendar
from django.contrib.auth import models as auth_models
from django.contrib.auth.management import create_superuser
from django.db.models import signals
from django.conf import settings


AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

@python_2_unicode_compatible
class Token(models.Model):
    """
    The default authorization token model.
    """
    key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        unique = uuid.uuid4()
        return hmac.new(unique.bytes, digestmod=sha1).hexdigest()

    def __unicode__(self):
        return self.key

    def __str__(self):
        return self.key


@python_2_unicode_compatible
class SchedulePolicy(models.Model):
    """
    Schedule policy
    """
    name = models.CharField(max_length=80, unique=True)
    repeat_times = models.IntegerField()

    class Meta:
        verbose_name = _('schedule_policy')
        verbose_name_plural = _('schedule_policies')

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name)


@python_2_unicode_compatible
class Service(models.Model):
    """
    Incidents are representations of a malfunction in the system.
    """
    name = models.CharField(max_length=80, unique=True)
    id = UUIDField(primary_key=True, auto=True)
    retry = models.IntegerField(blank=True, null=True)
    policy = models.ForeignKey(SchedulePolicy, blank=True, null=True)
    escalate_after = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = _('service')
        verbose_name_plural = _('service')

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.id)

@python_2_unicode_compatible
class EventLog(models.Model):
    """
    Event Log
    """
    service_key = models.ForeignKey(Service)
    data = models.TextField()
    occurred_at = models.DateTimeField()
    class Meta:
        verbose_name = _('eventlog')
        verbose_name_plural = _('eventlog')

    def __str__(self):
        return self.data

    def natural_key(self):
        return (self.service_key, self.id)


@python_2_unicode_compatible
class Incident(models.Model):
    TRIGGER = "trigger"
    RESOLVE = "resolve"
    ACKNOWLEDGE = "acknowledge"
    """
    Incidents are representations of a malfunction in the system.
    """
    service_key = models.ForeignKey(Service)
    incident_key = models.CharField(max_length=80)
    event_type = models.CharField(max_length=15)
    description = models.CharField(max_length=100)
    details = models.TextField()
    occurred_at = models.DateTimeField()


    class Meta:
        verbose_name = _('incidents')
        verbose_name_plural = _('incidents')
        unique_together = (("service_key", "incident_key"),)

    def __str__(self):
        return self.incident_key

    def natural_key(self):
        return (self.service_key, self.incident_key)
    def clean(self):
        if self.event_type not in ['trigger', 'acknowledge', 'resolve']:
            raise ValidationError("'%s' is an invalid event type, valid values are 'trigger', 'acknowledge' and 'resolve'" % self.event_type)

@python_2_unicode_compatible
class ServiceTokens(models.Model):
    """
    Service tokens
    """
    name = models.CharField(max_length=80)
    service_id = models.ForeignKey(Service)
    token_id = models.ForeignKey(Token)

    class Meta:
        verbose_name = _('service_tokens')
        verbose_name_plural = _('service_tokens')

    def __str__(self):
        return self.name




@python_2_unicode_compatible
class SchedulePolicyRule(models.Model):
    """
    Schedule rule
    """
    schedule_policy = models.ForeignKey(SchedulePolicy, related_name='rules')
    position = models.IntegerField()
    user_id = models.ForeignKey(User, blank=True, null=True)
    schedule = models.ForeignKey(Calendar, blank=True, null=True)
    escalate_after = models.IntegerField()

    class Meta:
        verbose_name = _('schedule_policy_rule')
        verbose_name_plural = _('schedule_policy_rules')

    def __str__(self):
        return self.id

@python_2_unicode_compatible
class CalendarSource(models.Model):
    name = models.CharField(max_length=80, unique=True)
    oauth2_credentials = CredentialsField()

    class Meta:
        verbose_name = _('calendar_source')
        verbose_name_plural = _('calendar_sources')

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', related_name='profile')
    phone_number = models.CharField(max_length=50)
    pushover_user_key = models.CharField(max_length=50)
    pushover_app_key = models.CharField(max_length=50)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

signals.post_save.connect(create_user_profile, sender=User)

signals.post_syncdb.disconnect(
    create_superuser,
    sender=auth_models,
    dispatch_uid='django.contrib.auth.management.create_superuser')


# Create our own root user automatically.

def create_testuser(app, created_models, verbosity, **kwargs):
  try:
    auth_models.User.objects.get(username='root')
  except auth_models.User.DoesNotExist:
    print '*' * 80
    print 'Creating root user -- login: root, password: toor'
    print '*' * 80
    assert auth_models.User.objects.create_superuser('root', 'admin@localhost', 'toor')
  else:
    print 'Test user already exists.'

signals.post_syncdb.connect(create_testuser,
    sender=auth_models, dispatch_uid='common.models.create_testuser')
