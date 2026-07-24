# Copyright 2026 VIREON Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
High-Performance Double-Buffered Canvas EEG Waveform Monitor.
Eliminates screen flickering using an off-screen buffer and requestAnimationFrame.
"""

import json
import numpy as np
import streamlit.components.v1 as components

from typing import Optional, List

CHANNEL_NAMES = ["Fp1", "Fp2", "C3", "C4", "P3", "P4", "O1", "O2"]
CHANNEL_COLORS = ["#00f2fe", "#7000ff", "#00f5d4", "#ff007f", "#ffd166", "#38bdf8", "#c084fc", "#f472b6"]

def render_double_buffered_eeg_canvas(
    signals: np.ndarray,
    height: int = 450,
    channel_names: Optional[List[str]] = None,
    channel_colors: Optional[List[str]] = None,
    title: str = "8-CHANNEL LIVE EEG TELEMETRY (DOUBLE-BUFFERED 100 HZ)"
) -> None:
    """
    Renders a multi-channel signal monitor using HTML5 Canvas with Double Buffering
    and requestAnimationFrame synchronization to eliminate UI flicker.
    
    Args:
        signals (np.ndarray): Shape (num_channels, N) array of voltage samples.
        height (int): Height of the component in pixels.
        channel_names (List[str], optional): Custom labels for each channel.
        channel_colors (List[str], optional): Custom hex colors for each channel.
        title (str): Header title for the canvas telemetry frame.
    """
    num_channels, num_samples = signals.shape
    names = channel_names if channel_names is not None else CHANNEL_NAMES[:num_channels]
    colors = channel_colors if channel_colors is not None else CHANNEL_COLORS[:num_channels]
    
    # Fallbacks if shapes mismatch
    if len(names) < num_channels:
        names += [f"Ch{i+1}" for i in range(len(names), num_channels)]
    if len(colors) < num_channels:
        colors += [CHANNEL_COLORS[i % len(CHANNEL_COLORS)] for i in range(len(colors), num_channels)]

    data_payload = []
    for ch in range(num_channels):
        ch_data = np.round(signals[ch, :], 2).tolist()
        data_payload.append(ch_data)

    payload_json = json.dumps(data_payload)
    channel_names_json = json.dumps(names)
    channel_colors_json = json.dumps(colors)
    title_json = json.dumps(title)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background-color: #06090e;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            }}
            .canvas-container {{
                position: relative;
                width: 100%;
                height: {height}px;
                background: radial-gradient(circle at 50% 50%, rgba(13, 20, 32, 0.95), rgba(6, 9, 14, 0.98));
                border: 1px solid rgba(0, 242, 254, 0.2);
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(0, 242, 254, 0.05);
            }}
            canvas {{
                display: block;
                width: 100%;
                height: 100%;
            }}
            .header-bar {{
                position: absolute;
                top: 8px;
                left: 12px;
                right: 12px;
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
                color: #00f2fe;
                text-transform: uppercase;
                pointer-events: none;
                z-index: 10;
                opacity: 0.85;
            }}
            .status-tag {{
                background: rgba(0, 242, 254, 0.1);
                border: 1px solid rgba(0, 242, 254, 0.3);
                padding: 2px 8px;
                border-radius: 4px;
                color: #00f2fe;
            }}
        </style>
    </head>
    <body>
        <div class="canvas-container">
            <div class="header-bar">
                <span id="titleTag"></span>
                <span class="status-tag">Status: Synced (rAF 60 FPS)</span>
            </div>
            <canvas id="visibleCanvas"></canvas>
        </div>

        <script>
            (function() {{
                const titleText = {title_json};
                document.getElementById('titleTag').textContent = titleText;
                const rawData = {payload_json};
                const channelNames = {channel_names_json};
                const channelColors = {channel_colors_json};
                
                const visibleCanvas = document.getElementById('visibleCanvas');
                const visibleCtx = visibleCanvas.getContext('2d', {{ alpha: false }});
                
                // -------------------------------------------------------------
                // 1. Double Buffering: Off-screen Canvas Setup
                // -------------------------------------------------------------
                const offscreenCanvas = document.createElement('canvas');
                const offscreenCtx = offscreenCanvas.getContext('2d', {{ alpha: false }});

                function resizeCanvases() {{
                    const rect = visibleCanvas.getBoundingClientRect();
                    const dpr = window.devicePixelRatio || 1;
                    
                    visibleCanvas.width = rect.width * dpr;
                    visibleCanvas.height = rect.height * dpr;
                    
                    offscreenCanvas.width = rect.width * dpr;
                    offscreenCanvas.height = rect.height * dpr;
                    
                    offscreenCtx.scale(dpr, dpr);
                }}

                window.addEventListener('resize', resizeCanvases);
                resizeCanvases();

                // -------------------------------------------------------------
                // 2. Off-screen Buffer Drawing Function
                // -------------------------------------------------------------
                function drawOffscreen(width, height) {{
                    // Clear off-screen background
                    offscreenCtx.fillStyle = '#06090e';
                    offscreenCtx.fillRect(0, 0, width, height);

                    const numChannels = rawData.length;
                    const channelHeight = height / numChannels;
                    const numSamples = rawData[0] ? rawData[0].length : 0;

                    // Draw grid lines & channel baselines
                    offscreenCtx.strokeStyle = 'rgba(0, 242, 254, 0.07)';
                    offscreenCtx.lineWidth = 1;
                    
                    // Vertical grid lines
                    const numGridCols = 10;
                    for (let c = 1; c < numGridCols; c++) {{
                        const x = (width / numGridCols) * c;
                        offscreenCtx.beginPath();
                        offscreenCtx.moveTo(x, 0);
                        offscreenCtx.lineTo(x, height);
                        offscreenCtx.stroke();
                    }}

                    // Draw each EEG trace
                    for (let ch = 0; ch < numChannels; ch++) {{
                        const centerY = (ch * channelHeight) + (channelHeight / 2) + 12;
                        const channelData = rawData[ch];
                        const color = channelColors[ch % channelColors.length];

                        // Channel baseline
                        offscreenCtx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
                        offscreenCtx.beginPath();
                        offscreenCtx.moveTo(40, centerY);
                        offscreenCtx.lineTo(width, centerY);
                        offscreenCtx.stroke();

                        // Channel Label
                        offscreenCtx.fillStyle = color;
                        offscreenCtx.font = '600 11px monospace';
                        offscreenCtx.fillText(channelNames[ch] || ('Ch' + (ch + 1)), 8, centerY + 3);

                        if (!channelData || channelData.length === 0) continue;

                        // Waveform Trace
                        offscreenCtx.strokeStyle = color;
                        offscreenCtx.lineWidth = 1.5;
                        offscreenCtx.shadowColor = color;
                        offscreenCtx.shadowBlur = 4;
                        offscreenCtx.beginPath();

                        const plotWidth = width - 45;
                        const dx = plotWidth / (numSamples - 1);

                        for (let i = 0; i < numSamples; i++) {{
                            const x = 45 + (i * dx);
                            // Scale microvolts: 1 µV = 0.5 pixels
                            const val = channelData[i];
                            const y = centerY - (val * 0.45);

                            if (i === 0) {{
                                offscreenCtx.moveTo(x, y);
                            }} else {{
                                offscreenCtx.lineTo(x, y);
                            }}
                        }}
                        offscreenCtx.stroke();
                        offscreenCtx.shadowBlur = 0; // Reset glow for performance
                    }}
                }}

                // -------------------------------------------------------------
                // 3. Hardware-Synchronized Render Loop (requestAnimationFrame)
                // -------------------------------------------------------------
                let animFrameId = null;

                function renderLoop() {{
                    const rect = visibleCanvas.getBoundingClientRect();
                    const width = rect.width;
                    const height = rect.height;

                    // Step 1: Render scene to the off-screen buffer
                    drawOffscreen(width, height);

                    // Step 2: Single atomic blit/copy to the visible screen
                    visibleCtx.drawImage(offscreenCanvas, 0, 0);

                    // Step 3: Request next animation frame aligned with display refresh rate
                    animFrameId = requestAnimationFrame(renderLoop);
                }}

                // Cleanup on unmount/unload to prevent orphaned requestAnimationFrame CPU loops
                function cleanup() {{
                    if (animFrameId) {{
                        cancelAnimationFrame(animFrameId);
                        animFrameId = null;
                    }}
                    window.removeEventListener('resize', resizeCanvases);
                }}
                window.addEventListener('unload', cleanup);
                window.addEventListener('beforeunload', cleanup);

                // Start render loop
                renderLoop();
            }})();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height + 10, scrolling=False)
