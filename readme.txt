This application was developed for kids entertainment, a one off local web server that hosts the egghunt via the browser. 
Users connected to the same wifi as your server (Windows laptop) will be able to scan QRcodes and interact with the game. 

Game:
- Series of questions loaded from questions.json (easily generated with any AI)
- Set of minigames unlocking the questions.
- Once user completes a minigame and answers the question they are given a location for the next QRcode (same questions.json)
- User's answer is validated by LLM for correctness allowing for a degree of leniency for user's typos etc. 
- The platform is vulnerable by design. it assumes that your home wifi is secure. 
- This egghunt is designed with multiple vulnerabilities (from "next_step" numbering sequence, web server, client-side to AI prompt engineering)
- Admin console hidden behind a fake one allows disabling the minigame requirement and step sequence guardrails. 
- Admin console allows QRcode generation 
- Admin password - click the sequence of eggs (check with images in static folder): 1,2,3,4. Sequence to be entered in Step view. 

Requirements:
- Python 3.11 (this should work with other versions too)
- Ollama with one of the latest llama models installed (small - approx. 3GB)

Usage:
- Start app.py
- Open the URL listed in console output as hosting link.
- Start the egghunt and click on all eggs on the screen. This takes you to the first question. 
- Click on admin egg sequence (1,2,3,4). 
- In Fake_Admin console tick "Enable Relativity Plus Filter" to access Admin Console
- Scroll down to reveal the links for QRcode printing and game mode selection. 
- Once QRcodes are printered, mobile users can scan them and connect to your web server via common wifi. 



easter-egg-hunt-webapp/
├── app.py                     # Main Flask application
├── questions.json             # Hunt questions, answers, hints, locations
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation (This file)
├── .gitignore                 # Files/folders for Git to ignore
│
├── static/
│   ├── css/
│   │   └── style.css          # Main CSS file
│   ├── js/
│   │   └── animations.js      # Egg animation, physics, minigame, admin logic
│   ├── images/
│   │   ├── egg1.png           # Egg images (up to egg8.png)
│   │   ├── egg2.png
│   │   ├── ...
│   │   ├── egg8.png
│   │   ├── basket.png         # Basket image for minigame
│   │   └── fav.ico            # Favicon for the browser tab
│   └── sounds/                # <-- Placeholder for future audio
│       ├── dynamic/           # <-- Placeholder for generated WAVs
│       ├── background_loop.mp3 # <-- Placeholder for background music
│       └── click.mp3          # <-- Placeholder for SFX
│
├── templates/
│   ├── admin.html             # Real admin console (Next Qs, Toggles)
│   ├── admin_print_qrs.html   # Page to display all QR codes
│   ├── correct.html           # Page shown after correct answer
│   ├── complete.html          # Page shown after finishing the hunt
│   ├── error.html             # Generic error page
│   ├── fake_admin.html        # Deceptive fake admin console
│   ├── home.html              # Starting page / Home challenge
│   ├── oops.html              # Page shown for wrong clicks in fake admin
│   ├── secret_qr.html         # Admin page showing App URL QR code
│   └── step.html              # Main question/interaction page
│
└── flask_session/             # <-- Created automatically by Flask-Session (add to .gitignore)
    └── ...                    #       (Contains server-side session files)

