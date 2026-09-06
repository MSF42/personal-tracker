import {
    CategoryScale,
    Chart,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';

let registered = false;

/** Register the Chart.js pieces the app's line charts need. Safe to call repeatedly. */
export function registerCharts(): void {
    if (registered) return;
    registered = true;
    Chart.register(
        CategoryScale,
        Filler,
        Legend,
        LinearScale,
        LineController,
        LineElement,
        PointElement,
        Title,
        Tooltip,
    );
}
