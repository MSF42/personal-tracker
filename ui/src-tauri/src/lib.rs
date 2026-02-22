use std::sync::Mutex;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            let app_data_dir = app
                .path()
                .app_data_dir()
                .expect("failed to resolve app data dir");

            std::fs::create_dir_all(&app_data_dir)
                .expect("failed to create app data dir");

            let db_path = app_data_dir.join("tracker.db");
            let uploads_path = app_data_dir.join("uploads");

            std::fs::create_dir_all(&uploads_path)
                .expect("failed to create uploads dir");

            let sidecar_command = app
                .shell()
                .sidecar("personal-tracker-api")
                .expect("failed to create sidecar command")
                .env("PORT", "8743")
                .env("HOST", "127.0.0.1")
                .env("DATABASE_PATH", db_path.to_str().unwrap())
                .env("UPLOADS_PATH", uploads_path.to_str().unwrap());

            let (_, child) = sidecar_command
                .spawn()
                .expect("failed to spawn sidecar");

            *app.state::<SidecarState>().0.lock().unwrap() = Some(child);

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let app = window.app_handle();
                kill_sidecar(app);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn kill_sidecar(app: &AppHandle) {
    if let Ok(mut guard) = app.state::<SidecarState>().0.lock() {
        if let Some(child) = guard.take() {
            let _ = child.kill();
        }
    }
}
