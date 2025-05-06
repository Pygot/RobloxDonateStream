"""
╔════════════════════════════════════════════════════════════╗
║  Author  : pygot                                           ║
║  GitHub  : https://github.com/pygot                        ║
╚════════════════════════════════════════════════════════════╝
"""

from datetime import datetime

import traceback


def log_it(message, message_type=1) -> None:
    """
    Logs a message to the console with a specific message type, adding timestamps and
    additional context depending on the type. Supports three types: INFO (1), ERROR (2),
    and a generic fallback for all others.

    :param message: The message content to be logged. If the message_type is ERROR (2),
        the `message` is expected to be an instance of an exception containing traceback
        information. Otherwise, it can be any string describing the log content.
    :type message: Union[Exception, str]
    :param message_type: The type of the message being logged. Defaults to 1 (INFO).
        Accepted values:
        - 1: INFO
        - 2: ERROR
        - Any other value: logged as an unspecified type.
    :type message_type: int, optional
    :return: None
    """
    time_now = datetime.now()

    match message_type:
        case 1: print(f"[{time_now}] - [INFO] : {message}")
        case 2:

            tb = message.__traceback__
            message = traceback.extract_tb(tb)
            print(f"[{time_now}] - [ERROR] 🔴 : {message[-1].lineno} | {message}")

        case _: print(f"[{time_now}] - [WHAT?!] 🔴: {message}")