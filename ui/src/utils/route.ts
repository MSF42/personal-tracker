/**
 * Geometry helpers for drawing a recorded route without a map library:
 * an equirectangular projection fitted into a box, as an SVG path.
 */

import type { RunSample } from '@/types/Running';

export interface LatLon {
    lat: number;
    lon: number;
}

/** A positioned sample with its offset (seconds) from the run start. */
export interface TrackPoint extends LatLon {
    t: number;
}

export interface TimeRange {
    start: number;
    end: number;
}

/** The slice of a track inside [start, end] seconds (inclusive), in order. */
export function sliceByTime<T extends { t: number }>(
    points: T[],
    range: TimeRange | null | undefined,
): T[] {
    if (!range) return [];
    return points.filter((p) => p.t >= range.start && p.t <= range.end);
}

export interface Point {
    x: number;
    y: number;
}

export interface ProjectedTrack {
    path: string;
    start: Point | null;
    end: Point | null;
    /** Project any lat/lon with the same transform (for overlays). */
    project: (p: LatLon) => Point;
}

/** Samples that carry a GPS position, in order. */
export function routePoints(samples: RunSample[]): TrackPoint[] {
    return samples
        .filter((s) => s.lat != null && s.lon != null)
        .map((s) => ({
            lat: s.lat as number,
            lon: s.lon as number,
            t: s.t_seconds,
        }));
}

export function hasRoute(samples: RunSample[]): boolean {
    return routePoints(samples).length >= 2;
}

/**
 * Project lat/lon points into a width × height box, preserving aspect ratio.
 * Longitude is scaled by cos(mean latitude) so shapes are not stretched.
 */
export function projectTrack(
    points: LatLon[],
    width: number,
    height: number,
    padding = 8,
): ProjectedTrack {
    if (points.length < 2) {
        return {
            path: '',
            start: null,
            end: null,
            project: () => ({ x: 0, y: 0 }),
        };
    }

    const meanLat = points.reduce((sum, p) => sum + p.lat, 0) / points.length;
    const kx = Math.cos((meanLat * Math.PI) / 180);

    const xs = points.map((p) => p.lon * kx);
    const ys = points.map((p) => p.lat);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const spanX = maxX - minX || 1e-9;
    const spanY = maxY - minY || 1e-9;
    const innerW = Math.max(1, width - 2 * padding);
    const innerH = Math.max(1, height - 2 * padding);
    const scale = Math.min(innerW / spanX, innerH / spanY);

    // Centre the fitted track inside the box.
    const offsetX = padding + (innerW - spanX * scale) / 2;
    const offsetY = padding + (innerH - spanY * scale) / 2;

    const project = (p: LatLon): Point => ({
        x: round(offsetX + (p.lon * kx - minX) * scale),
        // SVG y grows downwards; north should be up.
        y: round(offsetY + (maxY - p.lat) * scale),
    });

    const projected = points.map(project);
    const path = projected
        .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x} ${p.y}`)
        .join(' ');

    return {
        path,
        start: projected[0] ?? null,
        end: projected[projected.length - 1] ?? null,
        project,
    };
}

/** SVG path for a list of already-projected points. */
export function pathFor(points: Point[]): string {
    return points
        .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x} ${p.y}`)
        .join(' ');
}

function round(n: number): number {
    return Math.round(n * 100) / 100;
}
