# Copyright 2026 Sony Global Manufacturing & Operations Corporation

import asyncio
import datetime
import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkFont
from tkinter import messagebox, scrolledtext, filedialog
from typing import Any, Callable, Coroutine, Optional, List
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
app: Optional["WizardApp"] = None

class WizardApp:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("Measurement Wizard")

        # 画面中央に表示
        window_width  = 400
        window_height = 500
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(400, 410)
        #self.root.resizable(False, False)
        #self.root.option_add("*Label.Font", "Arial 16")

        self.root.tk_setPalette(background="#F8F8F8")  # 標準の背景色を #F8F8F8 に変更
        self.root.columnconfigure(0, weight=1)  # 伸縮
        self.root.rowconfigure(0, weight=0)     # 固定
        self.root.rowconfigure(1, weight=0)     # 固定
        self.root.rowconfigure(2, weight=1)     # 伸縮
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.mdl2_font_normal = tkFont.Font(family="Segoe MDL2 Assets", size=10, weight="normal")
        self.mdl2_font_bold = tkFont.Font(family="Segoe MDL2 Assets", size=10, weight="bold")
        self.high_mode_sample_rate_khz: int = 10

        # ウィジェット配置
        self._build_widgets()

        # 終了処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:

        # [1] メニュー領域

        # self.root.config(menu=...) で追加する標準のメニューバーは Window 環境では背景色を変更できないため、Frame で自作する。
        menu_background = "#F3F3F3"
        menu_bar = tk.Frame(self.root, bg=menu_background)
        menu_bar.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')

        # [1-1] Options メニュー

        options_menu_button = tk.Menubutton(menu_bar, text="Options", bg=menu_background)
        options_menu_button.pack(side="left", padx=4, pady=0)
        options_menu = tk.Menu(options_menu_button, tearoff=False, bg=menu_background)
        options_menu_button.config(menu=options_menu)

        # [1-1-1] Sample Rate メニュー

        sample_rate_menu_10khz_checked = tk.BooleanVar(value=True)
        sample_rate_menu_50khz_checked = tk.BooleanVar(value=False)
        sample_rate_menu_100khz_checked = tk.BooleanVar(value=False)

        def _on_sample_rate_menu_clicked(sample_rate_khz: int, check_target_variable: tk.BooleanVar):
            self.high_mode_sample_rate_khz = sample_rate_khz
            sample_rate_menu_10khz_checked.set(False)
            sample_rate_menu_50khz_checked.set(False)
            sample_rate_menu_100khz_checked.set(False)
            check_target_variable.set(True)

        sample_rate_menu = tk.Menu(options_menu, tearoff=False, bg=menu_background)
        options_menu.add_cascade(label="Sample Rate", menu=sample_rate_menu)
        sample_rate_menu.add_checkbutton(label="10 kHz", variable=sample_rate_menu_10khz_checked, command=lambda: _on_sample_rate_menu_clicked(10, sample_rate_menu_10khz_checked))
        sample_rate_menu.add_checkbutton(label="50 kHz", variable=sample_rate_menu_50khz_checked, command=lambda: _on_sample_rate_menu_clicked(50, sample_rate_menu_50khz_checked))
        sample_rate_menu.add_checkbutton(label="100 kHz", variable=sample_rate_menu_100khz_checked, command=lambda: _on_sample_rate_menu_clicked(100, sample_rate_menu_100khz_checked))

        # [2] メイン領域

        process_frame = tk.Frame(self.root, bd=0)
        process_frame.grid(row=1, column=0, padx=6, pady=0, sticky='nsew')
        process_frame.columnconfigure(0, weight=0)  # 固定
        process_frame.columnconfigure(1, weight=1)  # 伸縮
        process_frame.columnconfigure(2, weight=0, minsize=80)  # 固定
        process_frame.columnconfigure(3, weight=0, minsize=80)  # 固定
        process_frame.columnconfigure(4, weight=0, minsize=80)  # 固定

        # [2-1] Settings 領域

        tk.Label(process_frame, text="Settings").grid(row=0, column=0, padx=1, pady=(12, 0), sticky='w')

        settings_frame = tk.Frame(process_frame, bd=0)
        settings_frame.grid(row=0, column=1, columnspan=4, padx=0, pady=(12, 0), sticky='nsew')
        settings_frame.columnconfigure(0, weight=1)  # 伸縮
        settings_frame.columnconfigure(1, weight=0)  # 固定

        self.file_path: tk.StringVar = tk.StringVar()
        tk.Entry(settings_frame, textvariable=self.file_path, state="readonly").grid(row=0, column=0, padx=1, pady=0, sticky='ew')

        file_select_button = tk.Button(settings_frame, text="\uED25", font=self.mdl2_font_normal, command=lambda: asyncio.run_coroutine_threadsafe(self._process_load_settings_async(), async_loop))
        file_select_button.grid(row=0, column=1, padx=1, pady=0)
        self.file_select_button_wrapper = WidgetWrapper(file_select_button)

        # [2-2] Setup 領域

        self.setup_stop_requested = False
        tk.Label(process_frame, text="Setup").grid(row=1, column=0, padx=1, pady=(12, 0), sticky='w')

        setup_start_button = tk.Button(process_frame, text="Start", state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self._process_setup_start_async(), async_loop))
        setup_start_button.grid(row=1, column=2, padx=1, pady=(12, 0), sticky='ew')
        self.setup_start_button_wrapper = WidgetWrapper(setup_start_button)
        setup_stop_button = tk.Button(process_frame, text="Stop", state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self._process_setup_stop_async(), async_loop))
        setup_stop_button.grid(row=1, column=3, padx=1, pady=(12, 0), sticky='ew')
        self.setup_stop_button_wrapper = WidgetWrapper(setup_stop_button)
        setup_reset_button = tk.Button(process_frame, text="Reset", state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self._process_setup_reset_async(), async_loop))
        setup_reset_button.grid(row=1, column=4, padx=1, pady=(12, 0), sticky='ew')
        self.setup_reset_button_wrapper = WidgetWrapper(setup_reset_button)

        setup_frame = tk.Frame(process_frame, bd=1, relief="sunken")
        setup_frame.grid(row=2, column=1, columnspan=4, padx=0, pady=(6, 0), sticky='nsew')
        setup_frame.columnconfigure(0, weight=0)  # 固定
        setup_frame.columnconfigure(1, weight=1)  # 伸縮
        setup_frame.columnconfigure(2, weight=0)  # 固定

        self.setup_items: List[SetupItem] = [
            SetupItem(self, setup_frame, 0,  "Initialize",         self._process_initialize_core_async),
            SetupItem(self, setup_frame, 1,  "Move to Zero Point", self._process_move_to_zero_point_core_async),
            SetupItem(self, setup_frame, 2,  "Attach Chip",        self._process_attach_chip_core_async),
            SetupItem(self, setup_frame, 3,  "Apply Bias",         self._process_apply_bias_core_async),
            SetupItem(self, setup_frame, 4,  "First Cut",          self._process_first_cut_core_async),
            SetupItem(self, setup_frame, 5,  "Motor Training",     self._process_motor_training_core_async),
            SetupItem(self, setup_frame, 6,  "Piezo Training",     self._process_piezo_training_core_async),
            SetupItem(self, setup_frame, 7,  "Auto Cut",           self._process_auto_cut_core_async),
            SetupItem(self, setup_frame, 8,  "Change Mode",        self._process_change_mode_core_async),
            SetupItem(self, setup_frame, 9,  "Calibrate",          self._process_calibration_core_async),
            SetupItem(self, setup_frame, 10, "Expand Gap",         self._process_expand_gap_core_async),
        ]

        # [2-3] Measurement 領域

        tk.Label(process_frame, text="Measurement").grid(row=3, column=0, padx=1, pady=(12, 0), sticky='w')

        measurement_start_button = tk.Button(process_frame, text="Start", state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self._process_measurement_start_async(), async_loop))
        measurement_start_button.grid(row=3, column=3, padx=1, pady=(12, 0), sticky='ew')
        self.measurement_start_button_wrapper = WidgetWrapper(measurement_start_button)
        measurement_stop_button = tk.Button(process_frame, text="Stop", state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self._process_measurement_stop_async(), async_loop))
        measurement_stop_button.grid(row=3, column=4, padx=1, pady=(12, 0), sticky='ew')
        self.measurement_stop_button_wrapper = WidgetWrapper(measurement_stop_button)

        # [3] ログ表示領域

        self.record_display = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, state=tk.DISABLED, background="#FFFFFF")
        self.record_display.grid(row=2, column=0, padx=6, pady=(12, 6), sticky='nsew')

    def _lock_setup_items(self):
        for item in self.setup_items:
            item.lock()

    def _unlock_setup_items(self):
        for item in self.setup_items:
            item.unlock()

    def _on_setup_item_start(self, item_index: int):
        # check_label: item_index 以降グレーアウト
        # button: item_index 通常表示、item_index + 1 以降グレーアウト
        for item in self.setup_items[item_index:]:
            item.reset()
        self.setup_items[item_index].enable()

    def _on_setup_item_success(self, item_index: int):
        self.setup_items[item_index].mark_success()
        if item_index + 1 < len(self.setup_items):
            self.setup_items[item_index + 1].enable()
        else:
            self.measurement_start_button_wrapper.enable()

    # Setting Load ボタン押下時の処理
    async def _process_load_settings_async(self):
        file_path = filedialog.askopenfilename(initialdir=self.script_dir)
        if file_path:
            try:
                # ボタンを無効化
                self.root.after(0, self.file_select_button_wrapper.lock)
                self.root.after(0, self.setup_start_button_wrapper.lock)
                self.root.after(0, self.setup_reset_button_wrapper.lock)
                self.root.after(0, self.measurement_start_button_wrapper.lock)
                self.root.after(0, self.measurement_stop_button_wrapper.lock)

                self.root.after(0, self._lock_setup_items)
                with open(file_path, 'r') as file:
                    for line in file:
                        command = line.strip()
                        if command:
                            # 送信コマンドを表示
                            self.root.after(0, self._append_record, "INFO", f"Sending setting command: {command}")
                            await client.send_debug_async(command);

                # ファイル読み込み成功時のみ self.file_path に反映し、Setup 操作ボタンを解除
                old_file_path = self.file_path.get()
                self.root.after(0, lambda: self.file_path.set(file_path.replace("/", "\\")))

                # 初めて Load したときのみ Setup 操作ボタンを解除
                if not old_file_path:
                    self.root.after(0, self.setup_start_button_wrapper.enable)
                    self.root.after(0, self.setup_reset_button_wrapper.enable)
                    self.root.after(0, self.setup_items[0].enable)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")
            finally:
                # ボタンを再度有効化
                self.root.after(0, self._unlock_setup_items)
                self.root.after(0, self.file_select_button_wrapper.unlock)
                self.root.after(0, self.setup_start_button_wrapper.unlock)
                self.root.after(0, self.setup_reset_button_wrapper.unlock)
                self.root.after(0, self.measurement_start_button_wrapper.unlock)
                self.root.after(0, self.measurement_stop_button_wrapper.unlock)

    # Setup Start ボタン押下時の処理
    async def _process_setup_start_async(self) -> bool:
        for item in self.setup_items:
            # 成功済み項目はスキップ
            if item.succeeded():
                continue
            if not await item.process_async():
                return False
        return True

    # Setup Stop ボタン押下時の処理
    async def _process_setup_stop_async(self) -> bool:
        self.setup_stop_requested = True

        # MCBJ/ASZ 処理を停止する。停止している場合 戻値が false となるため、チェックしない。
        await client.command_mcbj_stop_async();
        return True

    # Setup Reset ボタン押下時の処理
    async def _process_setup_reset_async(self) -> bool:
        # Measurement Start/Stop ボタンはグレーアウト
        self.root.after(0, self.measurement_start_button_wrapper.reset)
        self.root.after(0, self.measurement_stop_button_wrapper.reset)

        # Setting Load ボタン、Setup Start ボタンは実行中グレーアウトし、完了したら通常表示に戻す。
        self.root.after(0, self.file_select_button_wrapper.reset)
        self.root.after(0, self.setup_start_button_wrapper.reset)

        # Setup Item ボタン: check_label - すべて reset(), button - item_index = 0 だけ enable()、他は reset()
        self.root.after(0, self._on_setup_item_start, 0)

        # MCBJ/ASZ 処理を停止する。停止している場合 戻値が false となるため、チェックしない。
        await client.command_mcbj_stop_async();
        result = await self._process_finalize_core_async()

        # Setup Reset 処理を終えたら Setting Load ボタン、Setup Start ボタンのグレーアウトを解除する。
        self.root.after(0, self.file_select_button_wrapper.enable)
        self.root.after(0, self.setup_start_button_wrapper.enable)
        return result

    # Setup 項目各ボタン押下時の処理
    async def _process_setup_item_async(self, item_index: int, func_async: Callable[[], Coroutine[Any, Any, bool]]) -> bool:
        # Measurement Start/Stop ボタンは一度 setup item を通ったらグレーアウト
        self.root.after(0, self.measurement_start_button_wrapper.reset)
        self.root.after(0, self.measurement_stop_button_wrapper.reset)

        # Setup Stop ボタンは実行中通常表示し、完了したらグレーアウトに戻す。
        self.setup_stop_requested = False
        self.root.after(0, self.setup_stop_button_wrapper.enable)

        # Setup Start は実行中グレーアウトし、完了したら通常表示に戻す。
        self.root.after(0, self.setup_start_button_wrapper.reset)

        # Setting Load ボタン、Setup Reset ボタンは実行中グレーアウトし、完了したら実行前の状態に戻す。
        self.root.after(0, self.setup_reset_button_wrapper.lock)
        self.root.after(0, self.file_select_button_wrapper.lock)

        # Setup Item ボタンは lock()/unlock() を用いて、実行中グレーアウトし、完了したら実行前の状態に戻す。
        self.root.after(0, self._lock_setup_items)
        try:
            self.root.after(0, self._on_setup_item_start, item_index)
            if (not await func_async()):
                return False
            if self.setup_stop_requested == True:
                return False
            self.root.after(0, self._on_setup_item_success, item_index)
            return True
        finally:
            self.root.after(0, self._unlock_setup_items)
            self.root.after(0, self.file_select_button_wrapper.unlock)
            self.root.after(0, self.setup_reset_button_wrapper.unlock)
            if item_index + 1 < len(self.setup_items) or not self.setup_items[item_index].succeeded():
                self.root.after(0, self.setup_start_button_wrapper.enable)
            self.root.after(0, self.setup_stop_button_wrapper.reset)

    # Measurement Start ボタン押下時の処理
    async def _process_measurement_start_async(self) -> bool:
        self.root.after(0, self.file_select_button_wrapper.lock)
        self.root.after(0, self.setup_reset_button_wrapper.lock)
        self.root.after(0, self._lock_setup_items)
        self.root.after(0, self.measurement_start_button_wrapper.reset)
        self.root.after(0, self.measurement_stop_button_wrapper.enable)

        result = await self._process_hold_gap_async()

        self.root.after(0, self.measurement_stop_button_wrapper.reset)
        self.root.after(0, self.measurement_start_button_wrapper.enable)
        self.root.after(0, self._unlock_setup_items)
        self.root.after(0, self.setup_reset_button_wrapper.unlock)
        self.root.after(0, self.file_select_button_wrapper.unlock)
        return result;

    # Measurement Stop ボタン押下時の処理
    async def _process_measurement_stop_async(self) -> bool:
        return await self._process_mcbj_stop_async()

    # 以下、client.command_*() 関数に成否のログ出力を追加し、各ステップごとにまとめたラッパー関数群

    async def _process_initialize_core_async(self) -> bool:
        return (
            self._print_result(await client.command_set_bias_async(0), "Setting the bias completed successfully: bias = 0", "Failed to set bias: bias = 0")
            and self._print_result(await client.command_set_ep_async(0), "Setting the ep completed successfully: ep = 0", "Failed to set ep: ep = 0")
            and self._print_result(await client.command_start_sampling_low_10k_async(), "Starting sampling completed successfully: mode = low, rate = 10kHz", "Failed to start sampling: mode = low, rate = 10kHz")
        )

    async def _process_move_to_zero_point_core_async(self) -> bool:
        return self._print_result(await client.command_move_to_zero_point_async(), "Moving to zero point completed successfully.", "Failed to move to zero point.")

    async def _process_attach_chip_core_async(self) -> bool:
        return messagebox.askokcancel("Setup", "Please attach a chip to the measuring instrument. Once attached, press OK to close.")

    async def _process_apply_bias_core_async(self) -> bool:
        return self._print_result(await client.command_set_bias_async(1), "Setting the bias completed successfully: bias = 1", "Failed to set bias: bias = 1")

    async def _process_first_cut_core_async(self) -> bool:
        return self._print_result(await client.command_mcbj_first_cut_async(), "First cut completed successfully.", "First cut failed.")

    async def _process_motor_training_core_async(self) -> bool:
        return (
            self._print_result(await client.command_mcbj_targeting_async(), "Targeting completed successfully.", "Targeting failed.")
            and self._print_result(await client.command_mcbj_motor_training_async(), "Moter training completed successfully.", "Moter training failed.")
        )

    async def _process_piezo_training_core_async(self) -> bool:
        return (
            self._print_result(await client.command_mcbj_targeting_async(), "Targeting completed successfully.", "Targeting failed.")
            and self._print_result(await client.command_mcbj_piezo_training_async(), "Piezo training completed successfully.", "Piezo training failed.")
        )

    async def _process_auto_cut_core_async(self) -> bool:
        return (
            self._print_result(await client.command_mcbj_targeting_async(), "Targeting completed successfully.", "Targeting failed.")
            and self._print_result(await client.command_mcbj_auto_cut_async(), "Auto cut completed successfully.", "Auto cut failed.")
        )

    async def _process_change_mode_core_async(self) -> bool:
        return (
            self._print_result(await client.command_set_bias_async(0), "Setting the bias completed successfully: bias = 0", "Failed to set bias: bias = 0")
            and self._print_result(await client.command_stop_sampling_async(), "Stopping sampling completed successfully.", "Failed to stop sampling.")
            and await self._command_start_sampling_high_async(self.high_mode_sample_rate_khz)
            and self._print_result(await client.command_set_bias_async(1), "Setting the bias completed successfully: bias = 1", "Failed to set bias: bias = 1")
        )

    async def _process_calibration_core_async(self) -> bool:
        return self._print_result(await client.command_mcbj_calibration_async(), "Calibration completed successfully.", "Calibration failed.")

    async def _process_expand_gap_core_async(self) -> bool:
        return self._print_result(await client.command_asz_expand_gap_async(), "Expanding gap completed successfully.", "Failed to expand gap.")

    async def _process_hold_gap_async(self) -> bool:
        return self._print_result(await client.command_asz_hold_gap_async(), "Holding gap completed successfully.", "Failed to hold gap.")

    async def _process_mcbj_stop_async(self) -> bool:
        return self._print_result(await client.command_mcbj_stop_async(), "Stopping the MCBJ/AGZ process completed successfully.", "Failed to stop MCBJ/AGZ process.")

    async def _process_finalize_core_async(self) -> bool:
        return (
            self._print_result(await client.command_set_bias_async(0), "Setting the bias completed successfully: bias = 0", "Failed to set bias: bias = 0")
            and self._print_result(await client.command_stop_sampling_async(), "Stopping sampling completed successfully.", "Failed to stop sampling.")
            and self._print_result(await client.command_start_sampling_low_10k_async(), "Starting sampling completed successfully: mode = low, rate = 10kHz", "Failed to start sampling: mode = low, rate = 10kHz")
            and self._print_result(await client.command_stop_sampling_async(), "Stopping sampling completed successfully.", "Failed to stop sampling.")
        )

    async def _command_start_sampling_high_async(self, sample_rate_khz: int) -> bool:
        match sample_rate_khz:
            case 100:
                result = await client.command_start_sampling_high_100k_async()
            case 50:
                result = await client.command_start_sampling_high_50k_async()
            case _:
                result = await client.command_start_sampling_high_10k_async()
                sample_rate_khz = 10

        return self._print_result(result, f"Starting sampling completed successfully: mode = high, rate = {sample_rate_khz}kHz", f"Failed to start sampling: mode = high, rate = {sample_rate_khz}kHz")

    # 以下、ログ出力用ヘルパー関数群

    def _print_result(self, result: bool, success_message: str, error_message: str) -> bool:
        if result:
            self.root.after(0, self._append_record, "INFO", success_message)
            return True;
        else:
            self.root.after(0, self._append_record, "ERROR", error_message)
            return False;

    def _append_record(self, level: str, message: str):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-2]
        self.record_display.config(state=tk.NORMAL)
        self.record_display.insert(tk.END, f"[{timestamp}][{level:<5}] {message}\n")
        self.record_display.config(state=tk.DISABLED)
        self.record_display.yview(tk.END)
        self.root.update_idletasks()  # イベントループを更新

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
#  Setup 項目の操作・状態を管理する。
# ====================================================
class SetupItem:

    # イニシャライザ
    def __init__(self, app: WizardApp, master: tk.Misc | None, row: int, item_text: str, process_core_async: Callable[[], Coroutine[Any, Any, bool]]):
        self.row: int = row
        self.process_core_async: Callable[[], Coroutine[Any, Any, bool]] = process_core_async

        # 処理の完了済みを表現するチェックマーク
        self.check_label = tk.Label(master, foreground="#32CD32", text="\uE73E", font=app.mdl2_font_bold, state=tk.DISABLED)
        self.check_label.grid(row=row, column=0, padx=1, pady=0)

        # 処理名称
        item_label = tk.Label(master, text=item_text)
        item_label.grid(row=row, column=1, padx=1, pady=0, sticky='w')

        # 処理の再実行を受け付けるボタン
        button = tk.Button(master, text="\uE7A6", font=app.mdl2_font_normal, state=tk.DISABLED, command=lambda: asyncio.run_coroutine_threadsafe(self.process_async(), async_loop))
        button.grid(row=row, column=2, padx=1, pady=0)
        self.buttonWrapper: WidgetWrapper = WidgetWrapper(button)

    # 処理中に状況に応じて reset()/mark_success()/enable()/lock()/unlock() を呼び、状態変化を加えるラッパー
    async def process_async(self) -> bool:
        return await app._process_setup_item_async(self.row, self.process_core_async)

    # チェックマークのグレーアウトを解除する。
    def mark_success(self):
        self.check_label.config(state=tk.NORMAL)

    def succeeded(self) -> bool:
        return self.check_label.cget('state') == tk.NORMAL

    # ボタンを操作可能とする。
    def enable(self):
        self.buttonWrapper.enable()

    # チェックマーク、ボタン共にグレーアウトする。
    def reset(self):
        self.check_label.config(state=tk.DISABLED)
        self.buttonWrapper.reset()

    # ボタンを一時的に操作不可とする。lock 中の場合、スキップする。
    def lock(self):
        self.buttonWrapper.lock()

    # ボタンの状態を復帰する。lock 中でない場合、スキップする。
    def unlock(self):
        self.buttonWrapper.unlock()

# ====================================================
#  一時的なグレーアウト操作を提供する。
# ====================================================
class WidgetWrapper:

    # イニシャライザ
    def __init__(self, widget: tk.Widget):
        self.widget: tk.Widget = widget
        self.state_on_locked: str | None = None

    # 操作可能とする。
    def enable(self):
        if self.state_on_locked == None:
            self.widget.config(state=tk.NORMAL)
        else:
            self.state_on_locked = tk.NORMAL  # lock 中の場合、復帰先を通常表示に上書きする。

    # グレーアウトする。
    def reset(self):
        if self.state_on_locked == None:
            self.widget.config(state=tk.DISABLED)
        else:
            self.state_on_locked = tk.DISABLED  # lock 中の場合、復帰先をグレーアウトに上書きする。

    # 一時的に操作不可とする。lock 中の場合、スキップする。
    def lock(self):
        if self.state_on_locked == None:
            self.state_on_locked = self.widget.cget('state')
            self.widget.config(state=tk.DISABLED)

    # 状態を復帰する。lock 中でない場合、スキップする。
    def unlock(self):
        if self.state_on_locked != None:
            self.widget.config(state=self.state_on_locked)
            self.state_on_locked = None

# ====================================================
#  メイン
# ====================================================
def main():
    global async_loop, running, client, app

    root = tk.Tk()
    app = WizardApp(root)

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
