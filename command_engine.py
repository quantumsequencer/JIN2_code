"""Single command owner; Debug prompt and worker Log completion are distinct."""
import re
import time
from collections import deque
from protocol import Command, STOP


class CommandEngine:
    SAMPLE_STOP_RETRY_LIMIT = 20
    SAMPLE_STOP_RETRY_DELAY = .5

    def __init__(self, send, result, accepted=lambda command: None, clock=time.monotonic):
        self.send, self.result, self.accepted, self.clock = send, result, accepted, clock
        self.current = None
        self.queue = deque()
        self.faulted = False
        self.stopping = False
        self.stop_requested = False
        self.retry_at = None
        self.sample_stop_retries = 0

    @property
    def busy(self):
        return self.current is not None

    def start(self, commands):
        if self.busy or self.faulted:
            return False
        self.queue = deque(commands)
        self.sample_stop_retries = 0
        self.retry_at = None
        self.stopping = self.stop_requested = False
        self._next()
        return True

    def _next(self):
        if not self.queue:
            self.current = None
            self.result('stopped' if self.stopping else 'success', '')
            return
        self.current = self.queue.popleft()
        self.response = []
        self.ack = False
        self.terminal = None
        self.deadline = self.clock() + 120  # Debug prompt, including zero-point move
        try:
            self.send(self.current.text)
        except Exception as error:
            self.fail(str(error))

    def fail(self, message):
        self.retry_at = None
        self.current = None
        self.queue.clear()
        self.faulted = True
        self.result('uncertain', message)

    def tick(self):
        if self.retry_at is not None:
            if self.clock() >= self.retry_at:
                self.retry_at = None
                self.queue.appendleft(self.current)
                self._next()
            return
        if self.busy and self.deadline is not None and self.clock() > self.deadline:
            self.fail('応答タイムアウト。装置状態は未確認です。Gatewayで状態を確認し、再接続してください。')

    def feed(self, topic, text):
        c = self.current
        if c is None or self.retry_at is not None:
            return
        if topic == 'Log' and c.done:
            if c.canceled and re.search(c.canceled, text):
                self.terminal = False
            elif re.search(c.done, text):
                self.terminal = True
        elif topic == 'Debug' and not self.ack:
            if text.strip() != '>':
                self.response.append(text.strip())
                if len(self.response) > 2000:
                    self.fail('コマンド応答が上限を超えました。')
                return
            self.ack = True
            # Manufacturer FWResultCode: -3 = API_RUNNING, not "already stopped".
            # A prompt without a response has also occurred on real hardware.
            # Retry both cases only after the prompt, without advancing the queue.
            response = [line for line in self.response if line]
            if c.text == 'sv_info_sender stop' and (not response or response == ['Stop error : -3']):
                if self.sample_stop_retries < self.SAMPLE_STOP_RETRY_LIMIT:
                    self.sample_stop_retries += 1
                    self.retry_at = self.clock() + self.SAMPLE_STOP_RETRY_DELAY
                    return
                if not response:
                    self.fail(
                        'sv_info_sender stop の応答が空のまま再試行上限に達しました。'
                        'データ取得の停止状態は未確認です。Gatewayで状態を確認し、再接続してください。'
                    )
                    return
            failed = any(re.search(r'error|failed|invalid|unknown', line, re.I) for line in self.response)
            # mcbj stop reports an error when already idle; the official Wizard ignores it.
            if c.text == STOP.text:
                failed = any(re.search(r'error|failed|invalid|unknown', line, re.I)
                             and not line.startswith('Stop error : ') for line in self.response)
            if c.success is not None:
                failed = failed or c.success not in self.response
            if failed:
                self.queue.clear()
                self.current = None
                self.result('failure', f'{c.text}: ' + ' / '.join(self.response))
                return
            self.deadline = self.clock() + c.timeout if c.timeout else None
            self.accepted(c)
        if not self.ack:
            return
        if self.stop_requested and not self.stopping:
            self._send_stop()
            return
        if not c.done or self.terminal is not None:
            if self.terminal is False and not self.stopping:
                self.queue.clear()
                self.current = None
                self.result('failure', f'{c.text}: 装置側でキャンセルされました。')
            else:
                self._next()

    def stop(self):
        if self.faulted or self.stopping:
            return False
        self.queue.clear()
        self.retry_at = None
        self.stop_requested = True
        if self.current is None or self.ack:
            self._send_stop()
        # Never inject a command while firmware has not returned its Debug prompt.
        return True

    def _send_stop(self):
        c = self.current
        terminal = self.terminal if c else None
        self.stopping = True
        if c and c.done and terminal is None:
            self.queue = deque([Command(STOP.text, done=c.done, canceled=c.canceled, timeout=30)])
        else:
            self.queue = deque([STOP])
        self._next()
