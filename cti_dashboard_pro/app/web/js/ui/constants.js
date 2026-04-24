export const INPUT_IDS = [
    'companyName', 'engineerName', 'projectName', 'date', 'lgRatio',
    'designWBT', 'designCWT', 'designHWT', 'designWaterFlow',
    'constantC', 'constantM', 'axXMin', 'axXMax', 'axYMin', 'axYMax',
    'offsetWbt20', 
    'off90r80', 'off90r100', 'off90r120',
    'off100r80', 'off100r100', 'off100r120',
    'off110r80', 'off110r100', 'off110r120'
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
    'off90r80', 'off90r100', 'off90r120',
    'off100r80', 'off100r100', 'off100r120',
    'off110r80', 'off110r100', 'off110r120'
];

export function isCurveAffectingInput(id) {
    return CURVE_INPUT_IDS.includes(id);
}
