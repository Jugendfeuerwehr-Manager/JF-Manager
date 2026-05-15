# Training Module (User Guide)

## What It Is

The training module helps teams plan, run, and document youth fire brigade training sessions.

It combines:

- a calendar of sessions
- reusable library blocks
- a visual planner timeline
- handout output for trainers
- mobile planner mode for on-site use

## Main User Flows

## 1. Create a Session

Open the training calendar and create a new session with:

- title and description
- date and start/end time
- location
- participating groups
- optional recurrence rule (weekly/biweekly/monthly)

## 2. Plan Session Content

In the planner view, add or reorder blocks:

- custom blocks specific to this session
- blocks copied from the shared library
- timing and lane/group assignment per block

## 3. Attach Media And Files

For both session blocks and library blocks you can:

- upload inline images for rich-text content
- add file attachments

## 4. Reuse Content Via Library

Library blocks provide reusable training content with:

- categories and tags
- default duration
- optional public/shared visibility
- usage tracking (where a block has been used)

## 5. Generate Repeating Sessions

For sessions with recurrence rules, use series generation to create future dates automatically.

## 6. Handout And Mobile Usage

- Handout view provides trainer-friendly session output.
- Mobile planner view supports practical use during training execution.

## Permissions

- Read access: authenticated users.
- Editing requires training permissions (`can_manage_training` / `can_manage_library`).

If you cannot edit sessions or library entries, ask an administrator to assign the required role/group.

## Routes

- `/training` – calendar
- `/training/library` – reusable library
- `/training/sessions/:id/plan` – planner
- `/training/sessions/:id/handout` – handout
- `/training/sessions/:id/mobile` – mobile planner

## Related Docs

- `docs/architecture/training-module.md`
- `docs/architecture/departments-and-permissions.md`
- `docs/api/reference.md`
