import initSqlJs, { type Database } from 'sql.js';
import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url';

import type { ApiResponse } from '@/types/ApiResponse';

import { SCHEMA_SQL, SCHEMA_VERSION, SEED_SQL } from './migrations';

const DB_KEY = 'personal_tracker_db';
let db: Database | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function loadFromStorage(): Uint8Array | null {
    const stored = localStorage.getItem(DB_KEY);
    if (!stored) return null;
    const binary = atob(stored);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

function saveToStorage(): void {
    if (!db) return;
    const data = db.export();
    const chunks: string[] = [];
    const chunkSize = 8192;
    for (let i = 0; i < data.length; i += chunkSize) {
        chunks.push(String.fromCharCode(...data.subarray(i, i + chunkSize)));
    }
    localStorage.setItem(DB_KEY, btoa(chunks.join('')));
}

function scheduleSave(): void {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveToStorage, 100);
}

// sql.js parameter binding (?) is broken on iOS WKWebView.
// Use SQL value interpolation instead. Safe for this local-only app.
function sqlValue(val: unknown): string {
    if (val === null || val === undefined) return 'NULL';
    if (typeof val === 'number') return String(val);
    if (typeof val === 'boolean') return val ? '1' : '0';
    return "'" + String(val).replace(/'/g, "''") + "'";
}

function interpolate(sql: string, params?: unknown[]): string {
    if (!params || params.length === 0) return sql;
    let idx = 0;
    return sql.replace(/\?/g, () => sqlValue(params[idx++]));
}

export async function initializeDb(): Promise<void> {
    if (db) return;

    const SQL = await initSqlJs({
        locateFile: () => wasmUrl,
    });

    const stored = loadFromStorage();
    db = stored ? new SQL.Database(stored) : new SQL.Database();

    db.exec('PRAGMA foreign_keys = ON;');

    // Always run schema — CREATE TABLE IF NOT EXISTS is safe on existing DBs.
    db.exec(SCHEMA_SQL);
    db.exec(SEED_SQL);

    const tables = db.exec(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version';",
    );
    const hasVersion = tables.length > 0 && tables[0]!.values.length > 0;
    if (!hasVersion) {
        db.exec(
            `INSERT INTO schema_version (version) VALUES (${SCHEMA_VERSION});`,
        );
    }
    saveToStorage();
}

function getDb(): Database {
    if (!db) {
        throw new Error('Database not initialized. Call initializeDb() first.');
    }
    return db;
}

function stmtToObjects<T>(sql: string, params?: unknown[]): T[] {
    const d = getDb();
    const finalSql = interpolate(sql, params);
    // Use prepare()+step() instead of exec() to avoid an iOS WKWebView bug
    // where exec() returns result[0].columns = undefined for non-empty SELECT results.
    // finalSql has no '?' (values were interpolated), so broken iOS binding isn't an issue.
    const stmt = d.prepare(finalSql);
    try {
        if (!stmt.step()) return [];
        const columns = stmt.getColumnNames();
        if (!columns || columns.length === 0) {
            throw new Error(
                `sql.js returned no column info for: ${finalSql.substring(0, 80)}`,
            );
        }
        const results: T[] = [];
        do {
            const row = stmt.get();
            const obj: Record<string, unknown> = {};
            for (let i = 0; i < columns.length; i++) {
                obj[columns[i]!] = row[i];
            }
            results.push(obj as T);
        } while (stmt.step());
        return results;
    } finally {
        stmt.free();
    }
}

function success<T>(data: T): ApiResponse<T> {
    return { data, error: null, success: true };
}

function fail<T>(message: string): ApiResponse<T> {
    return { data: null, error: { message }, success: false };
}

export function useDb() {
    const query = async <T>(
        sql: string,
        params?: unknown[],
    ): Promise<ApiResponse<T[]>> => {
        try {
            return success(stmtToObjects<T>(sql, params));
        } catch (err) {
            return fail(err instanceof Error ? err.message : 'Query failed');
        }
    };

    const queryOne = async <T>(
        sql: string,
        params?: unknown[],
    ): Promise<ApiResponse<T>> => {
        try {
            const rows = stmtToObjects<T>(sql, params);
            if (rows.length === 0) {
                return fail('Not found');
            }
            return success(rows[0]!);
        } catch (err) {
            return fail(err instanceof Error ? err.message : 'Query failed');
        }
    };

    const run = async (
        sql: string,
        params?: unknown[],
    ): Promise<ApiResponse<{ id: number }>> => {
        try {
            const d = getDb();
            const finalSql = interpolate(sql, params);
            d.exec(finalSql);
            const result = d.exec('SELECT last_insert_rowid() as id');
            const id =
                result.length > 0 ? (result[0]!.values[0]![0] as number) : 0;
            scheduleSave();
            return success({ id });
        } catch (err) {
            return fail(err instanceof Error ? err.message : 'Run failed');
        }
    };

    const execute = async (
        sql: string,
        params?: unknown[],
    ): Promise<ApiResponse<void>> => {
        try {
            const finalSql = interpolate(sql, params);
            getDb().exec(finalSql);
            scheduleSave();
            return success(undefined as void);
        } catch (err) {
            return fail(err instanceof Error ? err.message : 'Execute failed');
        }
    };

    return { query, queryOne, run, execute };
}
