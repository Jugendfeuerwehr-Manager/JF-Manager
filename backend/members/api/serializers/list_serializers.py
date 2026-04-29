"""
Serializers for the MemberList and MemberListEntry models.
"""
from rest_framework import serializers

from members.api_serializers import MemberListSerializer as MemberSerializer
from members.models import MemberList, MemberListEntry


class MemberListEntrySerializer(serializers.ModelSerializer):
    """Entry in a list — includes nested member data for display."""
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        source='member',
        queryset=__import__('members.models', fromlist=['Member']).Member.objects.all(),
        write_only=True,
    )

    class Meta:
        model = MemberListEntry
        fields = ['id', 'member', 'member_id', 'checked', 'checked_at', 'notes', 'added_at']
        read_only_fields = ['id', 'member', 'checked_at', 'added_at']


class MemberListSerializer(serializers.ModelSerializer):
    """Lightweight list representation for overview grids."""
    member_count = serializers.IntegerField(read_only=True)
    checked_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MemberList
        fields = ['id', 'name', 'description', 'color', 'member_count', 'checked_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'member_count', 'checked_count', 'created_at', 'updated_at']


class MemberListDetailSerializer(serializers.ModelSerializer):
    """Full list with all entries (members)."""
    entries = MemberListEntrySerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    checked_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MemberList
        fields = ['id', 'name', 'description', 'color', 'member_count', 'checked_count', 'entries', 'created_at', 'updated_at']
        read_only_fields = ['id', 'member_count', 'checked_count', 'entries', 'created_at', 'updated_at']


class MemberListCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberList
        fields = ['id', 'name', 'description', 'color']
