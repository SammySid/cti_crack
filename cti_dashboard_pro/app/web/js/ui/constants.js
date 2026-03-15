export const INPUT_IDS = [
    'companyName', 'engineerName', 'projectName', 'date', 'lgRatio',
    'designWBT', 'designCWT', 'designHWT', 'designWaterFlow',
    'constantC', 'constantM', 'axXMin', 'axXMax', 'axYMin', 'axYMax'
];

export const CURVE_INPUT_IDS = [
    'lgRatio',
    'designWBT',
    'designCWT',
    'designHWT',
    'designWaterFlow',
    'constantC',
    'constantM',
    'axXMin',
    'axXMax',
    'axYMin',
    'axYMax'
];

export function isCurveAffectingInput(id) {
    return CURVE_INPUT_IDS.includes(id);
}
