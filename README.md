# Sublichecker

**Sublichecker** is a powerful, multi-language GUI tool for discovering and analyzing subdomains. It uses `subfinder` to enumerate subdomains, checks HTTP status codes, tracks progress, handles redirects, and organizes results in a modern, futuristic interface.

---

## Features

- Multi-language support: DE, EN, FR, ES, IT, NL, PT  
- Each domain gets its own tab with live progress and results  
- Status Codes tab showing all non-200 responses, sorted by code  
- Handles HTTP redirects and shows final URLs  
- Export results to CSV  
- Log tab for chronological activity tracking  
- Futuristic and responsive GUI design with progress bars  

---

## Installation

1. Install **Python 3.10+**  
2. Install dependencies:

```bash
pip install PySide6 requests
```
3. Make sure subfinder is installed and available in your PATH.
   See subfinder GitHub for instructions.

4. Usage
Run the application:
```bash
python sublichecker.py
```


Enter domains (one per line).

Select your preferred language.

Click Start to scan.

View results per domain tab or in the Status Codes tab.

Export results to CSV if needed.
