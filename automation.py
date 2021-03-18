from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.options import Options as SafariOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import redis
import os
from flask import Flask, request, render_template, Response, url_for, abort, send_file
import sys
import traceback
import json
from twilio.rest import Client
import time
from datetime import datetime, date
import logging
import uuid
import urllib.parse
import re

print('Just getting started...')
app = Flask(__name__)

@app.before_request
def do_something_whenever_a_request_comes_in():
    r = request
    url = r.url
    method = r.method
    log('>>>> Call into %s with %s ' % (url, method))
    # This is to force output to stdout to show up when we're running in a container
    sys.stdout.flush()


@app.after_request
def apply_headers(response):
    # This is to force output to stdout to show up when we're running in a container
    sys.stdout.flush()
    # These are to fix low severity vulnerabilities identified by AppScan
    # in a dynamic scan
    response.headers['Content-Security-Policy'] = "object-src 'none'; script-src 'strict-dynamic'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Last-Modified'] = datetime.now()
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.errorhandler(Exception)
def handle_bad_request(e):
    log('Error: %s' % str(e))
    traceback.print_exc()
    error_content = {'Error': str(e)}
    send_sms('Automation error: %s' % str(e))
    return Response(json.dumps(error_content), status=500, mimetype='application/json')


"""
Routine to log
"""
def log(message):
    logging.info(message)

"""
Routine to print page source (just the last part of the body to eliminate the gorp
at the top). Used for debugging
"""


def print_page_source(driver, time_now):
    file = open('./screen_caps/%s.page_source.html' % time_now, 'w')
    page_source = driver.page_source
    file.writelines(page_source)
    file.close()


"""
Routine to send a text message through Twilio to alert
"""


def send_sms(msg):
    message = twilio_client.messages.create(
        body=msg,
        from_='+19842144312',
        to='+19192446142'
    )
    return message.sid


def send_mms(media_url):
    message = twilio_client.messages.create(
        from_='+19842144312',
        to='+19192446142',
        media_url=media_url
    )
    return message.sid


"""
Routine to grab a job if we find one
"""


def grab_job(driver):
    time_now = time.time()
    driver.get_screenshot_as_file('./screen_caps/%s.found.png' % time_now)
    # I don't think I need this anymore, these next two lines
    # jobs_button = driver.find_element_by_class_name("potential")
    # jobs_button.click()

    # Now we're clicking the first job we find, identified by the class ('a-primary') of the link
    job_link = driver.find_element_by_class_name("a-primary")
    job_link.click()

    # at this point we're asked to authenticate again. Authentication prompt comes up in a second
    # browser tab. Need to switch to it, authenticate, and then switch back. Assumption is that the
    # initial content is in the first tab (index 0) and the auth tab is the second (index 1).
    tabs = driver.window_handles
    driver.switch_to.window(tabs[1])
    driver.set_window_size(1024, 3600)
    # Now authenticate
    wait = WebDriverWait(driver, 10)
    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'session[email]')))
    # We have the authenticate page, but there is an overlay on top of the login button. We need to
    # first get rid of the overlay.
    overlay_buttons = driver.find_elements_by_class_name("b-SVGIcon")
    # these alerts are ephemeral so catch the stale element exception and ignore
    for button in overlay_buttons:
        try:
            button.click()
        except Exception:
            log('Stale button')
            pass
    # Now attempt to authenticate
    email = driver.find_element_by_name("session[email]")
    password = driver.find_element_by_name("session[password]")
    email.clear()
    email.send_keys(APPEN_USERID)
    password.clear()
    password.send_keys(APPEN_PASSWORD)
    sign_in_button = driver.find_element_by_name("commit")
    sign_in_button.click()
    # Unclear yet if the work appears in this tab or the original one
    print_page_source(driver, time_now)
    driver.get_screenshot_as_file('./screen_caps/%s.found2.png' % time_now)
    driver.switch_to.window(tabs[0])
    driver.get_screenshot_as_file('./screen_caps/%s.found3.png' % time_now)

def get_browser_options():

    if BROWSER == 'Chrome':
        options = ChromeOptions()
        # ref: https://stackoverflow.com/questions/53902507/unknown-error-session-deleted-because-of-page-crash-from-unknown-error-cannot
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if HEADLESS is True:
            options.headless = True
        else:
            options.headless = False
    elif BROWSER == 'Firefox':
        options = FirefoxOptions()
        if HEADLESS is True:
            options.add_argument("--headless")
    elif BROWSER == 'Safari':
        options = SafariOptions()
        if HEADLESS is True:
            options.headless = True
        else:
            options.headless = False
    else:
        options = ChromeOptions()

    return options

@app.route('/')
def automation():
    return render_template('index.html', url_root=url_root)


@app.route('/appen')
def appen():
    options = get_browser_options()
    if docker:
        driver = webdriver.Chrome(options=options)
    else:
        driver = webdriver.Chrome(DRIVER_PATH + CHROME_DRIVER_EXECUTABLE, options=options)
    try:
        driver.set_window_size(1024, 1800)
        wait = WebDriverWait(driver, 10)
        driver.fullscreen_window()
        driver.get("https://annotate.appen.com/")
        log("Retrieved https://annotate.appen.com/")
        wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'email')))
        # Once we see the authentication prompts, sign in
        email = driver.find_element_by_name("email")
        password = driver.find_element_by_name("password")
        email.clear()
        email.send_keys(APPEN_USERID)
        password.clear()
        password.send_keys(APPEN_PASSWORD)
        sign_in_button = driver.find_element_by_class_name("b-Login__submit-button")
        sign_in_button.click()
        wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'b-TaskListing__iframe')))

        # pausing here to wait for the login confirmation alert to disappear
        time.sleep(4)

        # Now, dismiss the other alerts
        alert_buttons = driver.find_elements_by_class_name("b-SVGIcon")
        # these alerts are ephemeral so catch the stale element exception and ignore
        for button in alert_buttons:
            try:
                button.click()
            except Exception:
                log('Stale button')
                pass

        # at this point we should be signed in. The content we're interested is in an iframe. So we need
        # to locate it and switch to it. This switch to the iframe is important. Otherwise all I see in
        # Selenium is the javascript entry. Switching to the iframe gets me the rendered HTML from the
        # javascript.
        iframe = driver.find_element_by_class_name("b-TaskListing__iframe")
        driver.switch_to.frame(iframe)

        # Dismiss the new user tour overlay
        buttons = driver.find_elements_by_class_name("btn-default")
        for button in buttons:
            if button.text == 'Skip Tour':
                try:
                    button.click()
                    break
                except Exception as e:
                    pass

        # Now look to see if there are tasks available. We're looking for the text message that indicates
        # no work ('No matching records').
        tasks_wrapper = driver.find_element_by_id("available-tasks_wrapper")
        text = tasks_wrapper.text

        if 'No matching records' in text:
            jobs = False
        else:
            jobs = True

        # If we've found jobs, send a text message, otherwise log that there were no jobs
        if jobs:
            # text me
            return_result = "Found jobs!"
            log(return_result)
            log(text)
            url = driver.current_url
            send_sms('Appen jobs found! %s' % url)
            grab_job(driver)
        else:
            return_result = "No jobs this time :("
            log(return_result)
            log(text)

        driver.close()
        response_content = {'Result': return_result}
        return Response(json.dumps(response_content), status=200, mimetype='application/json')
    except Exception as e:
        log('>>>>>>>> Error <<<<<<<<')
        log(e)
        traceback.print_exc()
        driver.get_screenshot_as_file('./screen_caps/%s.fail.png' % time.time())
        response_content = {'Result': 'Error: %s' % e}
        return Response(json.dumps(response_content), status=500, mimetype='application/json')

@app.route('/webtrac')
def webtrac():
    options = get_browser_options()
    if BROWSER == 'Chrome':
        if docker:
            driver = webdriver.Chrome(options=options)
        else:
            driver = webdriver.Chrome(DRIVER_PATH + CHROME_DRIVER_EXECUTABLE, options=options)
    elif BROWSER == 'Firefox':
        if docker:
            driver = webdriver.Firefox(options=options)
        else:
            firefox_executable = "%s%s" % (DRIVER_PATH, FIREFOX_DRIVER_EXECUTABLE)
            firefox_binary = FirefoxBinary(firefox_executable)
            driver = webdriver.Firefox(firefox_binary=firefox_binary, options=options)
    elif BROWSER == 'Safari':
        if docker:
            driver = webdriver.Safari()
        else:
            driver = webdriver.Safari()
    else:
        raise Exception('Invalid value for \'BROWSER\' environment variable')
    driver.set_window_size(1600, 1792)
    wait = WebDriverWait(driver, 5)

    one_week_out = date.fromordinal(date.today().toordinal() + 7)
    one_week_out_month_string = one_week_out.strftime("%m")
    one_week_out_day_string = one_week_out.strftime("%d")
    one_week_out_month = str(int(one_week_out_month_string))
    one_week_out_day = str(int(one_week_out_day_string))
    one_week_out_year = one_week_out.strftime("%Y")

    # This is what the URL looks like when you click the competition pool schedule for 7:00 AM
    # https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40440968&BeginMonth=1&BeginYear=2021

    now = datetime.now()
    this_day = now.strftime("%a")
    wait_time_between_tried_in_secs = 120
    total_processing_time_in_secs = 8 * 60 * 60

    if this_day == 'Sat' or this_day == 'Sun':
        webtrac_url = "%s&BeginMonth=%s&BeginYear=%s" % (WEBTRAC_URL_WEEKEND, one_week_out_month, one_week_out_year)
    else:
        webtrac_url = "%s&BeginMonth=%s&BeginYear=%s" % (WEBTRAC_URL_WEEKDAY, one_week_out_month, one_week_out_year)

    log('================== New Request ====================')
    log('Local time: %s' % now.strftime(' %a - %m/%d - %H:%M:%S'))

    driver.get(WEBTRAC_URL_BASE)
    wait.until(expected_conditions.visibility_of_element_located((By.ID, 'weblogin_username')))
    username_field = driver.find_element_by_id('weblogin_username')
    username_field.clear()
    username_field.send_keys(WEBTRAC_USERID)
    password_field = driver.find_element_by_id('weblogin_password')
    password_field.clear()
    password_field.send_keys(WEBTRAC_PASSWORD)
    login_button = driver.find_element_by_id('xxproclogin')
    login_button.click()
    log('Successfully authenticated.')

    try:
        count = 1
        done = False
        start_time = time.time()
        stop_time = start_time + total_processing_time_in_secs
        while not done and time.time() < stop_time:
            try:
                log('Loading %s' % webtrac_url)
                driver.get(webtrac_url)
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'content')))
                log('Schedule calendar loaded.')
                if count == 1:
                    send_screen_cap(driver)
                # At this point the calendar for this pool schedule is visible

                # Now we're going to loop through the days in the calendar, being sure to skip to the
                # beginning of the month, looking for the calendar entry for the day we want the reservation
                days = driver.find_elements_by_class_name('day')
                found_the_1st = False
                target_day = None
                for day in days:
                    day_text = re.match(r'\d+', day.text).group(0)
                    if day_text == '1':
                        found_the_1st = True
                    if found_the_1st and day_text == one_week_out_day:
                        target_day = day
                        break

                #  Not sure if this could happen
                if target_day is None:
                    raise Exception('Unable to find correct calendar entry')

                # Now click the calendar day we want the reservation on
                target_day.click()
                wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME,
                                            'websearch_multiselect_buttonaddtocart')))

                log('Found correct day and clicked it.')
                if count == 1:
                    send_screen_cap(driver)
                # Click the confirmation to add the reservation to shopping cart
                add_button = driver.find_element_by_class_name('websearch_multiselect_buttonaddtocart')
                add_button.click()
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'content')))
                log('Selected calendar schedule day and confirmed add to cart.')
                if count == 1:
                    send_screen_cap(driver)

                # We're logged in, now presented with terms of use, click the checkbox and the click on the
                # continue button.Sometimes these terms do not show up. Don't understand when.
                try:
                    terms_checkbox = driver.find_element_by_id('processingprompts_waivercheckbox')
                    terms_checkbox.click()
                    continue_button = driver.find_element_by_id('processingprompts_buttoncontinue')
                    continue_button.click()
                    log('Accepted terms.')
                except NoSuchElementException:
                    log('Accept terms page not displayed. Skipping.')

                # Now, we're at checkout, click the proceed to checkout button
                checkout_button = driver.find_element_by_id('webcart_buttoncheckout')
                checkout_button.click()
                log('Proceeding to checkout.')

                # Continue checkout
                continue_checkout_button = driver.find_element_by_id('webcheckout_buttoncontinue')
                continue_checkout_button.click()
                log('Checked out.')

                # Click to get email verification
                email_conf_button = driver.find_element_by_id('webconfirmation_buttonsumbit')
                email_conf_button.click()
                log('Email confirmation sent.')
                done = True
            except Exception as e:
                if count == 1:
                    send_screen_cap(driver)
                log('Exception: %s' % e)
                log('Unsuccessful on attempt: %s. Waiting for %s secs.' % (count, wait_time_between_tried_in_secs))
                time.sleep(wait_time_between_tried_in_secs)
                count += 1
                # driver.switch_to.alert.accept()
        if not done:
                raise Exception('Failed to see the desired schedule.')

        # Reservation successful
        send_email_button = driver.find_element_by_id('webconfirmation_buttonsumbit')
        send_email_button.click()
        result_msg = 'Reservation made for %s/%s' % (one_week_out_month, one_week_out_day)
        send_sms(result_msg)

        driver.close()
        response_content = {'Result': result_msg}
        return Response(json.dumps(response_content), status=200, mimetype='application/json')

    except Exception as e:
        log('>>>>>>>> Error <<<<<<<<')
        log(e)
        traceback.print_exc()
        log('Session ID: %s' % driver.session_id)
        if HEADLESS:
            send_screen_cap(driver)
            send_sms(e)
        response_content = {'Result': 'Error: %s' % e}
        return Response(json.dumps(response_content), status=500, mimetype='application/json')

def send_screen_cap(driver):
    r = request
    now = datetime.now()
    filename = '/automation/%s.%s.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
    mms_url = "http://%s/%sruntime_images%s" % (r.host, url_root, filename)
    image = driver.get_screenshot_as_png()
    sudoku_images.setex(filename, REDIS_TTL, image)
    if url_root != '':
        send_mms(mms_url)

@app.route('/omnify')
def omnify():
    options = get_browser_options()
    # https://stackoverflow.com/questions/50414007/unable-to-invoke-firefox-headless
    one_week_out = date.fromordinal(date.today().toordinal() + 7)
    date_string = one_week_out.strftime("%Y-%d-%m")
    now = datetime.now()
    today = now.strftime("%a")
    if BROWSER == 'Chrome':
        if docker:
            driver = webdriver.Chrome(options=options)
        else:
            driver = webdriver.Chrome(DRIVER_PATH + CHROME_DRIVER_EXECUTABLE, options=options)
    elif BROWSER == 'Firefox':
        if docker:
            driver = webdriver.Firefox(options=options)
        else:
            firefox_executable = "%s%s" % (DRIVER_PATH, FIREFOX_DRIVER_EXECUTABLE)
            firefox_binary = FirefoxBinary(firefox_executable)
            driver = webdriver.Firefox(firefox_binary=firefox_binary, options=options)
    elif BROWSER == 'Safari':
        if docker:
            driver = webdriver.Safari()
        else:
            driver = webdriver.Safari()
    else:
        raise Exception('Invalid value for \'BROWSER\' environment variable')
    try:
        log('Session ID: %s' % driver.session_id)
        driver.set_window_size(1600, 1792)
        wait = WebDriverWait(driver, 5)
        driver.get(OMNIFY_URL)

        count = 0
        max_iterations = 75
        while count < max_iterations:
            try:
                wait.until(
                    expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'client-schedule-card-list')))
                log("%s loaded." % OMNIFY_URL)

                logged_in_elements = driver.find_elements_by_id('w-dropdown-toggle-0')
                # if we don't find this element, or the text label is 'Chapel Hill...' instead of user name
                # it means we're not logged in
                if len(logged_in_elements) == 0 or 'Chapel' in logged_in_elements[0].text:
                    # This XPath navigation is to get the link to login
                    sign_up_elements = driver.find_elements_by_xpath("/html/body/div[3]/div[3]/div/div[2]/a[1]")
                    log_in = sign_up_elements[0]
                    log_in.click()
                    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'email')))
                    log('Login popup displayed.')
                    # Fill in user id
                    email = driver.find_element_by_name("email")
                    email.clear()
                    email.send_keys(WEBTRAC_USERID)
                    # Again XPath to get the button to continue with the login
                    continue_button = driver.find_element_by_xpath("//popup-modal[1]/div[1]/div[1]/div[1]/div[2]/button[1]")
                    continue_button.click()
                    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'password')))
                    log('Userid filled in, password prompt visible.')
                    # Fill in password
                    password = driver.find_element_by_name("password")
                    password.clear()
                    password.send_keys(WEBTRAC_PASSWORD)
                    login_button = driver.find_element_by_xpath("//popup-modal[1]/div[1]/div[1]/div[1]/div[2]/button[1]")
                    login_button.click()
                    # time.sleep(4)
                    # Should be authenticated at this point
                    # Compute date one week out an construct url to the schedule for that date
                    log('Successfully authenticated.')

                schedule_url = "%s#!/schedules/%s" % (OMNIFY_URL, date_string)
                driver.get(schedule_url)
                # time.sleep(4)
                # We now have the page for the day we want to make a reservation. Note the date slider
                # at the top of the page will not match
                # Get the links for all the pools and times available that day
                #
                # Because these slots fill up so fast, and because it takes a while for this cloud
                # function to spin up, we are going to start trying a little before the top of the
                # hour and then retry after 10 sec if we don't find the 7:00 slot. We'll try a total of 10 times.
                log('Schedule displayed for %s.' % date_string)

                if today == 'Sat' or today == 'Sun':
                    wait.until(expected_conditions.visibility_of_element_located((By.ID, '12-00-pm-12-00-pm')))
                    schedule_link = driver.find_element_by_xpath('//*[@id="12-00-pm-12-00-pm"]/div[2]/div[2]/a[2]/div')
                else:
                    wait.until(expected_conditions.visibility_of_element_located((By.ID, '07-00-am-07-00-am')))
                    schedule_link = driver.find_element_by_xpath('//*[@id="07-00-am-07-00-am"]/div[2]/div[2]/a[2]/div')
                schedule_link.click()
                wait.until(expected_conditions.visibility_of_element_located((By.ID, 'go-next')))
                break
            except Exception as e:
                count += 1
                log('Exception: %s' % e)
                log('Schedule not available on attempt: %s. Waiting for %s secs.' % (count, 5))
                driver.refresh()
        if count >= max_iterations:
            raise Exception('Failed to see the desired schedule.')

        # We now have the page to make the reservation
        # They'll be 5 entries here, one for each weekday. No weekend sessions at 7:00 AM. There are booking links
        # available if there is space left on that day. So, there could be 0 to 5 links.
        log('Competition pool schedule visible.')
        booking_links = driver.find_elements_by_name('class-schedules-checklist')
        if len(booking_links) == 0:
            raise Exception('No apparent availability on %s.' % date_string)
        elif len(booking_links) == 1:
            if booking_links[0].is_selected() is False:
                booking_links[0].click()
        else:
            booking_link = booking_links[len(booking_links) - 1]
            if booking_link.is_selected() is False:
                booking_link.click()
        # At this point we've selected a date for this pool and this time slot. Continue to the next step
        log('Selected an entry to make a reservation.')
        next_button = driver.find_element_by_id('go-next')
        next_button.click()
        time.sleep(2)
        # Now we have a pop up to add people to the reservation. We're not so, just continue.
        log('Popup to add people to the reservation visible.')
        next_button_2 = driver.find_element_by_id('save-attendees')
        next_button_2.click()
        wait.until(expected_conditions.visibility_of_element_located((By.ID, 'submitFinalReviewFormBtn')))
        log('Reservation confirmation page visible.')

        # Click to accept terms
        terms_check_box = driver.find_element_by_class_name('iCheck-helper')
        terms_check_box.click()

        # Finally, confirm reservation
        confirm_button = driver.find_element_by_id('submitFinalReviewFormBtn')
        confirm_button.click()
        wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'schedule-card')))
        log('Schedule card visible, reservation made.')
        # At this point we have a reservation
        schedule_cards = driver.find_elements_by_class_name('schedule-card')
        if len(schedule_cards) == 0:
            raise Exception('Failed to confirm reservation.')
        else:
            results = 'Confirmed reservation for %s.' % date_string
            send_sms(results)
            now = datetime.now()
            filename = '%s.%s.success.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
            driver.get_screenshot_as_file('./screen_caps/%s' % filename)
        driver.close()
        response_content = {'Result': results}
        return Response(json.dumps(response_content), status=200, mimetype='application/json')
    except Exception as e:
        log('>>>>>>>> Error <<<<<<<<')
        log(e)
        traceback.print_exc()
        log('Session ID: %s' % driver.session_id)
        if HEADLESS:
            r = request
            now = datetime.now()
            filename = '/automation/%s.%s.fail.png' % (now.strftime('%m-%d-%H-%M-%S'), uuid.uuid1())
            mms_url = "http://%s/%sruntime_images%s" % (r.host, url_root, filename)
            image = driver.get_screenshot_as_png()
            sudoku_images.setex(filename, REDIS_TTL, image)
            send_sms(e)
            if url_root != '':
                send_mms(mms_url)
        response_content = {'Result': 'Error: %s' % e}
        return Response(json.dumps(response_content), status=500, mimetype='application/json')


@app.route('/runtime_images', defaults={'file_path': ''})
@app.route('/runtime_images/<path:file_path>')
def images(file_path):

    if file_path is None or file_path == '':
        matrix_image_names_as_bytes = sudoku_images.keys()
        matrix_image_names = []
        for entry in matrix_image_names_as_bytes:
            matrix_image_names.append(entry.decode('utf-8'))
        return render_template('images.html', files=matrix_image_names, url_root=url_root, title='Screen Caps')
    else:
        url_file_path = urllib.parse.quote("/%s" % file_path)
        matrix_bytes = sudoku_images.get(url_file_path)
        if matrix_bytes is None:
            return abort(404)
        else:
            return Response(matrix_bytes, mimetype='image/png', status=200)

@app.route('/build', methods=['GET', 'POST'])
def build():
    return app.send_static_file('build.txt')


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon-96x96.png')

@app.route('/clear_redis')
def clear_redis():

    keys = sudoku_images.keys()
    number_of_entries = len(keys)
    for key in keys:
        sudoku_images.delete(key)
    return Response('Removed %s redis entries' % number_of_entries, mimetype='text/text', status=200)


CHROME_DRIVER_EXECUTABLE = 'chromedriver'
FIREFOX_DRIVER_EXECUTABLE = 'geckodriver'
DRIVER_PATH = './'
PORT = 5030
URL_ROOT_KEY = 'URL_ROOT'
OMNIFY_URL = 'https://tochaq.getomnify.com/'

# This is the weekday 7:00 competition pool schedule
WEBTRAC_URL_WEEKDAY = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40440968'

# This is the weekday 2:00 competition pool schedule
# WEBTRAC_URL_WEEKDAY = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40454272'

# This is the weekday 5:30 program pool schedule
# WEBTRAC_URL_WEEKDAY = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40455537'

# This is the Sat/Sun 6:00 PM competition pool schedule
WEBTRAC_URL_WEEKEND = 'https://webtrac.townofchapelhill.org/wbwsc/webtrac.wsc/search.html?Module=AR&Display=Calendar&CalendarFMID=40456132'

# Base URL
WEBTRAC_URL_BASE = 'https://webtrac.townofchapelhill.org/'

REDIS_TTL = 60 * 60 * 48

logging.basicConfig(level=logging.INFO)

url_root = os.environ.get(URL_ROOT_KEY, None)
if url_root is None:
    url_root = ''
else:
    if url_root[0] != '/':
        url_root = '/' + url_root

if 'APPEN_USERID' in os.environ:
    APPEN_USERID = os.environ['APPEN_USERID']
else:
    raise Exception("APPEN_USERID environment variable not defined.")
if 'APPEN_PASSWORD' in os.environ:
    APPEN_PASSWORD = os.environ['APPEN_PASSWORD']
else:
    raise Exception("APPEN_PASSWORD environment variable not defined.")
if 'WEBTRAC_USERID' in os.environ:
    WEBTRAC_USERID = os.environ['WEBTRAC_USERID']
else:
    raise Exception("WEBTRAC_USERID environment variable not defined.")
if 'WEBTRAC_PASSWORD' in os.environ:
    WEBTRAC_PASSWORD = os.environ['WEBTRAC_PASSWORD']
else:
    raise Exception("WEBTRAC_PASSWORD environment variable not defined.")
if 'TWILIO_ACCOUNT_SID' in os.environ:
    TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
else:
    raise Exception("TWILIO_ACCOUNT_SID environment variable not defined.")
if 'TWILIO_AUTH_TOKEN' in os.environ:
    TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
else:
    raise Exception("TWILIO_AUTH_TOKEN environment variable not defined.")
if 'REDIS_HOST' in os.environ:
    REDIS_HOST = os.environ['REDIS_HOST']
else:
    logging.info("Error no REDIS_HOST environment variable defined!")
if 'REDIS_PW' in os.environ:
    REDIS_PW = os.environ['REDIS_PW']
else:
    logging.info("Error no REDIS_PW environment variable defined!")
if 'REDIS_PORT' in os.environ:
    REDIS_PORT = os.environ['REDIS_PORT']
else:
    logging.info("Error no REDIS_PORT environment variable defined!")
if 'REDIS_CERT_FILE' in os.environ:
    REDIS_CERT_FILE = os.environ['REDIS_CERT_FILE']
else:
    logging.info("Error no REDIS_CERT_FILE environment variable defined!")

if 'BROWSER' in os.environ:
    BROWSER = os.environ['BROWSER']
    logging.info('Browser: %s' % BROWSER)
else:
    logging.info("Error no BROWSER environment variable defined!")

# Use the presence of HOSTNAME environment variable to determine if we're running in a Docker container
# (HOSTNAME is defined) or locally (no HOSTNAME).
if 'NODE_HOST' in os.environ:
    log('Starting in container')
    docker = True
else:
    log('Starting outside a container')
    docker = False

if 'HEADLESS' in os.environ:
    HEADLESS = os.environ['HEADLESS']
    if HEADLESS == 'True' or HEADLESS == 'true' or HEADLESS == 'TRUE':
        HEADLESS = True
    else:
        HEADLESS = False
else:
    HEADLESS = False
if HEADLESS:
    log('Running headless')
else:
    log('Running with a display')

# Your Account Sid and Auth Token from twilio.com/user/account
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = Client(account_sid, auth_token)

port = os.getenv('PORT', PORT)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log('Starting %s....' % sys.argv[0])
log('Python: ' + sys.version)
build_file = open('./static/build.txt')
log('Running build:')
for line in build_file.readlines():
    log(line.strip())
build_file.close()
sudoku_images = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PW,
    ssl=True,
    ssl_ca_certs=REDIS_CERT_FILE,
    decode_responses=False)
# Testing Redis connection.
sudoku_images.set('/test/test', 'test_value')
test_value = sudoku_images.delete('/test/test')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))
