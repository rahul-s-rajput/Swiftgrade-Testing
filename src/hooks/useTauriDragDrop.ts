import { useEffect, useCallback } from 'react';
import { getCurrentWebview } from '@tauri-apps/api/webview';
import { readFile } from '@tauri-apps/plugin-fs';

interface TauriWindow {
  __TAURI__: any;
}

declare global {
  interface Window extends TauriWindow {}
}

interface UseTauriDragDropReturn {
  isTauri: boolean;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
}

/**
 * Custom hook for handling drag and drop in both web and Tauri environments
 * Updated for Tauri v2 API
 */
export const useTauriDragDrop = (
  onFilesDropped: (files: File[]) => void,
  acceptedTypes: string[] = []
): UseTauriDragDropReturn => {
  const isTauri = typeof window !== 'undefined' && window.__TAURI__;
  
  console.log('[useTauriDragDrop] Hook initialized:', { isTauri, acceptedTypes });

  // Handle Tauri v2 drag drop events
  useEffect(() => {
    if (!isTauri) return;

    let unlisten: (() => void) | undefined;

    const setupTauriListener = async () => {
      try {
        console.log('[useTauriDragDrop] Setting up Tauri v2 drag drop listener');
        
        const webview = getCurrentWebview();
        
        // Use the new onDragDropEvent API for Tauri v2
        unlisten = await webview.onDragDropEvent(async (event) => {
          console.log('[useTauriDragDrop] Drag drop event received:', event);
          
          // Handle different event types
          // TypeScript types might be outdated, using type assertion
          const eventType = (event.payload as any).type;
          
          if (eventType === 'drop') {
            console.log('[useTauriDragDrop] Files dropped:', (event.payload as any).paths);
            
            const files: File[] = [];
            const droppedPaths = (event.payload as any).paths || [];
            
            for (const path of droppedPaths) {
              try {
                // Extract filename from path
                const filename = path.split(/[\\/]/).pop();
                if (!filename) continue;
                
                // Determine MIME type based on file extension
                const extension = filename.split('.').pop()?.toLowerCase();
                if (!extension) continue;
                
                let mimeType = 'application/octet-stream';
                if (['jpg', 'jpeg'].includes(extension)) mimeType = 'image/jpeg';
                else if (extension === 'png') mimeType = 'image/png';
                else if (extension === 'gif') mimeType = 'image/gif';
                else if (extension === 'webp') mimeType = 'image/webp';
                else if (extension === 'pdf') mimeType = 'application/pdf';
                else if (['txt', 'text'].includes(extension)) mimeType = 'text/plain';
                
                // Check if file type is accepted
                if (acceptedTypes.length > 0) {
                  const isAccepted = acceptedTypes.some(type => {
                    if (type.endsWith('/*')) {
                      return mimeType.startsWith(type.slice(0, -1));
                    }
                    return mimeType === type;
                  });
                  
                  if (!isAccepted) {
                    console.log(`[useTauriDragDrop] File type ${mimeType} not accepted, skipping ${filename}`);
                    continue;
                  }
                }
                
                console.log(`[useTauriDragDrop] Reading file: ${path}`);
                
                // Read file using the fs plugin
                // Note: readFile returns Uint8Array
                const fileData = await readFile(path);
                
                // Create File object from the data
                const blob = new Blob([fileData], { type: mimeType });
                const file = new File([blob], filename, { 
                  type: mimeType,
                  lastModified: Date.now()
                });
                
                files.push(file);
                console.log(`[useTauriDragDrop] Successfully processed file: ${filename} (${mimeType})`);
              } catch (error) {
                console.error('[useTauriDragDrop] Error reading file:', path, error);
              }
            }
            
            console.log(`[useTauriDragDrop] Processed ${files.length} files`);
            if (files.length > 0) {
              console.log('[useTauriDragDrop] Calling onFilesDropped with files:', files.map(f => ({ 
                name: f.name, 
                type: f.type, 
                size: f.size 
              })));
              onFilesDropped(files);
            } else {
              console.log('[useTauriDragDrop] No valid files to process');
            }
          } else if (eventType === 'over' || eventType === 'enter') {
            console.log('[useTauriDragDrop] Dragging over:', (event.payload as any).position);
          } else if (eventType === 'cancel' || eventType === 'leave') {
            console.log('[useTauriDragDrop] Drag cancelled/left');
          } else {
            console.log('[useTauriDragDrop] Unknown event type:', eventType, event);
          }
        });
        
        console.log('[useTauriDragDrop] Tauri v2 drag drop listener setup complete');
      } catch (error) {
        console.error('[useTauriDragDrop] Error setting up Tauri drag drop listener:', error);
      }
    };

    setupTauriListener();

    return () => {
      if (unlisten) {
        console.log('[useTauriDragDrop] Cleaning up Tauri drag drop listener');
        unlisten();
      }
    };
  }, [isTauri, onFilesDropped, acceptedTypes]);

  // Web drag and drop handlers (for non-Tauri environments)
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // For Tauri, the drag over is handled by the native listener
    if (!isTauri) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }, [isTauri]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    console.log('[useTauriDragDrop] handleDrop called:', { 
      isTauri, 
      filesCount: e.dataTransfer.files.length 
    });
    
    // In Tauri v2, the native drag drop handler will take care of this
    // We only process drops in web mode
    if (!isTauri && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      
      // Filter files by accepted types if specified
      const filteredFiles = acceptedTypes.length > 0 
        ? droppedFiles.filter(file => {
            return acceptedTypes.some(type => {
              if (type.endsWith('/*')) {
                return file.type.startsWith(type.slice(0, -1));
              }
              return file.type === type;
            });
          })
        : droppedFiles;
      
      if (filteredFiles.length > 0) {
        console.log('[useTauriDragDrop] Web mode: processing files:', filteredFiles.map(f => ({ 
          name: f.name, 
          type: f.type, 
          size: f.size 
        })));
        onFilesDropped(filteredFiles);
      }
    }
  }, [isTauri, onFilesDropped, acceptedTypes]);

  return {
    isTauri,
    handleDragOver,
    handleDragLeave,
    handleDrop
  };
};