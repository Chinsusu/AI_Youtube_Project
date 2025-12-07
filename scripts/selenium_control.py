"""
Selenium controller stub for YouTube playback automation.

This is optional when using the in-app PyQt WebEngine player, but provided
for workflows that prefer controlling an external browser.
"""

from __future__ import annotations

from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class YouTubeController:
    def __init__(self) -> None:
        self.driver: Optional[webdriver.Chrome] = None

    def start(self) -> None:
        if self.driver:
            return
        options = Options()
        options.add_argument("--start-maximized")
        # Headless can break video controls; prefer visible browser by default.
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    def stop(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    def open(self, url: str) -> None:
        if not self.driver:
            self.start()
        assert self.driver
        self.driver.get(url)

    def play(self) -> None:
        self._exec_js("(document.querySelector('video')||{}).play && document.querySelector('video').play();")

    def pause(self) -> None:
        self._exec_js("(document.querySelector('video')||{}).pause && document.querySelector('video').pause();")

    def next(self) -> None:
        self._exec_js("var b=document.querySelector('.ytp-next-button'); if(b){b.click()}")

    def _exec_js(self, script: str) -> None:
        if not self.driver:
            return
        self.driver.execute_script(script)

