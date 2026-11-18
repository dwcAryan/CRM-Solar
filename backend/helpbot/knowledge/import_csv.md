---
topic: import_csv
title: Importing Leads via CSV File
keywords: import, csv import, upload leads, bulk leads, round robin, assignment, duplicate phone, mapping
roles: [admin, manager]
regions: [IN, AU]
---
# Importing Leads via CSV

Managers and Admins can import bulk lead lists using the CSV Import wizard.

## CSV Requirements
1. **Required Columns**: Phone number, Full Name, Region (IN or AU), City/State.
2. **Optional Columns**: Email, Roof Type, Monthly Power Bill, Electricity Provider (DISCOM/Retailer), Source.
3. **Phone Formatting**: Recommended international format with country code (+91 for India, +61 for Australia) or standard 10-digit format.
4. **Duplicates Handling**: The system checks existing leads by normalized phone number. Duplicates can be configured to either "Skip" or "Update Existing".
5. **Round-Robin Assignment**: During import, you can choose to auto-distribute leads evenly across active sales reps in the matching region.
