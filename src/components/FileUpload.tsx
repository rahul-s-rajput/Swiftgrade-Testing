import React, { useState, useRef, useCallback, useId } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';

interface FileUploadProps {
  label: string;
  files: File[];
  onChange: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  label,
  files,
  onChange,
  accept = "image/*",
  multiple = true
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const dragCounterRef = useRef(0);
  const uniqueId = useId();
  
  // Check if we're in Tauri
  const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__;
  
  console.log('[FileUpload] Component rendered:', { 
    label, 
    isTauri, 
    currentFilesCount: files.length,
    uniqueId 
  });

  // Handle file selection from input
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    console.log('[FileUpload] Files selected via input:', selectedFiles.length);
    
    if (multiple) {
      onChange([...files, ...selectedFiles]);
    } else {
      onChange(selectedFiles);
    }
    
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [files, multiple, onChange]);

  // Remove file handler
  const removeFile = useCallback((index: number) => {
    console.log('[FileUpload] Removing file at index:', index);
    onChange(files.filter((_, i) => i !== index));
  }, [files, onChange]);

  // Web-based drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Only process if this is a file drag
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      dragCounterRef.current++;
      
      if (dragCounterRef.current === 1) {
        setIsDragOver(true);
        console.log(`[FileUpload-${uniqueId}] Drag enter`);
      }
    }
  }, [uniqueId]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    dragCounterRef.current--;
    
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
      console.log(`[FileUpload-${uniqueId}] Drag leave`);
    }
  }, [uniqueId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Set the drop effect to copy
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Reset drag counter and state
    dragCounterRef.current = 0;
    setIsDragOver(false);
    
    console.log(`[FileUpload-${uniqueId}] Drop event triggered`);
    
    // For Tauri, we don't process drops here if using native drag-drop
    // The native handler will take care of it
    if (isTauri) {
      console.log(`[FileUpload-${uniqueId}] Skipping web drop handler in Tauri`);
      return;
    }
    
    // Process files for web mode
    const droppedFiles = Array.from(e.dataTransfer.files);
    console.log(`[FileUpload-${uniqueId}] Processing ${droppedFiles.length} dropped files`);
    
    // Filter by accepted types
    const acceptedTypes = accept.split(',').map(t => t.trim());
    const filteredFiles = droppedFiles.filter(file => {
      return acceptedTypes.some(type => {
        if (type === '*' || type === '*/*') return true;
        if (type.endsWith('/*')) {
          return file.type.startsWith(type.slice(0, -2));
        }
        return file.type === type || file.name.endsWith(type.replace('*', ''));
      });
    });
    
    if (filteredFiles.length > 0) {
      const newFiles = multiple ? [...files, ...filteredFiles] : filteredFiles.slice(0, 1);
      console.log(`[FileUpload-${uniqueId}] Adding ${filteredFiles.length} files`);
      onChange(newFiles);
    }
  }, [files, multiple, onChange, accept, isTauri, uniqueId]);

  // Setup Tauri-specific drag and drop
  React.useEffect(() => {
    if (!isTauri || !dropZoneRef.current) return;

    const dropZone = dropZoneRef.current;
    
    // Import Tauri APIs
    const setupTauriDragDrop = async () => {
      try {
        const { getCurrentWebview } = await import('@tauri-apps/api/webview');
        const { readFile } = await import('@tauri-apps/plugin-fs');
        
        const webview = getCurrentWebview();
        
        console.log(`[FileUpload-${uniqueId}] Setting up Tauri drag-drop listener`);
        
        // Track if mouse is over this specific drop zone
        let isMouseOverDropZone = false;
        
        const handleMouseEnter = () => {
          isMouseOverDropZone = true;
        };
        
        const handleMouseLeave = () => {
          isMouseOverDropZone = false;
          setIsDragOver(false);
        };
        
        dropZone.addEventListener('mouseenter', handleMouseEnter);
        dropZone.addEventListener('mouseleave', handleMouseLeave);
        
        // Listen to Tauri drag-drop events
        const unlisten = await webview.onDragDropEvent(async (event) => {
          const eventType = (event.payload as any).type;
          
          if (eventType === 'over' || eventType === 'enter') {
            // Check if mouse is over this drop zone
            if (isMouseOverDropZone) {
              setIsDragOver(true);
            }
          } else if (eventType === 'leave' || eventType === 'cancel') {
            setIsDragOver(false);
          } else if (eventType === 'drop') {
            // Only process if mouse is over this drop zone
            if (!isMouseOverDropZone) {
              console.log(`[FileUpload-${uniqueId}] Drop ignored - not over this zone`);
              return;
            }
            
            console.log(`[FileUpload-${uniqueId}] Processing Tauri drop`);
            setIsDragOver(false);
            
            const droppedPaths = (event.payload as any).paths || [];
            const processedFiles: File[] = [];
            
            for (const path of droppedPaths) {
              try {
                const filename = path.split(/[\\/]/).pop();
                if (!filename) continue;
                
                const extension = filename.split('.').pop()?.toLowerCase();
                if (!extension) continue;
                
                // Determine MIME type
                let mimeType = 'application/octet-stream';
                if (['jpg', 'jpeg'].includes(extension)) mimeType = 'image/jpeg';
                else if (extension === 'png') mimeType = 'image/png';
                else if (extension === 'gif') mimeType = 'image/gif';
                else if (extension === 'webp') mimeType = 'image/webp';
                else if (extension === 'pdf') mimeType = 'application/pdf';
                
                // Check if accepted
                const acceptedTypes = accept.split(',').map(t => t.trim());
                const isAccepted = acceptedTypes.some(type => {
                  if (type === '*' || type === '*/*') return true;
                  if (type.endsWith('/*')) {
                    return mimeType.startsWith(type.slice(0, -2));
                  }
                  return mimeType === type || filename.endsWith(type.replace('*', ''));
                });
                
                if (!isAccepted) {
                  console.log(`[FileUpload-${uniqueId}] File rejected:`, filename);
                  continue;
                }
                
                // Read file
                const fileData = await readFile(path);
                const blob = new Blob([fileData], { type: mimeType });
                const file = new File([blob], filename, { 
                  type: mimeType,
                  lastModified: Date.now()
                });
                
                processedFiles.push(file);
                console.log(`[FileUpload-${uniqueId}] File processed:`, filename);
              } catch (error) {
                console.error(`[FileUpload-${uniqueId}] Error processing file:`, error);
              }
            }
            
            if (processedFiles.length > 0) {
              const newFiles = multiple 
                ? [...files, ...processedFiles] 
                : processedFiles.slice(0, 1);
              console.log(`[FileUpload-${uniqueId}] Updating with ${processedFiles.length} files`);
              onChange(newFiles);
            }
          }
        });
        
        // Cleanup function
        return () => {
          dropZone.removeEventListener('mouseenter', handleMouseEnter);
          dropZone.removeEventListener('mouseleave', handleMouseLeave);
          unlisten();
        };
      } catch (error) {
        console.error(`[FileUpload-${uniqueId}] Error setting up Tauri drag-drop:`, error);
      }
    };
    
    const cleanup = setupTauriDragDrop();
    
    return () => {
      cleanup.then(fn => fn && fn());
    };
  }, [isTauri, files, multiple, onChange, accept, uniqueId]);

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      
      {/* Drop Zone */}
      <div
        ref={dropZoneRef}
        onDrop={isTauri ? undefined : handleDrop}
        onDragOver={isTauri ? undefined : handleDragOver}
        onDragEnter={isTauri ? undefined : handleDragEnter}
        onDragLeave={isTauri ? undefined : handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center 
          transition-all duration-200 cursor-pointer
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50 scale-[1.02] shadow-lg' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
        `}
        data-drop-zone-id={uniqueId}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <Upload className={`
          w-8 h-8 mx-auto mb-2 transition-all duration-200
          ${isDragOver ? 'text-blue-500 scale-110' : 'text-gray-400'}
        `} />
        
        <p className="text-sm text-gray-600">
          {isDragOver ? (
            <span className="text-blue-600 font-semibold">Drop files here!</span>
          ) : (
            <>
              Drag and drop files here, or{' '}
              <span className="text-blue-600 font-medium hover:text-blue-700">
                browse
              </span>
            </>
          )}
        </p>
        
        <p className="text-xs text-gray-400 mt-1">
          {accept.includes('image') 
            ? 'PNG, JPG, JPEG up to 10MB each' 
            : 'Multiple files supported'
          }
        </p>
      </div>

      {/* File Previews */}
      {files.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {files.map((file, index) => (
            <div 
              key={`${file.name}-${index}-${file.size}`} 
              className="relative group"
            >
              <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden shadow-sm group-hover:shadow-md transition-shadow">
                {file.type.startsWith('image/') ? (
                  <img
                    src={URL.createObjectURL(file)}
                    alt={file.name}
                    className="w-full h-full object-cover"
                    onLoad={(e) => {
                      // Clean up object URL after image loads
                      URL.revokeObjectURL(e.currentTarget.src);
                    }}
                  />
                ) : (
                  <div className="flex items-center justify-center w-full h-full">
                    <ImageIcon className="w-8 h-8 text-gray-400" />
                  </div>
                )}
              </div>
              
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 
                  opacity-0 group-hover:opacity-100 transition-opacity shadow-md 
                  hover:bg-red-600 hover:scale-110 transform"
              >
                <X className="w-4 h-4" />
              </button>
              
              <p className="text-xs text-gray-600 mt-1 truncate" title={file.name}>
                {file.name}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};