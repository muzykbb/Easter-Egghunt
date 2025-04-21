import json
import os
import random
import socket
import io
import base64
from datetime import timedelta # <-- Import timedelta for session lifetime
from flask import ( Flask, render_template, request, redirect,
                    url_for, session, abort, Markup, flash, send_from_directory )
from flask_session import Session # <-- Import Session
import ollama
import qrcode

# --- Application Setup ---
app = Flask(__name__)

# *** IMPORTANT: Configure Session Handling ***
# 1. Set a FIXED secret key for persistence. Replace with your own random string.
#    NEVER commit a real secret key to version control.
app.config['SECRET_KEY'] = 'a_really_secret_key_that_should_be_random_and_long_for_a_real_app'
# 2. Configure Flask-Session extension
app.config['SESSION_TYPE'] = 'filesystem' # Store sessions in files
app.config['SESSION_FILE_DIR'] = './flask_session' # Directory we created
app.config['SESSION_PERMANENT'] = True # Make sessions persistent
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7) # Remember user for 7 days
app.config.update(SESSION_COOKIE_SAMESITE="Lax") # Good practice for cookies

# 3. Initialize the session extension
Session(app)
# Ensure the session directory exists
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
# *** End Session Configuration ***


MINIGAMES_DISABLED_FLAG_FILE = '.minigames_disabled'
UNLOCK_FLAG_FILE = '.hunt_is_unlocked'

# --- Other Configuration ---
HUNT_DATA_FILE = 'questions.json'
OLLAMA_MODEL = "llama3.2:latest"
NUM_EGGS = 16
SERVER_PORT = 5000
MAX_EGG_SCALE = 2
MIN_EGG_SCALE = 0.5
DECAY_RATE = 0.7
PERMANENT_SHRINK_FACTOR = 0.95
PERMANENT_MIN_SCALE_PENALTY = 0.4
PERMANENT_SHRINK_STEP_LIMIT = 20

# --- Global Data Store ---
HUNT_DATA = {}
HUNT_DATA_KEYS_ORDERED = []
FIBONACCI_SEQUENCE = []


# --- Global Data Store ---
HUNT_DATA = {}
HUNT_DATA_KEYS_ORDERED = []
FIBONACCI_SEQUENCE = []

HUNT_DATA_FILE = 'questions.json'
OLLAMA_MODEL = "llama3.2:latest"
NUM_EGGS = 16
SERVER_PORT = 5000
MAX_EGG_SCALE = 1.8
MIN_EGG_SCALE = 0.3
DECAY_RATE = 0.75

# *** ADD THESE THREE CONSTANTS IF MISSING ***
PERMANENT_SHRINK_FACTOR = 0.95 # Shrink by 5% on wrong answer
PERMANENT_MIN_SCALE_PENALTY = 0.4 # Minimum penalty factor (don't shrink infinitely below this multiplier)
PERMANENT_SHRINK_STEP_LIMIT = 20 # Stop shrinking penalty after this Fibonacci step ID  # Controls how quickly scale shrinks (0 < rate < 1), smaller is faster drop - ADJUST AS NEEDED
# --- Helper Functions ---

def load_hunt_data():
    """Loads question data, preserves key order, and generates Fibonacci sequence."""
    global HUNT_DATA, HUNT_DATA_KEYS_ORDERED, FIBONACCI_SEQUENCE
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        questions_path = os.path.join(base_dir, HUNT_DATA_FILE)
        print(f"Attempting to load questions from: {questions_path}")
        with open(questions_path, 'r') as f:
            HUNT_DATA = json.load(f)
        HUNT_DATA_KEYS_ORDERED = list(HUNT_DATA.keys())
        print(f"Loaded {len(HUNT_DATA)} steps from {HUNT_DATA_FILE}")
        print(f"Original data keys (load order): {HUNT_DATA_KEYS_ORDERED}")

        question_count = len(HUNT_DATA)
        if question_count == 0:
            print("Warning: No questions loaded.")
            FIBONACCI_SEQUENCE, HUNT_DATA_KEYS_ORDERED = [], []
            return

        generate_fibonacci_sequence(question_count)
        print(f"Using Fibonacci steps for hunt progression: {FIBONACCI_SEQUENCE}")

        if len(FIBONACCI_SEQUENCE) != len(HUNT_DATA_KEYS_ORDERED):
             print(f"CRITICAL ERROR: Mismatch between Fibonacci sequence length ({len(FIBONACCI_SEQUENCE)}) and number of questions loaded ({len(HUNT_DATA_KEYS_ORDERED)}).")
             HUNT_DATA, HUNT_DATA_KEYS_ORDERED, FIBONACCI_SEQUENCE = {}, [], []

    except FileNotFoundError:
        print(f"Error: {questions_path} not found.")
        HUNT_DATA, HUNT_DATA_KEYS_ORDERED, FIBONACCI_SEQUENCE = {}, [], []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {questions_path}.")
        HUNT_DATA, HUNT_DATA_KEYS_ORDERED, FIBONACCI_SEQUENCE = {}, [], []
    except Exception as e:
        print(f"An unexpected error occurred loading data: {e}")
        HUNT_DATA, HUNT_DATA_KEYS_ORDERED, FIBONACCI_SEQUENCE = {}, [], []

def generate_fibonacci_sequence(count):
    """Generates the first 'count' Fibonacci numbers (1, 2, 3, 5...)."""
    global FIBONACCI_SEQUENCE
    FIBONACCI_SEQUENCE = []
    a, b = 0, 1
    while len(FIBONACCI_SEQUENCE) < count:
        next_fib = a + b
        if next_fib >= 1: FIBONACCI_SEQUENCE.append(next_fib)
        a, b = b, next_fib
    FIBONACCI_SEQUENCE = sorted(list(set(FIBONACCI_SEQUENCE)))
    if count >= 1 and (not FIBONACCI_SEQUENCE or FIBONACCI_SEQUENCE[0] != 1): FIBONACCI_SEQUENCE.insert(0,1)
    if count >= 2 and (len(FIBONACCI_SEQUENCE) < 2 or FIBONACCI_SEQUENCE[1] != 2):
        if 1 in FIBONACCI_SEQUENCE: FIBONACCI_SEQUENCE.insert(FIBONACCI_SEQUENCE.index(1)+1, 2)
        else: FIBONACCI_SEQUENCE.insert(0,2)
    FIBONACCI_SEQUENCE = sorted(list(set(FIBONACCI_SEQUENCE)))
    FIBONACCI_SEQUENCE = FIBONACCI_SEQUENCE[:count]

def get_step_data(fibonacci_step_id):
    """Retrieves question data mapping Fibonacci step to sequential key."""
    global FIBONACCI_SEQUENCE, HUNT_DATA_KEYS_ORDERED, HUNT_DATA
    if not FIBONACCI_SEQUENCE or not HUNT_DATA_KEYS_ORDERED: return None
    try:
        fib_index = FIBONACCI_SEQUENCE.index(fibonacci_step_id)
        if 0 <= fib_index < len(HUNT_DATA_KEYS_ORDERED):
            original_key = HUNT_DATA_KEYS_ORDERED[fib_index]
            return HUNT_DATA.get(original_key)
        return None
    except ValueError: return None
    except Exception as e:
        print(f"Unexpected error in get_step_data for step {fibonacci_step_id}: {e}")
        return None

def get_next_fibonacci_step(current_fib_step_id):
    """Finds the next step ID in the Fibonacci sequence."""
    try:
        current_index = FIBONACCI_SEQUENCE.index(current_fib_step_id)
        return FIBONACCI_SEQUENCE[current_index + 1] if current_index + 1 < len(FIBONACCI_SEQUENCE) else None
    except ValueError: return None

def check_ollama_status():
    """Checks Ollama server connection and model availability at startup."""
    print("\n--- Checking Ollama Status ---")
    try:
        client = ollama.Client()
        local_models = client.list()
        print("Ollama connection successful.")
        model_found = False
        model_name_to_check = OLLAMA_MODEL.lower()
        base_name_to_check = model_name_to_check.split(':')[0]
        print(f"Checking for model: '{OLLAMA_MODEL}'")
        for model in local_models.get('models', []):
            full_listed_name = model.get('name', '').lower()
            base_listed_name = full_listed_name.split(':')[0]
            if model_name_to_check == full_listed_name or base_name_to_check == base_listed_name:
                print(f"  - Found available model: {model.get('name')}")
                model_found = True
                break
        if model_found: print(f"Success: Model '{OLLAMA_MODEL}' is available.")
        else: print(f"Warning: Model '{OLLAMA_MODEL}' not found. Try 'ollama pull {OLLAMA_MODEL}'")
    except Exception as e:
        print(f"Error connecting to Ollama or checking models: {type(e).__name__} - {e}")
        print("Ensure Ollama server is running.")
    print("----------------------------\n")

def ask_ollama_eval(user_answer, correct_answer):
    """Asks Ollama model to evaluate the user's answer. Returns a dictionary {'is_correct': bool, 'remark': str} or None on error."""
    prompt_content = f"""
You are "Llama", a slightly snarky but helpful evaluation assistant for a kids' Easter egg hunt quiz. Be creative and vary your responses!
Compare the 'User Answer' provided by the child to the 'Correct Answer'.
Determine if the User Answer is semantically close enough to be considered correct. Don't worrwy about plurar form or minor miss-spellings. Consider answers in enaglish, polish, german and french.
Respond ONLY with a JSON object containing two keys:
1. "is_correct": a boolean value (true or false).
2. "remark": A short, kid-friendly remark.
   - If the answer IS correct (is_correct: true), the remark must be null or an empty string "".
   - If the answer is incorrect (is_correct: false), make the remark slightly snarky or funny, hinting at why it's wrong or encouraging them to think again. Use variety in your remarks; don't always say the same thing! Examples: "Nope! Are you even trying?", "Way off! Did you read the hint?", "Close, but no banana!", "Not quite! Think harder!", "Is that your final answer? Hope not!", "Creative guess... but wrong!", "Think like a detective!", "Maybe take a peek at the hint again?", "Have another go!", "Incorrect! The squirrels know, maybe ask them?".

Context:
Correct Answer: {correct_answer}
User Answer: {user_answer}

Evaluation Result (JSON object with is_correct and remark):
"""
    try:
        print(f"--- Sending Snarky Eval to Ollama ({OLLAMA_MODEL}) ---")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt_content}],
            options={"temperature": 0.7},
            format='json'
        )
        content = response['message']['content']
        print(f"--- Ollama Raw Response --- \n{content}\n-------------------------")
        result_json = json.loads(content)
        if (isinstance(result_json, dict) and 'is_correct' in result_json and 'remark' in result_json):
            evaluation = bool(result_json['is_correct'])
            remark = result_json.get('remark', "") or ""
            if evaluation: remark = ""
            print(f"--- Ollama Parsed Evaluation: {'Correct' if evaluation else 'Incorrect'} ---")
            if remark: print(f"--- Ollama Remark: {remark} ---")
            return {"is_correct": evaluation, "remark": remark}
        else:
            print(f"Error: Ollama response malformed. Got: {content}")
            return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from Ollama. Content was: {content}")
        return None
    except ollama.ResponseError as e:
        print(f"Error: Ollama API response error: {e.status_code} - {e.error}")
        return None
    except Exception as e:
        print(f"Error: Failed to communicate with Ollama: {type(e).__name__} - {e}")
        return None

def get_local_network_ip():
    """Finds the local network IP address (likely 192.168.x.x)."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]
        if ip_address.startswith("192.168."):
            return ip_address
        else:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                 if ip.startswith("192.168.") and not ip.startswith("127."): return ip
            print("Warning: Could not reliably determine 192.168.* IP.")
            primary_ip = socket.gethostbyname(hostname)
            return primary_ip if not primary_ip.startswith("127.") else None
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None
    finally:
        if s: s.close()

def generate_qr_code_data_uri(data_string):
    """Generates a QR code for the given string and returns a Base64 data URI."""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(data_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

# --- Routes ---

@app.route('/')
def home():
    session.pop('highest_step_unlocked', None)
    session.pop('last_correct_step', None)
    session.pop('shrink_penalty_factor', None)
    # REMOVED: No need to track admin_first_access_done here anymore
    # if 'admin_first_access_done' not in session:
    #     session['admin_first_access_done'] = False
    resume_step_id = None
    # ... (logic to calculate resume_step_id) ...
    if session.get('highest_step_unlocked'):
         # ... determine resume_step_id ...
         highest_unlocked = session.get('highest_step_unlocked')
         last_correct = session.get('last_correct_step')
         if highest_unlocked and highest_unlocked in FIBONACCI_SEQUENCE:
            if last_correct and last_correct in FIBONACCI_SEQUENCE:
                resume_step_id = get_next_fibonacci_step(last_correct)
                if resume_step_id is None: resume_step_id = last_correct
            if resume_step_id is None: resume_step_id = highest_unlocked

    # REMOVED admin_first_access_done from render_template
    return render_template('home.html', resume_step_id=resume_step_id)

@app.route('/admin/toggle_lock', methods=['POST']) # <<< ADD THIS DECORATOR WITH METHODS
def admin_toggle_lock():
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Access denied.", "error"); return redirect(url_for('home'))

    # Check the submitted form data
    should_be_unlocked = 'unlock_mode_checkbox' in request.form
    currently_unlocked = os.path.exists(UNLOCK_FLAG_FILE)

    try:
        if should_be_unlocked and not currently_unlocked:
            open(UNLOCK_FLAG_FILE, 'a').close() # Create flag file
            print("ADMIN ACTION: Hunt globally UNLOCKED.")
            flash("Hunt steps are now globally unlocked!", "success")
        elif not should_be_unlocked and currently_unlocked:
            os.remove(UNLOCK_FLAG_FILE) # Delete flag file
            print("ADMIN ACTION: Hunt globally LOCKED.")
            flash("Hunt steps are now locked (normal progression enforced).", "info")
        else:
            flash("Hunt lock status unchanged.", "secondary")
    except OSError as e:
        print(f"Error changing hunt lock status file: {e}")
        flash(f"Error updating lock status: {e}", "error")

    return redirect(url_for('admin_area')) # Redirect back to admin page


@app.route('/start_hunt')
def start_hunt():
    """Clears old progress, initializes session for a NEW hunt, redirects to step 1."""
    print("Starting NEW hunt, resetting session progress...")
    if not FIBONACCI_SEQUENCE:
         flash("Error: Hunt data not loaded. Cannot start.", "error")
         return redirect(url_for('home'))

    first_step_id = FIBONACCI_SEQUENCE[0]
    # Clear previous hunt progress specifically
    session.pop('highest_step_unlocked', None)
    session.pop('last_correct_step', None)
    session.pop('shrink_penalty_factor', None)

    # Initialize for step 1
    session['highest_step_unlocked'] = first_step_id
    session['last_correct_step'] = None
    session['shrink_penalty_factor'] = 1.0
    # Don't reset admin_first_access_done here, let it persist if needed

    print(f"Session initialized for NEW hunt. Unlocked: {first_step_id}")
    return redirect(url_for('hunt_step', step_id=first_step_id))


@app.route('/hunt/step/<int:step_id>')
def hunt_step(step_id):
    # --- Access Check: Rely on session having been initialized ---
    # If user jumps here without starting, highest_unlocked might be None
    highest_unlocked = session.get('highest_step_unlocked')

    if not FIBONACCI_SEQUENCE or step_id not in FIBONACCI_SEQUENCE:
        abort(404) # Not a valid step

    hunt_globally_unlocked = os.path.exists(UNLOCK_FLAG_FILE)
    print(f"Step Access Check: Step {step_id}. Globally Unlocked? {hunt_globally_unlocked}")


    if not hunt_globally_unlocked:
        # --- NORMAL MODE: Check session progress ---
        highest_unlocked = session.get('highest_step_unlocked')
        if highest_unlocked is None:
            flash("Please start the hunt from the beginning.", "warning")
            print(f"Access denied for step {step_id}. No session progress found. Redirecting home.")
            return redirect(url_for('home'))
        elif step_id > highest_unlocked:
             flash(f"Step {step_id} hasn't been unlocked yet. Current progress: Step {highest_unlocked}.", "warning")
             print(f"Access denied for step {step_id}. Highest unlocked: {highest_unlocked}. Redirecting to last unlocked.")
             # Redirect to the highest step they *have* unlocked
             return redirect(url_for('hunt_step', step_id=highest_unlocked))
        # --- END NORMAL MODE CHECK ---
    else:
        # --- UNLOCKED MODE: Allow access if step is valid ---
        print(f"Hunt globally unlocked. Allowing direct access to step {step_id}.")
        # No specific action needed here, just proceed

    # ... (Rest of hunt_step logic: get_step_data, check minigame, calculate scale, etc.) ...
    step_data = get_step_data(step_id)
    if not step_data: abort(500)
    # Determine minigame type...
    is_minigame_type = 'standard'
    minigames_globally_disabled = os.path.exists(MINIGAMES_DISABLED_FLAG_FILE)
    print(f"Step {step_id}. Minigames Globally Disabled? {minigames_globally_disabled}")
    step_index = -1
    if not minigames_globally_disabled: # Only check for minigames if NOT disabled
        try:
            step_index = FIBONACCI_SEQUENCE.index(step_id)
            if (step_index + 1) % 3 == 0: # Is it a multiple of 3?
                minigame_num = (step_index + 1) // 3
                if minigame_num % 2 != 0: is_minigame_type = 'basket'
                else: is_minigame_type = 'moving_basket'
                print(f"Step {step_id} IS Minigame Type: {is_minigame_type}")
        except ValueError:
             print(f"Warning: Step ID {step_id} not in sequence for minigame check.")
        except Exception as e: print(f"Error checking minigame type: {e}")
    else:
         print(f"Minigames disabled globally, treating Step {step_id} as standard.")
    # Calculate scale...
    current_scale = MAX_EGG_SCALE # Start with default max
    if step_index != -1: # Only calculate if index was found
        try:
            # Exponential decay calculation
            calculated_scale = MIN_EGG_SCALE + (MAX_EGG_SCALE - MIN_EGG_SCALE) * (DECAY_RATE ** step_index)
            step_base_scale = max(MIN_EGG_SCALE, calculated_scale) # Apply minimum decay scale

            # Apply permanent shrink penalty from session
            shrink_penalty = session.get('shrink_penalty_factor', 1.0)
            final_calculated_scale = step_base_scale * shrink_penalty # Apply penalty

            # *** APPLY OVERALL MINIMUM SCALE LIMIT (60%) ***
            current_scale = max(0.6, final_calculated_scale) # Ensure scale is AT LEAST 0.6

            print(f"Step={step_id}, Idx={step_index}, BaseS={step_base_scale:.3f}, Penalty={shrink_penalty:.3f}, CalcFinalS={final_calculated_scale:.3f}, FINAL Scale (min 0.6)={current_scale:.3f}")

        except Exception as e:
            print(f"Error calculating scale for step {step_id}: {e}. Using default scale: {current_scale}")
            # Keep current_scale as MAX_EGG_SCALE in case of calculation error
    else:
        # step_index was -1, use default MAX_EGG_SCALE (already set)
         print(f"Warning: Using default max scale {current_scale} for step {step_id} due to missing index.")

    hint_egg_id = None
    if is_minigame_type == 'standard': hint_egg_id = random.randint(1, 8)
    # Admin status...
    # Exploit...
    html_comment_exploit = ""
    if is_minigame_type == 'standard' and step_id == 3: html_comment_exploit = Markup("<!-- Hint... -->")


    print(f"Rendering step {step_id}. Scale={current_scale:.3f}. HintEgg={hint_egg_id}. Minigame={is_minigame_type}")

    return render_template('step.html',
                           step_id=step_id, question=step_data['question'], hint=step_data.get('hint', ''),
                           hint_egg_id=hint_egg_id, current_scale=current_scale,
                           is_minigame_type=is_minigame_type,
                           html_exploit=html_comment_exploit)


@app.route('/hunt/check/<int:step_id>', methods=['POST'])
def check_answer(step_id):
    # Basic check if step is valid (could add session check too)
    if step_id not in FIBONACCI_SEQUENCE: abort(403)

    user_answer = request.form.get('answer', '').strip()
    step_data = get_step_data(step_id)
    if not step_data or not user_answer:
        flash("Missing data or no answer.", "error")
        return redirect(url_for('hunt_step', step_id=step_id))

    eval_result = ask_ollama_eval(user_answer, step_data['answer'])
    if eval_result is None:
        flash("Could not verify answer (Ollama issue?).", "error")
        return redirect(url_for('hunt_step', step_id=step_id))

    is_correct = eval_result["is_correct"]
    remark = eval_result["remark"]

    if is_correct:
        # --- Correct Answer ---
        session['last_correct_step'] = step_id
        session['shrink_penalty_factor'] = 1.0 # Reset penalty
        next_step_id = get_next_fibonacci_step(step_id)
        if next_step_id:
            # Update highest unlocked step
            session['highest_step_unlocked'] = max(session.get('highest_step_unlocked', 0), next_step_id)
            print(f"Correct for {step_id}. Highest unlocked now: {session['highest_step_unlocked']}")
            # Generate QR for next step...
            server_ip = get_local_network_ip()
            qr_code_uri = None
            next_step_url = f"http://{server_ip}:{SERVER_PORT}/hunt/step/{next_step_id}" if server_ip else None
            if next_step_url: qr_code_uri = generate_qr_code_data_uri(next_step_url)
            # Render correct page...
            next_loc_desc = step_data.get('next_location_description', 'Find next QR!')
            return render_template('correct.html',
                                   step_id=step_id, next_step_id=next_step_id,
                                   next_location_description=next_loc_desc,
                                   next_step_qr_code=qr_code_uri, next_step_url=next_step_url or "#")
        else: # Last step
            final_message = step_data.get('next_location_description', 'Congrats!')
            return render_template('complete.html', final_message=final_message)
    else:
        # --- Incorrect Answer ---
        flash_message = remark if remark else "That wasn't quite right."
        flash(flash_message, "warning")
        # Apply shrink penalty if applicable
        if step_id <= PERMANENT_SHRINK_STEP_LIMIT:
             current_penalty = session.get('shrink_penalty_factor', 1.0)
             new_penalty = max(PERMANENT_MIN_SCALE_PENALTY, current_penalty * PERMANENT_SHRINK_FACTOR)
             session['shrink_penalty_factor'] = new_penalty
             print(f"Incorrect for {step_id}: Shrink penalty now {new_penalty:.3f}")
        return redirect(url_for('hunt_step', step_id=step_id)) # Redirect back
    
CLICK_SEQUENCE_KEY = 'admin_access_granted'

@app.route('/admin/grant_access')
def grant_admin_access():
    # Grant main access AND mark that first access attempt is complete
    session[CLICK_SEQUENCE_KEY] = True
    print("Admin access sequence complete. Redirecting to Fake Admin...")
    # *** REDIRECT TO FAKE ADMIN PAGE ***
    return redirect(url_for('fake_admin_console')) # Changed from 'admin_area'

@app.route('/fake_admin')
def fake_admin_console():
    # Check if access was granted by the sequence
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Access denied.", "error")
        return redirect(url_for('home'))
    # No complex data needed, just render the template
    return render_template('fake_admin.html')

@app.route('/oops')
def oops_wrong_button():
    # Check if user should have been here (i.e., have admin access flag)
    # This prevents direct navigation to /oops
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Invalid access.", "error")
        return redirect(url_for('home'))
    # Clear the admin access grant so they have to re-enter sequence
    session.pop(CLICK_SEQUENCE_KEY, None)
    print("Oops page accessed. Cleared admin access grant.")
    flash("Incorrect access attempt. Security protocols engaged. Returning to base.", "error")
    return render_template('oops.html')


@app.route('/admin') # Original Admin: View Questions
def admin_area():
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Access denied.", "error")
        return redirect(url_for('home'))
    next_questions_data = {}
    try:
        # Find index of the *next* step to be shown (relative to last correct)
        last_step_id = session.get('last_correct_step')
        start_index = 0
        if last_step_id:
            try:
                last_index = FIBONACCI_SEQUENCE.index(last_step_id)
                start_index = last_index + 1 # Start from the one after the last correct
            except ValueError:
                pass # Keep start_index 0 if last_correct_step is somehow invalid

        # Get the original keys for the next 3 steps (or fewer if near end)
        num_to_show = 3
        end_index = min(start_index + num_to_show, len(HUNT_DATA_KEYS_ORDERED))
        next_keys = HUNT_DATA_KEYS_ORDERED[start_index:end_index]

        # Build the dictionary with data for these keys only
        for key in next_keys:
            if key in HUNT_DATA:
                next_questions_data[key] = HUNT_DATA[key]

    except Exception as e:
        print(f"Error preparing next questions for admin: {e}")
        flash("Error retrieving next questions data.", "error")


    # --- Generate QR Code ---
    server_ip = get_local_network_ip()
    qr_data_uri = None
    display_url = "N/A"
    if server_ip:
        display_url = f"http://{server_ip}:{SERVER_PORT}/"
        qr_data_uri = generate_qr_code_data_uri(display_url)
    else:
        flash("Could not determine server's local network IP for QR code.", "warning")

    # --- Render Template ---
    return render_template('admin.html',
                           next_questions=next_questions_data, # Pass the subset of questions
                           display_url=display_url,
                           qr_code_uri=qr_data_uri)
    # Optionally clear the flag after viewing once?
    # session.pop(CLICK_SEQUENCE_KEY, None)
    formatted_data = json.dumps(HUNT_DATA, indent=4)
    return render_template('admin.html', hunt_data=formatted_data)

# ***  Toggle Minigame Status ***
@app.route('/admin/toggle_minigames', methods=['POST'])
def admin_toggle_minigames():
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Access denied.", "error"); return redirect(url_for('home'))

    should_be_disabled = 'disable_minigames_checkbox' in request.form
    currently_disabled = os.path.exists(MINIGAMES_DISABLED_FLAG_FILE)

    try:
        if should_be_disabled and not currently_disabled:
            open(MINIGAMES_DISABLED_FLAG_FILE, 'a').close()
            print("ADMIN ACTION: Minigames DISABLED.")
            flash("Minigames are now DISABLED (steps will be standard).", "warning")
        elif not should_be_disabled and currently_disabled:
            os.remove(MINIGAMES_DISABLED_FLAG_FILE)
            print("ADMIN ACTION: Minigames ENABLED.")
            flash("Minigames are now ENABLED.", "success")
        else:
            flash("Minigame status unchanged.", "secondary")
    except OSError as e:
        print(f"Error changing minigame status file: {e}")
        flash(f"Error updating minigame status: {e}", "error")

    return redirect(url_for('admin_area'))

@app.route('/admin/print_qrs')
def admin_print_qrs():
    # Use same session check for access
    if not session.get(CLICK_SEQUENCE_KEY, False):
        flash("Access denied.", "error")
        return redirect(url_for('home'))

    qr_codes = [] # List to hold data for each QR code
    server_ip = get_local_network_ip()

    if not server_ip:
         flash("Cannot generate QR codes: Could not determine server IP.", "error")
         return render_template('admin_print_qrs.html', qr_codes=qr_codes, error=True) # Pass error flag

    # Iterate through the defined HUNT STEPS (Fibonacci sequence)
    for i, step_id in enumerate(FIBONACCI_SEQUENCE):
        step_url = f"http://{server_ip}:{SERVER_PORT}/hunt/step/{step_id}"
        qr_uri = generate_qr_code_data_uri(step_url)

        # Get the corresponding question data to display the location hint
        step_data = get_step_data(step_id) # Use mapping
        location_hint = f"Step {step_id} (Data Key: {HUNT_DATA_KEYS_ORDERED[i] if i<len(HUNT_DATA_KEYS_ORDERED) else '?'})" # Default label
        if step_data and 'next_location_description' in step_data:
             # Use the location description from the PREVIOUS step's data
             # Need to find the previous step ID first
             prev_step_id = FIBONACCI_SEQUENCE[i-1] if i > 0 else None
             prev_step_data = get_step_data(prev_step_id) if prev_step_id else None
             if prev_step_data and 'next_location_description' in prev_step_data:
                  location_hint = f"Step {step_id} (Place where '{prev_step_data['next_location_description']}' tells user to look)"
             elif i == 0: # First step
                  location_hint = f"Step {step_id} (Starting Point)"


        qr_codes.append({
            'step_id': step_id,
            'url': step_url,
            'qr_uri': qr_uri,
            'location_hint': location_hint # Add hint for placement
        })

    return render_template('admin_print_qrs.html', qr_codes=qr_codes, error=(not server_ip))


# --- Secret QR Console Route ---
@app.route('/secret-qr') # NEW QR Console
def secret_qr_console():
    # This page is now accessed *manually* or perhaps linked from admin_area
    # We remove the session check here, maybe add a different password later if needed.
    # OR, keep the session check if the click sequence should grant access to BOTH admin pages.
    # Let's KEEP the check for consistency:
    if not session.get(CLICK_SEQUENCE_KEY, False):
         flash("Secret access denied.", "error")
         return redirect(url_for('home'))

    server_ip = get_local_network_ip()
    qr_data_uri = None
    display_url = "N/A"

    if server_ip:
        display_url = f"http://{server_ip}:{SERVER_PORT}/"
        qr_data_uri = generate_qr_code_data_uri(display_url)
    else:
        flash("Could not determine the server's local network IP address.", "error")

    return render_template('secret_qr.html',
                           server_ip=server_ip or "Not Found",
                           display_url=display_url,
                           qr_code_uri=qr_data_uri)

# --- Favicon Route ---
@app.route('/favicon.ico')
def favicon():
    try:
        icon_path = os.path.join(app.root_path, 'static', 'fav.ico')
        return send_from_directory(os.path.dirname(icon_path), os.path.basename(icon_path), mimetype='image/vnd.microsoft.icon')
    except FileNotFoundError:
         print("Warning: fav.ico not found in static folder.")
         return '', 204

# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    message = "Page Not Found (404)"
    if request.url_rule and 'hunt_step' in request.url_rule.endpoint:
         message = f"Step not found (404)? Valid steps: {FIBONACCI_SEQUENCE}"
    return render_template('error.html', message=message), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', message="Forbidden (403). Access denied."), 403

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Server Error: {e}")
    import traceback
    traceback.print_exc()
    return render_template('error.html', message="Internal Server Error (500). Whoops!"), 500

# --- Main Execution ---
if __name__ == '__main__':
    load_hunt_data()
    check_ollama_status()
    if not HUNT_DATA or not FIBONACCI_SEQUENCE:
         print("\n*** WARNING: No hunt data loaded. App may not function. ***\n")
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)
    # --- END OF FILE app.py ---
