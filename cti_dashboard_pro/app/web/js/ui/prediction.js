export async function calculatePrediction(ui) {
    // Only calculate if all inputs are valid numbers
    const wbt = parseFloat(document.getElementById('pred-wbt').value);
    const range = parseFloat(document.getElementById('pred-range').value);
    const lg = parseFloat(document.getElementById('pred-lg').value);
    const constC = parseFloat(document.getElementById('pred-c').value);
    const constM = parseFloat(document.getElementById('pred-m').value);

    const inputsValid = [wbt, range, lg, constC, constM].every(val => Number.isFinite(val));
    if (!inputsValid) return; // Wait for valid input

    try {
        const response = await fetch('/api/calculate/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wbt: wbt,
                range: range,
                lg: lg,
                constC: constC,
                constM: constM
            })
        });

        if (!response.ok) throw new Error();
        
        const result = await response.json();

        if (result && result.cwt) {
            document.getElementById('pred-out-cwt').innerText = result.cwt.toFixed(2);
            document.getElementById('pred-out-app').innerText = result.approach.toFixed(2);
            document.getElementById('pred-out-hwt').innerText = result.hwt.toFixed(2) + '°C';
            document.getElementById('pred-out-demand').innerText = result.demandKavl.toFixed(4);
            document.getElementById('pred-out-supply').innerText = result.supplyKavl.toFixed(4);
        }
    } catch(err) {
        document.getElementById('pred-out-cwt').innerText = "ERR";
        document.getElementById('pred-out-app').innerText = "ERR";
        document.getElementById('pred-out-hwt').innerText = "--";
        document.getElementById('pred-out-demand').innerText = "--";
        document.getElementById('pred-out-supply').innerText = "--";
    }
}
