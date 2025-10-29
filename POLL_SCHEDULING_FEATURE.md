# ⏰ Poll Scheduling Feature Documentation

## Overview

The Poll Scheduling feature enables administrators to schedule voting competitions to start and end at specific dates and times. This powerful feature allows organizations to plan voting events in advance, manage multiple concurrent competitions, and automate competition lifecycle management.

## Why Poll Scheduling?

### Benefits

✅ **Advanced Planning**
- Create competitions weeks or months in advance
- Organize complex voting campaigns with multiple events
- No need to manually start/stop competitions

✅ **Better Organization**
- Time-based separation of voting events
- Clear visibility into upcoming competitions
- Prevents accidental early starts

✅ **Improved User Experience**
- Users know exactly when polls start
- Professional event management
- Prevents confusion about when to vote

✅ **Operational Efficiency**
- Reduce manual intervention
- Automated state transitions
- Predictable competition lifecycle

### Use Cases

1. **Scheduled Team Surveys**
   - Monday 10:00 AM: "Lunch spot poll"
   - Monday 2:00 PM: "Project priority voting"
   - Monday 4:00 PM: "Meeting time preference"

2. **Time-Limited Event Voting**
   - Conference: Day 1, 9:00 AM - 5:00 PM
   - Elections: Specific voting windows
   - Awards: Nomination and voting periods

3. **Multi-Stage Competitions**
   - Preliminary round: 10:00-11:00 AM
   - Semi-finals: 1:00-2:00 PM  
   - Finals: 3:00-4:00 PM

## Database Schema

### Updated Competitions Table

```sql
CREATE TABLE competitions (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  option_a VARCHAR(255) NOT NULL,
  option_b VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'scheduled',
  created_by INT REFERENCES users(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  -- New fields for scheduling
  scheduled_start TIMESTAMP,       -- When poll should start
  scheduled_end TIMESTAMP,         -- When poll should auto-close
  started_at TIMESTAMP,            -- When poll actually started
  closed_at TIMESTAMP              -- When poll was closed
);
```

### New Scheduled Tasks Table

```sql
CREATE TABLE scheduled_tasks (
  id SERIAL PRIMARY KEY,
  competition_id INT REFERENCES competitions(id) ON DELETE CASCADE,
  task_type VARCHAR(50) NOT NULL,  -- 'start', 'end', 'extend'
  scheduled_time TIMESTAMP NOT NULL,
  executed BOOLEAN DEFAULT FALSE,
  executed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### 1. Create Competition with Scheduling

**Endpoint:** `POST /api/admin/competitions`

**Authentication:** Admin required

**Request Body:**
```json
{
  "name": "Python vs JavaScript",
  "description": "Which is the better programming language?",
  "option_a": "Python",
  "option_b": "JavaScript",
  "scheduled_start": "2024-01-15T10:30:00",
  "scheduled_end": "2024-01-15T11:30:00"
}
```

**Response (201 Created):**
```json
{
  "id": 5,
  "name": "Python vs JavaScript",
  "description": "Which is the better programming language?",
  "option_a": "Python",
  "option_b": "JavaScript",
  "status": "scheduled",
  "created_at": "2024-01-14T15:00:00",
  "scheduled_start": "2024-01-15T10:30:00",
  "scheduled_end": "2024-01-15T11:30:00"
}
```

**Notes:**
- If `scheduled_start` is provided, competition starts in "scheduled" status
- If `scheduled_start` is omitted, competition starts in "active" status
- Both dates/times must be in ISO 8601 format
- `scheduled_end` is optional; if omitted, no auto-close

### 2. Get Scheduled Competitions

**Endpoint:** `GET /api/admin/competitions/scheduled`

**Authentication:** Admin required

**Response (200 OK):**
```json
[
  {
    "id": 5,
    "name": "Python vs JavaScript",
    "description": "Which is the better programming language?",
    "option_a": "Python",
    "option_b": "JavaScript",
    "status": "scheduled",
    "scheduled_start": "2024-01-15T10:30:00",
    "scheduled_end": "2024-01-15T11:30:00",
    "created_at": "2024-01-14T15:00:00"
  },
  {
    "id": 6,
    "name": "Coffee vs Tea",
    "status": "active",
    "scheduled_start": "2024-01-14T09:00:00",
    "scheduled_end": "2024-01-14T10:00:00",
    "created_at": "2024-01-14T08:00:00"
  }
]
```

**Notes:**
- Returns all competitions with scheduled times
- Includes scheduled, active, and closed competitions
- Sorted by start time (newest first), then by creation time

### 3. Update Competition Schedule

**Endpoint:** `POST /api/admin/competitions/<id>/schedule`

**Authentication:** Admin required

**Request Body:**
```json
{
  "scheduled_start": "2024-01-20T14:00:00",
  "scheduled_end": "2024-01-20T15:00:00"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Competition scheduled successfully"
}
```

### 4. Start Scheduled Competition Now

**Endpoint:** `POST /api/admin/competitions/<id>/open`

**Authentication:** Admin required

**Response (200 OK):**
```json
{
  "message": "Competition reopened"
}
```

**Notes:**
- Changes status from "scheduled" to "active"
- Starts accepting votes immediately
- Used to manually start scheduled competitions before scheduled_start time
- Can also be used to reopen closed competitions

## Frontend UI

### Create Competition Form

The admin dashboard form includes optional scheduling fields:

```
┌─────────────────────────────────────────────────────┐
│ CREATE NEW COMPETITION                              │
├─────────────────────────────────────────────────────┤
│ Competition Name: [text input]                      │
│ Description: [textarea]                             │
│ Option A: [text input]    Option B: [text input]    │
├─────────────────────────────────────────────────────┤
│ ⏰ SCHEDULE (Optional)                               │
│ Start Time: [datetime-local input]                  │
│ End Time: [datetime-local input]                    │
│                                                     │
│ [Create Button]  [Cancel Button]                    │
└─────────────────────────────────────────────────────┘
```

### Scheduled Competitions Panel

A new section displays all scheduled competitions:

```
┌──────────────────────────────────────────────────────────┐
│ ⏰ SCHEDULED COMPETITIONS                                │
├──────────────────────────────────────────────────────────┤
│ Name     │ Start Time      │ End Time        │ Actions   │
├──────────────────────────────────────────────────────────┤
│ Python   │ Jan 15 10:30 AM │ Jan 15 11:30 AM │ ▶ Start   │
│ vs JS    │                 │                 │ 🗑 Delete │
├──────────────────────────────────────────────────────────┤
│ Coffee   │ Jan 15 2:00 PM  │ Jan 15 3:00 PM  │ ▶ Start   │
│ vs Tea   │                 │                 │ 🗑 Delete │
└──────────────────────────────────────────────────────────┘
```

## Status Flow

### Competition Lifecycle

```
                 ┌─────────────┐
                 │  Scheduled  │
                 └──────┬──────┘
                        │
        ┌───────────────┴──────────────┐
        │                              │
   (at scheduled_start)        (manual click)
   (or "Start Now")            ("▶ Start Now")
        │                              │
        └──────────────┬───────────────┘
                       ↓
                ┌─────────────┐
                │   Active    │
                └──────┬──────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
  (at scheduled_end)          (manual click)
  (if set)                    ("Close" button)
        │                             │
        └──────────────┬──────────────┘
                       ↓
                ┌─────────────┐
                │   Closed    │
                └─────────────┘
```

### Status Definitions

| Status | Color | Meaning |
|--------|-------|---------|
| **Scheduled** | 🟣 Purple | Waiting for start time |
| **Active** | 🟢 Green | Currently accepting votes |
| **Closed** | 🔴 Red | No longer accepting votes |

## Usage Examples

### Example 1: Create and Schedule a Timed Poll

```
Admin Dashboard → Create New Competition

Name: "Favorite Programming Language"
Description: "Vote for your preferred language"
Option A: "Python"
Option B: "JavaScript"

Schedule:
  Start Time: 2024-01-15 10:00 AM
  End Time: 2024-01-15 11:00 AM

Click Create
```

**Result:**
- Competition created with status "SCHEDULED"
- Appears in "Scheduled Competitions" panel
- At 10:00 AM: automatically becomes "ACTIVE"
- Users can vote between 10:00-11:00 AM
- At 11:00 AM: automatically becomes "CLOSED"
- No more votes accepted after 11:00 AM

### Example 2: Create an Immediate Poll

```
Name: "Quick Decision Poll"
Option A: "Option A"
Option B: "Option B"

Schedule: (Leave both empty)

Click Create
```

**Result:**
- Competition created with status "ACTIVE"
- Immediately starts accepting votes
- No scheduled end time (manual close required)

### Example 3: Start Scheduled Poll Early

```
Admin Dashboard
Find "Python vs JavaScript" in Scheduled Competitions
Click "▶ Start Now"
```

**Result:**
- Poll immediately changes to "ACTIVE"
- Users can start voting immediately
- Original scheduled_end time still applies (if set)

### Example 4: Manage Multiple Back-to-Back Polls

```
09:30 AM: Schedule Poll 1 (9:00-10:00 AM) → ACTIVE
09:45 AM: Schedule Poll 2 (10:00-11:00 AM) → SCHEDULED
10:00 AM: Poll 1 auto-closes, Poll 2 auto-starts
11:00 AM: Poll 2 auto-closes
```

## Frontend Features

### Real-Time Updates

Dashboard automatically refreshes every 3 seconds:
- Scheduled → Active transitions appear instantly
- Vote counts update in real-time
- New scheduled polls appear immediately

### Responsive Design

- Works on desktop, tablet, and mobile
- Date/time pickers work across all browsers
- Touch-friendly buttons and inputs

### Dark Mode Support

- All UI elements support light/dark themes
- Colors optimized for both themes
- Persistent theme preference stored in localStorage

## Advanced Features

### Timezone Handling

**Current Implementation:**
- Browser's local timezone used for datetime pickers
- Times stored in database as UTC
- Results display in user's local timezone

**Example:**
```
User in EST timezone sets: 2024-01-15 2:00 PM EST
Stored in DB: 2024-01-15 19:00:00 UTC (UTC-5)
Displayed to EST user: 2024-01-15 2:00 PM EST
```

### Validation

**Input Validation:**
- End time must be after start time
- Cannot schedule in the past
- DateTime format must be valid
- Required fields enforced

**Business Logic:**
- Scheduled status prevents voting
- Active status allows voting
- Closed status blocks voting

## Best Practices

### 1. Plan Ahead

- Create competitions at least 1 day in advance
- Build in buffer time between events
- Account for timezones if distributed team

### 2. Set Appropriate Durations

- Short polls: 15-30 minutes
- Standard surveys: 1-2 hours
- Important decisions: 1-3 days

### 3. Use Meaningful Names

✅ Good: "Q1 Team Goals Priority Voting"
❌ Bad: "Poll 1", "Vote"

✅ Good: "Lunch Location - Jan 15 Noon"
❌ Bad: "Lunch"

### 4. Communicate Schedule

- Announce scheduled polls in advance
- Include date/time in poll description
- Set expectations about duration

### 5. Monitor Important Polls

- Check dashboard before scheduled times
- Verify automatic transitions occur
- Be ready to manually intervene if needed

## Troubleshooting

### Poll Not Starting at Scheduled Time

**Possible Causes:**
1. Background scheduler not running (scheduled_start is advisory)
2. Browser cache showing old data
3. Timezone mismatch

**Solutions:**
1. Click "▶ Start Now" button to start manually
2. Clear browser cache and refresh
3. Verify timezone settings

### Cannot See Scheduled Competitions

**Possible Causes:**
1. Not logged in as admin
2. No scheduled competitions exist
3. All competitions already started/closed

**Solutions:**
1. Verify admin status in header
2. Create a new scheduled competition
3. Scroll down to view panel (may be hidden if empty)

### DateTime Picker Not Working

**Possible Causes:**
1. Browser doesn't support datetime-local input
2. JavaScript disabled
3. Browser compatibility issue

**Solutions:**
1. Use Chrome/Firefox/Edge (latest versions)
2. Enable JavaScript in browser settings
3. Use manual datetime entry format

### Poll Status Won't Change

**Possible Causes:**
1. Page not refreshing
2. Browser cache issue
3. Database connection problem

**Solutions:**
1. Refresh page (Ctrl+F5)
2. Clear browser cache
3. Check database connection status

## Future Enhancements

### Phase 2: Auto-Scheduling

- Background worker automatically transitions competitions
- No manual "Start Now" required
- Scheduled_start and scheduled_end times respected

**Implementation:** Apache Celery or APScheduler

### Phase 3: Recurring Competitions

- Schedule competitions to repeat
- Examples: "Every Monday at 10 AM"
- Reduce manual scheduling for regular events

### Phase 4: Timezone Support

- Store user timezone preferences
- Display times in user's timezone
- Support for global teams across zones

### Phase 5: Competition Templates

- Save competition as template
- Reuse templates for recurring polls
- Quick scheduling with predefined options

### Phase 6: Notifications

- Email notifications before poll starts
- Slack/Teams integration
- Real-time alerts for important events

### Phase 7: Advanced Analytics

- Scheduling analytics
- Peak voting times
- Participation trends

## API Reference Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/admin/competitions` | Create competition (with scheduling) |
| GET | `/api/admin/competitions/scheduled` | Get scheduled competitions |
| POST | `/api/admin/competitions/<id>/schedule` | Update schedule |
| POST | `/api/admin/competitions/<id>/open` | Start competition now |
| POST | `/api/admin/competitions/<id>/close` | Close competition |
| DELETE | `/api/admin/competitions/<id>` | Delete competition |

## Code Examples

### Python/cURL: Create Scheduled Competition

```bash
curl -X POST http://localhost:8080/api/admin/competitions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Team Poll",
    "description": "Vote for your preference",
    "option_a": "Option A",
    "option_b": "Option B",
    "scheduled_start": "2024-01-15T10:00:00",
    "scheduled_end": "2024-01-15T11:00:00"
  }'
```

### JavaScript: Get Scheduled Polls

```javascript
fetch('/api/admin/competitions/scheduled', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(competitions => {
  console.log('Scheduled polls:', competitions);
});
```

## Summary

The Poll Scheduling feature provides:
- ✅ Advanced event planning capabilities
- ✅ Automated competition lifecycle
- ✅ Multiple concurrent competitions
- ✅ Professional voting administration
- ✅ Clear status indicators
- ✅ One-click manual controls

This enables organizations to efficiently manage complex voting scenarios with minimal manual intervention.
