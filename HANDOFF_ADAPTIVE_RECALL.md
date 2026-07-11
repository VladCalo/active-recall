# Handoff: Adaptive Active Recall + Final Rereading feature

This document is a complete context dump for continuing this feature build in a
fresh session/agent if the current one runs out of budget. It captures the
**requirements** (verbatim, as clarified through a long back-and-forth with the
user), all **confirmed design decisions**, the **architecture**, exactly
**what's already been built**, and **what's left**.

Repo: `/Users/vladcalo/Personal/github/active-recall`, branch `active-recall2`.
Related repo: `/Users/vladcalo/Personal/github/k3s-rpi5` (GitOps deploy target).

## Why this exists / context

The user is building this for his girlfriend, a non-technical person studying
for a residency exam on **November 13, 2026**. She described what she wanted to
ChatGPT, which produced a spec. The user is using this app (`active-recall2`,
a from-scratch cleanup of an existing `active-recall` app already running on
his home k3s cluster) to implement it. `active-recall` (main branch, its own
k8s namespace, SQLite DB) must **never be touched** — this is all on the
`active-recall2` branch/app/Postgres-DB, entirely separate.

**IMPORTANT process note for whoever picks this up**: this user explicitly said
*"if you have anything unknown don't assume, ask."* Several early
misunderstandings were caught this way (e.g. ChatGPT's spec doesn't define any
interval numbers at all — those came from a second, separate message). Do not
guess at exam-cycle dates, interval numbers, or transition rules — they are all
fully specified below. If something outside this doc is ambiguous, ask.

---

## Part 1: The requirements (verbatim, as given by the user)

### 1a. ChatGPT's original spec ("Final Active Recall & Reference Mode")

> **Final Active Recall Detection**
>
> The application should automatically detect when a chapter is reaching its
> last scheduled Active Recall before the Final Rereading period.
>
> After every completed Active Recall, the application calculates:
> `Completion Date + Next Interval`
>
> If that next review would occur on or after **October 13, 2026**, then the
> review that has just been completed becomes the chapter's **Final Active
> Recall**.
>
> Instead of scheduling another Active Recall, the application displays:
> **"⚠ This is the final Active Recall for this chapter before Final
> Rereading begins."**
>
> The chapter stores: Final Active Recall date · Final category (Hard /
> Medium / Easy) · Total Active Recall count.
>
> The next action becomes: **"Next step: Final Rereading."** No additional
> Active Recall sessions are scheduled for this chapter.
>
> **Reference Mode (October 13 → November 12)**
>
> On October 13 the application automatically switches to Reference Mode.
> Normal scheduling stops. Each chapter displays: Last Active Recall date ·
> Final Active Recall category · Review count · Current status. Instead of
> scheduling reviews, the app guides the rereading.
>
> **Rereading Recommendation** (based on final category):
> - **Hard → Deep Reread**: careful reading, weak concepts, difficult
>   sections, tables, algorithms, treatment details.
> - **Medium → Focused Reread**: normal reading pace, previously difficult
>   paragraphs, previous weak points.
> - **Easy → Quick Reread**: rapid chapter overview, titles, diagrams,
>   tables, key values. Only slow down if something feels uncertain.
>
> **Completion**: user presses **"✓ Final Reread Completed"**. App no longer
> schedules anything for that chapter, just tracks progress. Dashboard shows:
> chapters completed · chapters remaining · percentage completed · days
> remaining until the exam.
>
> **Main philosophy**: Phase 1 (Adaptive Active Recall) — the app decides
> when to review. Phase 2 (Final Rereading) — the user decides how to
> reread, app just guides via final category + recommended intensity.

### 1b. The actual adaptive engine spec (a *different*, later message — this
is where the real interval numbers and rating mechanics come from; **ChatGPT's
message above never specifies these**)

> **Categories**
>
> - **Hard** (~60–75% known): intervals `2 → 4 → 6 → 8` days. After reaching
>   8: `8 → 8 → 8…` (max interval 8).
> - **Medium** (~75–90% known): intervals `5 → 8 → 11 → 14` days. After
>   reaching 14: `14 → 14 → 14…` (max interval 14).
> - **Easy** (>90% known): intervals `10 → 14 → 18 → 21` days. After
>   reaching 21: `21 → 21 → 21…` (max interval 21).
>
> **Review Result** (asked after every Active Recall session):
>
> | Rating | If currently Hard | If currently Medium | If currently Easy |
> |---|---|---|---|
> | Major gaps | → Hard, 2 days | → Hard, 2 days | → Hard, 2 days |
> | Many confusions | → Hard, 4 days | → Medium, 5 days | → Medium, 5 days |
> | Good, minor hesitation | → Medium, 5 days | → progress through 5→8→11→14 | → Easy, **restart** at 10 days |
> | Excellent | → Medium, 8 days | → Easy, 10 days | → progress through 10→14→18→21 |
>
> "Hard chapters never jump directly to Easy."
>
> **Missed Study Days**: if study is missed, nothing changes automatically —
> overdue chapters keep the same category and stage. After eventually
> completing: `Next review date = Completion Date + Interval` — **not**
> `Scheduled Date + Interval`.
>
> **Overdue Priority** (display order): 1. Overdue Hard · 2. Today's Hard ·
> 3. Overdue Medium · 4. Today's Medium · 5. Overdue Easy · 6. Today's Easy.

---

## Part 2: Confirmed design decisions (resolved via back-and-forth)

These were genuinely ambiguous in the spec above and were explicitly
confirmed with the user — do not re-derive or second-guess them:

1. **Exam-cycle dates are configurable settings**, not hardcoded — because
   she may have another exam cycle in the future. Defaults:
   `final_recall_cutoff_date = 2026-10-13`, `reference_mode_end_date =
   2026-11-12`, `exam_date = 2026-11-13`.
2. **Chapters that haven't naturally reached Final Active Recall by the
   cutoff get force-converted** on read (lazy, no cron job available) —
   using whatever category they're currently sitting on as `final_category`
   (which is already Medium by default if never reviewed, since that's the
   starting category — no special-casing needed).
3. **New chapter creation is blocked once Reference Mode starts** (a
   brand-new chapter has no Active Recall history to build a Final category
   from).
4. **New chapters always start at Category=Medium, stage=0** (5-day first
   interval). There is no separate "pick Hard/Medium/Easy upfront" step —
   the very first rating just applies the same transition table starting
   from this baseline.
5. **The rating ONLY affects category/stage/interval — it does not add any
   separate adaptive-scheduling layer beyond the transition table itself**
   (i.e. the transition table above *is* the entire adaptive mechanism,
   there's nothing extra on top of it).
6. **Final category = a snapshot** of whatever category the chapter happens
   to be on the moment its Final Active Recall is detected. No separate
   input is collected at that moment.
7. **Total Active Recall count is computed, not stored** — it's
   `count(ReviewCompletion rows for that subject)`, avoiding a denormalized
   counter that could drift.
8. **Calendar page limitation (flagged, not objected to)**: because future
   intervals depend on a rating that hasn't happened yet, the app can no
   longer precompute a chapter's full future schedule like the old static
   engine did. Calendar now shows each chapter's single upcoming
   `next_due_date` plus its completed-session history — not a multi-month
   forward projection.
9. **The old `reschedule` concept is gone entirely** — "missed days" now
   just means the chapter stays overdue (shown via the overdue-priority
   sort) until whenever the user actually completes it; no manual
   reschedule action needed since `next_due_date` is always computed from
   the *actual* completion date, never the original due date.

---

## Part 3: Architecture / what changed

**This is a full replacement of the app's scheduling engine**, not an
additive feature. The old system was static/precomputed: a fixed list of
day-offsets (`[1,3,7,14,30,60,120,180]` or a CUSTOM list) computed once from
`start_date`, with a `ReviewEvent` row per (subject, due_date) toggled
complete/incomplete. That whole model is gone in `active-recall2`. (The
original `active-recall` app on `main` still has it — untouched, separate
Postgres/SQLite, separate k8s namespace.)

### New domain model

- **`Category`** enum: `HARD` / `MEDIUM` / `EASY` (`app/models/enums.py`)
- **`Rating`** enum: `MAJOR_GAPS` / `MANY_CONFUSIONS` / `GOOD_MINOR_HESITATION` / `EXCELLENT` (`app/models/enums.py`)
- **`Subject`** (chapter) now has: `category`, `stage` (0-3, index into that
  category's own ladder), `next_due_date` (nullable — null once final),
  `last_active_recall_date`, `is_final_recall_reached`,
  `final_active_recall_date`, `final_category`, `reread_completed_at`.
  Removed: `schedule_type`, `custom_intervals_days`, the `ScheduleType` enum.
- **`ReviewCompletion`** (`app/models/review_completion.py`) replaces the old
  `ReviewEvent` — one row per completed session (there's no "not completed"
  state anymore, since due dates aren't precomputed): `completed_at`,
  `rating`, `category_before/stage_before`, `category_after/stage_after`.
- **`User.review_tracking_start_date`** removed entirely (was only used by
  the old missed-day logic, which is gone).

### The engine (`app/services/adaptive_engine.py`)

Pure, side-effect-free, fully unit-tested (`tests/test_adaptive_engine.py`).
Key pieces:
- `LADDERS: dict[Category, list[int]]` — the interval ladders above.
- `State(category, stage)` NamedTuple.
- `apply_rating(current: State, rating: Rating) -> State` — the full
  transition table from Part 1b, encoded as `_FIXED_TRANSITIONS` (explicit
  fixed targets) + `_PROGRESS_TRANSITIONS` (the two "progress through the
  ladder" cases: Medium+Good, Easy+Excellent — these advance one stage from
  wherever the chapter currently is, capped at stage 3).
- `get_interval(category, stage)`, `next_due_date(completion_date, state)`,
  `is_final_active_recall(completion_date, new_state, cutoff_date)`.
- `REREAD_INTENSITY` — the Hard/Medium/Easy → {label, focus[]} mapping for
  Phase 2 recommendations.
- `DEFAULT_CATEGORY = Category.MEDIUM`, `DEFAULT_STAGE = 0`.

**Transition table cheat-sheet** (verified against Part 1b, all cells unit
tested):

| Rating | Hard | Medium | Easy |
|---|---|---|---|
| Major gaps | →Hard,0 | →Hard,0 | →Hard,0 |
| Many confusions | →Hard,**1** (flat, not relative) | →Medium,0 | →Medium,0 |
| Good, minor hesitation | →Medium,0 | →Medium, **advance** 1 (capped 3) | →Easy,0 (flat reset) |
| Excellent | →Medium,**1** | →Easy,0 | →Easy, **advance** 1 (capped 3) |

### Service layer

- **`SubjectService`** (`app/services/subject_service.py`): CRUD, plus
  `_apply_forced_cutover()` (the lazy Reference-Mode force-conversion,
  called from `get_all()`/`get_by_id()`), plus
  `total_active_recall_count()`. `create()` blocks if
  `today >= final_recall_cutoff_date`.
- **`ReviewService`** (`app/services/review_service.py`): `get_due_today()`
  (overdue-priority sorted), `complete_review(subject_id, rating,
  completed_at?)` (the core engine-application + final-recall-detection
  entry point), `get_calendar_range()`, `get_reference_mode_chapters()`,
  `complete_reread()`, `get_reference_mode_summary()`.
- **`app/core/timeutil.py`**: extracted `today_in_tz(tz_str)` helper shared
  by both services (was duplicated before).

### New config settings (`app/config.py`)

```python
final_recall_cutoff_date: date = date(2026, 10, 13)
reference_mode_end_date: date = date(2026, 11, 12)
exam_date: date = date(2026, 11, 13)
```

### API surface

- `api/subjects.py`: simplified — `SubjectCreate`/`Update` are just
  `name`/`start_date` now.
- `api/reviews.py`: `GET /api/reviews/today` (overdue-priority list),
  `GET /api/reviews/range` (calendar — upcoming + history), `POST
  /api/reviews/complete` (body: `subject_id`, `rating`, `completed_at?` →
  returns `is_final_recall`/`banner_message`). The old `/upcoming`,
  `/events/complete`, `/events/reschedule` endpoints are **gone**.
- **`api/reference_mode.py`** (new): `GET /api/reference-mode` (chapter
  list with recommended intensity), `GET /api/reference-mode/summary`
  (completed/remaining/%/days-left), `POST
  /api/reference-mode/{id}/complete-reread`.
- Registered in `app/api/__init__.py` and `app/main.py`.

---

## Part 4: What's already built (do not redo)

All on branch `active-recall2`, **not yet committed** (check `git status` —
run `git diff`/`git status` first thing to see current uncommitted state).

Backend, fully rewritten and internally consistent (compiles clean —
verified with `python3 -m py_compile` across the whole tree):
- `app/models/enums.py` (new)
- `app/models/subject.py` (rewritten)
- `app/models/review_completion.py` (new, replaces deleted `review_event.py`)
- `app/models/__init__.py` (updated exports)
- `app/models/user.py` (removed `review_tracking_start_date`)
- `app/core/timeutil.py` (new)
- `app/config.py` (added the 3 date settings)
- `app/services/adaptive_engine.py` (new — the core engine, unit-tested manually inline AND via `tests/test_adaptive_engine.py`)
- `app/services/subject_service.py` (rewritten)
- `app/services/review_service.py` (rewritten)
- `app/services/admin_service.py` (fixed 2 stale references: `schedule_type`→`category`, `get_subjects_due_today/in_range`→`get_due_today/get_calendar_range`)
- `app/services/auth_service.py` (removed dead `review_tracking_start_date` assignment + now-unused `ZoneInfo` import)
- `app/schemas/subject.py`, `app/schemas/review.py` (rewritten), `app/schemas/reference_mode.py` (new)
- `app/api/subjects.py`, `app/api/reviews.py` (rewritten), `app/api/reference_mode.py` (new)
- `app/api/admin.py` (fixed `SubjectSummary.schedule_type`→`category`)
- `app/api/__init__.py`, `app/main.py` (wired up new router, removed dead startup code)
- `alembic/env.py` (updated model import)
- `seed.py` (rewritten dev-seed script for the new model)

Tests:
- `tests/conftest.py` — rewritten fixtures (`sample_subject` = Medium/stage0,
  `sample_hard_subject` = Hard/stage0, `other_user_subject`; removed
  `sample_custom_subject` since CUSTOM schedules no longer exist)
- `tests/test_adaptive_engine.py` (new) — full transition table + ladder
  capping + boundary detection, all passing logic (manually verified via
  inline script execution, not yet run through actual `pytest`)
- `tests/test_review_service.py` (rewritten) — `complete_review`,
  `get_due_today` ordering, forced cutover, reference-mode summary
- Deleted: `tests/test_review_events.py`, old `tests/test_review_service.py`
  content (both tested the removed static engine)

**⚠ Not yet run**: none of these tests have actually been executed via
`pytest` yet (no venv/deps installed in this session to run them — only
verified by `py_compile` for syntax and one manual inline script for the
engine logic specifically). **First thing to do when resuming: set up a
venv, `pip install -r requirements.txt`, and run `pytest` — expect to find
and fix real bugs, this has not been validated end-to-end at all.**

**Still NOT updated** (found via grep sweep, but not yet touched):
- `tests/test_api_reviews.py` — entirely built around the old
  `/upcoming` endpoint and `schedule_type` fields; needs a full rewrite for
  the new `/today`, `/range`, `/complete` endpoints.
- `tests/test_api_subjects.py` — full of `schedule_type`/`custom_intervals_days`
  test cases that no longer apply; needs rewrite for the simplified
  create/update schema.
- `tests/test_admin.py` — imports `ScheduleType` (line 16, unused import
  now, will break) but otherwise probably mostly fine — just fix the import.
- `tests/test_user_isolation.py` — references
  `/api/reviews/upcoming` (removed endpoint) and `schedule_type` in a POST
  body; needs updates to match new endpoints/schema.

I was mid-way through rewriting `test_api_subjects.py` when this handoff was
requested — **that file has NOT been touched yet**, still has the old
content shown by `Read` earlier in this session.

---

## Part 5: Remaining work (task list — check `TaskList` tool if available
in the new session, otherwise use this)

1. ~~Adaptive engine module~~ ✅
2. ~~DB models rewrite~~ ✅
3. **Alembic migration** — pending. Need a new revision (on top of
   `20260126_005_add_review_events.py`) that: drops `review_events` table,
   drops `schedule_type`/`custom_intervals_days` columns from `subjects`,
   adds `category`/`stage`/`next_due_date`/`last_active_recall_date`/
   `is_final_recall_reached`/`final_active_recall_date`/`final_category`/
   `reread_completed_at` to `subjects`, creates the new `review_completions`
   table, drops `review_tracking_start_date` from `users`. No real data
   exists yet in the deployed `active-recall2` Postgres (only 1 admin user,
   0 subjects) so no data-migration logic needed — straightforward
   add/drop-column migration.
4. ~~Config additions~~ ✅
5. ~~Service layer rewrite~~ ✅
6. ~~API endpoints~~ ✅
7. **Backend tests** — in progress. Need to: (a) actually run `pytest` for
   the first time and fix whatever breaks, (b) rewrite the 4 stale test
   files listed in Part 4.
8. **Frontend API client + types** (`frontend/src/lib/api.ts`) — replace
   `completeReviewEvent(bool)` with `completeReview(subjectId, rating,
   completedAt?)`, add `getReferenceMode()`, `completeReread(subjectId)`,
   `getReferenceModeSummary()`; update subject create/update calls to drop
   `schedule_type`/`custom_intervals_days`.
9. **Frontend SubjectDialog simplification** — remove schedule_type/custom
   interval fields, just name + start_date.
10. **Frontend Dashboard rewrite** — replace the boolean complete-toggle
    with a 4-option rating picker (Major gaps / Many confusions / Good,
    minor hesitation / Excellent), show the ⚠ final-recall banner when
    `is_final_recall` comes back true, sort/group the due list by
    overdue-priority (Hard overdue → Hard today → Medium overdue → Medium
    today → Easy overdue → Easy today) — the backend already returns it
    pre-sorted, just render in that order with category color-coding
    (suggest red/yellow/green matching Hard/Medium/Easy, matches the user's
    own "traffic light" mental model from the conversation).
11. **Frontend Reference Mode view** (new page/view) — chapter list with
    last Active Recall date, final category badge, review count,
    recommended intensity (label + focus bullet list from
    `REREAD_INTENSITY`), "✓ Final Reread Completed" button; summary widget
    (completed/remaining/%/days-until-exam) at top. Should probably render
    *instead of* the normal Dashboard once `is_reference_mode` is true
    (check via the reference-mode summary endpoint), per the "application
    automatically switches" framing in the spec — not a separate nav item
    the user has to remember to click.
12. **Frontend Calendar adaptation** — rework to show each chapter's single
    upcoming `next_due_date` + completed-session history instead of a
    multi-month forward projection (flagged limitation, user did not
    object).
13. **Manual end-to-end verification** — build + push new
    `active-recall2-backend`/`active-recall2-frontend` images (see Part 6
    for the exact build process already set up), deploy, walk through: a
    chapter's full lifecycle (several ratings moving it through
    categories), the forced-cutover edge case, hitting the exact cutoff
    boundary, Reference Mode view, final reread completion, dashboard
    stats.

---

## Part 6: Deployment context (k3s-rpi5 repo) — already fully working,
reuse as-is

- **Registry**: in-cluster at `rpi5.local:5000`, exposed via `hostPort` on
  the single Pi node. Plain HTTP (no TLS).
- **Build process from this Mac**: a dedicated buildx builder trusts this
  registry as insecure *without* touching Docker Desktop's daemon settings
  (which has a known bug where manually-added `insecure-registries` config
  gets silently wiped on Apply). Already set up:
  - `/Users/vladcalo/Personal/github/active-recall/.buildkitd.toml`
    (gitignored) contains:
    ```toml
    [registry."rpi5.local:5000"]
      http = true
      insecure = true
    ```
  - Builder already created: `docker buildx create --name pi5builder
    --driver docker-container --config ./.buildkitd.toml --use` (persists
    across sessions as a named builder — just `docker buildx build
    --builder pi5builder ...` going forward, no need to recreate unless it's
    gone).
  - Build/push command pattern (arm64, since target is a Pi 5):
    ```bash
    docker buildx build --builder pi5builder --platform linux/arm64 \
      -t rpi5.local:5000/active-recall2-backend:<git-short-sha> \
      -t rpi5.local:5000/active-recall2-backend:latest \
      --push ./backend
    ```
    Frontend needs `--build-arg VITE_BASE=/active-recall2/` (see below).
- **⚠ Critical, already-fixed gotcha**: the k3s node itself (containerd)
  could NOT resolve `rpi5.local` at all (Go's pure-DNS resolver can't do
  mDNS `.local` names, unlike macOS). Fixed via
  `/etc/rancher/k3s/registries.yaml` on the Pi:
  ```yaml
  mirrors:
    "rpi5.local:5000":
      endpoint:
        - "http://192.168.1.137:5000"
  ```
  followed by `sudo systemctl restart k3s` (already done, confirmed
  working — images pull fine now). If a *new* Pi/cluster is ever involved,
  this step needs redoing.
- **Frontend base-path scoping** (already built into the `active-recall2`
  branch, separate from the adaptive-recall feature but load-bearing for
  deployment): `frontend/vite.config.ts` reads `base` from a `VITE_BASE`
  env var (default `/`), `frontend/src/main.tsx`'s `BrowserRouter` uses
  `basename={import.meta.env.BASE_URL...}`, and `frontend/src/lib/api.ts`
  derives the API base URL from `BASE_URL` too — all so the app can be
  built once and deployed under `/active-recall2/` without any bare
  `/api`/`/assets` routes that would collide with the original
  `active-recall` app sharing the same `rpi5.local` hostname. The
  Dockerfile has `ARG VITE_BASE=/` wired through already
  (`frontend/Dockerfile`).
- **k3s-rpi5 manifests already deployed and working**: `apps/postgres/`
  (shared Postgres instance for *any* future app, not just this one — onboard
  a new app's DB via `kubectl exec -n postgres deploy/postgres -- psql -U
  postgres -c "CREATE DATABASE ..."`, documented in that repo's
  `CLAUDE.md`), `apps/active-recall2/` (backend/frontend/redis deployments,
  `db-init-job.yaml` PreSync-ordered-via-sync-wave Job that creates the
  `active_recall2` database, `externalsecret.yaml` pulling
  `secret/active-recall2` — jwt-key/csrf-key/admin-password — from Vault,
  `httproute.yaml` for `/active-recall2` on the shared Gateway).
  `active-recall2` backend connects to Postgres **as the superuser**
  directly (no separate app-level DB role) — deliberate per the user's
  explicit request ("just a superuser account for the admin of
  active-recall2").
- Admin login for the currently-deployed `active-recall2`: email
  `adminvladcalo@gmail.com`, password is whatever the user put in Vault at
  `secret/active-recall2` → `admin-password` (never seen/handled by the
  agent).
- **After this feature is done**: needs a new Alembic migration to run
  against the live `active-recall2` Postgres (already has 1 admin user, 0
  subjects — the migration in Part 5 item 3 is safe to apply directly, no
  data to preserve), then rebuild+push both images with a new git-sha tag,
  update `apps/active-recall2/deployment.yaml` in `k3s-rpi5` with the new
  tags, push to `main`, then `kubectl apply -f argocd/active-recall2.yaml`
  (scoped re-sync — **do not** sync the ArgoCD root app, it cascades to
  every other app in the cluster including the untouched original
  `active-recall`).

---

## Part 7: User working style notes (for whoever picks this up)

- Wants correctness over speed — this is for a real exam, mistakes in the
  scheduling math matter.
- Explicitly rejects the agent probing for credentials/secrets itself
  (Vault tokens, etc.) — always ask the user to run those commands
  themselves.
- Explicitly rejected the agent running broad ArgoCD root-app syncs or full
  `k3s` restarts without being asked specifically — prefers scoped,
  narrow actions (e.g. `kubectl apply -f` a single Application manifest
  rather than triggering a cluster-wide reconcile).
- Prefers being asked with concrete options (this session used
  `AskUserQuestion` successfully several times) over the agent silently
  guessing on anything involving real data/dates/behavior for the actual
  exam.
