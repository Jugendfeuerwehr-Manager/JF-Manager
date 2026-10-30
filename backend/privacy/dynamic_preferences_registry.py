from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import IntegerPreference

from privacy.retention_settings import RETENTIONS

privacy = Section("privacy")

for _retention in RETENTIONS:
    global_preferences_registry.register(
        type(
            f"Retention_{_retention.name}",
            (IntegerPreference,),
            {
                "section": privacy,
                "name": _retention.name,
                "verbose_name": _retention.label,
                "help_text": _retention.help_text,
                "default": _retention.default,
            },
        )
    )
