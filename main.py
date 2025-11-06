"""
AGP System / Nora - Offline AI Desktop Assistant
Intelligent system-level app and file detection without hardcoded paths
"""

import customtkinter as ctk
import pyttsx3
import speech_recognition as sr
import threading
import time
import requests
import vosk
import sounddevice as sd
import os
import psutil
import webbrowser
import subprocess
import platform
import sqlite3
from datetime import datetime
from pathlib import Path
import json
from difflib import SequenceMatcher
import mimetypes
import queue

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SystemScanner:
    """Intelligently scans and indexes installed applications and files"""

    def __init__(self):
        self.system = platform.system()
        self.app_cache = {}
        self.file_index = {}
        self.last_scan = None
        self.init_scan()

    def init_scan(self):
        """Initial system scan on startup"""
        print("🔍 Scanning system for installed applications...")
        self.scan_installed_apps()
        print(f"✓ Found {len(self.app_cache)} applications")

    def scan_installed_apps(self):
        """Scan system for ALL installed applications dynamically"""
        if self.system == "Windows":
            self._scan_windows_apps()
        elif self.system == "Darwin":
            self._scan_macos_apps()
        else:
            self._scan_linux_apps()

    def _scan_windows_apps(self):
        """Scan Windows registry and common paths for installed apps"""
        import winreg
        # Scan Windows Registry
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)

                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            exe_path = None

                            # Try to get executable path
                            try:
                                exe_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                if not exe_path.endswith('.exe'):
                                    exe_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except:
                                try:
                                    exe_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                except:
                                    pass

                            if name and len(name) > 2:
                                # Store with multiple reference points
                                self.app_cache[name.lower()] = {
                                    'name': name,
                                    'path': exe_path,
                                    'keywords': self._generate_keywords(name)
                                }
                        except Exception as e:
                            # This key might not have DisplayName or InstallLocation, which is fine.
                            pass

                        winreg.CloseKey(subkey)
                    except Exception as e:
                        # Failed to open a subkey, can happen with permissions.
                        continue
                winreg.CloseKey(key)
            except Exception as e:
                # Failed to open the main Uninstall key.
                continue

        # Scan PATH environment variable
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for dir_path in path_dirs:
            if os.path.exists(dir_path):
                try:
                    for file in os.listdir(dir_path):
                        if file.endswith('.exe'):
                            name = file[:-4]
                            full_path = os.path.join(dir_path, file)
                            self.app_cache[name.lower()] = {
                                'name': name,
                                'path': full_path,
                                'keywords': self._generate_keywords(name)
                            }
                except OSError:
                    # Directory might not be readable
                    continue

        # Scan Start Menu
        start_menu_paths = [
            os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        ]

        for sm_path in start_menu_paths:
            if os.path.exists(sm_path):
                self._scan_directory_for_shortcuts(sm_path)

    def _scan_directory_for_shortcuts(self, directory):
        """Recursively scan directory for .lnk files"""
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.lnk'):
                        name = file[:-4]
                        full_path = os.path.join(root, file)
                        self.app_cache[name.lower()] = {
                            'name': name,
                            'path': full_path,
                            'keywords': self._generate_keywords(name)
                        }
        except OSError:
            # Permissions error might occur
            pass

    def _scan_macos_apps(self):
        """Scan macOS /Applications folder"""
        app_paths = ['/Applications', os.path.expanduser('~/Applications')]
        for path in app_paths:
            if os.path.exists(path):
                for item in os.listdir(path):
                    if item.endswith('.app'):
                        name = item[:-4]
                        self.app_cache[name.lower()] = {
                            'name': name,
                            'path': os.path.join(path, item),
                            'keywords': self._generate_keywords(name)
                        }

    def _scan_linux_apps(self):
        """Scan Linux .desktop files"""
        desktop_paths = [
            '/usr/share/applications',
            os.path.expanduser('~/.local/share/applications'),
        ]
        for path in desktop_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.desktop'):
                        name = file[:-8]
                        self.app_cache[name.lower()] = {
                            'name': name,
                            'path': os.path.join(path, file),
                            'keywords': self._generate_keywords(name)
                        }

    def _generate_keywords(self, name):
        """Generate searchable keywords from app name"""
        keywords = set()
        name_lower = name.lower()
        keywords.add(name_lower)

        # Add individual words
        words = name_lower.replace('-', ' ').replace('_', ' ').split()
        keywords.update(words)

        # Add without spaces
        keywords.add(name_lower.replace(' ', ''))

        return list(keywords)

    def find_app(self, query):
        """Intelligently find app using fuzzy matching"""
        query = query.lower().strip()
        best_match = None
        best_score = 0

        for app_key, app_data in self.app_cache.items():
            # Check exact match
            if query == app_key or query in app_data['keywords']:
                return app_data

            # Fuzzy matching
            for keyword in app_data['keywords']:
                score = SequenceMatcher(None, query, keyword).ratio()
                if score > best_score and score > 0.6:  # 60% similarity threshold
                    best_score = score
                    best_match = app_data

        return best_match

    def index_user_files(self, directories=None):
        """Index user files for quick searching"""
        if directories is None:
            directories = [
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Desktop'),
                os.path.expanduser('~/Downloads'),
                os.path.expanduser('~/Music'),
                os.path.expanduser('~/Videos'),
                os.path.expanduser('~/Pictures'),
            ]

        for directory in directories:
            if os.path.exists(directory):
                self._index_directory(directory)

    def _index_directory(self, directory, max_depth=3, current_depth=0):
        """Recursively index files in directory"""
        if current_depth >= max_depth:
            return

        try:
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)

                if os.path.isfile(full_path):
                    name_lower = item.lower()
                    self.file_index[name_lower] = {
                        'name': item,
                        'path': full_path,
                        'size': os.path.getsize(full_path),
                        'modified': os.path.getmtime(full_path),
                        'type': mimetypes.guess_type(full_path)[0]
                    }
                elif os.path.isdir(full_path):
                    self._index_directory(full_path, max_depth, current_depth + 1)
        except OSError:
            pass

    def find_file(self, query):
        """Find file using fuzzy matching"""
        query = query.lower().strip()
        best_match = None
        best_score = 0

        for file_key, file_data in self.file_index.items():
            score = SequenceMatcher(None, query, file_key).ratio()
            if score > best_score and score > 0.5:
                best_score = score
                best_match = file_data

        return best_match


class ProcessManager:
    """Manages running processes intelligently"""

    def get_running_apps(self):
        """Get all currently running applications"""
        running = {}
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                info = proc.info
                if info['name']:
                    running[info['name'].lower()] = {
                        'pid': info['pid'],
                        'name': info['name'],
                        'exe': info['exe']
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return running

    def is_app_running(self, app_name):
        """Check if app is currently running"""
        app_name = app_name.lower()
        running = self.get_running_apps()

        for proc_name, proc_info in running.items():
            if app_name in proc_name or proc_name.startswith(app_name):
                return proc_info
        return None

    def close_app_by_name(self, app_name):
        """Intelligently close app by name"""
        app_name = app_name.lower()
        killed_count = 0

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                if app_name in proc_name:
                    proc.terminate()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return killed_count


class MemoryManager:
    """Handles local memory and learning"""

    def __init__(self):
        self.db_path = "agp_memory.db"
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                command TEXT,
                intent TEXT,
                response TEXT,
                success INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_usage (
                app_name TEXT PRIMARY KEY,
                usage_count INTEGER,
                last_used TEXT,
                success_rate REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_interaction(self, command, intent, response, success):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interactions (timestamp, command, intent, response, success)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), command, intent, response, success))
        conn.commit()
        conn.close()

    def update_app_usage(self, app_name, success):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT usage_count, success_rate FROM app_usage WHERE app_name = ?', (app_name,))
        result = cursor.fetchone()

        if result:
            count, rate = result
            new_count = count + 1
            new_rate = ((rate * count) + (1 if success else 0)) / new_count
            cursor.execute('''
                UPDATE app_usage
                SET usage_count = ?, last_used = ?, success_rate = ?
                WHERE app_name = ?
            ''', (new_count, datetime.now().isoformat(), new_rate, app_name))
        else:
            cursor.execute('''
                INSERT INTO app_usage (app_name, usage_count, last_used, success_rate)
                VALUES (?, 1, ?, ?)
            ''', (app_name, datetime.now().isoformat(), 1.0 if success else 0.0))

        conn.commit()
        conn.close()

    def get_user_preference(self, key, default=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default

    def set_user_preference(self, key, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()


class IntentParser:
    """Advanced NLP-based intent parsing"""

    def parse(self, text):
        text = text.lower().strip()

        # Intent patterns with priority
        patterns = [
            ('toggle_listening', ['start listening', 'stop listening', 'continuous mode']),
            ('greeting', ['hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon']),
            ('open_app', ['open', 'launch', 'start', 'run']),
            ('close_app', ['close', 'quit', 'exit', 'kill', 'stop', 'end']),
            ('open_file', ['open file', 'show file', 'file', 'document']),
            ('play_media', ['play', 'play music', 'play video', 'music', 'video', 'song']),
            ('search_web', ['search', 'google', 'look up', 'find online', 'search for']),
            ('browse', ['browse', 'website', 'open site', 'go to']),
            ('system_info', ['system', 'computer info', 'specs', 'hardware']),
            ('time', ['time', 'what time', 'current time', "what's the time"]),
            ('date', ['date', 'what date', 'today', "what's today"]),
            ('help', ['help', 'what can you do', 'commands', 'capabilities']),
            ('thanks', ['thank', 'thanks', 'appreciate']),
        ]

        for intent, keywords in patterns:
            for keyword in keywords:
                if keyword in text:
                    param = text.replace(keyword, '').strip()
                    return intent, param if param else text

        return 'general', text

    def extract_entity(self, text, intent):
        """Extract the main entity (app name, file name, etc.)"""
        # Remove common words
        stop_words = ['the', 'a', 'an', 'please', 'can', 'you', 'could', 'would', 'will']
        words = text.lower().split()
        filtered = [w for w in words if w not in stop_words]
        return ' '.join(filtered).strip()


class SkillRouter:
    """Routes commands to system-level actions"""

    def __init__(self, scanner, process_mgr, memory):
        self.scanner = scanner
        self.process_mgr = process_mgr
        self.memory = memory
        self.system = platform.system()

    def open_app(self, app_query):
        """Open app using intelligent detection"""
        # First check if already running
        running = self.process_mgr.is_app_running(app_query)
        if running:
            return f"{app_query} is already running"

        # Find app in system scan
        app = self.scanner.find_app(app_query)

        if app:
            try:
                if self.system == "Windows":
                    if app['path'].endswith('.lnk'):
                        os.startfile(app['path'])
                    else:
                        subprocess.Popen(app['path'], shell=True)
                elif self.system == "Darwin":
                    subprocess.Popen(['open', '-a', app['name']])
                else:
                    subprocess.Popen([app['path']])

                self.memory.update_app_usage(app['name'], True)
                return f"Opening {app['name']}"
            except Exception as e:
                self.memory.update_app_usage(app['name'], False)
                return f"Error opening {app['name']}: {str(e)}"
        else:
            return f"Could not find application: {app_query}"

    def close_app(self, app_query):
        """Close app intelligently"""
        count = self.process_mgr.close_app_by_name(app_query)
        if count > 0:
            return f"Closed {count} instance(s) of {app_query}"
        else:
            return f"{app_query} is not running"

    def open_file(self, file_query):
        """Open file using intelligent search"""
        file_info = self.scanner.find_file(file_query)

        if file_info:
            try:
                if self.system == "Windows":
                    os.startfile(file_info['path'])
                elif self.system == "Darwin":
                    subprocess.Popen(['open', file_info['path']])
                else:
                    subprocess.Popen(['xdg-open', file_info['path']])
                return f"Opening {file_info['name']}"
            except Exception as e:
                return f"Error opening file: {str(e)}"
        else:
            return f"Could not find file: {file_query}"

    def play_media(self, query):
        """Play media file"""
        # Search in media folders
        media_dirs = [
            os.path.expanduser('~/Music'),
            os.path.expanduser('~/Videos')
        ]

        for directory in media_dirs:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if query.lower() in file.lower():
                            full_path = os.path.join(root, file)
                            return self.open_file(full_path)

        return f"Could not find media: {query}"

    def search_web(self, query):
        """Search web"""
        try:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Searching for: {query}"
        except Exception as e:
            return f"Error: {str(e)}"

    def browse_website(self, url):
        """Open website"""
        try:
            if not url.startswith('http'):
                url = 'https://' + url
            webbrowser.open(url)
            return f"Opening {url}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_system_info(self):
        """Get system info"""
        info = f"System: {platform.system()} {platform.release()}\n"
        info += f"CPU: {platform.processor()}\n"
        info += f"Cores: {psutil.cpu_count()}\n"
        info += f"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB"
        return info

    def get_time(self):
        return datetime.now().strftime("It's %I:%M %p")

    def get_date(self):
        return datetime.now().strftime("Today is %A, %B %d, %Y")


class AGPAssistant:
    """Main AI Assistant"""

    def __init__(self, gui):
        self.gui = gui
        self.continuous_listening = False

        # Initialize core systems
        print("🚀 Initializing AGP System...")
        self.scanner = SystemScanner()
        self.process_mgr = ProcessManager()
        self.memory = MemoryManager()
        self.parser = IntentParser()
        self.skills = SkillRouter(self.scanner, self.process_mgr, self.memory)

    def is_online(self):
        """Checks for an active internet connection."""
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except requests.ConnectionError:
            return False

        # TTS Engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 180)

        # Speech recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # Background file indexing
        threading.Thread(target=self._background_file_index, daemon=True).start()

        print("✅ AGP System Ready!")

    def _background_file_index(self):
        """Index files in background"""
        time.sleep(5)  # Wait for startup
        self.gui.update_status("Indexing files...")
        self.scanner.index_user_files()
        self.gui.update_status("Ready")

    def speak(self, text):
        """Text to speech"""
        self.gui.add_response(f"🗣️ {text}")
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except:
            pass

    def listen(self):
        """Listen to microphone and use the appropriate speech recognition engine."""
        if self.is_online():
            return self.listen_online()
        else:
            return self.listen_offline()

    def listen_online(self):
        """Listen to microphone and use Google Speech Recognition."""
        try:
            with self.microphone as source:
                self.gui.update_status("Listening (Online)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)

            self.gui.update_status("Processing...")
            text = self.recognizer.recognize_google(audio, language='en-US')
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            self.gui.add_response(f"❌ Online Recognition Error: {str(e)}")
            return None

    def listen_offline(self):
        """Listen to microphone and use VOSK for offline speech recognition."""
        model_path = "models/vosk-model-en-us-0.22-lgraph"
        if not os.path.exists(model_path):
            self.gui.add_response("❌ Offline model not found.")
            return None

        try:
            model = vosk.Model(model_path)
            samplerate = int(sd.query_devices(None, 'input')['default_samplerate'])
            q = queue.Queue()

            def callback(indata, frames, time, status):
                if status:
                    print(status, flush=True)
                q.put(bytes(indata))

            with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=None, dtype='int16',
                                    channels=1, callback=callback):
                self.gui.update_status("Listening (Offline)...")
                rec = vosk.KaldiRecognizer(model, samplerate)
                # Listen for a maximum of 5 seconds
                start_time = time.time()
                while time.time() - start_time < 5:
                    try:
                        data = q.get_nowait()
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            command = result['text']
                            if command:
                                return command.lower()
                    except queue.Empty:
                        time.sleep(0.1)
                # If loop finishes without recognizing anything, return None
                return None
        except Exception as e:
            self.gui.add_response(f"❌ Offline Recognition Error: {str(e)}")
            return None

    def process_command(self, command):
        """Process user command"""
        self.gui.add_command(command)
        self.gui.update_status("Thinking...")

        # Parse intent
        intent, param = self.parser.parse(command)

        # Route to appropriate skill
        response = ""
        success = True

        try:
            if intent == 'toggle_listening':
                if self.continuous_listening:
                    self.continuous_listening = False
                    response = "Continuous listening stopped."
                else:
                    self.continuous_listening = True
                    response = "Continuous listening started."
            elif intent == 'greeting':
                response = "Hello! How can I assist you today?"
            elif intent == 'open_app':
                response = self.skills.open_app(param)
            elif intent == 'close_app':
                response = self.skills.close_app(param)
            elif intent == 'open_file':
                response = self.skills.open_file(param)
            elif intent == 'play_media':
                response = self.skills.play_media(param)
            elif intent == 'search_web':
                response = self.skills.search_web(param)
            elif intent == 'browse':
                response = self.skills.browse_website(param)
            elif intent == 'system_info':
                response = self.skills.get_system_info()
            elif intent == 'time':
                response = self.skills.get_time()
            elif intent == 'date':
                response = self.skills.get_date()
            elif intent == 'help':
                response = self._get_help_text()
            elif intent == 'thanks':
                response = "You're welcome!"
            else:
                response = "I'm not sure how to help with that."
                success = False
        except Exception as e:
            response = f"Error: {str(e)}"
            success = False

        # Log interaction
        self.memory.log_interaction(command, intent, response, success)

        # Respond
        self.speak(response)
        self.gui.update_status("Ready")

        # If continuous listening is on, start listening again
        if self.continuous_listening and intent != 'toggle_listening':
            self.gui.on_voice_command()

    def _get_help_text(self):
        return ("I can open and close applications, play music and videos, "
                "search the web, tell you the time and date, and much more. "
                "Just ask me naturally!")


class AGPInterface(ctk.CTk):
    """Modern GUI Interface"""

    def __init__(self):
        super().__init__()

        self.title("AGP System - Nora")
        self.geometry("800x600")

        # Always on top
        self.attributes("-topmost", True)

        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray15"))
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        title = ctk.CTkLabel(header, text="🌌 AGP System / Nora",
                            font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=10)

        self.status_label = ctk.CTkLabel(header, text="Initializing...",
                                        font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

        # Output area
        self.output_frame = ctk.CTkScrollableFrame(self, fg_color=("gray90", "gray10"))
        self.output_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Input area
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="Type your command...",
                                        height=40, font=ctk.CTkFont(size=14))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind("<Return>", self.on_text_command)

        self.send_btn = ctk.CTkButton(input_frame, text="Send", width=100,
                                      command=self.on_text_command)
        self.send_btn.grid(row=0, column=1)

        self.voice_btn = ctk.CTkButton(input_frame, text="🎤 Voice", width=100,
                                       command=self.on_voice_command,
                                       fg_color=("green", "darkgreen"))
        self.voice_btn.grid(row=0, column=2, padx=(10, 0))

        # Initialize assistant
        self.assistant = AGPAssistant(self)
        self.update_status("Ready")

        # Initial greeting
        self.add_response("🌌 AGP System initialized. How can I help you?")

    def update_status(self, status):
        self.status_label.configure(text=f"Status: {status}")

    def add_command(self, text):
        frame = ctk.CTkFrame(self.output_frame, fg_color=("blue", "darkblue"))
        frame.pack(fill="x", pady=5, padx=10)
        label = ctk.CTkLabel(frame, text=f"👤 You: {text}", anchor="w",
                            font=ctk.CTkFont(size=13))
        label.pack(fill="x", padx=10, pady=5)

    def add_response(self, text):
        frame = ctk.CTkFrame(self.output_frame, fg_color=("gray80", "gray20"))
        frame.pack(fill="x", pady=5, padx=10)
        label = ctk.CTkLabel(frame, text=text, anchor="w", wraplength=700,
                            font=ctk.CTkFont(size=13))
        label.pack(fill="x", padx=10, pady=5)

    def on_text_command(self, event=None):
        command = self.input_entry.get().strip()
        if command:
            self.input_entry.delete(0, 'end')
            threading.Thread(target=self.assistant.process_command,
                           args=(command,), daemon=True).start()

    def on_voice_command(self):
        # Toggle continuous listening mode
        if self.assistant.continuous_listening:
            self.assistant.continuous_listening = False
            self.update_voice_btn()
            self.assistant.speak("Continuous listening stopped.")
        else:
            self.assistant.continuous_listening = True
            self.update_voice_btn()
            self.assistant.speak("Continuous listening started.")
            # Start the first listen
            threading.Thread(target=self._continuous_listen_loop, daemon=True).start()

    def _continuous_listen_loop(self):
        while self.assistant.continuous_listening:
            text = self.assistant.listen()
            if text:
                # Process command in the main thread via after()
                self.after(0, self.assistant.process_command, text)
            else:
                self.update_status("No speech detected")

    def update_voice_btn(self):
        if self.assistant.continuous_listening:
            self.voice_btn.configure(text="Listening...", fg_color="red")
        else:
            self.voice_btn.configure(text="🎤 Voice", fg_color=("green", "darkgreen"))


if __name__ == "__main__":
    app = AGPInterface()
    app.mainloop()
