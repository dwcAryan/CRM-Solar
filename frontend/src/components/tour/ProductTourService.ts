import { driver, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import './productTour.css';
import { TOUR_DEFINITIONS } from '../../tours/tourDefinitions';
import { updateTourState } from '../../api/client';

let activeDriver: Driver | null = null;

export const isTourActive = (): boolean => {
  return activeDriver !== null && activeDriver.isActive();
};

export const stopTour = () => {
  if (activeDriver) {
    activeDriver.destroy();
    activeDriver = null;
  }
};

export const startTour = (tourId: string = 'complete', onFinish?: () => void) => {
  stopTour();

  const tourDef = TOUR_DEFINITIONS[tourId] || TOUR_DEFINITIONS.complete;
  if (!tourDef || !tourDef.steps.length) {
    console.warn(`Tour definition not found for id: ${tourId}`);
    return;
  }

  // Filter steps whose target elements exist in DOM
  const availableSteps = tourDef.steps.filter(step => {
    if (!step.element) return true;
    const el = document.querySelector(step.element as string);
    return !!el;
  });

  if (!availableSteps.length) {
    console.warn(`No target elements found in DOM for tour: ${tourId}`);
    return;
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
      activeDriver = null;
      driverObj.destroy();
      // Record completed tour on server
      updateTourState({
        has_seen_tour: true,
        completed_tours: [tourId],
      }).catch(err => console.error('Failed to save tour state:', err));

      if (onFinish) onFinish();
    },
    steps: availableSteps,
  });

  activeDriver = driverObj;
  driverObj.drive();
};
