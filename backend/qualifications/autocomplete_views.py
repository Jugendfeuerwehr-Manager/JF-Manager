from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from members.models import Member

User = get_user_model()


@login_required
@permission_required('qualifications.add_qualification', raise_exception=True)
@require_http_methods(["GET"])
def user_autocomplete(request):
    """Autocomplete für Benutzer-Auswahl - nur für berechtigte Benutzer"""
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'pagination': {'more': False}})
    
    # Suche in User-Modell - nur aktive Benutzer
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query),
        is_active=True
    ).order_by('last_name', 'first_name')
    
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    users_page = users[start:end]
    
    results = []
    for user in users_page:
        # Nur notwendige Daten senden - keine sensiblen Informationen
        full_name = user.get_full_name() or user.username
        
        results.append({
            'id': user.id,
            'text': full_name,
        })
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'more': users.count() > end
        }
    })


@login_required
@permission_required('qualifications.add_qualification', raise_exception=True)
@require_http_methods(["GET"])
def member_autocomplete(request):
    """Autocomplete für Mitglieder-Auswahl - nur für berechtigte Benutzer"""
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'pagination': {'more': False}})
    
    # Basis-Queryset - alle Mitglieder
    members_qs = Member.objects.select_related('group', 'status')
    
    # Weitere Einschränkungen basierend auf Berechtigungen
    user = request.user
    if not user.has_perm('qualifications.view_all_qualifications'):
        if user.has_perm('qualifications.view_qualification'):
            # Jugendleiter - können alle Mitglieder sehen (TODO: Gruppenzugehörigkeit implementieren)
            pass
        else:
            # Normale Benutzer - nur eigene Mitgliedschaft
            members_qs = members_qs.filter(
                Q(user=user) | Q(email=user.email)
            )
    
    # Suche anwenden
    members = members_qs.filter(
        Q(name__icontains=query) |
        Q(lastname__icontains=query)
    ).order_by('lastname', 'name')
    
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    members_page = members[start:end]
    
    results = []
    for member in members_page:
        # Nur notwendige Daten senden - keine sensiblen Informationen
        full_name = f"{member.name} {member.lastname}".strip()
        detail_parts = []
        
        # Nur grundlegende Informationen hinzufügen
        if member.group and member.group.name:
            detail_parts.append(member.group.name)
        
        detail = " • ".join(detail_parts) if detail_parts else ""
        
        results.append({
            'id': member.id,
            'text': full_name,
            'detail': detail if detail else None
        })
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'more': members.count() > end
        }
    })
