// static/js/animations.js
// Corrected Click Handler Logic

document.addEventListener('DOMContentLoaded', function() {
    // --- DOM Element References ---
    const eggContainer = document.getElementById('egg-container');
    const bodyElement = document.body;
    const hintContainer = document.getElementById('hint-container');
    const startHuntButton = document.getElementById('start-hunt-button');
    const homeEggStatus = document.getElementById('home-egg-status');
    const foundCountSpan = document.getElementById('found-count');
    const totalCountSpan = document.getElementById('total-count');
    const submitButton = document.getElementById('submit-button');
    const minigameInstructions = document.getElementById('minigame-instructions');
    const minigameBasket = document.getElementById('minigame-basket');
    const minigameWinMessage = document.getElementById('minigame-win-message');

    // --- Configuration & Constants ---
    const numEggs = 16;
    const baseEggPath = '/static/images/egg';
    const adminSequence = ['1', '2', '3', '4'];

    // Physics Parameters
    const MOVING_BASKET_SPEED = 1.5;
    const boundaryPadding = 10;
    const dragFactor = 0.99;
    const angularDragFactor = 0.98;
    const gravity = 0.0;
    const bounceDamping = 0.6;
    const clickImpulseStrength = 8;
    const maxVelocity = 10;
    const baseSpinSpeedFactor = 0.03;
    const clickSpinMultiplier = 4;
    const baseWidth = 28; // Adjusted for CSS max size
    const baseHeight = 40; // Adjusted for CSS max size
    const homePageEggSpawnDelay = 150;
    const collisionPushFactor = 0.5;
    const bottomBoundaryFactor = 0.90;

    // Basket & Minigame Target Parameters
    const BASE_BASKET_WIDTH = 200;
    const BASKET_SCALE_FACTOR = 1.4;
    const targetAreaWidthFactor = 0.6;
    const targetAreaHeightFactor = 0.5;
    const targetAreaOffsetXFactor = 0.2;
    const targetAreaOffsetYFactor = 0.4;

    // --- State Variables ---
    let currentAdminSequence = [];
    let hintRevealed = false;
    const hintEggId = bodyElement ? bodyElement.dataset.hintEggId : null;
    const currentStepScale = bodyElement ? parseFloat(bodyElement.dataset.currentScale) : 1.0;
    const firstAccessDone = bodyElement ? bodyElement.dataset.firstAccessDone === 'true' : false;
    const isMinigameType = bodyElement ? bodyElement.dataset.isMinigameType : 'standard';
    const isMinigame = (isMinigameType === 'basket' || isMinigameType === 'moving_basket');

    const eggs = [];
    let animationFrameId = null;
    let homePageEggsFound = 0;
    let isHomePage = (window.location.pathname === '/');
    let minigameWon = false;

    // Moving Basket State
    let basketX = 0;
    let basketVX = 0;
    let basketWidth = 0;

    // --- Initialization ---
    function initialize() {
        if (!eggContainer && (isHomePage || isMinigame || (hintEggId !== null && hintEggId !== ''))) {
             console.error("Initialize Error: #egg-container!"); return;
        }
        if (isHomePage) { setupHomePage(); }
        else if (isMinigameType === 'moving_basket') { setupMovingBasketMinigame(); startAnimationLoop(); }
        else if (isMinigameType === 'basket') { setupStandardBasketMinigame(); startAnimationLoop(); }
        else if (hintEggId !== null && hintEggId !== '') { createAndPlaceEggs(currentStepScale); startAnimationLoop(); }
        else { console.log("Not initializing eggs."); }
    }

    // --- Home Page Specific Setup ---
    function setupHomePage() {
        if (startHuntButton) { startHuntButton.addEventListener('click', handleStartHuntClick); console.log("Listener added."); }
        else { console.error("Start Button not found!"); }
        if (totalCountSpan) totalCountSpan.textContent = numEggs;
        if (foundCountSpan) foundCountSpan.textContent = homePageEggsFound;
    }
    function handleStartHuntClick() {
        console.log("Start clicked!");
        if (startHuntButton) { startHuntButton.disabled = true; startHuntButton.textContent = "Catch!"; }
        if (homeEggStatus) homeEggStatus.style.display = 'block';
        spawnHomePageEggsOneByOne();
    }
    function spawnHomePageEggsOneByOne() {
        let i = 1;
        const interval = setInterval(() => {
            if (i > numEggs) { clearInterval(interval); console.log("Spawning complete."); return; }
            const egg = createOneEgg(i, 1.0);
            if (egg && i === 1 && !animationFrameId) startAnimationLoop();
            i++;
        }, homePageEggSpawnDelay);
    }

    // --- Minigame Specific Setup ---
    function setupStandardBasketMinigame() {
        console.log("Setting up Standard Basket");
        if (minigameBasket) {
            minigameBasket.style.display = 'block';
            const bw = BASE_BASKET_WIDTH * BASKET_SCALE_FACTOR;
            minigameBasket.style.width = `${bw}px`;
            minigameBasket.style.height = 'auto';
            minigameBasket.style.right = '5px'; minigameBasket.style.left = 'auto'; minigameBasket.style.bottom = '10%';
            console.log(`Standard Basket: ${bw}px`);
        } else { console.error("Basket element not found!"); }
        createAndPlaceEggs(currentStepScale);
    }
    function setupMovingBasketMinigame() {
        console.log("Setting up Moving Basket");
        if (!eggContainer) return;
        if (minigameBasket) {
            minigameBasket.style.display = 'block';
            basketWidth = BASE_BASKET_WIDTH * BASKET_SCALE_FACTOR;
            minigameBasket.style.width = `${basketWidth}px`; minigameBasket.style.height = 'auto';
            basketX = eggContainer.clientWidth - basketWidth - boundaryPadding;
            minigameBasket.style.left = `${basketX}px`; minigameBasket.style.right = 'auto'; minigameBasket.style.bottom = '10%';
            basketVX = -MOVING_BASKET_SPEED;
            console.log(`Moving Basket: ${basketWidth}px at X=${basketX}`);
        } else { console.error("Basket element not found!"); }
        createAndPlaceEggs(currentStepScale);
    }

    // --- Egg Creation (Generic - creates one) ---
    function createOneEgg(index, scale) {
        if (!eggContainer) return null;
        const containerWidth = eggContainer.clientWidth; const containerHeight = eggContainer.clientHeight;
        if (containerWidth <= 0 || containerHeight <= 0) { console.warn(`No container size for egg ${index}`); return null; }
        const eggElement = document.createElement('img');
        const imageNum = ((index - 1) % 8) + 1;
        eggElement.src = `${baseEggPath}${imageNum}.png`; eggElement.alt = `Egg ${index}`;
        eggElement.classList.add('easter-egg'); eggElement.dataset.eggId = String(index);
        eggElement.style.transformOrigin = 'center center';
        eggElement.onerror = () => console.error(`Failed load: ${eggElement.src}`);
        const scaledWidth = baseWidth * scale; const scaledHeight = baseHeight * scale;
        const eggState = { element: eggElement, id: String(index),
            x: Math.random()*(containerWidth - scaledWidth - 2*boundaryPadding) + boundaryPadding + scaledWidth/2,
            y: Math.random()*(containerHeight - scaledHeight - 2*boundaryPadding) + boundaryPadding + scaledHeight/2,
            vx: (Math.random()-0.5)*(isHomePage ? 4 : 2), vy: (Math.random()-0.5)*(isHomePage ? 4 : 2) + gravity,
            angle: Math.random()*360, va: (Math.random()-0.5)*baseSpinSpeedFactor*(isHomePage ? 2 : 1),
            scale: scale, width: scaledWidth, height: scaledHeight,
            clickedHome: false, isInBasket: false };
        updateElementStyle(eggState);
        eggElement.addEventListener('click', handleEggClick);
        eggContainer.appendChild(eggElement); eggs.push(eggState);
        return eggState;
    }

    // --- Egg Creation (Step Pages / Minigame) ---
    function createAndPlaceEggs(stepScale) {
        console.log(`Creating ${numEggs} eggs (scale ${stepScale.toFixed(3)})`);
        if (!eggContainer) { console.error("#egg-container missing!"); return; }
        const containerWidth = eggContainer.clientWidth; const containerHeight = eggContainer.clientHeight;
        if (containerWidth <= 0 || containerHeight <= 0) { setTimeout(() => createAndPlaceEggs(stepScale), 100); return; }
        const existingEggs = eggContainer.querySelectorAll('img.easter-egg');
        existingEggs.forEach(el => el.remove()); console.log(`Removed ${existingEggs.length} eggs.`);
        eggs.length = 0;
        for (let i = 1; i <= numEggs; i++) { createOneEgg(i, stepScale); }
        console.log(`Created ${eggs.length} eggs.`);
        if (isMinigame && minigameBasket) minigameBasket.style.display = 'block';
        if (!animationFrameId) startAnimationLoop();
    }

    // --- Animation Loop & Control ---
    function startAnimationLoop() {
        if (animationFrameId) return;
        function gameLoop(timestamp) {
            try {
                 if (!isMinigame || !minigameWon ) { updatePhysics(); renderEggs(); }
                 if (isMinigame && !minigameWon) { checkMinigameWinCondition(); }
                 animationFrameId = requestAnimationFrame(gameLoop);
            } catch (error) { console.error("Animation loop error:", error); stopAnimationLoop(); }
        }
        animationFrameId = requestAnimationFrame(gameLoop); console.log("Animation started.");
    }
    function stopAnimationLoop() {
         if (animationFrameId) { cancelAnimationFrame(animationFrameId); animationFrameId = null; console.log("Animation stopped."); }
    }

    // --- Physics Update ---
    function updatePhysics() {
        if (!eggContainer || !eggs.length) return;
        const cw = eggContainer.clientWidth; const ch = eggContainer.clientHeight;
        if (cw <= 0 || ch <= 0) return;
        const effBottom = ch * bottomBoundaryFactor - boundaryPadding;

        // Move Basket
        if (isMinigameType === 'moving_basket' && !minigameWon) {
             basketX += basketVX;
             if ((basketX < boundaryPadding && basketVX < 0) || (basketX + basketWidth > cw - boundaryPadding && basketVX > 0)) {
                 basketVX *= -1; basketX = Math.max(boundaryPadding, Math.min(basketX, cw - boundaryPadding - basketWidth));
             }
        }
        // Update Eggs
        eggs.forEach(egg => {
            if (isMinigame && egg.isInBasket) return; // Skip settled
            egg.vy += gravity; egg.vx *= dragFactor; egg.vy *= dragFactor; egg.va *= angularDragFactor;
            const speed = Math.sqrt(egg.vx*egg.vx + egg.vy*egg.vy);
            if (speed > maxVelocity) { egg.vx = (egg.vx/speed)*maxVelocity; egg.vy = (egg.vy/speed)*maxVelocity; }
            egg.x += egg.vx; egg.y += egg.vy; egg.angle = (egg.angle + egg.va*(180/Math.PI)) % 360;
            const hw = egg.width / 2; const hh = egg.height / 2;
            if ((egg.x-hw < boundaryPadding && egg.vx < 0) || (egg.x+hw > cw-boundaryPadding && egg.vx > 0)) {
                 egg.vx *= -bounceDamping; egg.x = Math.max(boundaryPadding+hw, Math.min(egg.x, cw-boundaryPadding-hw));
                 egg.va += (Math.random()-0.5)*baseSpinSpeedFactor*0.5;
            }
            if (egg.y-hh < boundaryPadding && egg.vy < 0) { // Top
                 egg.vy *= -bounceDamping; egg.y = boundaryPadding + hh; egg.va += (Math.random()-0.5)*baseSpinSpeedFactor*0.5;
            } else if (egg.y+hh > effBottom && egg.vy > 0) { // Bottom
                 egg.vy *= -bounceDamping; egg.y = effBottom - hh;
                 if (gravity > 0 && Math.abs(egg.vy) < 0.1) egg.vy = 0;
                 egg.va += (Math.random()-0.5)*baseSpinSpeedFactor*0.5;
            }
        });
        if (!isHomePage) { handleEggCollisions(); }
    }

    // --- Collision Handling ---
    function handleEggCollisions() {
        for (let i = 0; i < eggs.length; i++) {
            const e1 = eggs[i]; if (isMinigame && e1.isInBasket) continue;
            for (let j = i + 1; j < eggs.length; j++) {
                const e2 = eggs[j]; if (isMinigame && e2.isInBasket) continue;
                const dx=e2.x-e1.x, dy=e2.y-e1.y; const distSq=dx*dx+dy*dy;
                const r1=e1.width/2, r2=e2.width/2; const radSum=r1+r2; const radSumSq=radSum*radSum;
                if (distSq < radSumSq && distSq > 0.01) {
                    const dist=Math.sqrt(distSq); const overlap=radSum-dist;
                    const nx=dx/dist, ny=dy/dist; const push=overlap*collisionPushFactor*0.5;
                    if (!isMinigame||!e1.isInBasket) { e1.x-=nx*push; e1.y-=ny*push; }
                    if (!isMinigame||!e2.isInBasket) { e2.x+=nx*push; e2.y+=ny*push; }
                    const rvx=e2.vx-e1.vx, rvy=e2.vy-e1.vy; const dot=rvx*nx+rvy*ny;
                    if (dot<0) { const impMag=-dot*(1+bounceDamping)*0.5;
                         if (!isMinigame||!e1.isInBasket) { e1.vx-=nx*impMag; e1.vy-=ny*impMag; e1.va+=(Math.random()-0.5)*baseSpinSpeedFactor*0.2; }
                         if (!isMinigame||!e2.isInBasket) { e2.vx+=nx*impMag; e2.vy+=ny*impMag; e2.va-=(Math.random()-0.5)*baseSpinSpeedFactor*0.2; } } } } }
    }

    // --- Rendering ---
    function renderEggs() {
        eggs.forEach(updateElementStyle);
        if (isMinigameType === 'moving_basket' && minigameBasket) {
            const nl = `${basketX}px`; if (minigameBasket.style.left !== nl) { minigameBasket.style.left = nl; } }
    }
    function updateElementStyle(egg) {
        const tlx=egg.x-egg.width/2, tly=egg.y-egg.height/2;
        try { const tfV=`rotate(${egg.angle}deg) scale(${egg.scale})`;
            if (egg.element.style.transform !== tfV) { egg.element.style.transform = tfV; }
            if (egg.element.style.left !== `${tlx}px`) { egg.element.style.left = `${tlx}px`; }
            if (egg.element.style.top !== `${tly}px`) { egg.element.style.top = `${tly}px`; }
        } catch (e) { console.error(`Style Error Egg ${egg.id}:`, e); }
    }

    // --- Click Handling (Corrected Structure) ---
    function handleEggClick(event) {
        event.stopPropagation();
        const clickedElement = event.target;
        const clickedEggId = clickedElement.dataset.eggId;
        if (!clickedEggId) { console.log("Click ignored: No ID"); return; }
        const clickedEggState = eggs.find(e => e.id === clickedEggId);
        if (!clickedEggState) { console.log(`Click ignored: No state for ${clickedEggId}`); return; }

        // --- Branch based on page type ---
        if (isHomePage) {
            // --- Home Page Click Logic ---
            console.log(`HOME: Click Egg #${clickedEggId}, Clicked? ${clickedEggState.clickedHome}`);
            if (!clickedEggState.clickedHome) {
                clickedEggState.clickedHome = true; homePageEggsFound++;
                console.log(`HOME: Found! Count: ${homePageEggsFound}/${numEggs}`);
                clickedElement.style.opacity = '0.4'; clickedElement.style.cursor = 'default';
                if (foundCountSpan) foundCountSpan.textContent = homePageEggsFound;
                if (homePageEggsFound >= numEggs) {
                     console.log("HOME: All found! Redirecting..."); stopAnimationLoop();
                     window.location.href = '/start_hunt'; return;
                } else { console.log("HOME: Not complete."); }
            } else {
                 console.log(`HOME: Egg #${clickedEggId} already clicked.`);
                 const ixh = (Math.random()-0.5)*2*clickImpulseStrength*0.3;
                 const iyh = (Math.random()-0.5)*2*clickImpulseStrength*0.3;
                 clickedEggState.vx += ixh; clickedEggState.vy += iyh;
            }
             console.log(`HOME: Click processing finished for #${clickedEggId}.`);

        } else if (isMinigame) {
            // --- Minigame Click Logic ---
            if (minigameWon) { console.log("Minigame won."); return; }
            if (clickedEggState.isInBasket) { console.log(`Egg ${clickedEggId} settled.`); return; }
            console.log(`MINIGAME: Click Egg #${clickedEggId}`);
            const rect = eggContainer.getBoundingClientRect();
            const clx = event.clientX - rect.left, cly = event.clientY - rect.top;
            const dx = clickedEggState.x - clx, dy = clickedEggState.y - cly; const dist = Math.sqrt(dx*dx+dy*dy);
            let ix=0, iy=0;
            if (dist > 1) { ix = (dx/dist)*clickImpulseStrength; iy = (dy/dist)*clickImpulseStrength; }
            else { ix = (Math.random()-0.5)*2*clickImpulseStrength; iy = (Math.random()-0.5)*2*clickImpulseStrength; }
            const ia = (Math.random()-0.5)*baseSpinSpeedFactor*clickSpinMultiplier;
            clickedEggState.vx += ix; clickedEggState.vy += iy; clickedEggState.va += ia;
            console.log(`MINIGAME: Applied impulse`);

        } else {
            // --- Standard Step Page Click Logic ---
            console.log(`STANDARD: Click Egg #${clickedEggId}. Hint: #${hintEggId}. AdminDone: ${firstAccessDone}`);
            let adminRedirect = handleAdminSequenceCheck(clickedEggId); // Uses image# 1-8
            if (adminRedirect) return;

            let correctHint = false;
            if (hintEggId && !hintRevealed) {
                 const imgNum = ((parseInt(clickedEggId, 10) - 1) % 8) + 1;
                 if (String(imgNum) === String(hintEggId)) { correctHint = true; showHint(); restoreColorScheme(); }
                 else { applyPaleColorScheme(); }
                 applyVisualFeedback(clickedElement, correctHint);
            } else { console.log(hintEggId ? "Hint revealed." : "No hint egg."); }

            const ixs = (Math.random()-0.5)*2*clickImpulseStrength;
            const iys = (Math.random()-0.5)*2*clickImpulseStrength;
            const ias = (Math.random()-0.5)*baseSpinSpeedFactor*clickSpinMultiplier;
            clickedEggState.vx += ixs; clickedEggState.vy += iys; clickedEggState.va += ias;
            console.log(`STANDARD: Applied impulse`);
        }
    } // End handleEggClick

    // --- Admin Sequence Check ---
    function handleAdminSequenceCheck(clickedEggId_1_16) {
         if (window.location.pathname.startsWith('/admin') || window.location.pathname.startsWith('/secret-qr')) return false;
         const imageNum = String(((parseInt(clickedEggId_1_16, 10) - 1) % 8) + 1);
         // console.log(`Admin check using image#: ${imageNum}`);

         // Check based on firstAccessDone flag read at top


         // Subsequent times: check sequence
         currentAdminSequence.push(imageNum);
         console.log("Subsequent Admin Check - Seq:", currentAdminSequence);
         let match = currentAdminSequence.every((id, i) => i < adminSequence.length && id === adminSequence[i]);

         if (!match || currentAdminSequence.length > adminSequence.length) {
             console.log("Wrong admin sequence step, resetting.");
             currentAdminSequence = [];
             if (imageNum === adminSequence[0]) { currentAdminSequence.push(imageNum); } // Restart if first char clicked
             return false;
         }
         if (match && currentAdminSequence.length === adminSequence.length) {
             console.log("Admin sequence correct! Redirecting...");
             window.location.href = '/admin/grant_access'; // Use grant route
             return true;
         }
         console.log("Admin sequence partially correct...");
         return false;
     }

    // --- Hint Revealing ---
    function showHint() {
        if (hintContainer && !hintRevealed) { console.log("Revealing hint."); hintContainer.style.display = 'block'; hintRevealed = true; }
    }

    // --- Color Scheme Control ---
    function applyPaleColorScheme() { if (bodyElement) bodyElement.classList.add('pale-mode'); }
    function restoreColorScheme() { if (bodyElement) bodyElement.classList.remove('pale-mode'); }

    // --- Visual Feedback on Click ---
    function applyVisualFeedback(eggElement, isCorrect) {
        eggElement.classList.remove('correct-hint-egg', 'wrong-hint-egg');
        void eggElement.offsetWidth; const cls = isCorrect ? 'correct-hint-egg' : 'wrong-hint-egg';
        eggElement.classList.add(cls); setTimeout(() => eggElement.classList.remove(cls), isCorrect ? 3000 : 500);
    }

    // --- Minigame Win Condition Check ---
    function checkMinigameWinCondition() {
        if (!isMinigame || minigameWon || !minigameBasket || !eggContainer || eggs.length < numEggs) return;
        const basketRect = minigameBasket.getBoundingClientRect(); const containerRect = eggContainer.getBoundingClientRect();
        if (!containerRect || containerRect.width <= 0) return;
        const bLeft = basketRect.left - containerRect.left; const bTop = basketRect.top - containerRect.top;
        const bW = basketRect.width; const bH = basketRect.height;
        const tW = bW * targetAreaWidthFactor; const tH = bH * targetAreaHeightFactor;
        const tL = bLeft + (bW * targetAreaOffsetXFactor); const tT = bTop + (bH * targetAreaOffsetYFactor);
        const tR = tL + tW; const tB = tT + tH;
        // Debug Box Visualization (Keep commented out)
        /* ... */
        let currentInBasket = 0;
        eggs.forEach(egg => {
            if (!egg.isInBasket) {
                const inside = (egg.x > tL && egg.x < tR && egg.y > tT && egg.y < tB);
                if (inside) {
                     console.log(`>>> Egg ${egg.id} in target! Settling.`);
                     if (!egg.element) { console.error(`Null element egg ${egg.id}`); egg.isInBasket=true; egg.vx=0; egg.vy=0; egg.va=0;}
                     else { egg.isInBasket=true; egg.vx=0; egg.vy=0; egg.va=0; egg.element.style.zIndex=0; egg.element.style.opacity='0'; egg.element.style.pointerEvents='none'; }
                }
            }
            if (egg.isInBasket) currentInBasket++;
        });
        if (currentInBasket === numEggs && !minigameWon) { handleMinigameWin(); }
    }

    // --- Minigame Win Handler ---
    function handleMinigameWin() {
        console.log("MINIGAME WON!"); minigameWon = true;
        if (minigameInstructions) minigameInstructions.style.display = 'none';
        if (minigameWinMessage) minigameWinMessage.style.display = 'block';
        enableSubmitButton();
        const debugBox = document.getElementById('debug-target-box'); if (debugBox) debugBox.remove();
    }

    // --- Enable Submit Button ---
    function enableSubmitButton() {
        if (submitButton) { submitButton.disabled = false; submitButton.textContent = "Check Answer"; console.log("Submit enabled."); }
        else { console.warn("Submit button not found."); }
    }

    // --- Start Initialization ---
    initialize();

}); // End DOMContentLoaded