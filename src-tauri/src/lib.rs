use tauri::{Manager, AppHandle, Emitter};
use tauri::menu::{MenuBuilder, MenuItemBuilder, SubmenuBuilder};
use tauri::WebviewWindowBuilder;
use tauri::WebviewUrl;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::{ShellExt, process::CommandEvent};
use std::sync::Mutex;
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Debug, Serialize, Deserialize)]
struct BackendConfig {
    port: u16,
    env_path: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct EnvConfig {
    api_key: String,
    supabase_url: String,
    supabase_key: String,
    storage_bucket: String,
}

struct BackendState {
    port: Mutex<u16>,
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

// Helper function to kill backend process forcefully on Windows
#[cfg(target_os = "windows")]
fn kill_process_tree(pid: u32) {
    use std::process::Command;
    
    // Use Windows taskkill to kill the process tree
    let _ = Command::new("taskkill")
        .args(&["/F", "/T", "/PID", &pid.to_string()])
        .output();
}

#[cfg(not(target_os = "windows"))]
fn kill_process_tree(_pid: u32) {
    // On Unix-like systems, the normal kill should work
}

#[tauri::command]
async fn start_backend(
    app: AppHandle,
    state: tauri::State<'_, BackendState>
) -> Result<u16, String> {
    // Check if already running
    let backend_needs_restart = {
        // First, check if there's a child process
        let has_child = {
            let child_guard = state.child.lock().unwrap();
            child_guard.is_some()
        };
        
        if has_child {
            // Get the port value without holding the lock
            let port = {
                let port_guard = state.port.lock().unwrap();
                *port_guard
            };
            
            // Verify the backend is actually responding (without holding locks)
            let url = format!("http://127.0.0.1:{}/health", port);
            
            match reqwest::get(&url).await {
                Ok(response) if response.status().is_success() => {
                    println!("Backend already running on port {}", port);
                    return Ok(port);
                }
                _ => {
                    // Backend process exists but not responding, kill it
                    println!("Backend process exists but not responding, restarting...");
                    true // Signal that we need to restart
                }
            }
        } else {
            false // No backend running, proceed to start new one
        }
    };
    
    // If we determined we need to restart, kill the existing process
    if backend_needs_restart {
        let mut child_guard = state.child.lock().unwrap();
        if let Some(child) = child_guard.take() {
            let pid = child.pid();
            let _ = child.kill();

            #[cfg(target_os = "windows")]
            kill_process_tree(pid);
        }
    }
    
    // Find available port
    let port = portpicker::pick_unused_port()
        .ok_or_else(|| "Failed to find available port".to_string())?;
    
    // Get env file path
    let env_path = app.path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join(".env");
    
    println!("Starting backend with env file: {:?}", env_path);
    
    // Start backend sidecar
    let sidecar_command = app.shell()
        .sidecar("backend")
        .map_err(|e| e.to_string())?
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        .env("ENV_FILE_PATH", env_path.to_string_lossy().to_string());
    
    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;
    
    let pid = child.pid();
    println!("Started backend process with PID: {:?}", pid);
    
    // Store the child process
    {
        let mut child_guard = state.child.lock().unwrap();
        *child_guard = Some(child);
    }
    
    // Store the port
    {
        let mut port_guard = state.port.lock().unwrap();
        *port_guard = port;
    }
    
    // Listen to backend output
    let window = app.get_webview_window("main").unwrap();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    println!("Backend: {}", line_str);
                    let _ = window.emit("backend-output", line_str.to_string());
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    eprintln!("Backend error: {}", line_str);
                    let _ = window.emit("backend-error", line_str.to_string());
                }
                CommandEvent::Terminated(payload) => {
                    println!("Backend terminated: {:?}", payload);
                    let _ = window.emit("backend-terminated", payload);
                    break;
                }
                _ => {}
            }
        }
    });
    
    // Wait for backend to be ready with extended timeout
    println!("Waiting for backend to be ready on port {}...", port);
    for i in 0..120 {  // Increased to 60 seconds total
        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
        
        let url = format!("http://127.0.0.1:{}/health", port);
        match reqwest::get(&url).await {
            Ok(response) => {
                if response.status().is_success() {
                    println!("Backend is ready on port {} after {} attempts", port, i + 1);
                    
                    // Double-check the backend is fully ready
                    tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                    
                    return Ok(port);
                }
                println!("Backend responded with status: {} (attempt {})", response.status(), i + 1);
            }
            Err(e) => {
                if i % 10 == 0 {
                    println!("Waiting for backend... (attempt {}/120): {}", i + 1, e);
                }
            }
        }
    }
    
    println!("Backend failed to respond to health check after 60 seconds");
    Err("Backend failed to start within timeout".to_string())
}

#[tauri::command]
async fn stop_backend(
    state: tauri::State<'_, BackendState>
) -> Result<(), String> {
    println!("Stopping backend...");
    let mut child_guard = state.child.lock().unwrap();
    if let Some(child) = child_guard.take() {
        let pid = child.pid();
        println!("Killing backend process with PID: {:?}", pid);
        
        // Try graceful kill first
        child.kill().map_err(|e| e.to_string())?;
        
        // On Windows, also use taskkill to ensure all child processes are killed
        #[cfg(target_os = "windows")]
        kill_process_tree(pid);
        
        println!("Backend stopped successfully");
    }
    Ok(())
}

#[tauri::command]
fn get_backend_port(state: tauri::State<'_, BackendState>) -> u16 {
    *state.port.lock().unwrap()
}

#[tauri::command]
fn check_env_config(app: AppHandle) -> bool {
    let env_path = app.path()
        .app_data_dir()
        .ok()
        .map(|p| p.join(".env"));
    
    env_path.map(|p| p.exists()).unwrap_or(false)
}

#[tauri::command]
fn save_env_config(
    app: AppHandle,
    api_key: String,
    supabase_url: String,
    supabase_key: String,
    storage_bucket: Option<String>,
) -> Result<(), String> {
    let app_dir = app.path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    
    fs::create_dir_all(&app_dir).map_err(|e| e.to_string())?;
    
    let env_path = app_dir.join(".env");
    let bucket = storage_bucket.unwrap_or_else(|| "grading-images".to_string());
    
    let env_content = format!(
        "OPENROUTER_API_KEY={}\nSUPABASE_URL={}\nSUPABASE_SERVICE_ROLE_KEY={}\nSUPABASE_STORAGE_BUCKET={}\nOPENROUTER_DEBUG=0\nGRADING_MAX_CONCURRENCY=4",
        api_key, supabase_url, supabase_key, bucket
    );
    
    fs::write(env_path, env_content).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_env_config(app: AppHandle) -> Result<EnvConfig, String> {
    let env_path = app.path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join(".env");
    
    if !env_path.exists() {
        return Err("Configuration file not found".to_string());
    }
    
    let content = fs::read_to_string(env_path).map_err(|e| e.to_string())?;
    
    let mut api_key = String::new();
    let mut supabase_url = String::new();
    let mut supabase_key = String::new();
    let mut storage_bucket = String::from("grading-images");
    
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        
        if let Some((key, value)) = line.split_once('=') {
            let key = key.trim();
            let value = value.trim();
            
            match key {
                "OPENROUTER_API_KEY" => api_key = value.to_string(),
                "SUPABASE_URL" => supabase_url = value.to_string(),
                "SUPABASE_SERVICE_ROLE_KEY" => supabase_key = value.to_string(),
                "SUPABASE_STORAGE_BUCKET" => storage_bucket = value.to_string(),
                _ => {}
            }
        }
    }
    
    Ok(EnvConfig {
        api_key,
        supabase_url,
        supabase_key,
        storage_bucket,
    })
}

#[tauri::command]
fn open_env_file(app: AppHandle) -> Result<(), String> {
    let env_path = app.path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join(".env");
    
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("notepad")
            .arg(env_path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg("-t")
            .arg(env_path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(env_path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    Ok(())
}

#[tauri::command]
fn get_app_data_dir(app: AppHandle) -> Result<String, String> {
    app.path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

// Cleanup function to ensure backend is killed
fn cleanup_backend(state: &BackendState) {
    println!("Cleaning up backend process...");
    let mut child_guard = state.child.lock().unwrap();
    if let Some(child) = child_guard.take() {
        let pid = child.pid();
        println!("Force killing backend process with PID: {:?}", pid);
        
        // Try to kill normally first
        let _ = child.kill();
        
        // On Windows, use taskkill to ensure all child processes are killed
        #[cfg(target_os = "windows")]
        kill_process_tree(pid);
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_state = BackendState {
        port: Mutex::new(8000),
        child: Mutex::new(None),
    };
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(|app| {
            // Create menu
            let _app_handle = app.handle().clone();
            
            // File menu items
            let quit = MenuItemBuilder::with_id("quit", "Quit")
                .accelerator("CmdOrCtrl+Q")
                .build(app)?;
            
            // Configuration menu items
            let open_config = MenuItemBuilder::with_id("open_config", "Open Configuration")
                .accelerator("CmdOrCtrl+,")
                .build(app)?;
            let edit_config = MenuItemBuilder::with_id("edit_config", "Edit Environment File")
                .build(app)?;
            let show_config_folder = MenuItemBuilder::with_id("show_config_folder", "Show Config Folder")
                .build(app)?;
            let restart_backend = MenuItemBuilder::with_id("restart_backend", "Restart Backend")
                .accelerator("CmdOrCtrl+R")
                .build(app)?;
            
            // Help menu items
            let about = MenuItemBuilder::with_id("about", "About")
                .build(app)?;
            
            // Build submenus
            let file_menu = SubmenuBuilder::new(app, "File")
                .item(&quit)
                .build()?;
            
            let config_menu = SubmenuBuilder::new(app, "Configuration")
                .item(&open_config)
                .item(&edit_config)
                .separator()
                .item(&show_config_folder)
                .separator()
                .item(&restart_backend)
                .build()?;
            
            let help_menu = SubmenuBuilder::new(app, "Help")
                .item(&about)
                .build()?;
            
            // Build and set the menu
            let menu = MenuBuilder::new(app)
                .item(&file_menu)
                .item(&config_menu)
                .item(&help_menu)
                .build()?;
            
            app.set_menu(menu)?;
            
            // Handle menu events
            app.on_menu_event(move |app, event| {
                match event.id().as_ref() {
                    "quit" => {
                        // Clean up backend before quitting
                        let state = app.state::<BackendState>();
                        cleanup_backend(&state);
                        std::process::exit(0);
                    }
                    "open_config" => {
                        // Open configuration window
                        let _ = WebviewWindowBuilder::new(
                            app,
                            "config",
                            WebviewUrl::App("/settings".into())
                        )
                        .title("Configuration")
                        .inner_size(800.0, 600.0)
                        .build();
                    }
                    "edit_config" => {
                        let app_handle_clone = app.app_handle().clone();
                        let _ = open_env_file(app_handle_clone);
                    }
                    "show_config_folder" => {
                        let app_handle_clone = app.app_handle().clone();
                        if let Ok(dir) = get_app_data_dir(app_handle_clone) {
                            #[cfg(target_os = "windows")]
                            {
                                let _ = std::process::Command::new("explorer").arg(&dir).spawn();
                            }
                            #[cfg(target_os = "macos")]
                            {
                                let _ = std::process::Command::new("open").arg(&dir).spawn();
                            }
                            #[cfg(target_os = "linux")]
                            {
                                let _ = std::process::Command::new("xdg-open").arg(&dir).spawn();
                            }
                        }
                    }
                    "restart_backend" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let state = app.state::<BackendState>();
                            
                            // Stop current backend
                            cleanup_backend(&state);
                            
                            // Emit event to restart
                            let _ = window.emit("restart-backend", ());
                        }
                    }
                    "about" => {
                        // Show about dialog using the correct API
                        let app_handle_clone = app.app_handle().clone();
                        app_handle_clone.dialog()
                            .message("Mark Grading Assistant v1.0.0\n\nAn AI-powered tool for grading assessments.\n\n© 2024")
                            .title("About Mark Grading Assistant")
                            .blocking_show();
                    }
                    _ => {}
                }
            });
            
            Ok(())
        })
        .manage(backend_state)
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            get_backend_port,
            check_env_config,
            save_env_config,
            get_env_config,
            open_env_file,
            get_app_data_dir
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Stop backend when window closes
                let state = window.state::<BackendState>();
                cleanup_backend(&state);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}