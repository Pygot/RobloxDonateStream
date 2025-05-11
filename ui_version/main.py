"""
╔════════════════════════════════════════════════════════════╗
║  Author  : pygot                                           ║
║  GitHub  : https://github.com/pygot                        ║
╚════════════════════════════════════════════════════════════╝
"""

from PySide6.QtCore import Signal, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QTextEdit, QVBoxLayout, QLabel, QFormLayout,
    QSpinBox, QLineEdit, QComboBox, QGroupBox,
    QTabWidget, QHBoxLayout, QCheckBox, QScrollArea
)
from datetime import datetime
from random import choice
from json import dumps
from time import time

import traceback
import threading
import requests
import pytchat
import asyncio
import signal
import json
import sys
import os


original_signal = signal.signal
def patched_signal_handler(sig, handler):
    if threading.current_thread() is threading.main_thread():
        return original_signal(sig, handler)
    return signal.SIG_IGN
signal.signal = patched_signal_handler

class LogSignals(QObject):
    log_signal = Signal(str, int)

class Logger(QObject):
    def __init__(self):
        super().__init__()
        self.signals = LogSignals()
    def log_it(self, message, message_type=1):
        time_now = datetime.now()
        match message_type:
            case 1:
                formatted_message = f"[{time_now}] - [INFO] : {message}"
            case 2:
                if isinstance(message, Exception):
                    tb = message.__traceback__
                    tb_info = traceback.extract_tb(tb)
                    formatted_message = f"[{time_now}] - [ERROR] 🔴 : {tb_info[-1].lineno} | {tb_info}"
                else:
                    formatted_message = f"[{time_now}] - [ERROR] 🔴 : {message}"
            case _:
                formatted_message = f"[{time_now}] - [WHAT?!] 🔴: {message}"
        self.signals.log_signal.emit(formatted_message, message_type)

class GiveawayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = Logger()

        self.setWindowTitle("Pls Donate Stream 1.0-UI @Pygot")
        self.setMinimumSize(800, 600)

        self.config = {
            'price_max': 5,
            'video_id': 'dQw4w9WgXcQ',
            'giveaway_threshold': 120,
            'max_wins_per_user': 10,
            'command_prefix': 'join',
            'cookie': ""
        }

        self.config_file = "config.json"

        self.load_configuration()
        self.setup_ui()
        self.logger.signals.log_signal.connect(self.update_log)

        self.is_running = False
        self.giveaway_thread = None
        self.chat = None

        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)

    def load_configuration(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    self.logger.log_it(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            self.logger.log_it(f"Error loading configuration: {str(e)}", 2)

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        tabs = QTabWidget()
        config_tab = QWidget()
        logs_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        youtube_group = QGroupBox("YouTube Configuration")
        youtube_form = QFormLayout(youtube_group)
        self.video_id_input = QLineEdit(self.config['video_id'])
        youtube_form.addRow(QLabel("Video ID:"), self.video_id_input)
        self.command_prefix_input = QLineEdit(self.config['command_prefix'])
        youtube_form.addRow(QLabel("Command Prefix:"), self.command_prefix_input)
        giveaway_group = QGroupBox("Giveaway Settings")
        giveaway_form = QFormLayout(giveaway_group)
        self.price_max_input = QSpinBox()
        self.price_max_input.setRange(1, 1000)
        self.price_max_input.setValue(self.config['price_max'])
        giveaway_form.addRow(QLabel("Max Price (Robux):"), self.price_max_input)
        self.giveaway_threshold_input = QSpinBox()
        self.giveaway_threshold_input.setRange(10, 3600)
        self.giveaway_threshold_input.setValue(self.config['giveaway_threshold'])
        giveaway_form.addRow(QLabel("Giveaway Duration (seconds):"), self.giveaway_threshold_input)
        self.max_wins_input = QSpinBox()
        self.max_wins_input.setRange(1, 100)
        self.max_wins_input.setValue(self.config['max_wins_per_user'])
        giveaway_form.addRow(QLabel("Max Wins Per User:"), self.max_wins_input)
        security_group = QGroupBox("Security Configuration")
        security_form = QFormLayout(security_group)
        self.cookie_input = QLineEdit(self.config['cookie'])
        self.cookie_input.setEchoMode(QLineEdit.Password)
        security_form.addRow(QLabel("Roblox Security Cookie:"), self.cookie_input)
        config_layout.addWidget(youtube_group)
        config_layout.addWidget(giveaway_group)
        config_layout.addWidget(security_group)
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Giveaway")
        self.start_button.clicked.connect(self.toggle_giveaway)
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.clicked.connect(self.save_configuration)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.save_config_button)
        config_layout.addLayout(buttons_layout)
        config_layout.addStretch()
        logs_layout = QVBoxLayout(logs_tab)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["All Logs", "Info Only", "Errors Only"])
        self.log_level_combo.currentIndexChanged.connect(self.filter_logs)
        log_controls = QHBoxLayout()
        log_controls.addWidget(QLabel("Filter:"))
        log_controls.addWidget(self.log_level_combo)
        self.clear_logs_button = QPushButton("Clear Logs")
        self.clear_logs_button.clicked.connect(self.clear_logs)
        log_controls.addWidget(self.clear_logs_button)
        log_controls.addStretch()
        self.log_output = QTextEdit()
        self.log_output.setFocusPolicy(Qt.NoFocus)
        self.log_output.setReadOnly(True)
        logs_layout.addLayout(log_controls)
        logs_layout.addWidget(self.log_output)
        tabs.addTab(config_tab, "Configuration")
        tabs.addTab(logs_tab, "Logs")
        main_layout.addWidget(tabs)
        self.setCentralWidget(main_widget)
        self.statusBar().showMessage("Ready")
        self.time_left_layout = QHBoxLayout()
        self.time_left_label = QLabel("")
        font = self.log_output.font()
        font.setPointSize(20)
        self.time_left_label.setFont(font)
        self.time_left_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.time_left_layout.addWidget(self.time_left_label)
        self.time_left_label.setScaledContents(True)
        logs_layout.addLayout(self.time_left_layout)

    def update_countdown(self):
        if self.is_running:
            current_time = time()
            if hasattr(self, 'giveaway_end_time') and self.giveaway_end_time > current_time:
                remaining = self.giveaway_end_time - current_time
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                self.time_left_label.setText(f"Giveaway ends in: {minutes:02d}:{seconds:02d}")
            else:
                self.time_left_label.setText("Waiting for next giveaway...")
        else:
            self.time_left_label.setText("")

    def update_log(self, message, level):
        current_filter = self.log_level_combo.currentIndex()
        should_display = True
        if current_filter == 1 and level == 2:
            should_display = False
        elif current_filter == 2 and level == 1:
            should_display = False
        if should_display:
            self.log_output.append(message)
            scrollbar = self.log_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def filter_logs(self):
        self.log_output.clear()
        type = 1
        if self.log_level_combo.currentIndex() == 2: type = 2
        self.logger.log_it(f"Log filter changed to: {self.log_level_combo.currentText()}", type)

    def clear_logs(self):
        self.log_output.clear()
        self.logger.log_it("Logs cleared")

    def save_configuration(self):
        try:
            self.update_config_from_ui()

            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)

            self.logger.log_it(f"Configuration saved to {self.config_file}")
            self.statusBar().showMessage("Configuration saved", 3000)
        except Exception as e:
            self.logger.log_it(f"Error saving configuration: {str(e)}", 2)
            self.statusBar().showMessage("Error saving configuration", 3000)

    def update_config_from_ui(self):
        self.config['video_id'] = self.video_id_input.text()
        self.config['command_prefix'] = self.command_prefix_input.text()
        self.config['price_max'] = self.price_max_input.value()
        self.config['giveaway_threshold'] = self.giveaway_threshold_input.value()
        self.config['max_wins_per_user'] = self.max_wins_input.value()
        self.config['cookie'] = self.cookie_input.text()

    def toggle_giveaway(self):
        if not self.is_running:
            self.start_giveaway()
        else:
            self.stop_giveaway()

    def start_giveaway(self):
        self.update_config_from_ui()
        if not self.config['video_id']:
            self.logger.log_it("Video ID is required!", 2)
            return
        if not self.config['cookie']:
            self.logger.log_it("Roblox Security Cookie is required!", 2)
            return
        self.is_running = True
        self.start_button.setText("Stop Giveaway")
        self.statusBar().showMessage("Giveaway running")
        self.logger.log_it("Starting giveaway process...")
        self.logger.log_it(f"Configuration: Video ID: {self.config['video_id']}, Command: {self.config['command_prefix']}, "
                          f"Max Price: {self.config['price_max']}, Duration: {self.config['giveaway_threshold']}s")
        self.giveaway_thread = threading.Thread(
            target=self.run_giveaway_thread,
            daemon=True
        )
        self.giveaway_thread.start()

    def run_giveaway_thread(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.main_async())
            loop.close()
        except Exception as e:
            self.logger.log_it(f"Error in giveaway thread: {str(e)}", 2)
            QTimer.singleShot(0, self.on_giveaway_completed)

    def on_giveaway_completed(self):
        self.is_running = False
        self.start_button.setText("Start Giveaway")
        self.statusBar().showMessage("Giveaway completed")

    def stop_giveaway(self):
        self.is_running = False
        self.start_button.setText("Start Giveaway")
        self.statusBar().showMessage("Giveaway stopping...")
        self.logger.log_it("Stopping giveaway process...")

    def get_gamepass(self, username):
        try:
            user_response = requests.post(
                url='https://users.roproxy.com/v1/usernames/users',
                json={'usernames': [username], 'excludeBannedUsers': True}
            )

            if not user_response.text or user_response.status_code != 200:
                self.logger.log_it(f"Invalid response from users API for {username}: {user_response.status_code}", 2)
                return None, None

            user_data = user_response.json()
            if not user_data.get('data') or len(user_data['data']) == 0:
                self.logger.log_it(f"User {username} not found", 2)
                return None, None

            user_id = user_data['data'][0]['id']

            games_response = requests.get(f'https://games.roproxy.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc')

            if not games_response.text or games_response.status_code != 200:
                self.logger.log_it(f"Invalid response from games API for {username}: {games_response.status_code}", 2)
                return None, None

            games_data = games_response.json().get('data', [])
            gamepass = []

            for game in games_data:
                game_id = game.get('id')
                if not game_id:
                    continue

                gamepasses_response = requests.get(f'https://games.roproxy.com/v1/games/{game_id}/game-passes?limit=100&sortOrder=Asc')

                if not gamepasses_response.text or gamepasses_response.status_code != 200:
                    self.logger.log_it(f"Invalid response from game-passes API for game {game_id}: {gamepasses_response.status_code}", 2)
                    continue

                try:
                    gamepass_data = gamepasses_response.json().get('data', [])
                    filtered_passes = [
                        {'name': gp.get('name', 'Unnamed Pass'), 'price': gp.get('price'), 'id': gp.get('id')}
                        for gp in gamepass_data
                        if gp.get('price') is not None and 1 <= gp['price'] <= self.config['price_max']
                    ]
                    gamepass.extend(filtered_passes)
                except json.JSONDecodeError as e:
                    self.logger.log_it(f"Error parsing gamepass data for game {game_id}: {str(e)}", 2)
                    continue

            if gamepass:
                gamepass = max(gamepass, key=lambda x: x['price'])

                product_response = requests.get(
                    f'https://economy.roproxy.com/v1/game-pass/{gamepass["id"]}/game-pass-product-info'
                )

                if not product_response.text or product_response.status_code != 200:
                    self.logger.log_it(f"Invalid response from product-info API: {product_response.status_code}", 2)
                    return None, None

                try:
                    product_data = product_response.json()
                    gamepass['product_id'] = product_data.get('ProductId')
                    if not gamepass['product_id']:
                        self.logger.log_it(f"No product ID found for gamepass {gamepass['id']}", 2)
                        return None, None
                except json.JSONDecodeError as e:
                    self.logger.log_it(f"Error parsing product data for gamepass {gamepass['id']}: {str(e)}", 2)
                    return None, None
            else:
                gamepass = None

            return gamepass, user_id

        except json.JSONDecodeError as e:
            self.logger.log_it(f"JSON parsing error in get_gamepass: {str(e)}", 2)
            return None, None
        except Exception as e:
            self.logger.log_it(f"Error in get_gamepass: {str(e)}", 2)
            return None, None

    def delete_buy(self, gamepass):
        try:
            session = requests.Session()
            session.cookies['.ROBLOSECURITY'] = self.config['cookie']
            gamepass_id = gamepass[0]['id']

            csrf_response = session.post('https://auth.roblox.com/v2/login')
            if 'X-CSRF-Token' not in csrf_response.headers:
                self.logger.log_it("Failed to get CSRF token", 2)
                return

            headers = {
                'Origin': 'https://www.roblox.com',
                'Referer': f'https://www.roblox.com/game-pass/{gamepass_id}/{gamepass[0]["name"].strip()}',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'x-csrf-token': csrf_response.headers['X-CSRF-Token'],
            }

            revoke_response = session.post(
                f'https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}:revokeownership',
                headers=headers
            )

            if revoke_response.status_code != 200:
                self.logger.log_it(f"Failed to revoke ownership: {revoke_response.status_code}", 2)

            headers['Referer'] = 'https://www.roblox.com/'
            headers['Content-Type'] = 'application/json; charset=UTF-8'

            purchase_data = {
                'expectedCurrency': 1,
                'expectedPrice': gamepass[0]['price'],
                'expectedSellerId': gamepass[1]
            }

            purchase_response = session.post(
                url=f'https://apis.roblox.com/game-passes/v1/game-passes/{gamepass[0]["product_id"]}/purchase',
                headers=headers,
                data=dumps(purchase_data)
            )

            if not purchase_response.text:
                self.logger.log_it("Empty response from purchase API", 2)
                return

            try:
                purchase_result = purchase_response.json()
                if not purchase_result.get('purchased'):
                    self.logger.log_it(f"Purchase failed: {purchase_result}", 2)
                else:
                    self.logger.log_it(f"Successfully purchased gamepass for {gamepass[0]['price']} Robux")
            except json.JSONDecodeError as e:
                self.logger.log_it(f"Failed to parse purchase response: {str(e)}", 2)

        except Exception as e:
            self.logger.log_it(f"Error in delete_buy: {str(e)}", 2)

    async def init_pytchat(self):
        try:
            self.chat = await asyncio.to_thread(
                lambda: pytchat.create(video_id=self.config['video_id'])
            )
            self.logger.log_it(f"Successfully connected to YouTube chat for video ID: {self.config['video_id']}")
            return True
        except Exception as e:
            self.logger.log_it(f"Failed to initialize pytchat: {str(e)}", 2)
            return False

    async def main_async(self):
        try:
            if not await self.init_pytchat():
                QTimer.singleShot(0, self.on_giveaway_completed)
                return
            winners = {}
            while self.is_running:
                participants = []
                start_time = time()
                self.logger.log_it('Starting the next giveaway...')
                end_time = start_time + self.config['giveaway_threshold']
                self.giveaway_end_time = end_time
                while self.chat.is_alive() and time() < end_time and self.is_running:
                    try:
                        chat_items = await asyncio.to_thread(lambda: self.chat.get().sync_items())
                        for item in chat_items:
                            message = str(item.message).lower().replace(' ', '')
                            if message.startswith(self.config['command_prefix']):
                                username = message.replace(self.config['command_prefix'], '').capitalize()
                                if username and winners.get(username, 0) < self.config['max_wins_per_user']:
                                    if any(p[2] == username for p in participants):
                                        self.logger.log_it(f'User {username} is already in giveaway!')
                                        continue
                                    try:
                                        gamepass, user_id = await asyncio.to_thread(self.get_gamepass, username)
                                    except Exception as e:
                                        self.logger.log_it(str(e), 2)
                                        continue
                                    if gamepass:
                                        participants.append([gamepass, user_id, username])
                                        self.logger.log_it(f'Successfully joined {username}!')
                                else:
                                    self.logger.log_it(f'User {username} is not eligible.')
                                    continue
                    except Exception as chat_error:
                        self.logger.log_it(f"Error processing chat: {str(chat_error)}", 2)
                    await asyncio.sleep(1)
                if not self.is_running:
                    break
                self.logger.log_it('Selecting winner...')
                await asyncio.sleep(2)
                if participants and self.is_running:
                    winner = choice(participants)
                    self.logger.log_it(f'Winner is... {winner[2]}!')
                    winners[winner[2]] = winners.get(winner[2], 0) + 1
                    await asyncio.sleep(2)
                    self.logger.log_it(f'Buying the {winner[0]["price"]}R$ gamepass...')
                    await asyncio.to_thread(self.delete_buy, [winner[0], winner[1]])
                    await asyncio.sleep(2)
                else:
                    self.logger.log_it('No one entered the giveaway.')
                if self.is_running:
                    await asyncio.sleep(2)
                    self.logger.log_it('Resetting the giveaway...')
                    await asyncio.sleep(2)
            self.logger.log_it('Giveaway process stopped.')
        except Exception as e:
            self.logger.log_it(f"Error in main giveaway process: {str(e)}", 2)
        finally:
            QTimer.singleShot(0, self.on_giveaway_completed)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GiveawayApp()
    window.show()
    sys.exit(app.exec())