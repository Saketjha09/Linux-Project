# 📋 Poll Scheduling - Quick Reference Guide

## What is Poll Scheduling?

Schedule voting competitions to start and end automatically. Perfect for:
- Timed team surveys
- Event-based voting
- Automated competition management
- Multiple concurrent polls

---

## Quick Start (5 Minutes)

### Step 1: Login as Admin
```
Username: admin
Password: admin123
```

### Step 2: Go to Admin Dashboard
```
http://localhost:8080/admin/dashboard
```

### Step 3: Click "Create New Competition"

### Step 4: Fill in Competition Details
```
Name: "What's your favorite drink?"
Description: "Choose your preference"
Option A: "Coffee"
Option B: "Tea"
```

### Step 5: Set Schedule (Optional)
```
Start Time: Today 2:00 PM
End Time: Today 3:00 PM
```

### Step 6: Click "Create"

**Done!** Your poll is now scheduled.

---

## Status Indicators

| Emoji | Status | Meaning |
|-------|--------|---------|
| 🟣 | SCHEDULED | Waiting to start |
| 🟢 | ACTIVE | Currently voting |
| 🔴 | CLOSED | Voting ended |

---

## Available Actions

### In "Scheduled Competitions" Panel
- **▶ Start Now** - Begin voting immediately
- **🗑 Delete** - Remove scheduled poll

### In "Competitions" Panel  
- **Close** - Stop accepting votes
- **Open** - Reopen closed poll
- **Delete** - Remove poll

---

## Common Tasks

### Task 1: Schedule a Poll for Tomorrow
1. Click "Create New Competition"
2. Fill details
3. Set Start: Tomorrow 10:00 AM
4. Set End: Tomorrow 11:00 AM
5. Click Create

### Task 2: Start Poll Immediately
1. Leave Start/End times empty
2. Click Create
3. Poll is active now

### Task 3: Start Scheduled Poll Early
1. Find in "Scheduled Competitions"
2. Click "▶ Start Now"
3. Poll becomes active

### Task 4: View All Scheduled Polls
- Scroll to "Scheduled Competitions" section
- See all upcoming polls with times

### Task 5: Stop Accepting Votes
1. Find poll in main Competitions table
2. Click "Close" button
3. Poll becomes closed

---

## Time Format

### How to Enter Times

Use the **DateTime Picker** (easiest):
```
Click on date/time field
Select date from calendar
Select time from picker
```

### Format Examples

| Format | Example |
|--------|---------|
| ISO 8601 | 2024-01-15T14:30:00 |
| US Format | January 15, 2024 2:30 PM |
| Browser Local | 01/15/2024, 2:30 PM |

---

## Real-World Examples

### Example 1: Daily Team Poll
```
Name: "Lunch Location - Monday"
Start: Monday 11:30 AM
End: Monday 12:00 PM
Options: "Office Cafeteria" vs "Downtown Restaurant"
```

### Example 2: Weekly Meeting Time
```
Name: "Best Meeting Time - Week of Jan 15"
Start: Monday 9:00 AM
End: Monday 5:00 PM
Options: "Morning (9 AM)" vs "Afternoon (2 PM)"
```

### Example 3: Product Feedback
```
Name: "Feature Priority Q1"
Start: Jan 15 9:00 AM
End: Jan 19 5:00 PM
Options: "New Dashboard" vs "Mobile App"
```

### Example 4: Back-to-Back Decisions
```
9:00-9:30 AM: "Coffee Preference" (scheduled at 8:55)
9:30-10:00 AM: "Team Lunch" (scheduled at 8:55)
10:00-10:30 AM: "Meeting Room" (scheduled at 8:55)
```

---

## Pro Tips

✅ **DO:**
- Schedule 5-10 minutes before meeting
- Use clear, specific names
- Leave 15-30 min between polls
- Set end times for cleanup

❌ **DON'T:**
- Schedule in the past
- Create overlapping urgent polls
- Use vague names like "Poll #1"
- Leave very long end times

---

## Dashboard Overview

```
┌──────────────────────────────────────────────┐
│ ⚙️ ADMIN DASHBOARD                           │
├──────────────────────────────────────────────┤
│ [+ Create New Competition]                   │
├──────────────────────────────────────────────┤
│                                              │
│ COMPETITIONS TABLE                           │
│ Shows: Name | Votes | Status | Actions      │
│ Actions: Close, Open, Delete                 │
│                                              │
│ ⏰ SCHEDULED COMPETITIONS                    │
│ Shows: Name | Start Time | End Time | Action│
│ Action: Start Now, Delete                    │
│                                              │
└──────────────────────────────────────────────┘
```

---

## Keyboard Shortcuts

| Action | Key Combination |
|--------|-----------------|
| Create | Ctrl+Shift+N |
| Refresh | Ctrl+F5 |
| Focus Search | Ctrl+F |

---

## Status Transitions

```
Timeline →

SCHEDULED  ──(at start time or click ▶)──→  ACTIVE  ──(at end time or click Close)──→  CLOSED
```

### What Happens at Each Stage

1. **SCHEDULED**
   - Poll created with future time
   - Users cannot vote yet
   - Admin can modify or delete

2. **ACTIVE**
   - Poll starts accepting votes
   - Vote counts update in real-time
   - Cannot be deleted

3. **CLOSED**
   - Voting stopped
   - Can see final results
   - Can reopen or delete

---

## Troubleshooting

### Problem: Can't See Scheduled Polls
**Solution:** Scroll down in dashboard. Section hides if empty.

### Problem: Poll Not Starting
**Solution:** Click "▶ Start Now" button manually.

### Problem: DateTime Picker Not Working
**Solution:** Use latest Chrome/Firefox/Edge browser.

### Problem: Can't Create Poll
**Solution:** 
1. Fill all required fields (Name, Option A, Option B)
2. Click Create button
3. Check browser console for errors

### Problem: Wrong Time Set
**Solution:** Delete poll and create again with correct time.

---

## FAQ

**Q: Can I change the time after creating?**
A: Currently no. Delete and recreate with new time.

**Q: What if no end time?**
A: Poll stays active until you manually close it.

**Q: Do users see scheduled times?**
A: No, they only see polls when active.

**Q: Can I schedule for past dates?**
A: No, system prevents scheduling in past.

**Q: How often does dashboard refresh?**
A: Every 3 seconds automatically.

**Q: Can I delete scheduled polls?**
A: Yes, use "🗑 Delete" button before start time.

**Q: Can I reopen closed polls?**
A: Yes, click "Open" button in main table.

---

## API Quick Reference

### Create Poll with Schedule
```bash
POST /api/admin/competitions
{
  "name": "Poll Name",
  "option_a": "Choice A",
  "option_b": "Choice B",
  "scheduled_start": "2024-01-15T10:00:00",
  "scheduled_end": "2024-01-15T11:00:00"
}
```

### Get Scheduled Polls
```bash
GET /api/admin/competitions/scheduled
```

### Start Poll Now
```bash
POST /api/admin/competitions/{id}/open
```

### Close Poll
```bash
POST /api/admin/competitions/{id}/close
```

---

## Timezone Note

- Dashboard uses your local browser timezone
- Times stored in UTC on server
- Display converts to your local time
- Example: 2:00 PM EST = 7:00 PM UTC

---

## Dark Mode

Click moon/sun icon in top-right to toggle theme.
Preference saved automatically.

---

## Getting Help

If you encounter issues:

1. **Refresh page** (Ctrl+F5)
2. **Clear browser cache**
3. **Check if admin logged in** (see header)
4. **Check browser console** (F12 → Console tab)
5. **Verify service running** (docker ps)

---

## Summary Checklist

✓ Login as admin  
✓ Go to Admin Dashboard  
✓ Click "Create New Competition"  
✓ Fill Name, Options  
✓ (Optional) Set Schedule Times  
✓ Click Create  
✓ View in appropriate section  
✓ Use Start Now to begin early  
✓ Use Close to end voting  
✓ Use Delete to remove  

**You're ready to schedule polls!** 🎉
