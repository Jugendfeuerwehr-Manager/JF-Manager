class FormActionMixin:
    """Generic form action mixin supporting multiple submit buttons.

    Supports the following POST parameter values in a field named ``action``:
    - save: default behaviour → delegate to the normal success_url logic
    - save_and_add: stay on *create* view to add another object
    - save_and_continue: after create redirect to edit view of created object;
      after update stay on the same edit view (page reload) so user keeps editing

    The mixin is intentionally lightweight and does not assume specific URL
    patterns. ``save_and_add`` simply reloads the current path. For
    ``save_and_continue`` during create we try to replace occurrences of
    '/add/' with '/<pk>/edit/'; if that fails we fall back to current path.
    Override ``get_edit_url()`` if your edit URL cannot be derived like this.
    """

    add_indicator = '/add/'
    edit_indicator = '/edit/'

    def get_edit_url(self):  # pragma: no cover - override hook
        """Return the edit URL for the current object.

        Default implementation tries to transform the current path if it
        contains '/add/'. Subclasses can override for custom routing.
        """
        path = self.request.path
        if self.object and self.add_indicator in path:
            return path.replace(self.add_indicator, f'/{self.object.pk}{self.edit_indicator}')
        return path  # fallback – reload same page

    def get_success_url(self):  # pragma: no cover - simple branching
        action = self.request.POST.get('action', 'save')
        if action == 'save_and_add':
            # Stay on (or return to) create page
            return self.request.path
        if action == 'save_and_continue':
            return self.get_edit_url()
        return super().get_success_url()
