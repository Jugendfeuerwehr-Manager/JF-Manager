// Initialize Select2 for searchable dropdowns
$(document).ready(function() {
    // Initialize Select2 for elements with the select2-widget class
    $('.select2-widget').select2({
        allowClear: true,
        placeholder: function() {
            return $(this).data('placeholder') || 'Suchen...';
        },
        language: {
            noResults: function() {
                return "Keine Ergebnisse gefunden";
            },
            searching: function() {
                return "Suche...";
            },
            inputTooShort: function() {
                return "Bitte geben Sie mindestens 1 Zeichen ein";
            },
            loadingMore: function() {
                return "Weitere Ergebnisse werden geladen...";
            }
        }
    });
    
    // Re-initialize Select2 when forms are dynamically added (for formsets)
    $(document).on('formset:added', function(event, $row, formsetName) {
        $row.find('.select2-widget').select2({
            allowClear: true,
            placeholder: function() {
                return $(this).data('placeholder') || 'Suchen...';
            },
            language: {
                noResults: function() {
                    return "Keine Ergebnisse gefunden";
                },
                searching: function() {
                    return "Suche...";
                },
                inputTooShort: function() {
                    return "Bitte geben Sie mindestens 1 Zeichen ein";
                },
                loadingMore: function() {
                    return "Weitere Ergebnisse werden geladen...";
                }
            }
        });
    });
    
    // Clean up Select2 when forms are removed from formsets
    $(document).on('formset:removed', function(event, $row, formsetName) {
        $row.find('.select2-widget').select2('destroy');
    });
});
