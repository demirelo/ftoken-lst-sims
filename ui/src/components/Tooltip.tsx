import React, { useState } from 'react'
import { Info } from 'lucide-react'

interface TooltipProps {
    content: string
    children?: React.ReactNode
    position?: 'top' | 'bottom' | 'left' | 'right'
}

export default function Tooltip({ content, children, position = 'bottom' }: TooltipProps) {
    const [isVisible, setIsVisible] = useState(false)

    return (
        <div
            className="tooltip-container"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            {children || <Info size={14} className="tooltip-icon" />}

            {isVisible && (
                <div className={`tooltip-content tooltip-${position}`}>
                    {content}
                    <div className="tooltip-arrow" />
                </div>
            )}

            <style>{`
                .tooltip-container {
                    position: relative;
                    display: inline-flex;
                    align-items: center;
                    cursor: help;
                }
                
                .tooltip-icon {
                    color: var(--text-muted);
                    transition: color 0.2s;
                }
                
                .tooltip-container:hover .tooltip-icon {
                    color: var(--text-primary);
                }

                .tooltip-content {
                    position: absolute;
                    background: var(--bg-tertiary);
                    border: 1px solid var(--border-color);
                    color: var(--text-primary);
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.75rem;
                    line-height: 1.4;
                    width: max-content;
                    max-width: 250px;
                    z-index: 100;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    pointer-events: none;
                    animation: fadeIn 0.15s ease-out;
                }

                .tooltip-top {
                    bottom: 100%;
                    left: 50%;
                    transform: translateX(-50%) translateY(-8px);
                }
                
                .tooltip-bottom {
                    top: 100%;
                    left: 50%;
                    transform: translateX(-50%) translateY(8px);
                }

                .tooltip-arrow {
                    position: absolute;
                    width: 8px;
                    height: 8px;
                    background: var(--bg-tertiary);
                    border-right: 1px solid var(--border-color);
                    border-bottom: 1px solid var(--border-color);
                    transform: rotate(45deg);
                }

                .tooltip-top .tooltip-arrow {
                    bottom: -5px;
                    left: 50%;
                    margin-left: -4px;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(-4px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(-8px); }
                }
            `}</style>
        </div>
    )
}
