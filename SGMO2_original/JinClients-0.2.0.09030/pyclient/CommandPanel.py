# Copyright 2026 Sony Global Manufacturing & Operations Corporation

import asyncio
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from typing import Optional, List
from ZeroMQClient import ZeroMQClient

# ==== 設定 ====
VERSION:      str = "0.2.0"
SUB_ADDRESS:  str = "tcp://localhost:55555"
PUSH_ADDRESS: str = "tcp://localhost:55556"

# ==== グローバル ====
async_loop: Optional[asyncio.AbstractEventLoop] = None
running: bool = True
client: Optional[ZeroMQClient] = None
debug_port_lock: asyncio.Lock = asyncio.Lock()
debug_port_transaction: asyncio.Event = asyncio.Event();
debug_port_response_lock: threading.Lock = threading.Lock()
debug_port_response: Optional[List[str]] = None

# UI への反映用 (UI スレッドから読み書き)
app: Optional["CommandPanelApp"] = None

class CommandPanelApp:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("Command Panel")
        self.root.geometry(f"605x530")
        self.root.resizable(False, False)
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        # ウィジェット配置
        self._build_widgets()

        # 終了処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        # ボタンの設定をテーブル化
        buttons_config = [
            {"name": "Volt 0",                  "commands": ["dd_ep bias 0", "dd_ep ep 0"], "row": 0, "column": 0},
            {"name": "Go0 Point",               "commands": ["mw_ac go0"],                  "row": 1, "column": 0},
            {"name": "Volt 0.1",                "commands": ["dd_ep bias 1"],               "row": 2, "column": 0},

            {"name": "Current Data Low 10K",    "commands": ["sv_info_sender start 0"],     "row": 0, "column": 1},
            {"name": "Current Data High 10K",   "commands": ["sv_info_sender start 10"],    "row": 1, "column": 1},
            {"name": "Current Data High 50K",   "commands": ["sv_info_sender start 2"],     "row": 2, "column": 1},
            {"name": "Current Data High 100K",  "commands": ["sv_info_sender start 1"],     "row": 3, "column": 1},
            {"name": "Current Data Stop",       "commands": ["sv_info_sender stop"],        "row": 4, "column": 1},

            {"name": "First Cut",               "commands": ["mcbj fc start"],              "row": 0, "column": 2},
            {"name": "Targeting",               "commands": ["mcbj targeting start"],       "row": 1, "column": 2},
            {"name": "Motor Training",          "commands": ["mcbj mt start"],              "row": 2, "column": 2},
            {"name": "Piezo Training",          "commands": ["mcbj pt start"],              "row": 3, "column": 2},
            {"name": "Auto Cut",                "commands": ["mcbj ac start"],              "row": 4, "column": 2},

            {"name": "Calibration",             "commands": ["mcbj cal start"],             "row": 0, "column": 3},
            {"name": "Expand Gap",              "commands": ["asz eg start"],               "row": 1, "column": 3},
            {"name": "Hold Gap",                "commands": ["asz hg start"],               "row": 2, "column": 3},
            {"name": "MCBJ/ASZ Stop",           "commands": ["mcbj stop"],                  "row": 4, "column": 3},
        ]

        # ボタンフレームの作成
        button_frame = tk.Frame(self.root, bd=1, relief='ridge')
        button_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        # ボタンの作成と配置
        self.buttons = []
        for config in buttons_config:
            button = tk.Button(button_frame, text=config["name"], command=self._create_button_action(config["commands"]), width=18)
            button.grid(row=config["row"], column=config["column"], padx=5, pady=4)
            self.buttons.append(button)

        # カスタムコマンドフレームの作成
        custom_command_frame = tk.Frame(self.root, bd=1, relief='ridge')
        custom_command_frame.grid(row=1, column=0, padx=10, pady=4, sticky='nsew')

        # 任意のコマンドを入力するテキストボックスと送信ボタンの作成
        custom_command_label = tk.Label(custom_command_frame, text="Custom Command:")
        custom_command_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')

        self.custom_command_entry = tk.Entry(custom_command_frame, width=30)
        self.custom_command_entry.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        self.custom_command_button = tk.Button(custom_command_frame, text="Send", command=self._dispatch_invoke_custom_command)
        self.custom_command_button.grid(row=0, column=2, padx=10, pady=10, sticky='w')

        # ファイル選択＆送信フレームの作成
        self.file_frame = tk.Frame(self.root, bd=1, relief='ridge')
        self.file_frame.grid(row=2, column=0, padx=10, pady=0, sticky='nsew')

        # ファイル指定ボタンと送信ボタンの作成
        self.file_path = tk.StringVar(value="Not Select")
        self.file_select_button = tk.Button(self.file_frame, text="Select File", command=self._select_file)
        self.file_select_button.grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.file_send_button = tk.Button(self.file_frame, text="Send File Commands", command=self._dispatch_invoke_file_commands)
        self.file_send_button.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        # 応答表示用のスクロールテキストウィジェットの作成
        self.response_display = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=14, state=tk.DISABLED)
        self.response_display.grid(row=3, column=0, columnspan=3, padx=10, pady=4, sticky='nsew')

        # Abort ボタンの作成
        self.abort_button = tk.Button(self.root, text="Abort", state=tk.DISABLED, command=self._abort_command)
        self.abort_button.grid(row=4, column=0, padx=10, pady=4, sticky='nsew')

    def _create_button_action(self, commands):
        def _dispatch_invoke_preset_command():
            async def _invoke_preset_command():
                self.root.after(0, self._disable_command_widgets)
                # コマンドを順次送信
                for command in commands:
                    self.root.after(0, self._append_command_record, command)
                    await client.send_debug_async(command);

                self.root.after(0, self._enable_command_widgets)

            asyncio.run_coroutine_threadsafe(_invoke_preset_command(), async_loop)

        return _dispatch_invoke_preset_command

    def _dispatch_invoke_custom_command(self):
        command = self.custom_command_entry.get().strip()
        async def _invoke_custom_command():
            if command:
                self.root.after(0, self._disable_command_widgets)
                self.root.after(0, self._append_command_record, command)
                await client.send_debug_async(command);
                self.root.after(0, self._enable_command_widgets)

        asyncio.run_coroutine_threadsafe(_invoke_custom_command(), async_loop)

    def _select_file(self):
        file_path = filedialog.askopenfilename(initialdir=self.script_dir)
        if file_path:
            # メインスレッドで更新を行う
            self.root.after(0, self._update_file_path, file_path)

    def _update_file_path(self, file_path):
        self.file_path.set(file_path)

    def _dispatch_invoke_file_commands(self):
        async def _invoke_file_commands():
            file_path = self.file_path.get()
            if file_path and file_path != "Not Select":
                try:
                    # ボタンを無効化
                    self.root.after(0, self._disable_command_widgets)
                    with open(file_path, 'r') as file:
                        for line in file:
                            command = line.strip()
                            if command:
                                # 送信コマンドを表示
                                self.root.after(0, self._append_command_record, command)
                                await client.send_debug_async(command);
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to read file: {e}")
                finally:
                    # ボタンを再度有効化
                    self.root.after(0, self._enable_command_widgets)

        asyncio.run_coroutine_threadsafe(_invoke_file_commands(), async_loop)

    def _abort_command(self):
        self._enable_command_widgets()

    def _append_command_record(self, command: str):
        self.response_display.config(state=tk.NORMAL)
        self.response_display.insert(tk.END, f"Send : {command}\n")
        self.response_display.config(state=tk.DISABLED)
        self.response_display.yview(tk.END)
        self.root.update_idletasks()  # イベントループを更新

    def _enable_command_widgets(self):
        for button in self.buttons:
            button.config(state=tk.NORMAL)
        self.file_select_button.config(state=tk.NORMAL)
        self.file_send_button.config(state=tk.NORMAL)
        self.custom_command_button.config(state=tk.NORMAL)
        self.abort_button.config(state=tk.DISABLED)

    def _disable_command_widgets(self):
        for button in self.buttons:
            button.config(state=tk.DISABLED)
        self.file_select_button.config(state=tk.DISABLED)
        self.file_send_button.config(state=tk.DISABLED)
        self.custom_command_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.NORMAL)

    def _on_close(self) -> None:
        global running
        running = False
        try:
            if client is not None:
                client.stop()
        except Exception:
            pass
        self.root.destroy()

# ====================================================
#  メイン
# ====================================================
def main():
    global async_loop, running, client, app

    root = tk.Tk()
    app = CommandPanelApp(root)

    # 新しい asyncio のイベントループを作成し、バックグラウンドスレッドで開始
    async_loop = asyncio.new_event_loop()
    def run_async_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    threading.Thread(target=run_async_loop, args=(async_loop,), daemon=True).start()

    client = ZeroMQClient(SUB_ADDRESS, PUSH_ADDRESS)
    client.start()

    try:
        root.mainloop()
    finally:
        running = False
        try:
            client.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()
