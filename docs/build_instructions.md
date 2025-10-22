 pyinstaller backend_launcher.spec --clean
 copy dist\backend-x86_64-pc-windows-msvc.exe src-tauri\binaries\backend-x86_64-pc-windows-msvc.exe
 npm run build
 cd src-tauri
 cargo tauri build --debug