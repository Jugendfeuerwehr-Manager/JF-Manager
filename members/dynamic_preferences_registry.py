from dynamic_preferences.types import BooleanPreference, StringPreference, IntegerPreference
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.users.registries import user_preferences_registry

general = Section('general')
members = Section('members')
service = Section('service')

@global_preferences_registry.register
class SiteTitle(StringPreference):
    section = general
    name = 'title'
    verbose_name = 'Seitetitel'
    default = 'JF Manager'
    required = False

@global_preferences_registry.register
class MemberAlertThreshold(IntegerPreference):
    section = members
    name = 'alert_threshold'
    verbose_name = 'Alarm: Schwellenwert nicht Anwesend'
    help_text = 'Definiert den Schwellenwert wann ein Ausrufezeichen angezeigt wird. Berechnet wird hier z.B. 3 von <Intervalgröße>.' \
                'Daher: Wenn das Mitglied 3 von X nicht da war, wird das Flag angezeigt.'
    default = 3
    required = False

@global_preferences_registry.register
class MemberAlertThresholdLastEntries(IntegerPreference):
    section = members
    verbose_name = 'Alarm: Intervallgröße'
    help_text = 'Definiert die Anzahl an Diensten die Rückwertig betrachtet werden.'
    name = 'alert_threshold_last_entries'
    default = 10
    required = False


@global_preferences_registry.register
class ServiceStartTime(StringPreference):
    section = service
    name = 'service_start_time'
    verbose_name = 'Standard Start Zeit'
    default = '18:00'
    required = False

@global_preferences_registry.register
class ServiceEndTime(StringPreference):
    section = service
    name = 'service_end_time'
    verbose_name = 'Standard Ende Zeit'
    default = '19:30'
    required = False