from datetime import datetime
from colorama import Fore, Style

def logger(self, message: str, log_type: str = "info"):
    if self is None:
        print(f"SYSTEM {message}")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    index = self.account_index

    log_type = log_type.lower()
    tag_color = Fore.WHITE
    tag = " LOG   "

    if log_type == "info":
        tag = " INFO  "
        tag_color = Fore.CYAN
    elif log_type == "warn":
        tag = " WARN  "
        tag_color = Fore.YELLOW
    elif log_type == "success":
        tag = "SUCCESS"
        tag_color = Fore.GREEN
    elif log_type == "error":
        tag = " ERROR "
        tag_color = Fore.RED
    elif log_type == "debug":
        tag = " DEBUG "
        tag_color = Fore.MAGENTA
    elif log_type == "failed":
        tag = " FAILED "
        tag_color = Fore.LIGHTRED_EX

    index_colors = [Fore.BLUE, Fore.GREEN, Fore.YELLOW, Fore.MAGENTA, Fore.CYAN]
    index_color = index_colors[index % len(index_colors)]
    index_str = f"{index_color}{str(index).rjust(2)}{Style.RESET_ALL}"
    log_line = f"{Fore.LIGHTBLACK_EX}{now} {Style.RESET_ALL} | {tag_color}{tag}{Style.RESET_ALL} | {index_str} | {message}"
    print(log_line)
