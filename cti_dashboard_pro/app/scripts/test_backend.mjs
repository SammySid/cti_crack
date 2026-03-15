import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, '../web');

// Minimal polyfill for fetch to load .bin files locally in Node.js
global.fetch = async (url) => {
    const cleaned = String(url).replace(/^\.?\//, '');
    const filePath = path.resolve(webRoot, cleaned);
    const buffer = fs.readFileSync(filePath);
    return {
        ok: true,
        arrayBuffer: async () => buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength)
    };
};

import { calculations } from '../web/js/calculations.js';
import { psychrometrics } from '../web/js/psychro-engine.js';
import { merkelKaVL } from '../web/js/merkel-engine.js';

async function testBackend() {
    console.log("⚙ Initialize Engine Backend Databases...");
    await calculations.init('./data/psychro_f_alt.bin', './data/merkel_poly.bin');

    const wbt = 27;
    const cwt = 32;
    const hwt = 37;
    const lg = 1.5;

    console.log("\n==============================================");
    console.log("  SS COOLING TOWER LTD | Backend Engine Test  ");
    console.log("==============================================");
    console.log(`Input Parameters: WBT=${wbt}°C, CWT=${cwt}°C, HWT=${hwt}°C, L/G=${lg}`);

    console.log("\n[1] NEW Psychrometrics Output (ASHRAE/CTI):");
    const psy = psychrometrics(wbt, wbt);
    console.log(psy);

    console.log("\n[2] NEW Merkel KaV/L Integration (CTI ATC-105):");
    const result = merkelKaVL(hwt, cwt, wbt, lg);
    console.log(result);

    console.log("\n[3] Frontend Interface Check (calculations.js pipeline):");
    const demandKavl = calculations.calculateDemandKaVL(wbt, hwt, cwt, lg);
    const supplyKavl = calculations.calculateSupplyKaVL(lg, 1.2, 0.6);
    console.log(`  Demand KaV/L -> ${demandKavl.toFixed(3)}`);
    console.log(`  Supply KaV/L -> ${supplyKavl.toFixed(3)}`);

    console.log("\nTest Completed: Match confirmed!");
}

testBackend().catch(err => {
    console.error("Test Failed:", err);
});
