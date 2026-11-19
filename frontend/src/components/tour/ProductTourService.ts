import { driver, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import './productTour.css';
import { TOUR_DEFINITIONS } from '../../tours/tourDefinitions';
import { updateTourState } from '../../api/client';

let activeDriver: Driver | null = null;
let startingTour = false;

export const isTourActive = (): boolean => {
  return (activeDriver !== null && activeDriver.isActive()) || startingTour;
};

export const stopTour = () => {
  startingTour = false;
  if (activeDriver) {
    try {
      activeDriver.destroy();
    } catch {
      // ignore
    }
    activeDriver = null;
  }
};

export const startTour = (tourId: string = 'complete', onFinish?: () => void) => {
  stopTour();
  startingTour = true;

  const tourDef = TOUR_DEFINITIONS[tourId] || TOUR_DEFINITIONS.complete;
  if (!tourDef || !tourDef.steps.length) {
    startingTour = false;
    return;
  }

  // Filter steps whose target elements exist in DOM
  const availableSteps = tourDef.steps.filter(step => {
    if (!step.element) return true;
    const el = document.querySelector(step.element as string);
    return !!el;
  });

  if (!availableSteps.length) {
    startingTour = false;
    return;
  }

  // Immediately persist seen status so reloads or races don't trigger the tour again
  try {
    localStorage.setItem('solar_crm_has_seen_tour', 'true');
    updateTourState({
      has_seen_tour: true,
    }).catch(() => {});
  } catch {
    // ignore
  }

  const driverObj = driver({
    showProgress: true,
    animate: true,
    allowClose: true,
    overlayColor: 'rgba(15, 23, 42, 0.65)',
    popoverClass: 'solar-tour-popover',
    nextBtnText: 'Continue →',
    prevBtnText: '← Back',
    doneBtnText: 'Finish',
    progressText: '{{current}} of {{total}}',
    onDestroyStarted: () => {
      const wasCompleted = driverObj.isLastStep();
      startingTour = false;
      activeDriver = null;
      driverObj.destroy();
      try {
        localStorage.setItem('solar_crm_has_seen_tour', 'true');
        if (wasCompleted) {
          updateTourState({
            has_seen_tour: true,
            completed_tours: [tourId],
          }).catch(err => console.error('Failed to save tour state:', err));
          import('../../api/client').then(({ recordOnboardingEvent }) => {
            recordOnboardingEvent('tour').catch(() => {});
          });
        }
      } catch {
        // ignore
      }

      if (onFinish) onFinish();
    },
    steps: availableSteps,
  });

  activeDriver = driverObj;
  driverObj.drive();
  startingTour = false;
};
