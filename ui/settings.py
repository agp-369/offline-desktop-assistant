
import customtkinter as ctk

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")
        self.geometry("300x200")

        self.theme_label = ctk.CTkLabel(self, text="Theme:")
        self.theme_label.pack(pady=10)

        self.theme_menu = ctk.CTkOptionMenu(self, values=["Dark", "Light", "System"],
                                             command=self.change_theme)
        self.theme_menu.pack(pady=10)
        self.theme_menu.set(ctk.get_appearance_mode())

    def change_theme(self, theme):
        ctk.set_appearance_mode(theme)
