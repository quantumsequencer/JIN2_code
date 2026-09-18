"""Launch the supplied Gateway using its own saved settings."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess


DEFAULT_EXE = Path(__file__).resolve().parent.parent / 'SGMO2_original/JinGateway-0.2.0.09030/JinGateway.exe'


def running_executable(executable):
    if os.name != 'nt':
        return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                               wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    ids = (wintypes.DWORD * 8192)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ids, ctypes.sizeof(ids), ctypes.byref(needed)):
        raise OSError('起動中のGatewayを確認できませんでした。')
    expected = os.path.normcase(str(Path(executable).resolve()))
    for pid in ids[:needed.value // ctypes.sizeof(wintypes.DWORD)]:
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            continue
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                if os.path.normcase(buffer.value) == expected:
                    return True
        finally:
            kernel.CloseHandle(handle)
    return False


def launch_gateway(executable=DEFAULT_EXE):
    executable = Path(executable).resolve()
    if not executable.is_file():
        raise FileNotFoundError(f'Gatewayが見つかりません：{executable}')
    config_path = executable.parent / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
    ports = tuple(config.get(key, default) for key, default in [('PubPort', 55555), ('PullPort', 55556)])
    if any(type(port) is not int or not 1024 <= port <= 65535 for port in ports) or ports[0] == ports[1]:
        raise ValueError('Gatewayの通信ポート設定が不正です。config.jsonを確認してください。')
    for key in ('PubHost', 'PullHost'):
        if config.get(key, '127.0.0.1') not in ('127.0.0.1', 'localhost', '*', '0.0.0.0'):
            raise ValueError('このUIはローカルPCのGateway接続に対応しています。')
    settings_path = executable.parent / config.get('SettingsFileName', 'settings.json')
    values = json.loads(settings_path.read_text(encoding='utf-8-sig')).get('Values', {}) if settings_path.exists() else {}
    saved = ' / '.join(f'{label}: {values.get(key, "未設定")}' for label, key in
                       [('Host', 'HostPortUnit'), ('Debug', 'DebugPortUnit'), ('Log', 'LogPortUnit')])
    reused = running_executable(executable)
    if not reused:
        # This is the interactive Gateway window explicitly requested by the launch button.
        subprocess.Popen([str(executable)], cwd=str(executable.parent),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ports, saved, reused
