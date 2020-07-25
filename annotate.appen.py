from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
import os
from flask import Flask, request, render_template, Response, url_for
import sys
import traceback
import json
from twilio.rest import Client

app = Flask(__name__)
print('Just getting started...')
CHROMEDRIVER_EXECUTABLE = 'chromedriver'
CHROMEDRIVER_PATH = './'
PORT = 5030
URL_ROOT_KEY = 'URL_ROOT'

url_root = os.environ.get(URL_ROOT_KEY, None)
if url_root is None:
    url_root = ''

if 'USERID' in os.environ:
    USERID = os.environ['USERID']
else:
    raise Exception("USERID environment variable/parameter not defined.")
if 'PASSWORD' in os.environ:
    PASSWORD = os.environ['PASSWORD']
else:
    raise Exception("PASSWORD environment variable/parameter not defined.")
if 'TWILIO_ACCOUNT_SID' in os.environ:
    TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
else:
    raise Exception("TWILIO_ACCOUNT_SID environment variable/parameter not defined.")
if 'TWILIO_AUTH_TOKEN' in os.environ:
    TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
else:
    raise Exception("TWILIO_AUTH_TOKEN environment variable/parameter not defined.")

# Use the presence of HOSTNAME environment variable to determine if we're running in a Docker container
# (HOSTNAME is defined) or locally (no HOSTNAME).
if 'HOSTNAME' in os.environ:
    print('Starting in container')
    docker = True
else:
    print('Starting outside a container')
    docker = False

# Your Account Sid and Auth Token from twilio.com/user/account
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = Client(account_sid, auth_token)

@app.before_request
def do_something_whenever_a_request_comes_in():
    r = request
    url = r.url
    method = r.method
    print('>>>> Call into %s with %s ' % (url, method))
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
    return response


@app.errorhandler(Exception)
def handle_bad_request(e):
    print('Error: %s' % str(e))
    traceback.print_exc()
    error_content = {'Error': str(e)}
    send_sms('Appen automation error: %s' % str(e))
    return Response(json.dumps(error_content), status=500, mimetype='application/json')


"""
Routine to print page source (just the last part of the body to eliminate the gorp
at the top). Used for debugging
"""

def print_page_source(driver):
    print('========================================')
    print('Body for %s:' % driver.current_url)
    page_source = driver.page_source
    body_tag_index = page_source.find('<body')
    if body_tag_index < 0:
        print('No <body> tag found')
    else:
        end_body_tag_index = page_source.find('</body', body_tag_index)
        if end_body_tag_index < 0:
            print('No </body> tag found')
        else:
            if end_body_tag_index - body_tag_index <= 3200:
                print(page_source[body_tag_index:end_body_tag_index])
            else:
                print("Too long. Logging the last 3200 characters")
                print(page_source[end_body_tag_index-3200:end_body_tag_index])
    print('\n\n')


"""
Routine to send a text message through Twilio to alert
"""
def send_sms(msg):
    message = twilio_client.messages.create(
        body=msg,
        from_='+19842144460',
        to='+19192446142'
    )
    return message.sid

"""
Routine to grab a job if we find one
"""
def grab_job(driver):
    buttons = driver.find_elements_by_class_name("btn-default")
    found_skip_button = False
    for button in buttons:
        if button.text == 'Skip Tour':
            button.click()
            found_skip_button = True
            break
    if found_skip_button is False:
        raise Exception('Can\'t find the \'Skip\' button.')
    # need to dismiss overlay to be able to click on a button
    jobs_button = driver.find_element_by_class_name("potential")
    jobs_button.click()
    # Now we're clicking the first job we find, identified by the class ('a-primary') of the link
    job_link  = driver.find_element_by_class_name("a-primary")
    job_link.click()

    # at this point we're asked to authenticate again. Authentication prompt comes up in a second
    # browser tab. Need to switch to it, authenticate, and then switch back. Assumption is that the
    # initial content is in the first tab (index 0) and the auth tab is the second (index 1).
    tabs = driver.window_handles
    driver.switch_to.window(tabs[1])
    # Now authenticate
    wait = WebDriverWait(driver, 10)
    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'session[email]')))
    email = driver.find_element_by_name("session[email]")
    password = driver.find_element_by_name("session[password]")
    email.clear()
    email.send_keys(USERID)
    password.clear()
    password.send_keys(PASSWORD)
    sign_in_button = driver.find_element_by_name("commit")
    sign_in_button.click()
    # Unclear yet if the work appears in this tab or the original one
    print("Browser Tab[1]")
    print_page_source(driver)
    driver.switch_to.window(tabs[0])
    print("Browser Tab[0]")
    print_page_source(driver)


@app.route('/')
def appen():
    options = Options()
    if 'HEADLESS' in os.environ:
        HEADLESS = os.environ['HEADLESS']
        if HEADLESS == 'True' or HEADLESS == 'true' or HEADLESS == 'TRUE':
            options.headless = True
        else:
            options.headless = False
    else:
        options.headless = True
    if docker:
        driver = webdriver.Chrome(options=options)
    else:
        driver = webdriver.Chrome(CHROMEDRIVER_PATH + CHROMEDRIVER_EXECUTABLE, options=options)
    wait = WebDriverWait(driver, 10)
    driver.get("https://annotate.appen.com/")
    print("Retrieved https://annotate.appen.com/")
    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'email')))
    # Once we see the authentication prompts, sign in
    email = driver.find_element_by_name("email")
    password = driver.find_element_by_name("password")
    email.clear()
    email.send_keys(USERID)
    password.clear()
    password.send_keys(PASSWORD)
    sign_in_button = driver.find_element_by_class_name("b-Login__submit-button")
    sign_in_button.click()
    wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'b-TaskListing__iframe')))

    # at this point w should be signed in. The content we're interested is in an iframe. So we need
    # to locate it and switch to it. This switch to the iframe is important. Otherwise all I see in
    # Selenium is the javascript entry. Switching to the iframe gets me the rendered HTML from the
    # javascript.
    iframe = driver.find_element_by_class_name("b-TaskListing__iframe")
    driver.switch_to.frame(iframe)

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
        url = driver.current_url
        send_sms('Appen jobs found! %s' % url)
        grab_job(driver)
    else:
        return_result = "No jobs this time :("

    driver.close()
    print(return_result)
    print(text)
    response_content = {'Result': return_result}
    return Response(json.dumps(response_content), status=200, mimetype='application/json')

@app.route('/sms/<string:msg>')
def sms(msg):
    response = send_sms(msg)
    return Response(json.dumps({'Body': 'SMS OK', 'SID': response}), status=200, mimetype='application/json')

@app.route('/test')
def test():
    print("Testing...")
    return Response(json.dumps({'Body': 'Test OK'}), status=200, mimetype='application/json')


@app.route('/build')
def build():
    return app.send_static_file('build.txt')

@app.route('/error/<string:msg>')
def error(msg):
    raise Exception(msg)

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon-96x96.png')


port = os.getenv('PORT', PORT)

if __name__ == "__main__":
    print('Starting %s....' % sys.argv[0])
    print('Python: ' + sys.version)
    app.run(host='0.0.0.0', port=int(port))
