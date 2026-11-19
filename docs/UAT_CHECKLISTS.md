# Solar CRM - UAT Hand-Out Checklists (Phase 17)

This document contains printable, one-page hand-out checklists for staff, regional testers, native language reviewers, and the business owner.

---
<div style="page-break-before: always;"></div>

# Section 1: Manual UAT Checklist for Real Staff

**Tester Name**: __________________________  
**Role**: Operational Staff / QA Specialist  
**Execution Date**: _______________________  
**Environment**: Production Candidate (`APP_ENV=production`)

Please execute these real-world verifications using physical devices, authentic email accounts, and live network connections:

| # | Item / Verification Target | Action & Steps | Expected Result | Pass / Fail | Notes |
| :-: | :--- | :--- | :--- | :-: | :--- |
| **1** | **Email Deliverability (Spam Rating)** | Send password reset and lead assignment emails to live Gmail and corporate Outlook mailboxes. | Email arrives in the **Primary Inbox** (not Spam/Junk folder); SPF, DKIM, and DMARC alignments pass. | [ ] Pass<br>[ ] Fail | |
| **2** | **Email Dark Mode & Typography** | Open dispatched HTML quote and notifications on iPhone (Apple Mail) and Android (Gmail) in Dark Mode. | Premailer inlined CSS renders crisp text with high contrast; logo and buttons remain readable without washed-out colors. | [ ] Pass<br>[ ] Fail | |
| **3** | **Real Mobile Web Push Notifications** | Log into Solar CRM on a physical Android device in Chrome and an iOS 16.4+ device in Safari; click 'Enable Notifications'. | Native browser permission prompt appears; granting permission displays a sample follow-up alert on the device lock screen. | [ ] Pass<br>[ ] Fail | |
| **4** | **PWA Home Screen Installation** | In Chrome on desktop and mobile, click the 'Install App' prompt in the sidebar. | Solar CRM installs as a standalone app with custom solar icon; launches without browser address bar. | [ ] Pass<br>[ ] Fail | |
| **5** | **Physical PDF Document Opening** | Download quote PDF and DSAR dossier PDF onto an iPad and Android phone; open in Acrobat / Files app. | Multi-page PDF opens smoothly; solar layout diagrams, company logo, and pricing tables render without clipping. | [ ] Pass<br>[ ] Fail | |
| **6** | **Next Working Day Onboarding Latch** | Complete all 4 onboarding checklist items on Day 1. Log in the next working day on your primary workstation. | The "Getting Started with Solar CRM" card **never reappears**; dashboard metrics start at the top of the screen. | [ ] Pass<br>[ ] Fail | |

**Staff Tester Signature**: ___________________________________  
**Date Completed**: ___________________________________________

---
<div style="page-break-before: always;"></div>

# Section 2: Regional Tester Checklists (India & Australia)

### Part A: Indian Market Tester (Region: IN)
**Tester Name**: __________________________  
**Primary Region**: India (`IN`)  

| # | Item | Verification Steps | Pass / Fail |
| :-: | :--- | :--- | :-: |
| **IN-1** | **E.164 Phone Format** | Enter a 10-digit Indian phone (e.g., `9825123456`). System must automatically normalize to `+919825123456`. | [ ] |
| **IN-2** | **PM Surya Ghar Subsidy** | Create a 3kW residential rooftop quote. Confirm ₹78,000 national subsidy is applied and subtracted from the gross total. | [ ] |
| **IN-3** | **Currency & Number Grouping** | Verify amounts on dashboard and quotes format in Indian numbering (lakhs/crores, e.g., ₹1,80,000). | [ ] |
| **IN-4** | **TRAI Calling Hours** | Verify calls and SMS are allowed between 9:00 AM and 8:00 PM IST; alert displayed outside calling hours. | [ ] |
| **IN-5** | **WhatsApp & SMS Opt-Out** | Confirm Indian message footer includes compliant opt-out instruction: *"To opt out reply STOP to 9825000000"*. | [ ] |

---

### Part B: Australian Market Tester (Region: AU)
**Tester Name**: __________________________  
**Primary Region**: Australia (`AU`)  

| # | Item | Verification Steps | Pass / Fail |
| :-: | :--- | :--- | :-: |
| **AU-1** | **E.164 Australian Mobile** | Enter Australian mobile `0412 345 678`. System must normalize to `+61412345678`. | [ ] |
| **AU-2** | **STC Rebate Calculation** | Create a 6.6kW system quote in NSW. Confirm Small-scale Technology Certificates (STCs) discount is calculated and deducted in $ AUD. | [ ] |
| **AU-3** | **Quarterly Electricity Bill** | Enter quarterly bill ($950). System must calculate $3,800 annualized and $316.67 monthly equivalent. | [ ] |
| **AU-4** | **Perth vs Sydney Timezones** | Verify lead in Perth (AWST, UTC+8) and lead in Sydney (AEST, UTC+10/11) show their exact local time boundaries. | [ ] |
| **AU-5** | **ACMA & DNCR Compliance** | Confirm calling hours follow ACMA 9:00 AM – 8:00 PM state rules; leads marked on Do Not Call Register disable calls. | [ ] |
| **AU-6** | **Spam Act 2003 Unsubscribe** | Confirm Australian message footers include: *"Reply STOP to opt out. Solar CRM Pty Ltd, ABN 12 345 678 901"*. | [ ] |

**Regional QA Sign-off**: _____________________________________  
**Date**: ____________________________________________________

---
<div style="page-break-before: always;"></div>

# Section 3: Role & Permission Checklist for Business Owner

**Business Owner**: _______________________  
**Title**: CEO / Managing Director  
**Purpose**: Confirm that system permissions enforce company policy across all staff roles.

Please review the business rules below and tick to confirm agreement:

| Business Policy & Role Boundary | Enforced Behavior in Solar CRM | Confirmed |
| :--- | :--- | :-: |
| **Salesperson Boundary: No Lead Assignment** | Salespersons can only work leads assigned to them. They cannot reassign leads to other sales reps or self-assign from unassigned queues. | [ ] Confirmed |
| **Salesperson Boundary: No Data Export** | Salespersons are blocked from exporting leads to CSV to protect company customer databases from data leakage (HTTP 403 Forbidden). | [ ] Confirmed |
| **Salesperson Boundary: No Bulk CSV Import** | Only Managers and Admins can import lead batches. Salespersons cannot bulk-import leads without management oversight. | [ ] Confirmed |
| **Manager Oversight: Lost Lead Approval** | When a salesperson marks a lead "Lost" (due to price, competitor, or unreachable), it enters **Lost Approval Pending**. A Manager must formally approve or reject/reopen the lead. | [ ] Confirmed |
| **Manager Authority: Team Assignment** | Managers can assign individual leads or bulk-assign hundreds of unassigned leads across sales representatives and site surveyors. | [ ] Confirmed |
| **Surveyor Masking: No Price Visibility** | Field site surveyors can view technical roof requirements, customer address, and schedule, but **cannot view financial prices, quotes, or monthly bills**. | [ ] Confirmed |
| **Surveyor Isolation: No Lead/Quote Access** | Surveyors only have access to the **My Surveys** section. They cannot browse the active leads pipeline or edit pricing proposals. | [ ] Confirmed |
| **Admin Control: User Management & Masters** | Only Admins can create accounts, toggle user roles, configure outcome follow-up days, and edit public holidays. | [ ] Confirmed |

**Business Owner Formal Confirmation**:  
I confirm that the access control rules outlined above reflect our intended commercial workflow.

**Name**: ____________________________________________________  
**Signature**: _______________________________________________  
**Date**: ____________________________________________________

---
<div style="page-break-before: always;"></div>

# Section 4: Native Hindi Speaker Quality Checklist

**Reviewer Name**: ________________________  
**Native Language**: Hindi (हिन्दी)  
**Date**: _________________________________  

Please review the user interface in Hindi mode and verify natural vocabulary, grammatical accuracy, and layout elegance:

| # | Screen / Feature | Elements to Verify | Approved (Y/N) | Remarks |
| :-: | :--- | :--- | :-: | :--- |
| **1** | **लॉगिन स्क्रीन (Login Screen)** | 'साइन इन करें', 'उपयोगकर्ता नाम', 'पासवर्ड', 'पासवर्ड भूल गए?' | [ ] | |
| **2** | **डैशबोर्ड (Dashboard)** | 'बिक्री अवलोकन', 'सक्रिय लीड्स', 'पाइपलाइन', 'फ़नल मेट्रिक्स' | [ ] | |
| **3** | **लीड्स सूची (Leads List)** | 'सभी लीड्स', 'फ़िल्टर', 'नई लीड जोड़ें', स्थिति बैज ('नई', 'फ़ॉलो-अप') | [ ] | |
| **4** | **लीड विवरण (Lead Detail)** | ग्राहक संपर्क, छत का प्रकार ('आरसीसी', 'टिन शेड'), बिजली बिल | [ ] | |
| **5** | **कॉल परिणाम (Call Outcomes)** | 'कोई उत्तर नहीं', 'व्यस्त या स्विच ऑफ', 'बाद में कॉल करें', 'रुचि है' | [ ] | |
| **6** | **सर्वे बुकिंग (Survey Booking)** | 'साइट सर्वे शेड्यूल करें', सर्वेक्षक चयन, दिनांक और समय स्लॉट | [ ] | |
| **7** | **कोटेशन जनरेटर (Quote Generator)** | 'सिस्टम आकार (kW)', 'अनुदान (PM सूर्य घर)', 'अंतिम देय राशि' | [ ] | |
| **8** | **आज की कार्यसूची (Today Queue)** | 'आज के फ़ॉलो-अप', 'अतिदेय (Overdue)' चेतावनी कार्ड | [ ] | |
| **9** | **मैनेजर ध्यान सूची (Manager Queue)** | 'अस्वीकृत लीड्स', 'अनुमोदन लंबित', 'असाइन करें' | [ ] | |
| **10** | **हेल्प असिस्टेंट (Helpbot)** | प्राकृतिक हिंदी में बातचीत, कार्यप्रणाली उत्तर, विनम्र मनाही | [ ] | |
| **11** | **उत्पाद टूर (Product Tour)** | इंटरैक्टिव पॉपओवर, 'अगला' और 'समाप्त' बटन | [ ] | |
| **12** | **WhatsApp व ईमेल संदेश** | 'अनसब्सक्राइब करने के लिए STOP लिखें' अनुपालन पाद लेख | [ ] | |

**Hindi Reviewer Signature**: _________________________________  
**Date**: ____________________________________________________
