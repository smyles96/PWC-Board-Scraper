# PWC-Board-Scraper

## Disclaimer
This project's source makes web requests to a county website not
owned by the repo's owner. I am not responsible for the misuse
of this program and do not condone misuse of the source.

Be considerate when scraping sites.

## Description
Small Python based system used to scrape resolution PDFs from the Printce
William County Board of Supervisors site (https://www.pwcgov.org/government/bocs/Pages/Meeting-Room.aspx)
and extract basic details from them.

The purpose of this project is to tranform the data into a more easily
parsed format (currently JSON) for data science purposes.

## Installing

1) Ensure that Tesseract OCR and Selenium are installed and on system PATH

2) Clone the repo:
    ```git clone https://github.com/smyles96/PWC-Board-Scraper.git```

3) Create a virtual environment (Python 3):
    ```python3 -m venv env```

4) Activate the virtual environment:
    * Windows: ```env\Scripts\activate.bat```
    * Linux: ```source env/bin/activate```

3) Install project requirements:
    ```pip install -r requirements.txt```

4) Start scraping:
    ```python main.py```