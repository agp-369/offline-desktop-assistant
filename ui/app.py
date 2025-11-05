
import customtkinter as ctk

class VoiceAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Voice Assistant")
        self.geometry("500x400")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.status_label = ctk.CTkLabel(self, text="Status: Unknown")
        self.status_label.pack(pady=10)

        self.text_area = ctk.CTkTextbox(self, width=480, height=200)
        self.text_area.pack(pady=10)

        self.command_entry = ctk.CTkEntry(self, width=480, placeholder_text="Enter a command...")
        self.command_entry.pack(pady=10)

        self.listen_button = ctk.CTkButton(self, text="Listen", command=self.listen)
        self.listen_button.pack(pady=10)

    def listen(self):
        # This is now handled in the MainApp class
        pass
