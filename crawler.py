import datetime
import os.path
import random

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

MEETING_URL = "https://www.pwcgov.org/government/bocs/Pages/Meeting-Room.aspx"
BRIEF_URL_TEMPLATE = "https://docs.google.com/gview?url=http://eservice.pwcgov.org/documents/bocs/briefs/{0}/{1}.pdf"

HEADERS = {
    'HTTP_USER_AGENT': "",
    'HTTP_ACCEPT': 'text/html,application/xhtml+xml,application/xml; q=0.9,*/*; q=0.8',
    'Content-Type': 'application/x-www-form-urlencoded'
}

USER_AGENTS = [
   #Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    #Firefox
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
]

def crawl_meeting_links():
    """ Crawl the meeting archive page and extract meeting links """

    # Request archive page
    HEADERS["HTTP_USER_AGENT"] = random.choice(USER_AGENTS)
    archive_request = requests.get(MEETING_URL, headers = HEADERS)

    if archive_request.status_code == 200:
        soup = BeautifulSoup(archive_request.content, 'lxml')

        # Find each table containing data about the meetings for a certain year
        for meeting_table in soup.find_all("table", attrs = {"class": "listingTable", "id": "archive"}):
            for table_row in meeting_table.tbody.find_all("tr"):
                row_data = table_row.find_all("td")

                # Recent meetings will not yet have a briefing document created. Each
                # row must be check to see if a link to a briwfing document is available
                if row_data[4].find("a"):
                    brief_link = row_data[4].a["href"]

                    # The meeting dates have a hidden span tag that needs to be removed
                    for span_tag in row_data[1].findAll('span'):
                        span_tag.replace_with('')

                    # Format the date string from {Mon} {Day}, {Year} to {MonthNum}/{DayNum}/{Yeay}
                    meeting_date = datetime.datetime.strptime(row_data[1].text, '%b %d, %Y').strftime('%Y-%m-%d')

                    yield brief_link, meeting_date

def crawl_resolution_links(brief_link):
    # The brief pdf is displayed in a Google Docs GView container. Since this container
    # generates dynamic HTML, a web driver must be used to get the final rendered HTML
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)

    try:
        driver.get(brief_link)
        # brief_request = requests.get(brief_url, headers = HEADERS)

        #if brief_request.status_code == 200:
        soup = BeautifulSoup(driver.page_source, 'lxml')

        for resolution_pdf_tag in soup.find_all("a", attrs = {"class": "ndfHFb-c4YZDc-cYSp0e-DARUcf-hSRGPd", "href": True}):
            if ".pdf" in resolution_pdf_tag["href"]:
                yield resolution_pdf_tag["href"]
    finally:
        driver.quit()

def download_pdf(pdf_link, download_folder):
    pdf_name = os.path.join(download_folder, "temp.pdf")

    HEADERS["HTTP_USER_AGENT"] = random.choice(USER_AGENTS)
    pdf_req = requests.get(pdf_link, headers = HEADERS)
    
    if pdf_req.status_code == 200:
        with open(pdf_name, "wb") as pdf_file:
            pdf_file.write(pdf_req.content)

        print(f"    [*] PDF downloaded as {pdf_name}")
    else:
        raise IOError(f"Unable to download PDF (error code [{pdf_req.status_code}] received)")

    return pdf_name

if __name__ == "__main__":
    for link in crawl_resolution_links("http://pwcgov.granicus.com/MinutesViewer.php?view_id=23&clip_id=2641"):
        print(link)
    # pdf_path = download_pdf("http://eservice.pwcgov.org/documents/bocs/briefs/2019/1210/res19-587.pdf", "crawledpdfs")

    '''
    num = 0

    options = Options()
    options.private = True
    options.headless = True
    # driver = webdriver.Firefox(options=options)

    with webdriver.Firefox(options=options) as driver:
        for link, date in crawl_meeting_links():
            num += 1
            print(f"[*] {date} -> {link}")

            for res_link in crawl_resolution_links(date, driver):
                print(f"\t{res_link}")

            if num == 1:
                break
    '''