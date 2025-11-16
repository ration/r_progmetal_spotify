# Quickstart Guide: Admin Sync Page

**Feature**: 007-admin-sync-page
**Date**: 2025-11-16
**Branch**: `007-admin-sync-page`

## Overview

This guide provides step-by-step instructions for implementing and testing the admin sync page feature. This feature moves sync controls from the main catalog page to a dedicated admin page.

---

## Prerequisites

- Python 3.14
- Django 5.2.8 installed
- Progmetal catalog app running
- Existing sync functionality working (sync button, status updates)

---

## Implementation Steps

### Step 1: Create Admin Sync Page View

**File**: `catalog/views.py`

Add the new view function:

```python
def admin_sync_page(request: HttpRequest) -> HttpResponse:
    """
    Display the admin sync page with sync controls.

    Context:
        latest_sync: Most recent successful sync operation
        page_title: Page title for template
    """
    from catalog.models import SyncRecord

    latest_sync: Optional[SyncRecord] = SyncRecord.objects.filter(
        status="completed"
    ).order_by("-sync_timestamp").first()

    return render(request, "catalog/admin_sync.html", {
        "latest_sync": latest_sync,
        "page_title": "Sync Administration"
    })
```

**Type Annotations**: Add `Optional` import from `typing` if not already present.

---

### Step 2: Add Admin Page URL Route

**File**: `catalog/urls.py`

Add the new URL pattern to `urlpatterns`:

```python
urlpatterns = [
    # ... existing patterns ...
    path("admin/sync/", views.admin_sync_page, name="admin-sync"),
]
```

**Location**: Add after existing sync-related patterns for logical grouping.

---

### Step 3: Create Admin Sync Template

**File**: `catalog/templates/catalog/admin_sync.html` (new file)

Create the template:

```django
{% extends "catalog/base.html" %}

{% block title %}{{ page_title }} - Progressive Metal Catalog{% endblock %}

{% block content %}
<div class="w-full">
    <!-- Page Header -->
    <div class="mb-8">
        <h1 class="text-4xl font-bold mb-2">{{ page_title }}</h1>
        <p class="text-base-content/70">
            Manage album synchronization with Google Sheets and Spotify API
        </p>
    </div>

    <!-- Navigation back to catalog -->
    <div class="mb-6">
        <a href="{% url 'catalog:album-list' %}" class="btn btn-outline btn-sm">
            ← Back to Catalog
        </a>
    </div>

    <!-- Sync Button and Status -->
    {% include "catalog/components/sync_button.html" %}
    {% include "catalog/components/sync_status.html" %}

    <!-- Last Sync Timestamp -->
    {% if latest_sync %}
    <div class="mb-6 text-sm text-base-content/70">
        Last synced: <span class="timeago" data-timestamp="{{ latest_sync.sync_timestamp.isoformat }}">{{ latest_sync.sync_timestamp|date:"Y-m-d H:i:s" }}</span>
    </div>
    {% else %}
    <div class="mb-6 text-sm text-base-content/70">
        Never synced
    </div>
    {% endif %}
</div>

<script>
// Update relative timestamp display
function updateTimeago() {
    const timeagoElements = document.querySelectorAll('.timeago');

    timeagoElements.forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        if (!timestamp) return;

        const date = new Date(timestamp);
        const now = new Date();
        const secondsAgo = Math.floor((now - date) / 1000);

        let relativeTime;
        if (secondsAgo < 60) {
            relativeTime = 'just now';
        } else if (secondsAgo < 3600) {
            const minutes = Math.floor(secondsAgo / 60);
            relativeTime = minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
        } else if (secondsAgo < 86400) {
            const hours = Math.floor(secondsAgo / 3600);
            relativeTime = hours === 1 ? '1 hour ago' : `${hours} hours ago`;
        } else {
            const days = Math.floor(secondsAgo / 86400);
            relativeTime = days === 1 ? '1 day ago' : `${days} days ago`;
        }

        element.textContent = relativeTime;
    });
}

// Update on page load
updateTimeago();

// Update every minute (60000ms)
setInterval(updateTimeago, 60000);
</script>
{% endblock %}
```

**Notes**:
- Uses Tailwind CSS and DaisyUI classes (already in project)
- Includes existing sync components (no duplication)
- Copies timeago JavaScript from album_list.html

---

### Step 4: Add Navigation to Admin Page

**File**: `catalog/templates/catalog/base.html`

Add admin link to the navigation area. The exact location depends on your base template structure, but typically:

```django
<nav class="navbar">
    <div class="navbar-start">
        <a href="{% url 'catalog:album-list' %}" class="btn btn-ghost">Catalog</a>
    </div>
    <div class="navbar-end">
        <a href="{% url 'catalog:admin-sync' %}" class="btn btn-primary btn-sm">Admin</a>
    </div>
</nav>
```

**Styling**: Use DaisyUI button classes consistent with your existing navigation.

---

### Step 5: Remove Sync Components from Catalog Page

**File**: `catalog/templates/catalog/album_list.html`

Remove these lines:

```django
<!-- Remove these lines: -->
{% include "catalog/components/sync_button.html" %}
{% include "catalog/components/sync_status.html" %}

<!-- Remove last sync timestamp section: -->
{% if latest_sync %}
<div class="mb-6 text-sm text-base-content/70">
    Last synced: <span class="timeago" data-timestamp="{{ latest_sync.sync_timestamp.isoformat }}">{{ latest_sync.sync_timestamp|date:"Y-m-d H:i:s" }}</span>
</div>
{% else %}
<div class="mb-6 text-sm text-base-content/70">
    Never synced
</div>
{% endif %}

<!-- Keep all other content (statistics, filters, album grid) -->
```

**Context Update**: If `AlbumListView` provides `latest_sync` context, it can be removed (optional cleanup).

---

### Step 6: Run Type Checking

Verify type annotations are correct:

```bash
pyright catalog/views.py
```

**Expected**: Zero errors for the new `admin_sync_page` function.

---

### Step 7: Run Linting

Check code quality:

```bash
ruff check catalog/
ruff format catalog/
```

**Expected**: Zero errors, automatic formatting applied.

---

## Testing Checklist

### Manual Testing

Run through these scenarios:

#### Test 1: Admin Page Access
- [ ] Navigate to `http://localhost:8000/catalog/admin/sync`
- [ ] Verify page loads with title "Sync Administration"
- [ ] Verify sync button is visible
- [ ] Verify sync status display is visible
- [ ] Verify "Back to Catalog" link is present

#### Test 2: Sync Button Functionality
- [ ] Click "Sync Now" button on admin page
- [ ] Verify button changes to "Sync in Progress" (or similar)
- [ ] Verify button is disabled during sync
- [ ] Wait for sync to complete
- [ ] Verify button returns to "Sync Now" state

#### Test 3: Status Updates
- [ ] Trigger a sync from admin page
- [ ] Observe status display updates every ~2 seconds
- [ ] Verify progress messages appear (e.g., "Processing tab: 2025 Prog-metal")
- [ ] Verify status shows completion message when done

#### Test 4: Timestamp Display
- [ ] Complete a sync operation
- [ ] Verify "Last synced: X minutes ago" appears
- [ ] Wait 1 minute
- [ ] Verify timestamp updates to "X+1 minutes ago"
- [ ] Refresh page, verify timestamp persists

#### Test 5: Navigation Flow
- [ ] From catalog page (`/catalog/`), click "Admin" link
- [ ] Verify lands on admin sync page
- [ ] Click "Back to Catalog" link
- [ ] Verify returns to catalog page
- [ ] Verify sync components NOT present on catalog page

#### Test 6: Catalog Page Changes
- [ ] Navigate to main catalog page (`/catalog/`)
- [ ] Verify sync button is NOT present
- [ ] Verify sync status is NOT present
- [ ] Verify last sync timestamp is NOT present
- [ ] Verify "Admin" navigation link IS present
- [ ] Verify catalog functionality still works (filters, search, pagination)

#### Test 7: Multiple Tabs
- [ ] Open admin page in tab 1
- [ ] Open admin page in tab 2
- [ ] Trigger sync from tab 1
- [ ] Verify tab 2 shows sync status updates
- [ ] Verify both tabs show same sync state

#### Test 8: Error Handling
- [ ] Stop Django server while on admin page
- [ ] Start server again
- [ ] Refresh page
- [ ] Verify page loads correctly
- [ ] Verify no JavaScript errors in browser console

---

## Common Issues and Solutions

### Issue 1: Admin Page Shows 404

**Symptom**: Navigating to `/catalog/admin/sync` returns "Page not found"

**Solution**:
- Verify URL pattern added to `catalog/urls.py`
- Check `app_name = "catalog"` is defined in urls.py
- Restart Django development server: `python manage.py runserver`

---

### Issue 2: Sync Button Not Visible on Admin Page

**Symptom**: Admin page loads but sync button component missing

**Solution**:
- Verify `{% include "catalog/components/sync_button.html" %}` in admin_sync.html
- Check template file path: `catalog/templates/catalog/components/sync_button.html` exists
- Check for Django template errors in console/logs

---

### Issue 3: Status Not Updating in Real-Time

**Symptom**: Sync status shows static text, doesn't update during sync

**Solution**:
- Verify HTMX library loaded in base template
- Check browser developer console for HTMX errors
- Verify sync_status.html component has `hx-trigger="every 2s"` attribute
- Check `/catalog/sync/status/` endpoint returns 200 status

---

### Issue 4: Timestamp Not Showing

**Symptom**: "Last synced" section always shows "Never synced"

**Solution**:
- Verify at least one sync has completed successfully
- Check `SyncRecord` model has entries with `status="completed"`
- Verify query in view: `SyncRecord.objects.filter(status="completed")`
- Check database: `python manage.py shell` → `SyncRecord.objects.all()`

---

### Issue 5: Timeago Not Updating

**Symptom**: Timestamp shows "5 minutes ago" but doesn't update as time passes

**Solution**:
- Check browser console for JavaScript errors
- Verify `<script>` block copied to admin_sync.html
- Verify `setInterval(updateTimeago, 60000)` called at end of script
- Check `.timeago` class present on timestamp span

---

### Issue 6: Catalog Page Still Shows Sync Button

**Symptom**: Sync button appears on both catalog and admin pages

**Solution**:
- Verify removed `{% include "catalog/components/sync_button.html" %}` from album_list.html
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Restart Django server to reload templates

---

## Rollback Procedure

If issues arise, rollback by reversing the changes:

1. **Restore catalog page sync components**:
   - Add back `{% include "catalog/components/sync_button.html" %}` to album_list.html
   - Add back `{% include "catalog/components/sync_status.html" %}` to album_list.html
   - Add back last sync timestamp section

2. **Remove admin page navigation**:
   - Remove "Admin" link from base.html

3. **Optional: Remove admin page**:
   - Remove `path("admin/sync/", ...)` from urls.py
   - Remove `admin_sync_page` view from views.py
   - Delete `catalog/templates/catalog/admin_sync.html`

The sync functionality will continue working as before.

---

## Performance Validation

Verify success criteria from spec:

- **SC-001**: Admin page accessible in <2 clicks
  - Test: From catalog page, click "Admin" = 1 click ✓

- **SC-002**: Status updates within 2 seconds
  - Test: Trigger sync, measure time until first status update
  - Expected: ~2 seconds (HTMX polling interval)

- **SC-003**: Catalog page loads faster
  - Test: Measure page load time before/after (browser DevTools Network tab)
  - Expected: Reduction due to fewer includes and no HTMX polling on catalog page

- **SC-004**: Identical sync functionality
  - Test: Trigger sync from admin page, verify albums imported correctly
  - Expected: Same behavior as before

- **SC-005**: Zero regression
  - Test: Run full test suite: `pytest`
  - Expected: All existing tests pass

---

## Development Tips

### Tip 1: Use Django Shell for Testing Queries

Test the `SyncRecord` query before implementing:

```bash
python manage.py shell
```

```python
from catalog.models import SyncRecord
latest = SyncRecord.objects.filter(status="completed").order_by("-sync_timestamp").first()
print(latest.sync_timestamp if latest else "Never synced")
```

---

### Tip 2: Test HTMX Polling in Browser DevTools

Monitor HTMX polling behavior:

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "sync"
4. Trigger sync from admin page
5. Observe requests to `/catalog/sync/button/` and `/catalog/sync/status/` every 2 seconds

---

### Tip 3: Use Django Debug Toolbar

Install and configure django-debug-toolbar to inspect:
- Template rendering performance
- Database queries
- Context data passed to templates

---

## Next Steps

After implementation and testing:

1. **Create pull request** from `007-admin-sync-page` branch
2. **Review checklist** from `specs/007-admin-sync-page/checklists/requirements.md`
3. **Document any deviations** from the plan
4. **Update CLAUDE.md** if new patterns established

---

## Resources

- **Spec**: `specs/007-admin-sync-page/spec.md`
- **Plan**: `specs/007-admin-sync-page/plan.md`
- **Research**: `specs/007-admin-sync-page/research.md`
- **Data Model**: `specs/007-admin-sync-page/data-model.md`
- **Contracts**: `specs/007-admin-sync-page/contracts/http-endpoints.md`

- **Django Templates**: https://docs.djangoproject.com/en/5.2/topics/templates/
- **Django URLs**: https://docs.djangoproject.com/en/5.2/topics/http/urls/
- **HTMX**: https://htmx.org/docs/
- **DaisyUI**: https://daisyui.com/components/

---

## Summary

This quickstart guide provides everything needed to implement the admin sync page feature. The implementation is straightforward:

1. Add new view and URL
2. Create admin template reusing existing components
3. Add navigation link
4. Remove sync components from catalog page

Total time estimate: **2-3 hours** including testing.
