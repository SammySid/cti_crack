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

        for (let approach = 0.5; approach < 30; approach += 0.02) {
            const cwtGuess = wbt + approach;
            const hwt = cwtGuess + actualRange;

            if (hwt > 80 || cwtGuess < wbt) continue;

            try {
                const demandKaVL = calculations.calculateDemandKaVL(wbt, hwt, cwtGuess, actualLG);
                if (isNaN(demandKaVL) || demandKaVL <= 0 || demandKaVL > 100) continue;

                const diff = Math.abs(supplyKaVL - demandKaVL);
                if (diff < minDiff) {
                    minDiff = diff;
                    bestCWT = cwtGuess;
                }
            } catch (e) {
                continue;
            }
        }

        return bestCWT;
    }
};
