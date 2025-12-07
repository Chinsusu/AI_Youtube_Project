"""
Selenium controller stub for YouTube playback automation.

This is optional when using the in-app PyQt WebEngine player, but provided
for workflows that prefer controlling an external browser.
"""

from __future__ import annotations

from typing import Optional

from selenium import webdriver
import os
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class YouTubeController:
    def __init__(self) -> None:
        self.driver: Optional[webdriver.Chrome] = None

    def start(self) -> None:
        if self.driver:
            return
        # Try Chrome first (supports overrides via env vars)
        try:
            c_opts = ChromeOptions()
            c_opts.add_argument("--start-maximized")
            c_opts.add_argument("--autoplay-policy=no-user-gesture-required")
            chrome_binary = os.getenv("CHROME_BINARY")
            if chrome_binary:
                c_opts.binary_location = chrome_binary
            chromedriver_path = os.getenv("CHROMEDRIVER") or os.getenv("WEBDRIVER_CHROME")
            if chromedriver_path and os.path.exists(chromedriver_path):
                c_service = ChromeService(chromedriver_path)
            else:
                c_service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=c_service, options=c_opts)
            return
        except WebDriverException:
            # Fallback to Edge if Chrome is not available
            e_opts = EdgeOptions()
            e_opts.add_argument("--start-maximized")
            e_opts.add_argument("--autoplay-policy=no-user-gesture-required")
            edge_binary = os.getenv("EDGE_BINARY")
            if edge_binary:
                try:
                    e_opts.binary_location = edge_binary
                except Exception:
                    pass
            edgedriver_path = os.getenv("EDGEDRIVER") or os.getenv("WEBDRIVER_EDGE")
            if edgedriver_path and os.path.exists(edgedriver_path):
                e_service = EdgeService(edgedriver_path)
            else:
                e_service = EdgeService(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=e_service, options=e_opts)

    def stop(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    def open(self, url: str) -> None:
        if not self.driver:
            self.start()
        assert self.driver
        # Add autoplay/mute hints when opening YouTube watch URLs
        from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

        try:
            p = urlparse(url)
            if p.netloc.endswith("youtube.com") and p.path.startswith("/watch"):
                q = dict(parse_qsl(p.query))
                q.setdefault("autoplay", "1")
                q.setdefault("mute", "1")
                url = urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))
        except Exception:
            pass
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

    def exec_js(self, script: str) -> None:
        self._exec_js(script)

    def skip_ads_tick(self) -> None:
        """Try to skip/accelerate ads; safe to call periodically."""
        js = (
            "(function(){\n"
            "  try {\n"
            "    var close=document.querySelector('.ytp-ad-overlay-close-button'); if(close){close.click();}\n"
            "    var skip=document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button'); if(skip){skip.click();}\n"
            "    var player=document.querySelector('.html5-video-player');\n"
            "    var v=document.querySelector('video');\n"
            "    if(player && player.classList && player.classList.contains('ad-showing') && v){\n"
            "      try{ v.muted=true; }catch(e){}\n"
            "      try{ v.playbackRate = 16.0; }catch(e){}\n"
            "    } else if(v){\n"
            "      if(v.playbackRate && v.playbackRate>1.1){ try{ v.playbackRate = 1.0; }catch(e){} }\n"
            "    }\n"
            "  } catch(e){}\n"
            "})();"
        )
        self._exec_js(js)
