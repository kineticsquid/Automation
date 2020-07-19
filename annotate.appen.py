from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
import os


CHROMEDRIVER_EXECUTABLE = 'chromedriver'
CHROMEDRIVER_PATH = './'

def main(request_input):

    if request_input.get('action') == 'Test':
        print("Testing...")
        print("Request Input:")
        print(request_input)
        print("Environment Variables:")
        for key in os.environ.keys():
            print("%s - %s" %  (key, os.environ[key]))
        return {"statusCode": 200, "body": "Test OK"}

    if 'USERID' in os.environ:
        USERID = os.environ['USERID']
    elif request_input.get('USERID') is not None:
        USERID = request_input.get('USERID')
    else:
        raise Exception("USERID environment variable/parameter not defined.")
    if 'PASSWORD' in os.environ:
        PASSWORD = os.environ['PASSWORD']
    elif request_input.get('PASSWORD') is not None:
        PASSWORD = request_input.get('PASSWORD')
    else:
        raise Exception("PASSWORD environment variable/parameter not defined.")

    # Use the presence of HOSTNAME environment variable to determine if we're running in a Docker container
    # (HOSTNAME is defined) or locally (no HOSTNAME).
    if 'HOSTNAME' in os.environ:
        docker = True
    else:
        docker = False

    options = Options()
    options.headless = True
    if docker:
        driver = webdriver.Chrome(options=options)
    else:
        driver = webdriver.Chrome(CHROMEDRIVER_PATH + CHROMEDRIVER_EXECUTABLE, options=options)
    wait = WebDriverWait(driver, 10)
    driver.get("https://annotate.appen.com/")
    wait.until(expected_conditions.visibility_of_element_located((By.NAME, 'email')))
    email = driver.find_element_by_name("email")
    password = driver.find_element_by_name("password")
    email.clear()
    email.send_keys(USERID)
    password.clear()
    password.send_keys(PASSWORD)
    sign_in_button = driver.find_element_by_class_name("b-Login__submit-button")
    sign_in_button.click()
    # At this point we should be signed in.

    wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'b-TaskListing__iframe')))
    iframe = driver.find_element_by_class_name("b-TaskListing__iframe")
    # This switch to the iframe is important. Otherwise all I see in Selenium is the
    # javascript entry. Switching to the iframe gets me the rendered HTML from the
    # javascript.
    driver.switch_to.frame(iframe)
    tasks_wrapper = driver.find_element_by_id("available-tasks_wrapper")
    text = tasks_wrapper.text

    if 'No matching records' in tasks_wrapper.text:
        jobs = False
    else:
        jobs = True
    driver.close()

    if jobs:
        # text me
        return_result = "Found jobs!"
    else:
        return_result = "No jobs this time :("
    print(return_result)
    print(text)
    return {"statusCode": 200, "body": return_result}


if __name__ == '__main__':
    main({"action": "No Test"})
