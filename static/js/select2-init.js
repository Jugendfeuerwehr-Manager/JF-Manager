// Initialize Select2 for searchable dropdowns
$(document).ready(function() {
    // Initialize Select2 for elements with the select2-widget class
    $('.select2-widget').each(function() {
        var $this = $(this);
        var config = {
            allowClear: true,
            placeholder: $this.data('placeholder') || 'Suchen...',
            width: '100%',
            language: {
                noResults: function() {
                    return "Keine Ergebnisse gefunden";
                },
                searching: function() {
                    return "Suche...";
                },
                inputTooShort: function() {
                    return "Bitte geben Sie mindestens 2 Zeichen ein";
                },
                loadingMore: function() {
                    return "Weitere Ergebnisse werden geladen...";
                }
            }
        };

        // Wenn eine Ajax-URL vorhanden ist, konfiguriere Ajax-Suche
        if ($this.data('ajax-url')) {
            config.ajax = {
                url: $this.data('ajax-url'),
                dataType: 'json',
                delay: 250,
                data: function(params) {
                    return {
                        q: params.term,
                        page: params.page || 1
                    };
                },
                processResults: function(data, params) {
                    params.page = params.page || 1;
                    return {
                        results: data.results,
                        pagination: {
                            more: data.pagination && data.pagination.more
                        }
                    };
                },
                cache: true
            };
            config.minimumInputLength = 2;
            config.templateResult = function(item) {
                if (item.loading) {
                    return item.text;
                }
                
                var $result = $('<div>');
                $result.text(item.text);
                
                if (item.detail) {
                    $result.append('<br><small class="text-muted">' + item.detail + '</small>');
                }
                
                return $result;
            };
        }

        $this.select2(config);
    });

    // Spezielle Behandlung für Qualifikations-Form
    $('#id_type').on('change', function() {
        var typeId = $(this).val();
        if (typeId) {
            // Auto-Berechnung des Ablaufdatums
            $.get('/qualifications/api/calculate-expiry/', {
                type_id: typeId,
                date_acquired: $('#id_date_acquired').val()
            }, function(data) {
                if (data.date_expires) {
                    $('#id_date_expires').val(data.date_expires);
                }
            });
        }
    });

    $('#id_date_acquired').on('change', function() {
        var typeId = $('#id_type').val();
        var dateAcquired = $(this).val();
        if (typeId && dateAcquired) {
            $.get('/qualifications/api/calculate-expiry/', {
                type_id: typeId,
                date_acquired: dateAcquired
            }, function(data) {
                if (data.date_expires) {
                    $('#id_date_expires').val(data.date_expires);
                }
            });
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
