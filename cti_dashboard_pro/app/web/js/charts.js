/**
 * Premium Charting Logic using Chart.js
 */

export const charts = {
    instances: {},

    /**
     * Initialize or update a performance chart
     */
    render: (id, data, title, xMin, xMax, yMin, yMax, isPrint = false) => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const textColor = isPrint ? '#000000' : 'rgba(255, 255, 255, 0.9)';
        const gridColor = isPrint ? 'rgba(0, 0, 0, 0.2)' : 'rgba(148, 163, 184, 0.15)';
        const labelColor = isPrint ? '#000000' : '#94a3b8';

        // Create Gradients (Subtle for print, vanished for clear vector)
        const gradient80 = ctx.createLinearGradient(0, 0, 0, 400);
        gradient80.addColorStop(0, isPrint ? 'rgba(16, 185, 129, 0.05)' : 'rgba(16, 185, 129, 0.2)');
        gradient80.addColorStop(1, 'rgba(16, 185, 129, 0)');

        const gradient100 = ctx.createLinearGradient(0, 0, 0, 400);
        gradient100.addColorStop(0, isPrint ? 'rgba(6, 182, 212, 0.05)' : 'rgba(6, 182, 212, 0.2)');
        gradient100.addColorStop(1, 'rgba(6, 182, 212, 0)');

        const gradient120 = ctx.createLinearGradient(0, 0, 0, 400);
        gradient120.addColorStop(0, isPrint ? 'rgba(245, 158, 11, 0.05)' : 'rgba(245, 158, 11, 0.2)');
        gradient120.addColorStop(1, 'rgba(245, 158, 11, 0)');

        if (charts.instances[id]) {
            charts.instances[id].destroy();
        }

        const config = {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Range 80%',
                        data: data.map(p => ({ x: p.wbt, y: p.range80 })),
                        borderColor: '#10B981',
                        backgroundColor: gradient80,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0,
                        tension: 0.4
                    },
                    {
                        label: 'Range 100%',
                        data: data.map(p => ({ x: p.wbt, y: p.range100 })),
                        borderColor: '#06B6D4',
                        backgroundColor: gradient100,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0,
                        tension: 0.4
                    },
                    {
                        label: 'Range 120%',
                        data: data.map(p => ({ x: p.wbt, y: p.range120 })),
                        borderColor: '#F59E0B',
                        backgroundColor: gradient120,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                layout: {
                    padding: isPrint ? {
                        top: 20,
                        right: 30,
                        bottom: 40,
                        left: 60 /* More space for Y-axis title/ticks */
                    } : 15
                },
                plugins: {
                    title: {
                        display: true,
                        text: title.toUpperCase(),
                        color: textColor,
                        font: { size: 16, weight: '900', family: "'Inter', sans-serif" },
                        padding: { bottom: 20 }
                    },
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: {
                            color: labelColor,
                            usePointStyle: true,
                            font: { size: 12, weight: 'bold', family: "'Inter', sans-serif" }
                        }
                    },
                    tooltip: { enabled: !isPrint }
                },
                scales: {
                    x: {
                        type: 'linear',
                        min: xMin,
                        max: xMax,
                        title: {
                            display: true,
                            text: 'WET BULB TEMPERATURE (°C)',
                            color: labelColor,
                            font: { size: 10, weight: 'bold', family: "'Inter', sans-serif" }
                        },
                        grid: { color: gridColor, drawBorder: true, borderColor: labelColor },
                        ticks: {
                            color: labelColor,
                            stepSize: 1,
                            font: { size: 10, weight: 'bold', family: "'JetBrains Mono', monospace" }
                        }
                    },
                    y: {
                        min: yMin,
                        max: yMax,
                        title: {
                            display: true,
                            text: 'COLD WATER TEMPERATURE (°C)',
                            color: labelColor,
                            font: { size: 10, weight: 'bold', family: "'Inter', sans-serif" }
                        },
                        grid: { color: gridColor, drawBorder: true, borderColor: labelColor },
                        ticks: {
                            color: labelColor,
                            stepSize: 1,
                            font: { size: 10, weight: 'bold', family: "'JetBrains Mono', monospace" }
                        }
                    }
                }
            }
        };

        charts.instances[id] = new Chart(ctx, config);
    }
};
