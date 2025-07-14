import os
import time
import random
from typing import Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
class FormFiller:
    def __init__(self, config: Dict[str, Any], randomize_delay: bool = True, headless: bool = False):
        self.config = config
        self.randomize_delay = randomize_delay
        chrome_options = ChromeOptions()
        
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
        
        # 1. Define the path RELATIVE to your project root.
        #    This is much cleaner and more reliable.
        driver_path = os.path.abspath("chromedriver.exe")
        
        # 2. Check if the file actually exists before trying to use it.
        #    This provides a much better error message.
        if not os.path.exists(driver_path):
            raise FileNotFoundError(
                f"ChromeDriver not found at the expected path: {driver_path}\n"
                "Please make sure 'chromedriver.exe' is in your main project directory, next to 'gui.py'."
            )
            
        # 3. Create the service with the now-verified executable path.
        service = ChromeService(executable_path=driver_path)

        # 4. Initialize the driver. This will now work.
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        self.driver.implicitly_wait(5)
    def _get_element(self, by: By, value: str) -> WebElement:
        """Finds an element with robust error handling."""
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            raise NoSuchElementException(f"Error: Could not find element with {by}='{value}'")

    def _human_like_delay(self):
        """Adds a short, random delay to simulate human behavior."""
        if self.randomize_delay:
            time.sleep(random.uniform(0.3, 1.0))

    def fill_form_for_row(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        try:
            form_url = self.config['form_url']
            full_url = 'file:///' + os.path.abspath(form_url).replace('\\', '/')
            self.driver.get(full_url)
            self._human_like_delay()

            # --- START OF MODIFIED LOGIC ---
            # Fill in the fields
            for data_key, form_field_name in self.config['field_mappings'].items():
                # Get the value from the data row, or use None if the key doesn't exist.
                value = data_row.get(data_key)

                # If the value is None or an empty string, use a placeholder.
                # Otherwise, use the actual value.
                if value is None or str(value).strip() == "":
                    fill_value = "N/A" # Our placeholder for required fields
                    print(f"Info: Using placeholder '{fill_value}' for empty field '{data_key}'.")
                else:
                    fill_value = value
                
                # Now, fill the element with the determined value.
                try:
                    element = self._get_element(By.NAME, form_field_name)
                    self._fill_element(element, fill_value)
                    self._human_like_delay()
                except NoSuchElementException as e:
                    return {'status': 'FAILED', 'reason': str(e), 'data': data_row}
            # --- END OF MODIFIED LOGIC ---
            
            # Click the submit button
            submit_info = self.config['submit_button']
            submit_by = getattr(By, submit_info['type'].upper())
            submit_button = self._get_element(submit_by, submit_info['value'])
            submit_button.click()
            
            # Check for success
            try:
                time.sleep(1)
                if "success.html" in self.driver.current_url:
                    return {'status': 'SUCCESS', 'reason': 'Form submitted successfully.', 'data': data_row}
                else:
                    return {'status': 'FAILED', 'reason': 'Submission did not lead to the expected success page.', 'data': data_row}
            except WebDriverException as e:
                return {'status': 'CRASHED', 'reason': f'Browser window closed unexpectedly after submission. Error: {e.__class__.__name__}', 'data': data_row}

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            return {'status': 'FAILED', 'reason': f'A browser or element error occurred: {e.__class__.__name__}', 'data': data_row}
        except Exception as e:
            return {'status': 'FAILED', 'reason': f"An unexpected Python error occurred: {e}", 'data': data_row}

    def _fill_element(self, element: WebElement, value: Any):
        """Fills a single form element based on its type."""
        elem_type = element.get_attribute('type')
        tag_name = element.tag_name.lower()

        if tag_name == 'select':
            Select(element).select_by_value(str(value))
        elif elem_type == 'radio':
            # For radio buttons, find the specific option by its value
            radio_selector = f"input[name='{element.get_attribute('name')}'][value='{value}']"
            self.driver.find_element(By.CSS_SELECTOR, radio_selector).click()
        elif elem_type == 'checkbox':
            # Check the box if the value is considered "truthy"
            if value:
                element.click()
        elif tag_name in ['input', 'textarea']:
            element.clear()
            element.send_keys(str(value))
        else:
            print(f"Warning: Unsupported element type for '{element.get_attribute('name')}'")

    def close(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()