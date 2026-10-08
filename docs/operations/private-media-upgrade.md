# Update auf private Medien

1. Datenbank und Uploadverzeichnis sichern; keine Uploaddateien verschieben oder löschen.
2. Backend und Frontend gemeinsam aktualisieren. Beide ausgelieferten Nginx-Konfigurationen sperren `/uploads/` vollständig. Eigene Reverse-Proxys müssen diese Sperre ebenfalls übernehmen; keine alternative Alias-/CDN-Freigabe für MEDIA_ROOT behalten.
3. Vorhandene Proxy-/CDN-Caches für sämtliche bisherigen Upload-URLs löschen. Bereits von Dritten heruntergeladene Kopien lassen sich dadurch nicht zurückrufen.
4. Bilder, Anhänge und Vorschauen verwenden nun `/api/v1/private-media/…` beziehungsweise die authentifizierte Anhangvorschau. Alte öffentliche Links funktionieren nicht mehr. Exportierte Medienlinks benötigen Anmeldung an der Ursprungsinstanz und übertragen keine Zugriffstokens.
5. Branding bleibt eine ausdrücklich öffentliche externe Logo-URL. Private Uploads nicht als Branding verlinken.
6. Mit einem berechtigten Testkonto eine Mitglieds-/Trainingsvorschau öffnen; denselben Link abgemeldet und in einer fremden Abteilung aufrufen. Nur das berechtigte Konto darf Dateiinhalt erhalten. Antworten dürfen nicht öffentlich gecacht werden.

Neue Uploads: höchstens 10 MB je Datei, 20 Dateien und 50 MB je Objekt (Trainingsbilder und Anhänge zusammen). Mailanhänge werden vor dem Speichern gemeinsam geprüft. Bilder werden auf Format und Pixelzahl geprüft; Avatare werden ohne Originalmetadaten neu kodiert. SVG/HTML sind keine zulässigen neuen Uploads. Unbekannte oder aktive Altdateien werden ausschließlich als Download ausgeliefert.
