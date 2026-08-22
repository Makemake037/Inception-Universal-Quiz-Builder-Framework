  /* --- Countdown Timer --- */
    function startCountdown() {
        if (timerInterval) clearInterval(timerInterval);
        updateTimerDisplay();
        
        timerInterval = setInterval(() => {
            if (totalSecondsLeft <= 0) {
                clearInterval(timerInterval);
                document.getElementById('timerDisplay').innerText = "00:00 - TIME UP";
                alert("Time is up!");
                return;
            }
            totalSecondsLeft--;
            updateTimerDisplay();
        }, 1000);
    }

    function updateTimerDisplay() {
        const minutes = Math.floor(totalSecondsLeft / 60);
        const seconds = totalSecondsLeft % 60;
        document.getElementById('timerDisplay').innerText = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function resetTimerFromDropdown() {
        const selectElement = document.getElementById('durationSelect');
        const selectedMinutes = parseInt(selectElement.value, 10);
        totalSecondsLeft = selectedMinutes * 60;
        startCountdown();
    }
