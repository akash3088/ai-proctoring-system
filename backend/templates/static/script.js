const form = document.getElementById("loginForm");
const statusDiv = document.getElementById("status");

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("username").value;

    statusDiv.innerText = "Starting Exam... Please allow webcam and mic.";

    // Call backend API to start AI Proctor
    try {
        const response = await fetch("/start_exam", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username })
        });

        const data = await response.json();
        statusDiv.innerText = data.message;
    } catch (err) {
        statusDiv.innerText = "Error starting exam!";
        console.error(err);
    }
});
