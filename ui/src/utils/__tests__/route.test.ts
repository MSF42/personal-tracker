import { describe, expect, it } from 'vitest';

import type { RunSample } from '@/types/Running';

import { hasRoute, projectTrack, routePoints, sliceByTime } from '../route';

const square = [
    { lat: 0, lon: 0 },
    { lat: 0, lon: 0.01 },
    { lat: 0.01, lon: 0.01 },
    { lat: 0.01, lon: 0 },
];

function coords(path: string): number[][] {
    return path
        .split(' ')
        .join(' ')
        .match(/[ML]([\d.]+) ([\d.]+)/g)!
        .map((m) => m.slice(1).split(' ').map(Number));
}

describe('projectTrack', () => {
    it('returns nothing for fewer than two points', () => {
        expect(projectTrack([], 100, 100)).toMatchObject({
            path: '',
            start: null,
            end: null,
        });
        expect(projectTrack([{ lat: 1, lon: 1 }], 100, 100).path).toBe('');
    });

    it('fits a square track inside the box with padding', () => {
        const { path, start, end } = projectTrack(square, 200, 100, 10);
        const pts = coords(path);
        for (const [x, y] of pts) {
            expect(x!).toBeGreaterThanOrEqual(10);
            expect(x!).toBeLessThanOrEqual(190);
            expect(y!).toBeGreaterThanOrEqual(10);
            expect(y!).toBeLessThanOrEqual(90);
        }
        // Square stays square: limited by the 80px height, centred horizontally.
        const xs = pts.map((p) => p[0]!);
        const ys = pts.map((p) => p[1]!);
        expect(Math.max(...xs) - Math.min(...xs)).toBeCloseTo(80, 5);
        expect(Math.max(...ys) - Math.min(...ys)).toBeCloseTo(80, 5);
        expect(Math.min(...xs)).toBeCloseTo(60, 5);
        expect(start).toEqual(pts[0] && { x: pts[0][0], y: pts[0][1] });
        expect(end).toEqual(pts[3] && { x: pts[3][0], y: pts[3][1] });
    });

    it('puts north at the top', () => {
        const { start, end } = projectTrack(
            [
                { lat: 0, lon: 0 },
                { lat: 1, lon: 0 },
            ],
            100,
            100,
            0,
        );
        expect(start!.y).toBeGreaterThan(end!.y);
    });

    it('narrows longitude at high latitude', () => {
        // One degree of longitude near 60°N is about half as wide as at the equator.
        const equator = projectTrack(
            [
                { lat: 0, lon: 0 },
                { lat: 0.5, lon: 1 },
            ],
            100,
            100,
            0,
        );
        const north = projectTrack(
            [
                { lat: 60, lon: 0 },
                { lat: 60.5, lon: 1 },
            ],
            100,
            100,
            0,
        );
        // Equator track is wider than tall (fills width); the northern one is
        // roughly square so it fills height and is narrower.
        const width = (t: typeof equator) => Math.abs(t.end!.x - t.start!.x);
        expect(width(north)).toBeLessThan(width(equator));
    });

    it('handles identical points without dividing by zero', () => {
        const { path } = projectTrack(
            [
                { lat: 5, lon: 5 },
                { lat: 5, lon: 5 },
            ],
            100,
            100,
        );
        expect(path).not.toContain('NaN');
    });
});

describe('routePoints / hasRoute', () => {
    const sample = (lat: number | null, lon: number | null): RunSample => ({
        t_seconds: 0,
        distance_km: null,
        heart_rate: null,
        cadence: null,
        speed_mps: null,
        altitude_m: null,
        power: null,
        lat,
        lon,
    });

    it('keeps only samples with a position', () => {
        const pts = routePoints([sample(1, 2), sample(null, 2), sample(3, 4)]);
        expect(pts).toEqual([
            { lat: 1, lon: 2, t: 0 },
            { lat: 3, lon: 4, t: 0 },
        ]);
        expect(hasRoute([sample(1, 2), sample(null, null)])).toBe(false);
        expect(hasRoute([sample(1, 2), sample(3, 4)])).toBe(true);
    });
});

describe('sliceByTime', () => {
    const pts = [0, 10, 20, 30, 40].map((t) => ({ t }));

    it('returns the inclusive slice for a range', () => {
        expect(
            sliceByTime(pts, { start: 10, end: 30 }).map((p) => p.t),
        ).toEqual([10, 20, 30]);
    });

    it('returns nothing without a range', () => {
        expect(sliceByTime(pts, null)).toEqual([]);
    });
});
