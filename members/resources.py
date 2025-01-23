from import_export import resources, fields, widgets
from .models import Member, Parent


class MemberResource(resources.ModelResource):


    class Meta:
        model = Member

