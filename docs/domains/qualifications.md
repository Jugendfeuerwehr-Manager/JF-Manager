# Qualifications & Special Tasks

## Overview

Django module for managing qualifications and special tasks (Sonderaufgaben) in the youth fire brigade.

## Qualifications

- **Qualification types**: Various kinds (Jugendspange, Atemschutz, etc.)
- **Validity periods**: Automatic expiry date calculation
- **Status tracking**: Active, expired, expiring soon
- **Certificate management**: Certificate numbers and issuing organizations

### QualificationType Model
- `name` – Qualification name
- `description` – Description
- `validity_period_months` – Validity duration (optional)
- `is_required` – Whether it's mandatory

### Qualification Model
- `member` – Associated member
- `qualification_type` – Type reference
- `date_acquired` – When acquired
- `date_expires` – Expiry date (auto-calculated)
- `certificate_number` – Certificate number (optional)
- `issuing_organization` – Issuing org (optional)

## Special Tasks (Sonderaufgaben)

- **Task types**: Various roles and responsibilities
- **Leadership roles**: Marking for leadership positions
- **Time periods**: Start and end dates
- **Status**: Active/inactive based on time periods

### SpecialTaskType Model
- `name` – Task type name
- `description` – Description
- `is_leadership` – Whether it's a leadership role

### SpecialTask Model
- `member` – Associated member
- `task_type` – Type reference
- `start_date`, `end_date` – Active period

## Permissions

| Role | Access |
|------|--------|
| Admin | Full access, manage types |
| Jugendleiter | Create/edit qualifications and tasks, view all members |
| Mitglied | Read-only access to own qualifications and tasks |

## API Endpoints

```
GET    /api/v1/qualifications/types/   # List qualification types
GET    /api/v1/qualifications/         # List qualifications
POST   /api/v1/qualifications/         # Create qualification
PATCH  /api/v1/qualifications/{id}/    # Update qualification
DELETE /api/v1/qualifications/{id}/    # Delete qualification

GET    /api/v1/specialtasks/types/     # List special task types
GET    /api/v1/specialtasks/           # List special tasks
```
