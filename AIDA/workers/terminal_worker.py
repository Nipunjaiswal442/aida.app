from PyQt6.QtCore import QThread, pyqtSignal

from terminal_brain import (
    copy_command,
    execute_command,
    is_blacklisted,
    log_command,
    summarize_output,
    translate_to_command,
)


class TerminalCommandWorker(QThread):
    command_ready = pyqtSignal(str, bool)
    blocked = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, request_text: str):
        super().__init__()
        self.request_text = request_text

    def run(self):
        try:
            command = translate_to_command(self.request_text)

            if command.startswith("UNSAFE:"):
                reason = command.replace("UNSAFE:", "").strip()
                log_command(self.request_text, command, output=reason, confirmed=False)
                self.blocked.emit(f"I can't generate that command safely. {reason}")
                return

            if command.startswith("ERROR:"):
                log_command(self.request_text, command, output="", confirmed=False)
                self.error.emit(command)
                return

            if is_blacklisted(command):
                log_command(self.request_text, command, output="Blacklisted command.", confirmed=False)
                self.blocked.emit("That command is on my permanent safety blacklist. I won't run it even if asked.")
                return

            copied = copy_command(command)
            self.command_ready.emit(command, copied)
        except Exception as e:
            self.error.emit(str(e))


class TerminalExecuteWorker(QThread):
    execution_done = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, request_text: str, command: str):
        super().__init__()
        self.request_text = request_text
        self.command = command

    def run(self):
        try:
            output = execute_command(self.command)
            log_command(self.request_text, self.command, output=output, confirmed=True)
            summary = summarize_output(output, self.request_text)
            full_response = f"Command: {self.command}\n\nOutput:\n{output}"
            self.execution_done.emit(full_response, summary)
        except Exception as e:
            self.error.emit(str(e))
