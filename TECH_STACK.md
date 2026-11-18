# Solar CRM - Technical Stack & Dependency Manifest

This document provides a comprehensive inventory of all technologies, libraries, and frameworks utilized across the Solar CRM platform, including versions, architectural roles, licenses, and environment configuration parameters.

---

## 1. Backend Python Libraries (`backend/requirements.txt`)

| Package | Version Spec | Purpose in Solar CRM | License |
|:---|:---|:---|:---|
| **Django** | `>=5.1,<6.0` | Core web framework, ORM, transaction management, migration engine, and admin back-office. | BSD 3-Clause |
| **djangorestframework** | `>=3.15.0` | REST API framework providing viewsets, serializers, pagination, filtering, and HTTP response handling. | BSD 3-Clause |
| **djangorestframework-simplejwt** | `>=5.3.0` | JSON Web Token (JWT) authentication, access/refresh token generation, and token rotation. | MIT |
| **drf-spectacular** | `>=0.27.0` | OpenAPI 3.0 schema generation and interactive Swagger UI / ReDoc sandbox. | BSD 3-Clause |
| **django-cors-headers** | `>=4.3.0` | Cross-Origin Resource Sharing (CORS) headers middleware for frontend communication. | MIT |
| **django-filter** | `>=24.0` | Declarative filtering for REST API endpoints by status, assignee, region, and dates. | BSD 3-Clause |
| **apscheduler** | `>=3.10.0` | Advanced Python Scheduler running background reminder cron jobs (9 AM follow-ups, 6 PM surveys). | MIT |
| **python-dotenv** | `>=1.0.0` | Loads environment variables from `backend/.env` into system settings. | BSD 3-Clause |
| **psycopg[binary]** | `>=3.1.0` | PostgreSQL database driver and connection pooler. | LGPL 3.0+ |
| **pytest** | `>=8.0.0` | Modern Python test runner for unit, integration, and API test suites. | MIT |
| **pytest-django** | `>=4.8.0` | Pytest fixtures and database test isolation for Django applications. | BSD 3-Clause |
| **pytest-xdist** | `>=3.5.0` | Multi-core parallel execution plugin for pytest. | MIT |
| **factory-boy** | `>=3.3.0` | Test data and fixture generation for users, regions, leads, surveys, and quotes. | MIT |
| **time-machine** | `>=2.14.0` | Time mocking library to simulate time-of-day execution for APScheduler tests. | MIT |
| **ruff** | `>=0.3.0` | Extremely fast Python linter and code quality validator. | MIT |
| **pillow** | `>=10.0.0` | Image processing library for uploaded rooftop site survey photos. | HPND / PIL |
| **openpyxl** | `>=3.1.0` | Reads and parses Microsoft Excel (`.xlsx`) files for bulk lead importing. | MIT |
| **anthropic** | `>=0.40.0` | Official Anthropic SDK for Claude AI suggestion generation. | MIT |
| **phonenumbers** | `>=8.13.0` | Google libphonenumber Python port for international E.164 phone normalization and validation. | Apache 2.0 |
| **tzdata** | `>=2024.1` | IANA standard time zone database supporting Indian (`Asia/Kolkata`) and Australian zones. | Public Domain / Apache 2.0 |
| **reportlab** | `>=4.2.0` | PDF document generation engine for downloading customer solar proposals. | BSD 3-Clause |

---

## 2. Frontend NPM Packages (`frontend/package.json`)

### Runtime Dependencies
| Package | Version | Purpose in Solar CRM | License |
|:---|:---|:---|:---|
| **react** | `^19.3.1` | Modern component-based declarative UI library. | MIT |
| **react-dom** | `^19.3.1` | React DOM renderer for web browser environments. | MIT |
| **react-router-dom** | `^7.18.5` | Declarative client-side routing, protected routes, and role-based redirects. | MIT |
| **@mantine/core** | `^9.8.1` | Polished accessible UI library (Inputs, Buttons, Cards, Modals, Badges, Tables). | MIT |
| **@mantine/dates** | `^9.8.1` | Date and time pickers, calendar widgets for follow-up and survey scheduling. | MIT |
| **@mantine/hooks** | `^9.8.1` | React hooks for responsive breakpoints, local storage, and modal states. | MIT |
| **@mantine/notifications** | `^9.8.1` | User notification manager for floating toast alerts and error notices. | MIT |
| **@tabler/icons-react** | `^3.52.0` | Icon set for navigation, actions, phone, calendar, and solar equipment. | MIT |
| **@tanstack/react-query** | `^5.107.2` | Server-state caching, background refetching, and optimistic mutations. | MIT |
| **axios** | `^1.21.1` | HTTP client with automatic JWT token refresh interceptors. | MIT |
| **dayjs** | `^1.11.23` | Date formatting and manipulation library. | MIT |

### Development & Tooling Dependencies
| Package | Version | Purpose in Solar CRM | License |
|:---|:---|:---|:---|
| **vite** | `^8.3.6` | Ultra-fast development server and optimized production build engine. | MIT |
| **@vitejs/plugin-react** | `^6.1.2` | Fast Refresh plugin for React in Vite. | MIT |
| **typescript** | `~7.0.2` | Static type checker for JavaScript. | Apache 2.0 |
| **@types/react** | `^19.3.0` | TypeScript definitions for React. | MIT |
| **@types/react-dom** | `^19.3.0` | TypeScript definitions for React DOM. | MIT |
| **@types/node** | `^24.19.2` | TypeScript definitions for Node.js APIs. | MIT |
| **@playwright/test** | `^1.65.1` | Browser end-to-end automation and testing framework. | Apache 2.0 |
| **oxlint** | `^1.90.0` | High-performance JavaScript/TypeScript linter. | MIT |

---

## 3. Core Environment Configurations & Feature Flags

Configured in `backend/.env` (and documented in `backend/.env.example`):

### Country and Multi-Region Controls
* **`ENABLED_COUNTRIES`**
  - **Default**: `IN,AU`
  - **Values**: Comma-separated ISO 3166-1 alpha-2 country codes (e.g. `IN`, `AU`, or `IN,AU`).
  - **Function**: Restricts active regions across the entire CRM. When set to `IN`, only Indian states, INR currency (₹), 5% solar GST, and DISCOM utilities are shown. When set to `AU`, only Australian states, AUD ($), 10% inclusive GST, and CEC STC rebate calculations are shown. When set to `IN,AU`, users with multi-region privileges can seamlessly switch between both markets.

### Messaging and Communication Gateways
* **`SMS_PROVIDER`**
  - **Default**: `console`
  - **Values**: `console`, `twilio`
  - **Function**: Selects the active SMS dispatch engine. In `console` mode, outgoing SMS notifications are printed to terminal logs and recorded in the database `MessageLog` table. In `twilio` mode, messages are dispatched via the Twilio REST API.
* **`WHATSAPP_PROVIDER`**
  - **Default**: `console`
  - **Values**: `console`, `whatsapp_cloud`
  - **Function**: Selects the WhatsApp messaging provider for automated survey reminders and quote notifications. Never sends messages to leads flagged with `do_not_contact=True`.

### AI Assistance and Recommendation Controls
* **`AI_PROVIDER`**
  - **Default**: `rules`
  - **Values**: `rules`, `anthropic`
  - **Function**: `rules` provides instant, deterministic suggestions derived from status history and activity rules without cost or external dependencies. `anthropic` activates Claude AI via the official Anthropic Messages SDK.
* **`ANTHROPIC_API_KEY`**: API key for Anthropic Claude (kept blank when using `rules`).
* **`AI_MODEL`**: Model identifier (default: `claude-sonnet-5-5`).
* **`AI_TIMEOUT_SECONDS`**: Maximum API request timeout in seconds (default: `15`).
* **`AI_MAX_CALLS_PER_USER_PER_DAY`**: Rate limit safeguard per user per day (default: `50`).
