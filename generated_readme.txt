A fun, local network web application designed for a family Easter egg hunt. It includes question steps accessed via QR codes, interactive minigames, security "exploits" for educational purposes, and AI integration using Ollama for flexible answer checking.

## Features

*   **Fibonacci Step Progression:** Questions follow the Fibonacci sequence (1, 2, 3, 5...).
*   **QR Code Integration:** Designed to be used with physical QR codes pointing to specific step URLs.
*   **Ollama Answer Checking:** Uses a local Ollama LLM (e.g., Llama 3.2) to evaluate user answers flexibly and provide "snarky" feedback.
*   **Interactive Animations:** Features bouncing/spinning Easter eggs using JavaScript physics simulation.
*   **Minigames:** Includes two alternating minigames every 3rd step:
    *   **Static Basket:** Collect eggs in a stationary basket.
    *   **Moving Basket:** Collect eggs in a side-to-side moving basket.
*   **Home Page Challenge:** Users must click all 16 spawned eggs on the home page before starting the first question.
*   **Hint System:** On standard steps, clicking a specific randomly chosen egg reveals the hint.
*   **Progressive Difficulty:**
    *   Eggs visually shrink over steps (with a minimum size limit).
    *   Incorrect answers apply a temporary shrinking penalty (reset on correct answer, capped by step number).
*   **Admin Console:**
    *   **Fake Console:** A complex-looking, interactive decoy console accessed via a secret click sequence (`1, 2, 3, 4` based on egg *image* number 1-8). Most interactions lead to an "Oops" page.
    *   **Secret Checkbox:** A specific checkbox ("Engage Relativity Plus Filter") within the fake console reveals links to the real admin functions.
    *   **Real Admin (Questions):** Displays the next 3 upcoming questions and answers. Includes toggles for game modes.
    *   **Real Admin (Print QRs):** Generates and displays all QR codes for the hunt steps, including placement hints, ready for printing.
    *   **Real Admin (App QR):** Displays a QR code for the main application URL.
*   **Admin Toggles:**
    *   **Unlock Steps:** Allows admins to disable the step progression check, letting users access any valid step URL directly.
    *   **Disable Minigames:** Allows admins to turn off the minigame steps, making them behave like standard question steps.
*   **Security Education Elements:**
    *   **Information Disclosure:** Hint/answer potentially visible in HTML source comments on specific steps (e.g., Step 3).
    *   **Reflected XSS:** Incorrect answers are displayed unsafely on the redirect page (for demonstration).
    *   **(Disabled):** IDOR (Direct URL guessing) is possible only when "Unlock Steps" is enabled in admin.
*   **Persistent Sessions:** Uses Flask-Session with filesystem storage to remember user progress (highest step unlocked, last correct step, shrink penalty) across browser sessions and server restarts.

## Tech Stack

*   **Backend:** Python 3, Flask, Flask-Session
*   **AI:** Ollama (running locally) with an appropriate model (e.g., Llama 3.2) via the `ollama` Python library.
*   **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
*   **QR Codes:** `qrcode` Python library (with Pillow)

## Prerequisites

1.  **Python 3:** Ensure Python 3 (preferably 3.8+) is installed.
2.  **Ollama:** Download and install Ollama from [https://ollama.com/](https://ollama.com/).
3.  **Ollama Model:** Pull the language model you intend to use. The default in `app.py` is `llama3.2:latest`. Run:
    ```bash
    ollama pull llama3.2
    ```
    *(If you use a different model, update the `OLLAMA_MODEL` constant in `app.py`)*.
4.  **Ollama Service:** The Ollama application/service **must be running** in the background *before* you start the Flask app. You can typically start it by running `ollama serve` in a terminal, or just running `ollama run <your_model_name>` once might start the background service.

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd easter-egg-hunt-webapp
    ```
2.  **Create Virtual Environment:** (Recommended)
    ```bash
    python -m venv venv
    # Activate (Windows cmd)
    venv\Scripts\activate
    # Activate (MacOS/Linux bash)
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create Session Directory:** Manually create the folder where session files will be stored:
    ```bash
    mkdir flask_session
    ```
    *(Alternatively, the app will create it on first run if permissions allow).*
5.  **Prepare `questions.json`:** Ensure your `questions.json` file is in the root directory and saved with **UTF-8 encoding**. It should follow the format:
    ```json
    {
        "1": {
            "question": "...",
            "answer": "...",
            "hint": "...",
            "next_location_description": "Under the clock..."
        },
        "2": { ... },
        ...
    }
    ```
6.  **Place Static Files:** Ensure your `egg1.png` - `egg8.png`, `basket.png`, and `fav.ico` are inside the `static/images/` directory.

## Configuration

Modify constants near the top of `app.py` as needed:

*   `OLLAMA_MODEL`: Set to the exact name of the Ollama model you pulled (e.g., `"llama3.2:latest"`).
*   `SERVER_PORT`: Change the port if `5000` is in use.
*   `SECRET_KEY`: **IMPORTANT:** Change the default hardcoded key to a long, random, secret string for any deployment beyond local testing. Keep this key consistent for session persistence.
*   `UNLOCK_FLAG_FILE`, `MINIGAMES_DISABLED_FLAG_FILE`: Names of the files used for admin toggles.
*   Physics/Scaling parameters (`MAX_EGG_SCALE`, `DECAY_RATE`, etc.) can be tweaked.

## Running the App

1.  **Start Ollama:** Ensure the Ollama service is running.
2.  **Start Flask Server:** Navigate to the project root directory in your terminal (where `app.py` is) and run:
    ```bash
    python app.py
    ```
3.  **Access the App:**
    *   Find your server laptop's **Local Network IP Address** (e.g., using `ipconfig` on Windows or `ip addr` on Linux/macOS - look for an address like `192.168.x.x` or `10.x.x.x`).
    *   From a mobile device or another computer **on the same Wi-Fi network**, open a web browser and go to `http://<Your_Laptop_IP>:<PORT>` (e.g., `http://192.168.5.60:5000`).
4.  **Firewall:** You might need to configure your server laptop's firewall (e.g., Windows Defender Firewall) to **allow incoming connections** on the specified `SERVER_PORT` (default 5000) for other devices to connect.

## Planned Development (Future Features)

*   **Audio Integration:**
    *   **Background Music:** Add a looping background track using the HTML `<audio>` tag.
    *   **Sound Effects:** Add short SFX for clicks, bounces, hints, wins using the JavaScript `Audio` object.
    *   **(Complex)** **Dynamic Multi-User Sounds:** Explore using **Flask-SocketIO** or **SSE** to allow the server to trigger dynamically generated sounds (e.g., based on specific events or TTS) simultaneously for all connected users. This would involve:
        *   Server-side sound generation (using `wave`, `pydub`, or TTS libraries).
        *   Storing/logging recent sound events (e.g., in a file like `recent_sounds.json` or a simple DB).
        *   A WebSocket/SSE connection manager in Flask.
        *   Broadcasting "play sound" commands from the server.
        *   Client-side JavaScript listeners to receive commands and play the specified audio using the `Audio` object.
        *   A mechanism for clients joining later to potentially "catch up" on recent sounds (within a time limit).
*   **Deployment Strategy:**
    *   Develop instructions/scripts for deploying the app (e.g., using Waitress or Gunicorn).
    *   Create a setup script or guide to automate/simplify the installation of prerequisites like Python, Ollama, and the required Ollama model on the target server.
    *   Consider containerization (e.g., Docker) for easier deployment.
*   **Refine UI/UX:** Improve visual styling, mobile responsiveness, and user feedback.
*   **More Minigames:** Add other types of interactive challenges.
*   **Admin Enhancements:** Password protection for admin, ability to edit questions via UI.
