document.addEventListener("DOMContentLoaded", function() {
    
    // ==========================================
    // 1. GLOBAL SLIDER LOGIC (Click & Drag Only)
    // ==========================================
    
    // Track which slider is currently being dragged
    let activeSlider = null;

    const sliders = document.querySelectorAll('.ba-slider-container');

    sliders.forEach(slider => {
        // Prevent default browser dragging for images (stops "ghost" images)
        const images = slider.querySelectorAll('img');
        images.forEach(img => {
            img.addEventListener('dragstart', (e) => e.preventDefault());
        });

        // MOUSE DOWN: Start tracking this specific slider
        slider.addEventListener('mousedown', (e) => {
            // CRITICAL FIX: If user clicks the "Reel Overlay" (video), IGNORE the drag.
            // This prevents the slider from jumping when interacting with the video area.
            if (e.target.closest('.reel-layer')) return;

            activeSlider = slider;
            updateSlider(e, slider); // Jump to click spot immediately
        });

        // TOUCH START: Start tracking (Mobile)
        slider.addEventListener('touchstart', (e) => {
            if (e.target.closest('.reel-layer')) return;
            
            activeSlider = slider;
            updateSlider(e, slider);
        }, { passive: false });
    });

    // WINDOW LISTENERS (Handles the drag movement globally)
    // This ensures smooth dragging even if mouse leaves the box
    
    // MOUSE MOVE
    window.addEventListener('mousemove', (e) => {
        if (!activeSlider) return; // If not clicking, DO NOTHING.
        e.preventDefault(); // Stop text selection
        updateSlider(e, activeSlider);
    });

    // MOUSE UP
    window.addEventListener('mouseup', () => {
        activeSlider = null; // Stop tracking immediately
    });

    // TOUCH MOVE (Mobile)
    window.addEventListener('touchmove', (e) => {
        if (!activeSlider) return;
        updateSlider(e, activeSlider);
    }, { passive: false });

    // TOUCH END (Mobile)
    window.addEventListener('touchend', () => {
        activeSlider = null;
    });


    // THE MATH (Calculates the width)
    function updateSlider(e, container) {
        const overlay = container.querySelector('.img-overlay');
        const handle = container.querySelector('.slider-handle');
        const rect = container.getBoundingClientRect();
        
        let clientX;

        // Get X position from Mouse or Touch
        if(e.type.includes('touch')) {
            clientX = e.touches[0].clientX;
        } else {
            clientX = e.clientX;
        }

        let x = clientX - rect.left;

        // Constraint logic (0 to Width)
        if (x < 0) x = 0;
        if (x > rect.width) x = rect.width;

        const percentage = (x / rect.width) * 100;

        // Update CSS
        overlay.style.width = percentage + "%";
        handle.style.left = percentage + "%";
    }

    // ==========================================
    // 2. HORIZONTAL SCROLL (MOUSE WHEEL)
    // ==========================================
    const scrollContainer = document.querySelector('.gallery-scroll-container');
    if (scrollContainer) {
        scrollContainer.addEventListener("wheel", (evt) => {
            evt.preventDefault();
            scrollContainer.scrollLeft += evt.deltaY;
        });
    }
});

// ==========================================
// 3. TOGGLE REEL LOGIC (Single Button Control)
// ==========================================

function toggleReel(button, link) {
    // 1. Find the card and the hidden layer
    const card = button.closest('.work-card');
    const reelLayer = card.querySelector('.reel-layer');
    const iframe = reelLayer.querySelector('.reel-iframe');

    // 2. Check if it is currently visible
    const isVisible = reelLayer.style.display === 'flex';

    if (isVisible) {
        // --- ACTION: CLOSE IT ---
        reelLayer.style.display = 'none';
        iframe.src = ""; // Stop video playback
        
        // Reset Button UI to "Watch Reel"
        button.innerHTML = '<i class="fa-brands fa-instagram"></i> Watch Reel';
        button.classList.remove('active-reel-btn'); 
    } else {
        // --- ACTION: OPEN IT ---
        iframe.src = link;
        reelLayer.style.display = 'flex';
        
        // Change Button UI to "Close Reel"
        button.innerHTML = '<i class="fa-solid fa-xmark"></i> Close Reel';
        button.classList.add('active-reel-btn'); 
    }
}