---
topic: date_filter
title: How to Filter Leads by Date
keywords: date filter, filter by date, date range, from date, to date, presets, created date, follow up date, last activity, last updated, won date, export filtered
roles: [admin, manager, salesperson, surveyor]
regions: [IN, AU]
---
# How to Filter Leads by Date

The Leads page provides date range filtering to help you find leads created, updated, or followed up within specific timeframes.

## Available Date Fields
You can filter leads by any of the following fields:
1. **Created date** (default): The date when the lead was first entered into the CRM.
2. **Next follow-up date**: The scheduled date and time for the next customer follow-up call or task.
3. **Last activity date**: The timestamp when the most recent call, remark, note, or survey activity was logged for the lead.
4. **Last updated date**: The timestamp when the lead record was last modified.
5. **Won date**: The date when the lead reached 'Won' status.

## Using Date Presets and Custom Ranges
- **Quick Presets**: Select one-click presets including **Today**, **Yesterday**, **Last 7 days**, **This month**, and **Last month**.
- **Custom Range**: Pick explicit **From date** and **To date** values using the calendar picker (DD/MM/YYYY format). Either date may be left empty for open-ended queries (e.g., all leads up to a certain date or all leads after a specific date).
- **Timezone Awareness**: The date boundaries are computed in your user profile's local timezone (e.g., Asia/Kolkata or Australia/Sydney) and converted to UTC, ensuring inclusive whole-day coverage.
- **Active Range Chip**: An active date filter is displayed as a badge chip that can be cleared with one click.
- **Bookmarks & Sharing**: The active date filter parameters (`date_field`, `date_from`, `date_to`) are saved in the URL query string, allowing filtered views to be bookmarked or shared with colleagues.
- **CSV Export**: When exporting leads to CSV, the active date filter is automatically applied to export only the matching records.
