export function intToBool(value: number | null | undefined): boolean {
    return value === 1;
}

export function boolToInt(value: boolean | null | undefined): number {
    return value ? 1 : 0;
}

export function nowIso(): string {
    return new Date().toISOString();
}

export function calculateRunningMetrics(
    duration_seconds: number,
    distance_km: number,
): { pace: number; speed: number; pace_formatted: string } {
    if (distance_km <= 0 || duration_seconds <= 0) {
        return { pace: 0, speed: 0, pace_formatted: '0:00' };
    }
    const pace = duration_seconds / 60 / distance_km;
    const speed = distance_km / (duration_seconds / 3600);
    const minutes = Math.floor(pace);
    const seconds = Math.floor((pace % 1) * 60);
    return {
        pace,
        speed,
        pace_formatted: `${minutes}:${String(seconds).padStart(2, '0')}`,
    };
}

export function repeatDaysToString(
    days: number[] | null | undefined,
): string | null {
    if (!days || days.length === 0) return null;
    return days.join(',');
}

export function repeatDaysFromString(
    str: string | null | undefined,
): number[] | null {
    if (!str) return null;
    return str.split(',').map(Number);
}
