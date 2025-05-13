'''
2025
'''
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
import traceback
import time
from datetime import datetime, timedelta
import traceback
from threading import Thread

# https://resy.com/cities/chicago-il/venues/armitage-alehouse?date=2025-04-12&seats=2
RESY_URL = 'https://resy.com/cities/chicago-il/venues/armitage-alehouse?date=%s&seats=%s'

LOG_FILE_NAME = 'log.txt'
log_file = open(LOG_FILE_NAME, 'w')

GECKODRIVER_PATH = '../geckodriver'
LOG_FILE_NAME = 'geckodriver.log'
# Number of days in advance when reservations become available (21 days - 1)
RESERVATION_WINDOW = 20
# Time of day when reservations become available - may need to adjust for time zone differences
RESERVATION_TIME = 10
# Reservation retry interval in milliseconds
RETRY_INTERVAL = 500 
# Reservation attempt period - time, in seconds, after which we give up
RESERVATION_ATTEMPT_PERIOD = 30

def find_and_click_button(driver, button_text, optional=False):
    buttons = driver.find_elements(By.TAG_NAME, "button")
    found_button = None
    for button in buttons:
        if button_text in button.text:
            found_button = button
            break
    if found_button is None:
        if optional is False:
            raise Exception("\"%s\" button not found" % button_text)
        else:
            log("\"%s\" button not found." % button_text)    
    else:
        found_button.click()
        log("\"%s\" button clicked." % button_text)
    return

def login(driver):
    login_button = driver.find_element(By.CLASS_NAME, "Button--login")
    login_button.click()
    find_and_click_button(driver, "Password")
    email_field = driver.find_element(By.ID, "email")
    email_field.send_keys("meetthekellermans@gmail.com")
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys("vjw6rmy-fqx2wyz*FKC")
    find_and_click_button(driver, "Continue")
    # need to wait here for overlay to display at clicking to login
    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CLASS_NAME, "AnnouncementContent__main-container")))
    find_and_click_button(driver, "No Thanks", optional=True)
    log("Logged in")
    return 

def get_driver():
    options = FirefoxOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = FirefoxService(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)
    size = driver.get_window_size()
    driver.set_window_size(size['width'],size['height']*2)
    return driver

def log(msg):
    print('%s - %s' % (datetime.now().strftime('%m/%d/%y: %H:%M:%S.%f'), msg))
    log_file.write("%s - %s\n" % (datetime.now().strftime('%m/%d/%y: %H:%M:%S.%f'), msg))

def idle_until_reservation_time():
    now = datetime.now()
    reservation_time = datetime(year=now.year, month=now.month, day=now.day, hour=RESERVATION_TIME)
    if reservation_time > now:
        idle_time = (reservation_time - now).seconds - 5
        log("Idling for %s seconds" % idle_time)
        time.sleep(idle_time)
        log("Resuming")
    else:
        log("Don't need to idle")
    return

def get_reservation(driver):
    done = False
    reservation_found = False
    start_time = datetime.now()
    while not done:
        driver.refresh()
        time.sleep(0.5)
        find_and_click_button(driver, "No Thanks", optional=True)
        # WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.ID, "page-content")))
        if (datetime.now() - start_time).seconds > RESERVATION_ATTEMPT_PERIOD:
            done = True
        venue_pages = driver.find_elements(By.CLASS_NAME, "VenuePage")
        if len(venue_pages) > 0:
            # This means that the date page has rendered successfully
            log("Schedule page rendered")
            shift_inventories = driver.find_elements(By.CLASS_NAME, "ShiftInventory__shift")
            if len(shift_inventories) > 0:
                # This means that the reservation schedule is available for this day
                log("Schedule available for this day")
                get_screen_cap(driver)
                reservation_buttons = driver.find_elements(By.CLASS_NAME, "ReservationButton")
                if len(reservation_buttons) == 0:
                    log("No reservations available")
                else:
                    acceptable_reservation = None
                    for button in reservation_buttons:
                        if "Table" in button.text:
                            if "7:" in button.text or "6:3" in button.text or "6:4" in button.text:
                                acceptable_reservation = button
                                acceptable_reservation.click()
                                log("reservation found: %s" % button.text)
                                # Including this next line to prevent execution from
                                # completing and then losing the browser session and reservation.
                                input("Press \"return\" to continue.")
                                break
                    if acceptable_reservation is None:
                        log("No acceptable reservation found")
                done = True
            else:
                log("Schedule not yet available")
        else:
            log("Page did not completely render")
    return

def get_screen_cap(driver):
    results=[]
    th = Thread(target=screen_cap_job,
        args=(driver, results))
    th.start()
    return

def screen_cap_job(driver, results):
    # parm results is required as an iterable because this routine is used in a threaded job.
    now = datetime.now()
    log("Screen cap: %s" % now)
    driver.save_full_page_screenshot("%s.png" % now)
    return


def main():
    try:
        driver = None
        log(">>>> Attempt Start <<<<< ")
        future = (datetime.now() + timedelta(RESERVATION_WINDOW)).strftime('%Y-%m-%d')
        driver = get_driver()
        url = RESY_URL % (future, 2)
        log(url)
        driver.get(url)
        login(driver)
        idle_until_reservation_time()
        get_reservation(driver)

    except Exception as e:
        log('Exception Error: ' + str(e))
        traceback.print_exc()
    finally:
        if driver is not None:
            driver.close()
        log_file.close()

if __name__ == '__main__':
    main()