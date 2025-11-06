
import requests
import pyttsx3
import vosk
import sounddevice as sd
import queue
import json
import os
import threading
from functools import partial
import speech_recognition as sr
import datetime
import webbrowser
import platform

def is_online():
    """Checks for an active internet connection."""
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except requests.ConnectionError:
        return False

def speak(text):
    """Converts text to speech."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return text

def listen_offline():
    """Listens for and recognizes voice commands using VOSK."""
    model_path = "models/vosk-model-en-us-0.22-lgraph"
    if not os.path.exists(model_path):
        print("Offline model not found. Please download and place it in the 'models' directory.")
        return None

    model = vosk.Model(model_path)
    samplerate = int(sd.query_devices(None, 'input')['default_samplerate'])
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=None, dtype='int16',
                            channels=1, callback=callback):
        print("Listening for offline commands...")
        rec = vosk.KaldiRecognizer(model, samplerate)
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                command = result['text']
                print(f"Recognized (offline): {command}")
                return command.lower()

# --- Offline Command Functions ---

def open_notepad():
    system = platform.system()
    if system == "Windows":
        os.system("notepad.exe")
    elif system == "Darwin":
        os.system("open /System/Applications/TextEdit.app")
    else:
        os.system("gedit")
    return "Opening a text editor..."

def open_calculator():
    system = platform.system()
    if system == "Windows":
        os.system("calc.exe")
    elif system == "Darwin":
        os.system("open /System/Applications/Calculator.app")
    else:
        os.system("gnome-calculator")
    return "Opening Calculator..."

def open_file_explorer():
    system = platform.system()
    if system == "Windows":
        os.system("explorer")
    elif system == "Darwin":
        os.system("open .")
    else:
        os.system("xdg-open .")
    return "Opening File Explorer..."

def get_time():
    now = datetime.datetime.now()
    return speak(f"The current time is {now.strftime('%H:%M')}")

# --- Command Handling ---

offline_command_map = {
    "open notepad": open_notepad,
    "open calculator": open_calculator,
    "open file explorer": open_file_explorer,
    "what time is it": get_time,
}

def handle_offline_command(command):
    """Handles offline commands by iterating through a command map."""
    for phrase in sorted(offline_command_map.keys(), key=len, reverse=True):
        if command.startswith(phrase):
            return offline_command_map[phrase]()
    return "Command not recognized."

def listen_online():
    """Listens for and recognizes voice commands using Google Speech Recognition."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for online commands...")
        audio = r.listen(source)
        try:
            command = r.recognize_google(audio)
            print(f"Recognized (online): {command}")
            return command.lower()
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None

# --- Online Command Functions ---

def open_google():
    webbrowser.open("https://www.google.com")
    return "Opening Google..."

def search_youtube(command):
    query = command.replace("search youtube for", "").strip()
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    return f"Searching YouTube for '{query}'..."

def search_wikipedia(command):
    query = command.replace("search wikipedia for", "").strip()
    webbrowser.open(f"https://en.wikipedia.org/wiki/{query}")
    return f"Searching Wikipedia for '{query}'..."

def search_google(command):
    query = command.replace("search for", "").strip()
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searching Google for '{query}'..."


online_command_map = {
    "open google": open_google,
    "search youtube for": search_youtube,
    "search wikipedia for": search_wikipedia,
    "search for": search_google, # Must be last to avoid overriding more specific searches
}

def handle_online_command(command):
    """Handles online commands by iterating through a command map."""
    for phrase in sorted(online_command_map.keys(), key=len, reverse=True):
        if command.startswith(phrase):
            func = online_command_map[phrase]
            # Check if the function needs the command string passed to it
            import inspect
            sig = inspect.signature(func)
            if len(sig.parameters) > 0:
                return func(command)
            else:
                return func()
    return "Command not recognized."

if __name__ == "__main__":
    if is_online():
        print("Status: Online")
        # speak("Hello! I am online and ready to assist you.")
        command = listen_online()
        if command:
            handle_online_command(command)
    else:
        print("Status: Offline")
        # speak("Hello! I am offline, but I can still help with local tasks.")
        # command = listen_offline()
        # if command:
            # handle_offline_command(command)
