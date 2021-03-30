import os, os.path, glob

#import PyPDF2
from PIL import Image 
import pytesseract 
import sys 
from pdf2image import convert_from_path, pdfinfo_from_path
from num2words import num2words

Image.warnings.simplefilter('error', Image.DecompressionBombWarning)

def extract_resolution_details(pdf_web_path, pdf_local_path):
    # Resolution PDFs created prior to June 2019 used scanned images instead of
    # having actual text in the PDF. In order to extract text from resolution
    # PDFs older than June 2019 OCR (optical character recognition) must be
    # utilized, otherwise a basic PDF extraction library can be used
    pdf_text = _extract_text(pdf_local_path)
    
    # Parse the necessary data about the resolution
    return _parse_text(pdf_web_path, pdf_text)


def _extract_text(pdf_path):
    print("    [*] Extracting text from document")

    # This list will hold all the relevant word tokens that are extracted
    relevant_text_list = []

    for page_num in range(0, pdfinfo_from_path(pdf_path)["Pages"]):
        try:
            print("    [*] Converting PDF page to image")
            page_image = convert_from_path(pdf_path, dpi = 500, first_page = page_num + 1, last_page = page_num + 1)[0]

            # Recognize the text as string in image using pytesserct then
            # split the text by newline, strip leading/trailing whitespace,
            # and remove any empty strings that are present
            text = str(((pytesseract.image_to_string( page_image ))))
            text = list(filter(None, [element.strip() for element in text.split("\n")] ))

            # Pages 2 onward all start off with a four line header stating
            # the date, type of meeting, resolution number, and the page
            # number in the format "Page {Number}". 
            # 
            # These lines make extracting relevant information harder, so
            # they are trimmed off using the index of the "Page {Number}" line
            # (which is guaranteed to always come last).
            #
            # Sometimes a blank page will be encountered, so the text must be
            # checked to ensure this isn't the case
            if (page_num + 1) > 1 and text != []: 
                last_header_sentence_index = text.index("Page " + num2words(page_num + 1).capitalize())
                del text[0:last_header_sentence_index + 1]

            relevant_text_list += text

            # The page with the 'Votes:' section concludes the informal
            # information about the resolution itself, the rest of the pages
            # contain extra attachements. These don't need to be parsed, as the
            # link to them will be included on the resolution's page
            if "Votes:" in text:
                break
        finally:
            page_image.close()

    return relevant_text_list

def _parse_text(pdf_web_path, text_list):
    print("    [*] Parsing document text")

    # Locate the indexes of string within the document that contain these keywords
    keywords = ["Res. No.","MOTION:","SECOND:","RE:","ACTION:","Votes:","Ayes:","Nays:","Absent from Vote:","Absent from Meeting:","ATTEST:"]
    indexes = _get_keyword_indexes(keywords, text_list)

    # Sometimes Tessearct will incorrectly treat the "MOTION:", "SECOND:", AND "RE:" portions as their
    # own line. In this case, a different parsing mechanism needs to be done to extract these fields
    if "MOTION:" in text_list and "SECOND:" in text_list and "RE:" in text_list and "ACTION:" in text_list:
        res_name = (text_list[ indexes["SECOND:"] + 5 ]).split(" ")[-1]
        who_motioned = (text_list[ indexes["ACTION:"] + 1 ]).split(" ")[0]
        who_seconded = (text_list[ indexes["SECOND:"] + 5 ]).split(" ")[0]
        action = "APPROVED" if "APPROVED" in text_list else "FAILED"
        re = " ".join( (text_list[ indexes["SECOND:"] + 6 : text_list.index(action)]) )
    else:
        res_name = (text_list[ indexes["Res. No."] ]).split("Res. No.")[1]
        who_motioned = (text_list[ indexes["MOTION:"] ]).split(" ")[1]
        who_seconded = (text_list[ indexes["SECOND:"] ]).split(" ")[1]
        action = (text_list[ indexes["ACTION:"] ]).split(" ")[1]
        re = (" ".join( text_list[ indexes["RE:"] : indexes["ACTION:"] ] )).replace("RE:", "")

    # Parse the string data into a dictionary
    resolution_data = {
        "name": res_name,
        "motion": who_motioned,
        "second": who_seconded,
        "re": re,
        "action": action,
        "votes": {
            "ayes": text_list[indexes["Ayes:"]].replace("Ayes: ","").replace(" ","").split(","),
            "nays": text_list[indexes["Nays:"]].replace("Nays: ","").replace(" ","").split(","),
            "absentFromVote": text_list[indexes["Absent from Vote:"]].replace("Absent from Vote: ","").replace(" ","").split(","),
            "absentFromMeeting": text_list[indexes["Absent from Meeting:"]].replace("Absent from Meeting: ","").replace(" ","").split(","),
        },
        "link": pdf_web_path
    }

    # Sanitize "None" strings into actual None
    sanitize_none = lambda field_list: [] if field_list == ["None"] else field_list

    resolution_data["votes"]["ayes"] = sanitize_none(resolution_data["votes"]["ayes"])
    resolution_data["votes"]["nays"] = sanitize_none(resolution_data["votes"]["nays"])
    resolution_data["votes"]["absentFromVote"] = sanitize_none(resolution_data["votes"]["absentFromVote"])
    resolution_data["votes"]["absentFromMeeting"] = sanitize_none(resolution_data["votes"]["absentFromMeeting"])

    # Mark text_list for garbase collection
    del text_list

    return resolution_data

def _get_keyword_indexes(keywords, strings):
    keyword_indexes = {keyword: -1 for keyword in keywords}

    for i in range(0, len(strings)):
        string = strings[i]
        for keyword in keywords:
            if keyword in string:
                keyword_indexes[keyword] = i

    return keyword_indexes