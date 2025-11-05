
from ui.app import VoiceAssistantApp
from src.core import is_online, listen_online, handle_online_command, listen_offline, handle_offline_command
import threading
import queue

class MainApp(VoiceAssistantApp):
    def __init__(self):
        super().__init__()
        self.update_status()
        self.text_queue = queue.Queue()
        self.after(100, self.process_text_queue)

    def update_status(self):
        if is_online():
            self.status_label.configure(text="Status: Online")
        else:
            self.status_label.configure(text="Status: Offline")

    def listen(self):
        self.listen_button.configure(text="Listening...")
        self.update_status()

        def listen_thread():
            if is_online():
                command = listen_online()
                if command:
                    self.after(0, self.handle_command, command, True)
            else:
                command = listen_offline()
                if command:
                    self.after(0, self.handle_command, command, False)
            self.after(0, self.reset_listen_button)

        thread = threading.Thread(target=listen_thread)
        thread.daemon = True
        thread.start()

    def handle_command(self, command, online):
        response = ""
        if online:
            response = handle_online_command(command)
        else:
            response = handle_offline_command(command)
        self.animate_text(response)

    def animate_text(self, text):
        for char in text:
            self.text_queue.put(char)

    def process_text_queue(self):
        try:
            char = self.text_queue.get_nowait()
            self.text_area.insert("end", char)
            self.after(50, self.process_text_queue)
        except queue.Empty:
            self.after(100, self.process_text_queue)

    def reset_listen_button(self):
        self.listen_button.configure(text="Listen")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
