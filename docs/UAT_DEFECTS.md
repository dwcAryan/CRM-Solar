# Solar CRM - User Acceptance Testing (UAT) Defect Log

- **Phase**: Phase 17 - User Acceptance Testing (UAT)
- **Date**: November 19, 2026
- **Status**: ALL DEFECTS RESOLVED (0 Open Defects)

---

## Remediated Defects Summary

| Defect ID | Title / Description | Severity | Component | Root Cause | Fix Applied | Regression Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | `OnboardingState` TypeScript Interface Stripping in Vite | **Medium** | Frontend / Onboarding | `import { OnboardingState }` in `GetStartedChecklist.tsx` was treated as an ES module value at runtime, throwing `does not provide an export named 'OnboardingState'` and halting checklist rendering. | Changed to `import { type OnboardingState }` in `frontend/src/components/tour/GetStartedChecklist.tsx`. | `frontend/tests/onboarding_latch.spec.ts` |
| **DEF-002** | Playwright Mock Route CORS Missing Origin Header | **Low** | Tests / Mocking | In Playwright test interceptor for onboarding latch, `route.fulfill` lacked `Access-Control-Allow-Origin`, leading to preflight rejection in mocked tests. | Added `CORS_HEADERS` with allowed methods and origins in `onboarding_latch.spec.ts`. | `frontend/tests/onboarding_latch.spec.ts` |
| **DEF-003** | Product Tour Early Exit Prematurely Ticking Tour Item | **Low** | Frontend / Tour Service | `ProductTourService.ts` called `updateTourState` with `completed_tours` upon `onDestroyStarted` even if the user closed the tour early or pressed Escape. | Updated `onDestroyStarted` to verify `driverObj.isLastStep()` before recording completion; ending early records seen status without completion latch. | `frontend/tests/onboarding_latch.spec.ts` |
| **DEF-004** | Missing Server-Side Onboarding Completion Latch | **Medium** | Backend / Accounts | The onboarding checklist was originally tracking completion solely in local React state, risking reappearance on other devices, incognito windows, or session resets. | Implemented `UserOnboardingState` server-side model with permanent `completed_at` latch, `/api/me/onboarding/` API, and zero-flicker loading. | `backend/tests/test_phase17_onboarding_latch.py` |

---

## Open Defects
**None**. All 147 automated scenarios passed cleanly across 4 workers (100% pass rate).
