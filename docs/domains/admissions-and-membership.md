# Admissions, Membership Movements And The DJF Annual Report

Two apps cover a member's way from the application to the yearly statistics:

- `backend/admissions/` – digital application forms, vouchers, public submission, committee
  decisions, seals and the takeover into the member administration (own navigation group
  "Aufnahme").
- `backend/membership/` – membership movements (joins, stage changes, transfers, exits) and the
  DJF annual report ("Jahresmeldung").

Both build on the privacy module (`privacy.ConsentRecord`, `privacy.ConsentKind`, legal pages,
`Member.left_at`).

## Membership stages and movements

- `members.Status` has a fixed `category` (`applicant`, `trial`, `active`, `passive`, `left`,
  `transferred`), an owning `department` (NULL = central, visible everywhere, editable
  organisation-wide) and a `sort_order`. Departments name stages freely; reports only use the
  category.
- `membership.MembershipEvent` stores one movement per member **and department**: `joined_new`,
  `joined_other_org`, `joined_from_kf`, `stage_changed`, `exit_ea`, `exit_other` (with one of the six
  DJF exit reasons).
- All writes go through `membership.services.lifecycle`: `admit()`, `record_stage_change()`,
  `record_department_changes()`, `record_exit()`. `record_exit()` wraps
  `members.services.membership_leave.record_leave()`, the only writer of `left_at`.
- `POST /api/v1/members/{id}/leave/` accepts optional `kind` and `exit_reason`; creating or editing a
  member logs joins, stage changes and department moves.
- `/api/v1/membership/events/` lists movements and lets editors correct date, kind, reason or note
  (member rights; no create or delete; a join stays a join).
- `manage.py backfill_membership_events` creates the join for members that only have `joined`.

## Application forms

- `AdmissionForm` holds the draft (`draft_schema`), settings and the decision body;
  `AdmissionFormVersion` is the frozen, immutable version applicants fill in.
- `department=NULL` is an organisation form for every department (visible to all, changed only
  with the right organisation-wide). The voucher, or on a public link the applicant's choice among
  `public_departments`, decides where an application goes.
- `access`: `voucher` or `public`. Public forms get a `public_slug` (`/aufnahme/f/<slug>`); vouchers
  keep working for them.
- Schema: pages → sections → elements. Element types: inputs (`text`, `textarea`, `number`, `date`, `email`,
  `phone`, `select`, `radio`, `checkbox`, `photo`), content (`heading`, `richtext`, `divider`), legal
  (`legal_ack` → a published `LegalPage`, `consent` → an active `ConsentKind`), `guardians` and
  `signature`. Visibility: `{"age_below": n}` or `{"field": key, "equals": value}`.
- `admissions/field_catalog.py` lists the member and guardian fields a form may fill, plus the
  additional member fields (`member.extra.<key>`, see below). Every data input needs a target so
  no answer is lost on takeover; only required checkboxes (confirmations) stay in the application
  alone. Legal texts, consents (per kind and person) and signatures (per role) occur once per form.
- Organisation forms may only use organisation-wide additional fields; department forms also their
  own department's. Select options of additional fields are copied into the version on publishing.
- `draft_issues` includes what blocks publishing elsewhere (e.g. an unpublished privacy text), so the
  builder's publish dialog lists it before the request fails.
- `admissions/schema.py` holds the rules (drafts must pass `check_structure`, publishing the full
  `check_schema`). Draft rich text is sanitised on save.
- Publishing copies text blocks, the published legal text and the consent wording into the
  version and stores a canonical SHA-256 (`schema_hash`).
- The builder (`views/admissions/FormBuilderView.vue`) uses no PrimeVue components: own controls on
  the `--jf-*` tokens, drag & drop with interact.js plus click-to-add and arrow buttons. The palette
  offers blocks by destination (member data, additional fields, people & legal, content); used
  single-use blocks are greyed out. Elements are edited inline; consent kinds
  (`privacy/consent-kinds`) and additional fields can be created from modal dialogs.

## Additional member fields

- `members.MemberFieldDefinition` (`department=NULL`: organisation-wide) with `key`, `label`,
  `field_type` (`text`, `textarea`, `number`, `date`, `select`, `checkbox`) and `options`; values live
  in `Member.extra_fields` keyed by `key`. API `GET/POST /api/v1/member-fields/`: every staff account
  reads, writing needs the model rights in the owning department. Key, type and scope are fixed
  after creation; a field with values can only be deactivated.
- `members/services/extra_fields.py` cleans values for the member dialog and the takeover; a member
  carries the fields of the organisation and of its departments. Anonymization clears them.

## Vouchers and the public form

- `AdmissionVoucher`: 12 Crockford Base32 characters (`XXXX-XXXX-XXXX`), only the SHA-256 is stored,
  the code is returned once by `POST /api/v1/admissions/vouchers/`.
- Public links: `GET`/`POST /api/v1/public/admissions/form/<slug>/` with the chosen `department`
  (must be one of the offered ones) and a honeypot field `website`; same throttle as codes.
- The QR code points to `/aufnahme#code=…`; the fragment never reaches the server. The page sends
  the code in the `X-Admission-Code` header to `GET`/`POST /api/v1/public/admissions/`.
- Unknown, used, expired and revoked codes get the same 404 answer; the endpoints are throttled per
  IP (`admission_code`, 10/min) and CSRF-protected.
- Submissions are checked against the published version, images are re-encoded (photo ≤ 1.5 MB,
  scaled down in the browser), the voucher is redeemed under a row lock and the inbox gets an
  `admission_submitted` task.

## Seals

- `admissions/services/seal.py`: canonical JSON → SHA-256 → Ed25519 signature with
  `ADMISSIONS_SEAL_KEY` (derived from `DJANGO_SECRET_KEY` if unset; `jfctl` creates the key on
  install). Each `Seal` stores its public key, so seals made with an earlier key still verify.
- Seals of a subject form a chain (`prev_hash`): submission → decisions → every export. The
  annual report is sealed when finalized.
- Sealed rows (`Application` content, `ApplicationFile`, `AdmissionDecision`, `Seal`) refuse
  changes in `save()`.
- `GET /api/v1/admissions/applications/{id}/verify/` re-checks all seals against the stored data;
  `GET /api/v1/public/admissions/verify/{public_id}/` answers valid/invalid without personal data
  (QR on every PDF).

## Decisions and takeover

- `CommitteeMeeting` and `AdmissionDecision` (`approved`, `rejected`, `deferred`, optional votes).
  Only `submitted` or `deferred` applications can be decided; `POST /meetings/{id}/decide/` decides
  several at once. Right: `admissions.record_decision`.
- `POST /applications/{id}/take-over/` (rights `admissions.take_over_application` and
  `members.add_member`) creates the member (mapped fields, photo, status from the form, join date
  from the decision), creates guardians or links chosen existing parents of the department, logs
  `joined_new` and records every consent through `privacy.services.consent.record_consent`
  with the sealed wording and version. Optionally invites the guardians to the portal.

## DJF annual report

- `StatisticsProfile` per department: 21-character DJF organisation id, JF/KF, founding date and
  the stage categories that count as members (default trial + active).
- `membership.services.annual_report.compute()` returns the portal fields: members at 31.12. by
  m/w/d, joins (new, other organisation, children's brigade), exits (Einsatzabteilung, other + six
  reasons), age structure (under 5, 5–18, over 18), supervisors and activities entered by hand.
- Plausibility like the portal: members = sum of the age structure, previous year + joins − exits
  = members, reasons = other exits. Warnings list members without gender, birthday or exit reason.
- The previous year comes from the finalized report when there is one. Finalizing is possible after
  the reference date and seals the numbers. Anonymized members still count; their age comes from
  the birth year. Erased members are missing from later calculations.
- Endpoints under `/api/v1/membership/annual-reports/`: `preview`, `manual`, `finalize`, `export`
  (xlsx, audited); profiles under `/api/v1/membership/statistics-profiles/`.

## Rights

See `docs/planning/role-permission-manifest.md`: blocks `admission_editor`, `admission_committee`
and `annual_reporter` (part of the Jugendwart roles, template version 9). Existing installations
see the newer template version in the role templates and can adopt it there.
