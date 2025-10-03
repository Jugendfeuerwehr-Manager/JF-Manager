from rest_framework import serializers
from .models import Member, Parent


class MemberSerializer(serializers.ModelSerializer):
    parents = serializers.SerializerMethodField()
    status = serializers.CharField(source='status.name', read_only=True)

    class Meta:
        model = Member
        fields = [
            'name',
            'lastname',
            'birthday',
            'email',
            'street',
            'zip_code',
            'city',
            'phone',
            'mobile',
            'notes',
            'joined',
            'identityCardNumber',
            'parents',
            'canSwimm',
            'status',
        ]

    def get_parents(self, instance):
        parents = instance.parent_set.all()
        return ParentSerializer(parents, context=self.context, many=True).data


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = '__all__'
