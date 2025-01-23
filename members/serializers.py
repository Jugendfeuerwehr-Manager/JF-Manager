from rest_framework import serializers
from .models import Member, Parent


class MemberSerializer(serializers.ModelSerializer):
    parents = serializers.SerializerMethodField()
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
        """
        Retrieve the parents associated with the given member instance.

        Args:
            instance (Member): The member instance for which to retrieve parents.

        Returns:
            list: A list of serialized parent data.
        """
        parents = instance.parent_set.prefetch_related().all()
        parents = instance.parent_set.all()
        return ParentSerializer(parents, context=self.context, many=True).data


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = '__all__'