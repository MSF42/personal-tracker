import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUnits } from '../useUnits';

vi.mock('@/composables/api/useSettingsApi', () => ({
    useSettingsApi: () => ({
        getSetting: vi.fn().mockResolvedValue({ success: false }),
        setSetting: vi.fn().mockResolvedValue({ success: true }),
    }),
}));

describe('useUnits', () => {
    let units: ReturnType<typeof useUnits>;

    beforeEach(() => {
        units = useUnits();
        // Reset module-level shared state between tests
        units.distanceUnit.value = 'km';
        units.weightUnit.value = 'kg';
    });

    // --- fmtDistance ---

    describe('fmtDistance', () => {
        it('formats km correctly when unit is km', () => {
            units.distanceUnit.value = 'km';
            expect(units.fmtDistance(5)).toBe('5.00 km');
        });

        it('converts and formats correctly when unit is mi', () => {
            units.distanceUnit.value = 'mi';
            // 5 km * 0.621371 = 3.106855, toFixed(2) = "3.11"
            expect(units.fmtDistance(5)).toBe('3.11 mi');
        });

        it('formats 0 as 0.00 km', () => {
            units.distanceUnit.value = 'km';
            expect(units.fmtDistance(0)).toBe('0.00 km');
        });
    });

    // --- fmtPace ---

    describe('fmtPace', () => {
        it('formats whole minutes correctly with km unit', () => {
            units.distanceUnit.value = 'km';
            expect(units.fmtPace(5)).toBe('5:00 /km');
        });

        it('formats fractional minutes correctly with km unit', () => {
            units.distanceUnit.value = 'km';
            expect(units.fmtPace(5.5)).toBe('5:30 /km');
        });

        it('returns — for pace <= 0', () => {
            units.distanceUnit.value = 'km';
            expect(units.fmtPace(0)).toBe('—');
        });

        it('uses /mi label when unit is mi', () => {
            units.distanceUnit.value = 'mi';
            // pace in min/km; for mi display, multiply by MI_TO_KM = 1.60934
            // fmtPace(5) -> 5 * 1.60934 = 8.0467 -> 8 min 2.8... sec -> "8:03 /mi"
            const result = units.fmtPace(5);
            expect(result).toMatch(/\/mi$/);
        });
    });

    // --- toKm ---

    describe('toKm', () => {
        it('returns value unchanged when unit is km', () => {
            units.distanceUnit.value = 'km';
            expect(units.toKm(10)).toBeCloseTo(10, 3);
        });

        it('converts miles to km when unit is mi', () => {
            units.distanceUnit.value = 'mi';
            expect(units.toKm(1)).toBeCloseTo(1.60934, 3);
        });
    });

    // --- fromKm ---

    describe('fromKm', () => {
        it('returns value unchanged when unit is km', () => {
            units.distanceUnit.value = 'km';
            expect(units.fromKm(10)).toBeCloseTo(10, 3);
        });

        it('converts km to miles when unit is mi', () => {
            units.distanceUnit.value = 'mi';
            expect(units.fromKm(1.60934)).toBeCloseTo(1, 3);
        });
    });

    // --- round-trip ---

    describe('round-trip conversion', () => {
        it('fromKm(toKm(3)) ≈ 3 when unit is mi', () => {
            units.distanceUnit.value = 'mi';
            expect(units.fromKm(units.toKm(3))).toBeCloseTo(3, 3);
        });

        it('fromKm(toKm(3)) === 3 when unit is km', () => {
            units.distanceUnit.value = 'km';
            expect(units.fromKm(units.toKm(3))).toBeCloseTo(3, 3);
        });
    });
});
