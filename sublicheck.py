import sys
import subprocess
import threading
import requests
import time
import csv
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTabWidget, QComboBox, QLabel, QProgressBar,
    QLineEdit, QCheckBox, QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont

# ---------------- SIGNALBUS ----------------
class SignalBus(QObject):
    log = Signal(str)
    init_domain = Signal(str, int)
    progress = Signal(str, int, int)
    result = Signal(str, str)
    statuscode = Signal(str, int, str, int)  # domain, code, url, size

signals = SignalBus()

# ---------------- HILFSFUNKTIONEN ----------------
def normalize(domain):
    # Entfernt '*.' und Leerzeichen
    return domain.replace("*.", "").strip()

def timestamp():
    return time.strftime("%H:%M:%S")

def run_subfinder(domain):
    # Führt subfinder aus und gibt Subdomains zurück
    try:
        cmd = ["subfinder", "-d", domain, "-silent"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return list(set(output.splitlines()))
    except Exception:
        signals.log.emit(f"[{timestamp()}] ❌ subfinder fehlgeschlagen für {domain}")
        return []

def check_http(sub):
    # Prüft HTTP(S)-Statuscodes, Redirects und Seitengröße
    for scheme in ("https://", "http://"):
        try:
            r = requests.get(scheme + sub, timeout=6, allow_redirects=True)
            final_url = r.url
            size = len(r.content)
            code = r.status_code
            if code == 200:
                return f"{final_url} [200] | {size} Bytes", code, final_url, size
            else:
                return None, code, final_url, size
        except Exception:
            continue
    return None, None, sub, 0

# ---------------- WORKER ----------------
def worker(domain):
    domain = normalize(domain)
    signals.log.emit(f"[{timestamp()}] ▶ Starte subfinder: {domain}")
    subs = run_subfinder(domain)

    total = len(subs)
    signals.init_domain.emit(domain, total)

    found = 0
    checked = 0

    for sub in subs:
        checked += 1
        result, code, final_url, size = check_http(sub)
        if result:
            found += 1
            signals.result.emit(domain, result)
        else:
            if code is not None:
                signals.statuscode.emit(domain, code, final_url, size)
        signals.progress.emit(domain, checked, found)

    signals.log.emit(f"[{timestamp()}] ✅ Fertig mit {domain}")

# ---------------- HAUPTFENSTER ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SUBLICHECKER PROFI")
        self.resize(1300, 800)

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.domain_tabs = {}
        self.stats = {}
        self.status_codes = defaultdict(list)

        self.language = "DE"  # Standard Sprache
        self.translations = {
            "DE": {"control":"KONTROLLE","log":"LOG","status":"STATUSCODES",
                   "input":"Domains eingeben (eine pro Zeile)","start":"STARTEN",
                   "found":"[INFO] Subdomains gefunden: {}",
                   "checked":"Geprüft: {}/{} | 200 OK: {} | Fortschritt: {}%"},
            "EN": {"control":"CONTROL","log":"LOG","status":"STATUS CODES",
                   "input":"Enter domains (one per line)","start":"START",
                   "found":"[INFO] Subdomains found: {}",
                   "checked":"Checked: {}/{} | 200 OK: {} | Progress: {}%"},
            "FR": {"control":"CONTROLE","log":"JOURNAL","status":"CODES HTTP",
                   "input":"Entrez les domaines (un par ligne)","start":"DÉMARRER",
                   "found":"[INFO] Sous-domaines trouvés: {}",
                   "checked":"Vérifié: {}/{} | 200 OK: {} | Progression: {}%"},
            "ES": {"control":"CONTROL","log":"REGISTRO","status":"CÓDIGOS",
                   "input":"Ingrese dominios (uno por línea)","start":"INICIAR",
                   "found":"[INFO] Subdominios encontrados: {}",
                   "checked":"Comprobado: {}/{} | 200 OK: {} | Progreso: {}%"},
            "IT": {"control":"CONTROLLO","log":"LOG","status":"CODICI HTTP",
                   "input":"Inserisci domini (uno per riga)","start":"AVVIA",
                   "found":"[INFO] Sottodomini trovati: {}",
                   "checked":"Controllato: {}/{} | 200 OK: {} | Progresso: {}%"},
            "NL": {"control":"CONTROLE","log":"LOG","status":"STATUSCODES",
                   "input":"Voer domeinen in (één per regel)","start":"START",
                   "found":"[INFO] Subdomeinen gevonden: {}",
                   "checked":"Gecontroleerd: {}/{} | 200 OK: {} | Voortgang: {}%"},
            "PT": {"control":"CONTROLO","log":"LOG","status":"CÓDIGOS",
                   "input":"Insira domínios (um por linha)","start":"INICIAR",
                   "found":"[INFO] Subdomínios encontrados: {}",
                   "checked":"Verificado: {}/{} | 200 OK: {} | Progresso: {}%"}
        }

        self.setup_ui()
        self.apply_style()

        # Signale verbinden
        signals.log.connect(self.write_log)
        signals.init_domain.connect(self.init_domain)
        signals.progress.connect(self.update_progress)
        signals.result.connect(self.write_result)
        signals.statuscode.connect(self.add_statuscode)

    # ---------------- GUI SETUP ----------------
    def setup_ui(self):
        # Steuerungs-Tab
        control = QWidget()
        layout = QVBoxLayout()

        self.lang_selector = QComboBox()
        self.lang_selector.addItems(["DE","EN","FR","ES","IT","NL","PT"])
        self.lang_selector.currentTextChanged.connect(self.change_language)

        self.input = QTextEdit()
        self.input.setPlaceholderText(self.translations[self.language]["input"])
        self.input.setFixedHeight(120)

        self.start_btn = QPushButton(self.translations[self.language]["start"])
        self.start_btn.clicked.connect(self.start_scan)

        # Export Button
        self.export_btn = QPushButton("EXPORT CSV")
        self.export_btn.clicked.connect(self.export_csv)

        layout.addWidget(self.lang_selector)
        layout.addWidget(self.input)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.export_btn)
        control.setLayout(layout)

        self.tabs.addTab(control, self.translations[self.language]["control"])

        # Log Tab
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.tabs.addTab(self.log_box, self.translations[self.language]["log"])

        # Status Codes Tab
        self.status_tab = QTextEdit()
        self.status_tab.setReadOnly(True)
        self.tabs.addTab(self.status_tab, self.translations[self.language]["status"])

    # ---------------- SPRACHE ÄNDERN ----------------
    def change_language(self, lang):
        self.language = lang
        self.input.setPlaceholderText(self.translations[lang]["input"])
        self.start_btn.setText(self.translations[lang]["start"])
        self.tabs.setTabText(0,self.translations[lang]["control"])
        self.tabs.setTabText(1,self.translations[lang]["log"])
        self.tabs.setTabText(2,self.translations[lang]["status"])

    # ---------------- SCAN START ----------------
    def start_scan(self):
        domains = self.input.toPlainText().splitlines()
        for d in domains:
            d = normalize(d)
            if not d or d in self.domain_tabs:
                continue

            # Tab pro Domain
            box = QTextEdit()
            box.setReadOnly(True)

            # Fortschrittsbalken
            progress = QProgressBar()
            progress.setValue(0)

            self.domain_tabs[d] = {"box":box,"progress":progress}
            self.stats[d] = {"total":0,"checked":0,"found":0}

            tab_widget = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.addWidget(progress)
            tab_layout.addWidget(box)
            tab_widget.setLayout(tab_layout)

            self.tabs.addTab(tab_widget, d)
            threading.Thread(target=worker,args=(d,),daemon=True).start()

    # ---------------- DOMAIN INITIALISIERUNG ----------------
    def init_domain(self,domain,total):
        self.stats[domain]["total"] = total
        self.domain_tabs[domain]["box"].append(self.translations[self.language]["found"].format(total))

    # ---------------- FORTSCHRITT UPDATE ----------------
    def update_progress(self,domain,checked,found):
        total = self.stats[domain]["total"]
        self.stats[domain]["checked"] = checked
        self.stats[domain]["found"] = found
        percent = int((checked/total)*100) if total else 100
        self.domain_tabs[domain]["progress"].setValue(percent)
        self.domain_tabs[domain]["box"].append(self.translations[self.language]["checked"].format(checked,total,found,percent))

    # ---------------- RESULTAT ----------------
    def write_result(self,domain,msg):
        self.domain_tabs[domain]["box"].append(f"✔ {msg}")

    # ---------------- STATUSCODE ----------------
    def add_statuscode(self,domain,code,url,size):
        self.status_codes[code].append((domain,url,size))
        self.refresh_status_tab()

    def refresh_status_tab(self):
        self.status_tab.clear()
        for code in sorted(self.status_codes):
            self.status_tab.append(f"--- {code} ---")
            for domain,url,size in self.status_codes[code]:
                self.status_tab.append(f"{domain} | {url} | {size} Bytes")
            self.status_tab.append("")

    # ---------------- LOG ----------------
    def write_log(self,msg):
        self.log_box.append(msg)

    # ---------------- EXPORT CSV ----------------
    def export_csv(self):
        path,_ = QFileDialog.getSaveFileName(self,"Save CSV","subdomains.csv","CSV Files (*.csv)")
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Domain","URL","Status","Size(Bytes)"])
                for code in sorted(self.status_codes):
                    for domain,url,size in self.status_codes[code]:
                        writer.writerow([domain,url,code,size])
            self.write_log(f"[{timestamp()}] ✅ CSV exportiert: {path}")

    # ---------------- STYLING ----------------
    def apply_style(self):
        font = QFont("JetBrains Mono")
        font.setPointSize(11)
        self.setFont(font)
        self.setStyleSheet("""
        QWidget {background-color:#0b0f1a;color:#cfd8ff;}
        QTextEdit {background-color:#11162a;border:1px solid #2c3569;}
        QPushButton {background-color:#1b2fff;color:white;padding:12px;border-radius:6px;font-weight:bold;}
        QPushButton:hover {background-color:#3b4fff;}
        QProgressBar {background-color:#222244;color:#cfd8ff;border:1px solid #2c3569;border-radius:5px;text-align:center;}
        QProgressBar::chunk {background-color:#1bffdd;border-radius:5px;}
        QTabBar::tab:selected {background:#1b2fff;}
        """)

# ---------------- RUN ----------------
if __name__=="__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
