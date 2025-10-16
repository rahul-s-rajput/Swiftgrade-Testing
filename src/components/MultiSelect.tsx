import React, { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown, Search, X, MoreVertical } from 'lucide-react';
import { AIModel } from '../types';

interface MultiSelectProps {
  label: string;
  options: AIModel[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  getChipBadge?: (id: string) => React.ReactNode;
  onChipMenuRequest?: (id: string, anchorRect: DOMRect) => void;
  shouldShowChipMenu?: (id: string) => boolean;
  renderOptionMeta?: (id: string) => React.ReactNode;
  getChipSuffix?: (id: string) => React.ReactNode;
  allowDuplicates?: boolean;
  getChipBadgeAt?: (id: string, index: number) => React.ReactNode;
  onChipMenuRequestAt?: (id: string, index: number, anchorRect: DOMRect) => void;
  shouldShowChipMenuAt?: (id: string, index: number) => boolean;
  maxPerOption?: number;
  dropdownPlacement?: 'right' | 'bottom' | 'top';
}

export const MultiSelect: React.FC<MultiSelectProps> = ({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = "Select options...",
  getChipBadge,
  onChipMenuRequest,
  shouldShowChipMenu,
  renderOptionMeta,
  getChipSuffix,
  allowDuplicates = false,
  getChipBadgeAt,
  onChipMenuRequestAt,
  shouldShowChipMenuAt,
  maxPerOption,
  dropdownPlacement = 'bottom',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [menuMaxHeight, setMenuMaxHeight] = useState<number>(384);

  const filteredOptions = options.filter(option =>
    option.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    option.provider.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Set fixed max height for dropdown
  useEffect(() => {
    if (!isOpen) return;
    // Fixed height of 400px for consistent dropdown size
    setMenuMaxHeight(400);
  }, [isOpen]);

  const toggleOption = (optionId: string) => {
    if (allowDuplicates) {
      const count = selectedValues.filter(id => id === optionId).length;
      if (typeof maxPerOption === 'number' && count >= maxPerOption) {
        return;
      }
      onChange([...selectedValues, optionId]);
      return;
    }
    if (selectedValues.includes(optionId)) {
      onChange(selectedValues.filter(id => id !== optionId));
    } else {
      onChange([...selectedValues, optionId]);
    }
  };

  const removeOptionAt = (index: number) => {
    onChange(selectedValues.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      
      <div className="relative" ref={dropdownRef}>

        {/* Trigger + Dropdown positioned together */}
        <div className="relative">
          {/* Dropdown trigger */}
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            ref={triggerRef}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <div className="flex items-center justify-between">
              <span className="text-gray-500">
                {selectedValues.length > 0 
                  ? `${selectedValues.length} model${selectedValues.length !== 1 ? 's' : ''} selected`
                  : placeholder
                }
              </span>
              <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </div>
          </button>

          {/* Dropdown menu */}
          {isOpen && (
            <div
              className={
                dropdownPlacement === 'right'
                  ? "absolute z-50 w-96 left-full top-0 ml-2 bg-white border border-gray-300 rounded-lg shadow-lg overflow-hidden"
                  : dropdownPlacement === 'top'
                  ? "absolute z-50 w-full bottom-full mb-1 bg-white border border-gray-300 rounded-lg shadow-lg overflow-hidden"
                  : "absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg overflow-hidden"
              }
              style={{ maxHeight: menuMaxHeight }}
            >
            {/* Search input */}
            <div className="p-2 border-b border-gray-200">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search models..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); } }}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Options list */}
            <div
              className="overflow-y-auto"
              style={{ maxHeight: Math.max(0, menuMaxHeight - 56) }}
            >
              {filteredOptions.map(option => {
                const count = selectedValues.filter(id => id === option.id).length;
                const atMax = allowDuplicates && typeof maxPerOption === 'number' && count >= maxPerOption;
                return (
                  <button
                    type="button"
                    key={option.id}
                    onClick={() => toggleOption(option.id)}
                    disabled={atMax}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between group ${atMax ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'}`}
                  >
                    <div>
                      <div className="font-medium text-gray-900">{option.name}</div>
                      <div className="text-sm text-gray-500">{option.provider}</div>
                      {(() => {
                        if (!renderOptionMeta) return null;
                        const node = renderOptionMeta(option.id);
                        return node ? (
                          <div className="text-xs text-gray-400 mt-0.5">{node}</div>
                        ) : null;
                      })()}
                    </div>
                    {selectedValues.includes(option.id) && (
                      <Check className="w-4 h-4 text-blue-600" />
                    )}
                  </button>
                );
              })}
              {filteredOptions.length === 0 && (
                <div className="px-3 py-2 text-gray-500 text-center">
                  {options.length > 0 && searchTerm ? 'No results' : 'No models found'}
                </div>
              )}
            </div>
            </div>
          )}
        </div>
      </div>

      {/* Selected items display BELOW dropdown */}
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedValues.map((id, idx) => {
            const option = options.find(o => o.id === id);
            if (!option) return null;
            const chipKey = `${id}-${idx}`;
            const showMenu = typeof shouldShowChipMenuAt === 'function'
              ? shouldShowChipMenuAt(id, idx)
              : (shouldShowChipMenu ? shouldShowChipMenu(id) : false);
            const badgeNode = typeof getChipBadgeAt === 'function'
              ? getChipBadgeAt(id, idx)
              : (getChipBadge ? getChipBadge(id) : null);
            return (
            <span
              key={chipKey}
              className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
            >
              {option.name}
              {(() => {
                if (!getChipSuffix) return null;
                const node = getChipSuffix(option.id);
                return node ? (
                  <span className="ml-1 text-[10px] text-blue-900/70">{node}</span>
                ) : null;
              })()}
              {badgeNode && (
                <span className="ml-1">{badgeNode}</span>
              )}
              {(onChipMenuRequestAt || onChipMenuRequest) && showMenu && (
                <button
                  type="button"
                  aria-label={`Configure ${option.name}`}
                  onClick={(e) => {
                    const rect = (e.currentTarget as HTMLButtonElement).getBoundingClientRect();
                    if (onChipMenuRequestAt) {
                      onChipMenuRequestAt(id, idx, rect);
                    } else if (onChipMenuRequest) {
                      onChipMenuRequest(option.id, rect);
                    }
                  }}
                  className="ml-1 hover:bg-blue-200 rounded-full p-0.5"
                >
                  <MoreVertical className="w-3 h-3" />
                </button>
              )}
              <button
                type="button"
                onClick={() => removeOptionAt(idx)}
                className="ml-1 hover:bg-blue-200 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
            );
          })}
        </div>
      )}
    </div>
  );
};