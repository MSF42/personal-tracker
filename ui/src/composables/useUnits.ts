import { ref } from 'vue';

import { useSettingsApi } from '@/composables/api/useSettingsApi';

// Module-level shared state — one instance across the whole app
const weightUnit = ref<'kg' | 'lbs'>('kg');
const distanceUnit = ref<'km' | 'mi'>('km');
let loaded = false;

const KG_TO_LBS = 2.20462;
const KM_TO_MI = 0.621371;
const MI_TO_KM = 1.60934;

export function useUnits() {
    const { getSetting, setSetting } = useSettingsApi();

    async function loadUnits() {
        if (loaded) return;
        loaded = true;
        const [wRes, dRes] = await Promise.all([
            getSetting('unit_weight'),
            getSetting('unit_distance'),
        ]);
        if (wRes.success && wRes.data?.value) {
            weightUnit.value = wRes.data.value as 'kg' | 'lbs';
        }
        if (dRes.success && dRes.data?.value) {
            distanceUnit.value = dRes.data.value as 'km' | 'mi';
        }
    }

    async function setWeightUnit(unit: 'kg' | 'lbs') {
        weightUnit.value = unit;
        loaded = true;
        await setSetting('unit_weight', unit);
    }

    async function setDistanceUnit(unit: 'km' | 'mi') {
        distanceUnit.value = unit;
        loaded = true;
        await setSetting('unit_distance', unit);
    }

    /** Format a weight stored in kg for display */
    function fmtWeight(kg: number | null | undefined): string {
        if (kg == null) return '—';
        if (weightUnit.value === 'lbs') {
            return `${(kg * KG_TO_LBS).toFixed(1)} lbs`;
        }
        return `${kg} kg`;
    }

    /** Format a distance stored in km for display */
    function fmtDistance(km: number): string {
        if (distanceUnit.value === 'mi') {
            return `${(km * KM_TO_MI).toFixed(2)} mi`;
        }
        return `${km.toFixed(2)} km`;
    }

    /** Format a pace stored as min/km, including the unit label */
    function fmtPace(paceMinPerKm: number): string {
        if (paceMinPerKm <= 0) return '—';
        const paceValue =
            distanceUnit.value === 'mi'
                ? paceMinPerKm * MI_TO_KM
                : paceMinPerKm;
        const mins = Math.floor(paceValue);
        const secs = Math.round((paceValue - mins) * 60);
        return `${mins}:${String(secs).padStart(2, '0')} /${distanceUnit.value}`;
    }

    /** Convert a value entered in the user's preferred distance unit to km */
    function toKm(value: number): number {
        return distanceUnit.value === 'mi' ? value * MI_TO_KM : value;
    }

    /** Convert a stored km value to the user's preferred display unit */
    function fromKm(km: number): number {
        return distanceUnit.value === 'mi' ? km * KM_TO_MI : km;
    }

    /** Convert a value entered in the user's preferred weight unit to kg */
    function toKg(value: number): number {
        return weightUnit.value === 'lbs' ? value / KG_TO_LBS : value;
    }

    /** Convert a stored kg value to the user's preferred display unit */
    function fromKg(kg: number): number {
        return weightUnit.value === 'lbs' ? kg * KG_TO_LBS : kg;
    }

    return {
        weightUnit,
        distanceUnit,
        loadUnits,
        setWeightUnit,
        setDistanceUnit,
        fmtWeight,
        fmtDistance,
        fmtPace,
        toKm,
        fromKm,
        toKg,
        fromKg,
        KG_TO_LBS,
        KM_TO_MI,
        MI_TO_KM,
    };
}
