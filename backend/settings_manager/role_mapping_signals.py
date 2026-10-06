from django.db.models.signals import post_delete
from django.dispatch import receiver

from departments.assignment_sources import remove_external_mapping
from settings_manager.models import LDAPDepartmentRoleMapping, OIDCGroupMapping


@receiver(post_delete, sender=LDAPDepartmentRoleMapping)
def revoke_ldap_mapping(sender, instance, **kwargs):
    remove_external_mapping("ldap", instance.pk)


@receiver(post_delete, sender=OIDCGroupMapping)
def revoke_oidc_mapping(sender, instance, **kwargs):
    remove_external_mapping("oidc", instance.pk)
