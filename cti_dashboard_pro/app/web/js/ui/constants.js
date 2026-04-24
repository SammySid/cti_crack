export const INPUT_IDS = [
    'companyName', 'engineerName', 'projectName', 'date', 'lgRatio',
    'designWBT', 'designCWT', 'designHWT', 'designWaterFlow',
    'constantC', 'constantM', 'axXMin', 'axXMax', 'axYMin', 'axYMax',
    'offsetWbt20', 'offsetRange80', 'offsetRange120', 'offsetFlow90', 'offsetFlow110'
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
    'axYMax',
    'offsetWbt20', 
    'offsetRange80', 
    'offsetRange120', 
    'offsetFlow90', 
    'offsetFlow110'
];

export function isCurveAffectingInput(id) {
    return CURVE_INPUT_IDS.includes(id);
}
