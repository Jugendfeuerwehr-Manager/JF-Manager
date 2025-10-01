from rest_framework import serializers
from qualifications.models import QualificationType, Qualification, SpecialTaskType, SpecialTask


class QualificationTypeSerializer(serializers.ModelSerializer):
    """Serializer für Qualifikationstypen"""
    
    class Meta:
        model = QualificationType
        fields = '__all__'


class QualificationSerializer(serializers.ModelSerializer):
    """Serializer für Qualifikationen"""
    
    type_name = serializers.CharField(source='type.name', read_only=True)
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Qualification
        fields = [
            'id',
            'type',
            'type_name',
            'user',
            'user_name',
            'member', 
            'member_name',
            'date_acquired',
            'date_expires',
            'issued_by',
            'note'
        ]


class SpecialTaskTypeSerializer(serializers.ModelSerializer):
    """Serializer für Sonderaufgaben-Typen"""
    
    class Meta:
        model = SpecialTaskType
        fields = '__all__'


class SpecialTaskSerializer(serializers.ModelSerializer):
    """Serializer für Sonderaufgaben"""
    
    task_name = serializers.CharField(source='task.name', read_only=True)
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = SpecialTask
        fields = [
            'id',
            'task',
            'task_name',
            'user',
            'user_name', 
            'member',
            'member_name',
            'start_date',
            'end_date',
            'note'
        ]