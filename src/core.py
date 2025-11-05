
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

def handle_offline_command(command):
    """Handles offline commands."""
    if "open notepad" in command:
        print("Opening Notepad...")
        os.system("notepad.exe")
    elif "what time is it" in command:
        now = datetime.datetime.now()
        speak(f"The current time is {now.strftime('%H:%M')}")
    else:
        print("Command not recognized.")

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

def handle_online_command(command):
    """Handles online commands."""
    if "open google" in command:
        print("Opening Google...")
        webbrowser.open("https://www.google.com")
    elif "search for" in command:
        query = command.replace("search for", "")
        print(f"Searching for {query}...")
        webbrowser.open(f"https://www.google.com/search?q={query}")
    else:
        print("Command not recognized.")

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
