
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Building with DevTools enabled...');

// Set environment variable to enable DevTools
process.env.TAURI_DEBUG = '1';
process.env.RUST_BACKTRACE = '1';

// Run the build
try {
    execSync('cargo tauri build --debug', {
        stdio: 'inherit',
        cwd: path.join(__dirname, 'src-tauri')
    });
    console.log('Build complete with DevTools enabled!');
} catch (error) {
    console.error('Build failed:', error);
    process.exit(1);
}
