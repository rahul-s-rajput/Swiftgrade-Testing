import React, { useState, useRef, useCallback, useId } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';

interface FileUploadProps {
  label: string;
  files: File[];
  onChange: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
}

/**
 * FileUpload component optimized for Tauri v2 with HTML5 drag-drop
 * To use this, set dragDropEnabled: false in tauri.conf.json
 */
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
  
  console.log('[FileUpload] Component rendered:', { 
    label, 
    currentFilesCount: files.length,
    uniqueId 
  });

  // Handle file selection from input
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    console.log(`[FileUpload-${uniqueId}] Files selected via input:`, selectedFiles.length);
    
    if (multiple) {
      onChange([...files, ...selectedFiles]);
    } else {
      onChange(selectedFiles);
    }
    
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [files, multiple, onChange, uniqueId]);

  // Remove file handler
  const removeFile = useCallback((index: number) => {
    console.log(`[FileUpload-${uniqueId}] Removing file at index:`, index);
    onChange(files.filter((_, i) => i !== index));
  }, [files, onChange, uniqueId]);

  // Process dropped files
  const processFiles = useCallback((droppedFiles: File[]) => {
    console.log(`[FileUpload-${uniqueId}] Processing ${droppedFiles.length} files`);
    
    // Filter by accepted types
    const acceptedTypes = accept.split(',').map(t => t.trim());
    const filteredFiles = droppedFiles.filter(file => {
      return acceptedTypes.some(type => {
        if (type === '*' || type === '*/*') return true;
        if (type.endsWith('/*')) {
          return file.type.startsWith(type.slice(0, -2));
        }
        // Check both MIME type and file extension
        const extension = '.' + file.name.split('.').pop()?.toLowerCase();
        return file.type === type || 
               type === extension || 
               (type.includes('image') && file.type.startsWith('image/'));
      });
    });
    
    if (filteredFiles.length > 0) {
      const newFiles = multiple 
        ? [...files, ...filteredFiles] 
        : filteredFiles.slice(0, 1);
      console.log(`[FileUpload-${uniqueId}] Adding ${filteredFiles.length} files`);
      onChange(newFiles);
    } else {
      console.log(`[FileUpload-${uniqueId}] No valid files to add`);
    }
  }, [files, multiple, onChange, accept, uniqueId]);

  // Drag and drop handlers with proper event management
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Check if dragging files
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      const hasFiles = Array.from(e.dataTransfer.items).some(
        item => item.kind === 'file'
      );
      
      if (hasFiles) {
        dragCounterRef.current++;
        if (dragCounterRef.current === 1) {
          setIsDragOver(true);
          console.log(`[FileUpload-${uniqueId}] Drag enter - files detected`);
        }
      }
    }
  }, [uniqueId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Ensure we're showing copy cursor
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
      console.log(`[FileUpload-${uniqueId}] Drag leave`);
    }
  }, [uniqueId]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Reset state
    dragCounterRef.current = 0;
    setIsDragOver(false);
    
    console.log(`[FileUpload-${uniqueId}] Drop event - processing files`);
    
    // Get dropped files
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      processFiles(droppedFiles);
    }
  }, [processFiles, uniqueId]);

  // Prevent default browser behavior for the entire document
  React.useEffect(() => {
    const preventDefault = (e: DragEvent) => {
      // Only prevent default if we're not over a drop zone
      if (!e.target || !(e.target as HTMLElement).closest('[data-drop-zone-id]')) {
        e.preventDefault();
      }
    };
    
    // Prevent default drag behavior on document level
    document.addEventListener('dragover', preventDefault);
    document.addEventListener('drop', preventDefault);
    
    return () => {
      document.removeEventListener('dragover', preventDefault);
      document.removeEventListener('drop', preventDefault);
    };
  }, []);

  // Clean up object URLs when component unmounts
  React.useEffect(() => {
    return () => {
      files.forEach(file => {
        if (file.type.startsWith('image/')) {
          // Clean up any remaining object URLs
          try {
            URL.revokeObjectURL(URL.createObjectURL(file));
          } catch (e) {
            // Ignore errors
          }
        }
      });
    };
  }, [files]);

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      
      {/* Drop Zone */}
      <div
        ref={dropZoneRef}
        data-drop-zone-id={uniqueId}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center 
          transition-all duration-200 cursor-pointer select-none
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50 scale-[1.02] shadow-lg' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileSelect}
          className="hidden"
          aria-label={label}
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
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </p>
            {files.length > 0 && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="text-xs text-red-600 hover:text-red-700 font-medium"
              >
                Clear all
              </button>
            )}
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {files.map((file, index) => {
              // Create a stable key for each file
              const fileKey = `${file.name}-${file.size}-${file.lastModified}`;
              
              return (
                <div 
                  key={fileKey} 
                  className="relative group animate-fadeIn"
                >
                  <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden shadow-sm group-hover:shadow-md transition-shadow">
                    {file.type.startsWith('image/') ? (
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="w-full h-full object-cover"
                        onLoad={(e) => {
                          // Clean up object URL after image loads to prevent memory leaks
                          const img = e.currentTarget;
                          setTimeout(() => {
                            URL.revokeObjectURL(img.src);
                          }, 100);
                        }}
                        onError={(e) => {
                          // Handle error gracefully
                          console.error(`Failed to load image: ${file.name}`);
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="flex items-center justify-center w-full h-full bg-gradient-to-br from-gray-100 to-gray-200">
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
                      opacity-0 group-hover:opacity-100 transition-all duration-200 shadow-md 
                      hover:bg-red-600 hover:scale-110 transform"
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="w-4 h-4" />
                  </button>
                  
                  <p className="text-xs text-gray-600 mt-1 truncate" title={file.name}>
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-400">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};