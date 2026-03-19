/**
 * Calculation Core for Cooling Tower Performance
 * Includes Psychrometric properties and Merkel Method (CTI ATC 105)
 */

import { psychrometrics, initPsychroEngine } from './psychro-engine.js';
import { merkelKaVL, initMerkelEngine } from './merkel-engine.js';

export const calculations = {
    init: async (psychroLibPath = './data/psychro_f_alt.bin', merkelLibPath = './data/merkel_poly.bin') => {
        await Promise.all([
            initPsychroEngine(psychroLibPath),
            initMerkelEngine(merkelLibPath)
        ]);
    },

    /**
     * Psychrometric properties calculation using the new engine
     */
    getPsychrometricProps: (twb) => {
        try {
            const props = psychrometrics(twb, twb);
            return { ws: props.HR, hs: props.H, pws: props.P };
        } catch (e) {
            return { ws: 0, hs: 0, pws: 0 };
        }
    },

    /**
     * CTI Merkel demand calculation using new merkelKaVL engine
     */
    calculateDemandKaVL: (twb, hwt, cwt, lgRatio) => {
        try {
            const result = merkelKaVL(hwt, cwt, twb, lgRatio);
            if (result && result.valid) {
                return result.kavl;
            }
            return NaN;
        } catch (e) {
            return NaN;
        }
    },

    calculateSupplyKaVL: (lgRatio, constantC, constantM) => {
        return constantC * Math.pow(lgRatio, -constantM);
    },

    /**
     * Find CWT for given WBT and range percentage
     */
    findCWT: (inputs, wbt, rangePercent, flowPercent) => {
        const designRange = inputs.designHWT - inputs.designCWT;
        const actualRange = designRange * rangePercent / 100;
        const actualLG = inputs.lgRatio * (flowPercent / 100);

        const supplyKaVL = calculations.calculateSupplyKaVL(actualLG, inputs.constantC, inputs.constantM);

        let bestCWT = wbt + 1;
        let minDiff = Infinity;
        let lowApproach = 0.01;
        let highApproach = 80.0;
        const tolerance = 1e-7;

        for (let i = 0; i < 100; i++) {
            let midApproach = (lowApproach + highApproach) / 2;
            let cwtGuess = wbt + midApproach;
            let hwt = cwtGuess + actualRange;

            let demandKaVL;
            try {
                demandKaVL = calculations.calculateDemandKaVL(wbt, hwt, cwtGuess, actualLG);
            } catch (e) { demandKaVL = NaN; }
            
            if (isNaN(demandKaVL) || demandKaVL <= 0) {
                lowApproach = midApproach;
                continue;
            }

            let diff = demandKaVL - supplyKaVL;
            let absDiff = Math.abs(diff);

            if (absDiff < minDiff) {
                minDiff = absDiff;
                bestCWT = cwtGuess;
            }

            if (absDiff < tolerance) {
                break;
            }

            if (diff > 0) {
                lowApproach = midApproach;
            } else {
                highApproach = midApproach;
            }
        }

        return bestCWT;
    },

    /**
     * Solves for the predicted CWT (Performance Prediction Off-Design capability)
     * Given WBT, Range, L/G, C, and m, find the CWT that balances Demand/Supply
     */
    solveOffDesignCWT: (wbt, range, lg, constC, constM) => {
        // First get the physical tower's supply capability
        const supplyKavl = calculations.calculateSupplyKaVL(lg, constC, constM);
        if (isNaN(supplyKavl) || supplyKavl <= 0) {
            return null;
        }

        // We use Bisection Method to find the approach where Demand equals Supply
        // The relationship is invariant: HWT = CWT + Range 
        let lowApproach = 0.01;
        let highApproach = 80.0;
        let bestCwt = NaN;
        let bestDiff = Infinity;
        let matchedDemand = NaN;
        const tolerance = 1e-7;
        const maxIters = 100;
        
        for (let i = 0; i < maxIters; i++) {
            let midApproach = (lowApproach + highApproach) / 2;
            let guessCwt = wbt + midApproach;
            let guessHwt = guessCwt + range;

            let demandKavl;
            try {
                demandKavl = calculations.calculateDemandKaVL(wbt, guessHwt, guessCwt, lg);
            } catch (e) {
                demandKavl = NaN;
            }
            
            if (isNaN(demandKavl) || demandKavl <= 0) {
                // Invalid usually means approach is too low (Demand shoots to infinity)
                lowApproach = midApproach;
                continue;
            }

            let diff = demandKavl - supplyKavl;
            let absDiff = Math.abs(diff);

            if (absDiff < bestDiff) {
                bestDiff = absDiff;
                bestCwt = guessCwt;
                matchedDemand = demandKavl;
            }

            if (absDiff < tolerance) {
                break;
            }

            if (diff > 0) {
                // Demand is higher than Supply. Need more driving force -> increase temperatures (approach).
                lowApproach = midApproach;
            } else {
                // Demand is lower than Supply. Need less driving force -> decrease temperatures (approach).
                highApproach = midApproach;
            }
        }

        if (isNaN(bestCwt) || bestDiff > 0.5) return null; // Unsolvable

        return {
            cwt: bestCwt,
            approach: bestCwt - wbt,
            hwt: bestCwt + range,
            demandKavl: matchedDemand,
            supplyKavl: supplyKavl
        };
    }
};
