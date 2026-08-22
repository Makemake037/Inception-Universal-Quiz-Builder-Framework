// --- Advanced Layout UI Controllers & Context State ---
const mainContainer = document.getElementById('main-container');
const quizColumn = document.getElementById('quiz-column');
const canvasColumn = document.getElementById('canvas-column');
const resizer = document.getElementById('resizer');

const canvas = document.getElementById('drawCanvas');
const ctx = canvas.getContext('2d');

// State Engine Defaults
let history = [];
let isDrawing = false;
let currentTool = 'pen'; // Core modes: 'pen' or 'eraser'
let userSelectedColor = '#222222';
let currentStrokeWeight = 3;

function initCanvasStyles() {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    updateContextBrushStyles();
}

function updateContextBrushStyles() {
    if (currentTool === 'eraser') {
        ctx.strokeStyle = '#ffffff'; // Match workspace canvas element background string
        ctx.lineWidth = currentStrokeWeight * 2.5; // Scale structural size out for fast erasing
    } else {
        ctx.strokeStyle = userSelectedColor;
        ctx.lineWidth = currentStrokeWeight;
    }
}

function setTool(toolMode) {
    currentTool = toolMode;
    const penBtn = document.getElementById('tool-pen');
    const eraserBtn = document.getElementById('tool-eraser');
    
    if (toolMode === 'eraser') {
        eraserBtn.style.background = '#dc3545';
        penBtn.style.background = '#6c757d';
        canvas.style.cursor = 'cell';
    } else {
        penBtn.style.background = '#007bff';
        eraserBtn.style.background = '#6c757d';
        canvas.style.cursor = 'crosshair';
    }
    updateContextBrushStyles();
}

function updateColor(hexValue) {
    userSelectedColor = hexValue;
    document.getElementById('canvasColorPicker').value = hexValue;
    if (currentTool === 'pen') {
        updateContextBrushStyles();
    }
}

function updateStrokeWeight(widthVal) {
    currentStrokeWeight = parseInt(widthVal, 10);
    document.getElementById('brushSlider').value = widthVal;
    document.getElementById('weightValDisplay').innerText = `${widthVal}px`;
    updateContextBrushStyles();
}

function fitCanvasToContainer() {
    let currentSnapshot = history.length > 0 ? ctx.getImageData(0, 0, canvas.width, canvas.height) : null;
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    initCanvasStyles();
    if (currentSnapshot) ctx.putImageData(currentSnapshot, 0, 0);
}

function toggleCanvas() {
    document.body.classList.toggle('scratchpad-active');
    const isActive = document.body.classList.contains('scratchpad-active');

    if (isActive) {
        quizColumn.style.width = "50%";
        canvasColumn.style.width = "50%";
        setTimeout(fitCanvasToContainer, 50);
    } else {
        quizColumn.style.width = "100%";
    }
}

// --- Resizing Event Handlers ---
resizer.addEventListener('mousedown', function(e) {
    e.preventDefault();
    resizer.classList.add('dragging');
    document.addEventListener('mousemove', resizeHandler);
    document.addEventListener('mouseup', stopResizeHandler);
});

function resizeHandler(e) {
    const containerWidth = mainContainer.clientWidth;
    let pointerX = e.clientX;
    let quizWidthPercent = (pointerX / containerWidth) * 100;
    
    if (quizWidthPercent < 20) quizWidthPercent = 20;
    if (quizWidthPercent > 80) quizWidthPercent = 80;

    quizColumn.style.width = `${quizWidthPercent}%`;
    canvasColumn.style.width = `${100 - quizWidthPercent}%`;

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    initCanvasStyles();
}

function stopResizeHandler() {
    resizer.classList.remove('dragging');
    document.removeEventListener('mousemove', resizeHandler);
    document.removeEventListener('mouseup', stopResizeHandler);
    fitCanvasToContainer();
}

// --- Pure Interaction Canvas Painting Code Loop ---
canvas.addEventListener('mousedown', (e) => {
    isDrawing = true;
    history.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
});

canvas.addEventListener('mousemove', (e) => {
    if (isDrawing) {
        ctx.lineTo(e.offsetX, e.offsetY);
        ctx.stroke();
    }
});

canvas.addEventListener('mouseup', () => { isDrawing = false; });
canvas.addEventListener('mouseleave', () => { isDrawing = false; });

function undo() { if (history.length > 0) ctx.putImageData(history.pop(), 0, 0); }
function clearCanvas() { ctx.clearRect(0, 0, canvas.width, canvas.height); history = []; }

function saveCanvas() {
    const saveCanvas = document.createElement('canvas');
    const saveCtx = saveCanvas.getContext('2d');
    saveCanvas.width = canvas.width;
    saveCanvas.height = canvas.height;
    saveCtx.fillStyle = '#ffffff';
    saveCtx.fillRect(0, 0, saveCanvas.width, saveCanvas.height);
    saveCtx.drawImage(canvas, 0, 0);

    const link = document.createElement('a');
    link.download = `quiz-sketch-${Date.now()}.png`;
    link.href = saveCanvas.toDataURL('image/png');
    link.click();
}

// ==========================================
// CENTRALIZED INTERACTIVE KEYBOARD HOTKEYS
// ==========================================
window.addEventListener('keydown', (e) => {
    const activeElem = document.activeElement.tagName.toLowerCase();
    // Do not trigger hotkeys if typing in inputs, text fields, or selectors
    if (activeElem === 'input' || activeElem === 'textarea' || activeElem === 'select') {
        return;
    }

    const key = e.key.toLowerCase();

    // Standard Actions Mapping
    if (key === 'd') {
        e.preventDefault();
        toggleCanvas();
    } else if (key === 'p') {
        e.preventDefault();
        setTool('pen');
    } else if (key === 'e') {
        e.preventDefault();
        setTool('eraser');
    } else if (key === 'c') {
        e.preventDefault();
        document.getElementById('canvasColorPicker').click(); // Pop native hex node layout open
    } else if (key === 's') {
        e.preventDefault();
        // Cycle brush options cleanly through 2px -> 5px -> 9px -> 13px loops
        let currentWeights = [2, 5, 9, 13];
        let nextIndex = (currentWeights.indexOf(currentStrokeWeight) + 1) % currentWeights.length;
        updateStrokeWeight(currentWeights[nextIndex]);
    } else if ((e.ctrlKey || e.metaKey) && key === 'z') {
        e.preventDefault();
        undo();
    }
});