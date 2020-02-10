import crawler
import resminer

import os, os.path, json
from time import sleep
from random import randint

from selenium.common.exceptions import TimeoutException, WebDriverException

def load_runtime():
    runtime = {"lastBrief": "9999-01-01", "errors": []}

    if os.path.exists("runtime_dump.json"):
        with open("runtime_dump.json") as runtime_json:
            runtime = json.load(runtime_json)
            runtime["errors"] = []

            last_crawl_halt = runtime["lastBrief"]
            print(f"[*] Resuming last crawl that halted at [{last_crawl_halt}]")
    else:
        print("[*] Starting new crawl")

    return runtime

# If a runtime dump exists from the last crawl, load it and resume where the last
# crawl ended
runtime_dump = load_runtime()

exception_counter = 0
MAX_CONSECUTIVE_ERRORS = 5

COMPLETE_ABORT = False

print("[*] Starting crawl")

# Get all the brief PDF links from the archive page
try:
    for meeting_link, meeting_date in crawler.crawl_meeting_links():

        if meeting_date > runtime_dump["lastBrief"]:
            continue

        print(f"[*] Now crawling brief for meeting on [{meeting_date}] using [{meeting_link}]")
        runtime_dump["lastBrief"] = meeting_date

        # Initialize meeting object (will be turned to json later)
        meeting = {
            "meetingDate": meeting_date,
            "briefLink": meeting_link,
            "resolutions": []
        }

        # Crawl the links to each of the resolution PDFs from a brief document
        for resolution_pdf_link in crawler.crawl_resolution_links(meeting_link):
            try:
                print(f"    [*] Attempting to download resolution PDF [{resolution_pdf_link}]")

                # Download the PDF for a resolution
                pdf_path = crawler.download_pdf(resolution_pdf_link, "crawledpdfs")

                print("    [*] PDF downloaded")
                print("    [*] Running OCR on downloaded PDF")

                resolution_details = resminer.extract_resolution_details(pdf_path)

                print("    [*] Appending resolution details to JSON", end = "\n\n")
                meeting["resolutions"].append(resolution_details)

                # Reset exception counter
                exception_counter = 0

            except IndexError:
                print(f"    [!] List index out of range", end = "\n\n")
                runtime_dump["errors"].append({"type": "parsing", "target": resolution_pdf_link, "reason": "index error"})

            except IOError as ioe:
                exception_counter += 1

                print(f"    [!] {ioe}", end = "\n\n")
                runtime_dump["errors"].append({"type": "io", "target": resolution_pdf_link, "reason": str(ioe)})

            except TimeoutException as te:
                exception_counter += 1

                print(f"    [!] {te}", end = "\n\n")
                runtime_dump["errors"].append({"type": "driver", "target": resolution_pdf_link, "reason": str(te)})

            except ConnectionRefusedError as ce:
                exception_counter += 1

                print("[!] Script has been blocked by PWC", end = "\n\n")
                runtime_dump["errors"].append({"type": "crawler", "target": resolution_pdf_link, "reason": str(e)})

            except WebDriverException as wde:
                exception_counter += 1

                print(f"    [!] {wde}", end = "\n\n")
                runtime_dump["errors"].append({"type": "driver", "target": resolution_pdf_link, "reason": str(wde)})

            except KeyboardInterrupt:
                COMPLETE_ABORT = True
                break

            except Exception as e:
                exception_counter += 1

                if len(str(e)) < 75:
                    print(f"    [!] {e}", end = "\n\n")
                else:
                    print("    [!] Long error occurred")

                runtime_dump["errors"].append({"type": "general", "target": resolution_pdf_link, "reason": str(e)})

            # In the event that the exception counter reaches MAX_EXCEPTIONS, halt the program
            if exception_counter == MAX_CONSECUTIVE_ERRORS:
                print("[!] Max consecutive errors reached. Shutting down script")

                errors.append({"type": "fatal", "target": "", "reason": "Max errors reached"})
                break

            # Wait a bit so our IP isn't banned
            sleep( randint(10, 20) )
        
        try:
            # Dump meeting info to file
            meeting_filename = "_".join(meeting_date.split("/")) + ".json"
            with open( os.path.join("meetings",meeting_filename) , "w" ) as meeting_json_file:
                json.dump(meeting, meeting_json_file, separators=(',', ':'))
        except Exception as e:
            print(f"  [!] Error dumping meeting file: {e}", end = "\n\n")
            errors.append({"type": "dump", "target": meeting_link, "reason": str(e)})
        finally:
            del meeting

        if COMPLETE_ABORT:
            break

        sleep( randint(5, 9) )

except KeyboardInterrupt:
    pass
finally:
    # Dump all errors to error json file
    try:
        with open( "runtime_dump.json" , "w" ) as error_file:
            json.dump(runtime_dump, error_file)
    except:
        print("[!] Error dumping errors to file. Redirecting to stdout...")

        for error in runtime_dump["errors"]:
            print( error )