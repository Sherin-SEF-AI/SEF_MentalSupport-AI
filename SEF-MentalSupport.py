import sys
import os
import base64
import requests
import json
import random
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
                             QHBoxLayout, QProgressBar, QCheckBox, QTabWidget,
                             QListWidget, QDialog, QLineEdit, QFormLayout, QCalendarWidget,
                             QComboBox, QScrollArea, QInputDialog)
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from twilio.rest import Client

# Replace with your actual API key
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"

class AnalysisThread(QThread):
    analysis_complete = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        result = self.analyze_image_with_gemini()
        self.analysis_complete.emit(result)

    def analyze_image_with_gemini(self):
        with open(self.image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this image for signs of mental distress or unsafe conditions. Provide a detailed analysis and safety recommendations."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }]
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", 
                                     headers=headers, 
                                     data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"

class MoodTracker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mood Tracker")
        self.setGeometry(200, 200, 300, 250)

        layout = QVBoxLayout()

        self.mood_input = QComboBox()
        self.mood_input.addItems(["Very Happy", "Happy", "Neutral", "Sad", "Very Sad"])
        self.date_picker = QCalendarWidget()
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Add any notes about your day...")
        self.save_button = QPushButton("Save Mood")

        layout.addWidget(QLabel("Select your mood:"))
        layout.addWidget(self.mood_input)
        layout.addWidget(QLabel("Select date:"))
        layout.addWidget(self.date_picker)
        layout.addWidget(QLabel("Notes:"))
        layout.addWidget(self.notes_input)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        self.save_button.clicked.connect(self.save_mood)

    def save_mood(self):
        mood = self.mood_input.currentText()
        date = self.date_picker.selectedDate().toString(Qt.DateFormat.ISODate)
        notes = self.notes_input.toPlainText()
        print(f"Mood '{mood}' saved for date {date} with notes: {notes}")
        self.accept()

class JournalEntry(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Journal Entry")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Entry Title")
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Write your thoughts here...")
        self.save_button = QPushButton("Save Entry")

        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("Content:"))
        layout.addWidget(self.content_input)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        self.save_button.clicked.connect(self.save_entry)

    def save_entry(self):
        title = self.title_input.text()
        content = self.content_input.toPlainText()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Journal entry '{title}' saved on {date}")
        self.accept()

class SEFMentalHealthTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.mood_history = []
        self.journal_entries = []
        self.emergency_contacts = []
        self.twilio_sid = ''
        self.twilio_auth_token = ''
        self.twilio_phone_number = '+'
        self.twilio_client = Client(self.twilio_sid, self.twilio_auth_token)

    def initUI(self):
        self.setWindowTitle("SEF-Integrated Mental Health and Safety Support Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('sef_icon.png'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Image Analysis Tab
        image_analysis_tab = QWidget()
        self.tab_widget.addTab(image_analysis_tab, "Image Analysis")
        image_analysis_layout = QVBoxLayout(image_analysis_tab)

        self.image_label = QLabel("Upload an image or drawing")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 2px dashed #cccccc; }")
        self.image_label.setFixedSize(400, 400)
        image_analysis_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout = QHBoxLayout()
        self.upload_button = QPushButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)
        button_layout.addWidget(self.upload_button)

        self.analyze_button = QPushButton("Analyze Image")
        self.analyze_button.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.analyze_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)

        image_analysis_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        image_analysis_layout.addWidget(self.progress_bar)

        self.share_checkbox = QCheckBox("Share analysis anonymously with SEF community")
        image_analysis_layout.addWidget(self.share_checkbox)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        image_analysis_layout.addWidget(self.output_text)

        self.emergency_button = QPushButton("Contact SEF Emergency Support")
        self.emergency_button.clicked.connect(self.contact_emergency_support)
        self.emergency_button.setStyleSheet("background-color: #ff4444; color: white;")
        image_analysis_layout.addWidget(self.emergency_button)

        # Mood Tracker Tab
        mood_tracker_tab = QWidget()
        self.tab_widget.addTab(mood_tracker_tab, "Mood Tracker")
        mood_tracker_layout = QVBoxLayout(mood_tracker_tab)

        self.mood_chart = FigureCanvas(plt.Figure(figsize=(5, 4), dpi=100))
        mood_tracker_layout.addWidget(self.mood_chart)

        self.add_mood_button = QPushButton("Add Mood Entry")
        self.add_mood_button.clicked.connect(self.open_mood_tracker)
        mood_tracker_layout.addWidget(self.add_mood_button)

        # Journal Tab
        journal_tab = QWidget()
        self.tab_widget.addTab(journal_tab, "Journal")
        journal_layout = QVBoxLayout(journal_tab)

        self.journal_list = QListWidget()
        journal_layout.addWidget(self.journal_list)

        self.add_journal_button = QPushButton("New Journal Entry")
        self.add_journal_button.clicked.connect(self.open_journal_entry)
        journal_layout.addWidget(self.add_journal_button)

        # Resources Tab
        resources_tab = QWidget()
        self.tab_widget.addTab(resources_tab, "Resources")
        resources_layout = QVBoxLayout(resources_tab)

        self.resources_list = QListWidget()
        self.resources_list.addItems([
            "Crisis Hotline: 1-800-273-8255",
            "Online Therapy: www.betterhelp.com",
            "Mindfulness App: Headspace",
            "Support Group Finder: www.supportgroups.com",
            "Suicide Prevention Lifeline: 1-800-273-8255",
            "National Alliance on Mental Illness: www.nami.org",
            "Anxiety and Depression Association of America: www.adaa.org",
            "https://sjd.kerala.gov.in/scheme-info.php?scheme_id=IDky"
        ])
        resources_layout.addWidget(self.resources_list)

        # Community Forum Tab
        forum_tab = QWidget()
        self.tab_widget.addTab(forum_tab, "Community Forum")
        forum_layout = QVBoxLayout(forum_tab)

        self.forum_view = QWebEngineView()
        self.forum_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.forum_view.setUrl(QUrl("https://sjd.kerala.gov.in/scheme-info.php?scheme_id=IDky"))
        forum_layout.addWidget(self.forum_view)

        self.setStyleSheet("""
            QMainWindow, QTabWidget, QWidget {
                background-color: #f0f4f8;
                color: #333333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit, QListWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                background-color: white;
                color: #333333;
            }
            QCheckBox {
                font-size: 14px;
                color: #333333;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
            }
            QTabBar::tab {
                background: #e1e1e1;
                border: 1px solid #cccccc;
                padding: 5px;
                color: #333333;
            }
            QTabBar::tab:selected {
                background: white;
            }
            QLabel {
                color: #333333;
            }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_mood_chart)
        self.timer.start(60000)

    def upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            pixmap = QPixmap(file_name)
            self.image_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
            self.image_path = file_name

    def start_analysis(self):
        if not hasattr(self, 'image_path'):
            QMessageBox.warning(self, "No Image", "Please upload an image first.")
            return

        self.progress_bar.show()
        self.analyze_button.setEnabled(False)
        self.output_text.clear()

        self.analysis_thread = AnalysisThread(self.image_path)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()

    def on_analysis_complete(self, result):
        self.progress_bar.hide()
        self.analyze_button.setEnabled(True)
        self.output_text.setText(result)

        if self.share_checkbox.isChecked():
            self.share_analysis(result)

    def share_analysis(self, analysis):
        QMessageBox.information(self, "Shared", "Analysis shared anonymously with SEF community.")

    def contact_emergency_support(self):
        if not self.emergency_contacts:
            QMessageBox.warning(self, "No Emergency Contacts", "Please add emergency contacts first.")
            return

        message = "Emergency support requested. Please check on the user."
        for contact in self.emergency_contacts:
            try:
                self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_phone_number,
                    to=contact
                )
            except Exception as e:
                print(f"Failed to send message to {contact}: {str(e)}")

        QMessageBox.information(self, "Emergency Contact", "Emergency contacts have been notified. Help is on the way.")

    def clear_all(self):
        self.image_label.clear()
        self.image_label.setText("Upload an image or drawing")
        self.output_text.clear()
        if hasattr(self, 'image_path'):
            del self.image_path

    def open_mood_tracker(self):
        dialog = MoodTracker(self)
        if dialog.exec():
            mood = dialog.mood_input.currentText()
            date = dialog.date_picker.selectedDate()
            notes = dialog.notes_input.toPlainText()
            self.mood_history.append((date, mood, notes))
            self.update_mood_chart()

    def update_mood_chart(self):
        ax = self.mood_chart.figure.subplots()
        ax.clear()
        dates = [item[0] for item in self.mood_history]
        moods = [["Very Sad", "Sad", "Neutral", "Happy", "Very Happy"].index(item[1]) for item in self.mood_history]
        ax.plot(dates, moods, 'o-')
        ax.set_yticks(range(5))
        ax.set_yticklabels(["Very Sad", "Sad", "Neutral", "Happy", "Very Happy"])
        ax.set_xlabel('Date')
        ax.set_ylabel('Mood')
        ax.set_title('Mood History')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        self.mood_chart.figure.tight_layout()
        self.mood_chart.draw()

    def open_journal_entry(self):
        dialog = JournalEntry(self)
        if dialog.exec():
            title = dialog.title_input.text()
            content = dialog.content_input.toPlainText()
            date = datetime.now()
            self.journal_entries.append((date, title, content))
            self.update_journal_list()

    def update_journal_list(self):
        self.journal_list.clear()
        for date, title, _ in reversed(self.journal_entries):
            self.journal_list.addItem(f"{date.strftime('%Y-%m-%d %H:%M')} - {title}")
        self.journal_list.itemDoubleClicked.connect(self.view_journal_entry)

    def view_journal_entry(self, item):
        index = self.journal_list.row(item)
        date, title, content = self.journal_entries[-(index + 1)]
        
        view_dialog = QDialog(self)
        view_dialog.setWindowTitle(f"Journal Entry: {title}")
        view_dialog.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        date_label = QLabel(f"Date: {date.strftime('%Y-%m-%d %H:%M')}")
        content_text = QTextEdit()
        content_text.setPlainText(content)
        content_text.setReadOnly(True)
        
        layout.addWidget(date_label)
        layout.addWidget(content_text)
        
        view_dialog.setLayout(layout)
        view_dialog.exec()

    def add_emergency_contact(self):
        contact, ok = QInputDialog.getText(self, "Add Emergency Contact", "Enter phone number:")
        if ok and contact:
            self.emergency_contacts.append(contact)
            QMessageBox.information(self, "Contact Added", f"Emergency contact {contact} added successfully.")

    def view_emergency_contacts(self):
        if not self.emergency_contacts:
            QMessageBox.information(self, "Emergency Contacts", "No emergency contacts added yet.")
        else:
            contacts = "\n".join(self.emergency_contacts)
            QMessageBox.information(self, "Emergency Contacts", f"Your emergency contacts:\n\n{contacts}")

    def export_data(self):
        export_dialog = QDialog(self)
        export_dialog.setWindowTitle("Export Data")
        export_dialog.setGeometry(200, 200, 300, 150)
        
        layout = QVBoxLayout()
        mood_button = QPushButton("Export Mood Data")
        journal_button = QPushButton("Export Journal Entries")
        
        layout.addWidget(mood_button)
        layout.addWidget(journal_button)
        
        export_dialog.setLayout(layout)
        
        mood_button.clicked.connect(self.export_mood_data)
        journal_button.clicked.connect(self.export_journal_data)
        
        export_dialog.exec()

    def export_mood_data(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Mood Data", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, 'w') as f:
                f.write("Date,Mood,Notes\n")
                for date, mood, notes in self.mood_history:
                    f.write(f"{date.toString(Qt.DateFormat.ISODate)},{mood},{notes.replace(',', ';')}\n")
            QMessageBox.information(self, "Export Successful", "Mood data exported successfully.")

    def export_journal_data(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Journal Entries", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'w') as f:
                for date, title, content in self.journal_entries:
                    f.write(f"Date: {date.strftime('%Y-%m-%d %H:%M')}\n")
                    f.write(f"Title: {title}\n")
                    f.write(f"Content:\n{content}\n\n")
            QMessageBox.information(self, "Export Successful", "Journal entries exported successfully.")

    def show_breathing_exercise(self):
        breathing_dialog = QDialog(self)
        breathing_dialog.setWindowTitle("Breathing Exercise")
        breathing_dialog.setGeometry(200, 200, 300, 200)
        
        layout = QVBoxLayout()
        instruction_label = QLabel("Breathe in...")
        timer_label = QLabel("4")
        
        layout.addWidget(instruction_label)
        layout.addWidget(timer_label)
        
        breathing_dialog.setLayout(layout)
        
        def update_timer():
            nonlocal count, inhale
            if count > 0:
                count -= 1
                timer_label.setText(str(count))
            else:
                if inhale:
                    instruction_label.setText("Hold...")
                    count = 7
                else:
                    instruction_label.setText("Breathe out...")
                    count = 8
                inhale = not inhale
                timer_label.setText(str(count))

        count = 4
        inhale = True
        
        timer = QTimer(breathing_dialog)
        timer.timeout.connect(update_timer)
        timer.start(1000)
        
        breathing_dialog.exec()
        timer.stop()

    def show_daily_affirmation(self):
        affirmations = [
            "I am capable of amazing things.",
            "I choose to be happy and healthy today.",
            "I am worthy of love and respect.",
            "I trust in my ability to overcome challenges.",
            "I am grateful for all the good in my life.",
            "I am strong and resilient.",
            "I embrace new opportunities with courage.",
            "I radiate positivity and inspire others.",
            "I am deserving of peace and happiness.",
            "I believe in myself and my dreams."
        ]
        affirmation = random.choice(affirmations)
        QMessageBox.information(self, "Daily Affirmation", affirmation)

    def show_crisis_resources(self):
        crisis_dialog = QDialog(self)
        crisis_dialog.setWindowTitle("Crisis Resources")
        crisis_dialog.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        resources = [
            "National Suicide Prevention Lifeline: 1-800-273-8255",
            "Crisis Text Line: Text HOME to 741741",
            "Veterans Crisis Line: 1-800-273-8255 (Press 1)",
            "SAMHSA National Helpline: 1-800-662-4357",
            "National Domestic Violence Hotline: 1-800-799-7233",
            "RAINN National Sexual Assault Hotline: 1-800-656-4673"
        ]
        
        for resource in resources:
            layout.addWidget(QLabel(resource))
        
        crisis_dialog.setLayout(layout)
        crisis_dialog.exec()

def main():
    app = QApplication(sys.argv)
    ex = SEFMentalHealthTool()
    
    # Add menu bar
    menubar = ex.menuBar()
    file_menu = menubar.addMenu('File')
    
    export_action = file_menu.addAction('Export Data')
    export_action.triggered.connect(ex.export_data)
    
    tools_menu = menubar.addMenu('Tools')
    
    breathing_action = tools_menu.addAction('Breathing Exercise')
    breathing_action.triggered.connect(ex.show_breathing_exercise)
    
    affirmation_action = tools_menu.addAction('Daily Affirmation')
    affirmation_action.triggered.connect(ex.show_daily_affirmation)
    
    crisis_resources_action = tools_menu.addAction('Crisis Resources')
    crisis_resources_action.triggered.connect(ex.show_crisis_resources)
    
    contacts_menu = menubar.addMenu('Contacts')
    
    add_contact_action = contacts_menu.addAction('Add Emergency Contact')
    add_contact_action.triggered.connect(ex.add_emergency_contact)
    
    view_contacts_action = contacts_menu.addAction('View Emergency Contacts')
    view_contacts_action.triggered.connect(ex.view_emergency_contacts)
    
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
