"""
Selenium controller stub for YouTube playback automation.

This is optional when using the in-app PyQt WebEngine player, but provided
for workflows that prefer controlling an external browser.
"""

from __future__ import annotations

from typing import Optional

from selenium import webdriver
import os
import shutil
from pathlib import Path
import subprocess
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import time

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class YouTubeController:
    def __init__(self) -> None:
        self.driver: Optional[webdriver.Chrome] = None
        self._proxy: Optional[str] = None
        self._profile_dir: Optional[str] = None
        # Error-recovery state
        self._last_check_ts: float = 0.0
        self._last_reload_ts: float = 0.0
        self._last_video_time: Optional[float] = None
        self._last_video_time_ts: float = 0.0
        self._reload_backoff_s: float = 10.0
        self._reload_backoff_max_s: float = 300.0

    def start(self, proxy: Optional[str] = None, profile_dir: Optional[str] = None) -> None:
        if self.driver:
            return
        # Normalize proxy
        def norm_proxy(p: Optional[str]) -> Optional[str]:
            if not p:
                return None
            p = p.strip()
            if not p:
                return None
            if "://" not in p:
                p = "http://" + p
            return p
        self._proxy = norm_proxy(proxy)
        self._profile_dir = profile_dir.strip() if isinstance(profile_dir, str) else None
        # Project root and drivers folder
        repo_root = Path(__file__).resolve().parent.parent
        drivers_dir = repo_root / "drivers"

        def find_driver(names: list[str]) -> str | None:
            # 1) Env overrides
            for env_name in ("CHROMEDRIVER", "WEBDRIVER_CHROME", "EDGEDRIVER", "WEBDRIVER_EDGE"):
                p = os.getenv(env_name)
                if p and os.path.exists(p):
                    return p
            # 2) drivers/ folder
            for n in names:
                p = drivers_dir / n
                if p.exists():
                    return str(p)
            # 3) PATH
            for n in names:
                p = shutil.which(n)
                if p:
                    return p
            return None

        def find_binary(candidates: list[str], env_name: str | None = None) -> str | None:
            if env_name:
                p = os.getenv(env_name)
                if p and os.path.exists(p):
                    return p
            for p in candidates:
                if os.path.exists(p):
                    return p
            return None

        # Try Chrome first (supports overrides via env vars and local drivers)
        chrome_error: Exception | None = None
        edge_error: Exception | None = None
        try:
            c_opts = ChromeOptions()
            c_opts.add_argument("--start-maximized")
            c_opts.add_argument("--autoplay-policy=no-user-gesture-required")
            c_opts.add_argument("--log-level=3")
            c_opts.add_argument("--disable-logging")
            try:
                c_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
            except Exception:
                pass
            chrome_binary = find_binary([
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ], env_name="CHROME_BINARY")
            if chrome_binary:
                c_opts.binary_location = chrome_binary
            if self._proxy:
                c_opts.add_argument(f"--proxy-server={self._proxy}")
            if self._profile_dir:
                try:
                    os.makedirs(self._profile_dir, exist_ok=True)
                except Exception:
                    pass
                c_opts.add_argument(f"--user-data-dir={self._profile_dir}")

            chromedriver_path = find_driver(["chromedriver.exe", "chromedriver"])
            if chromedriver_path:
                c_service = ChromeService(chromedriver_path, log_output=subprocess.DEVNULL)
            else:
                # Fallback to online manager (requires internet)
                c_service = ChromeService(ChromeDriverManager().install(), log_output=subprocess.DEVNULL)
            self.driver = webdriver.Chrome(service=c_service, options=c_opts)
            return
        except Exception as e:
            chrome_error = e
            # Fallback to Edge if Chrome is not available
            e_opts = EdgeOptions()
            e_opts.add_argument("--start-maximized")
            e_opts.add_argument("--autoplay-policy=no-user-gesture-required")
            e_opts.add_argument("--log-level=3")
            e_opts.add_argument("--disable-logging")
            try:
                e_opts.add_experimental_option("excludeSwitches", ["enable-logging"])
            except Exception:
                pass
            edge_binary = find_binary([
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
            ], env_name="EDGE_BINARY")
            if edge_binary:
                try:
                    e_opts.binary_location = edge_binary
                except Exception:
                    pass
            if self._proxy:
                e_opts.add_argument(f"--proxy-server={self._proxy}")
            if self._profile_dir:
                try:
                    os.makedirs(self._profile_dir, exist_ok=True)
                except Exception:
                    pass
                e_opts.add_argument(f"--user-data-dir={self._profile_dir}")

            edgedriver_path = find_driver(["msedgedriver.exe", "msedgedriver"])
            if edgedriver_path:
                e_service = EdgeService(edgedriver_path, log_output=subprocess.DEVNULL)
            else:
                # Fallback to online manager (requires internet)
                e_service = EdgeService(EdgeChromiumDriverManager().install(), log_output=subprocess.DEVNULL)
            try:
                self.driver = webdriver.Edge(service=e_service, options=e_opts)
                return
            except Exception as e2:
                edge_error = e2
                # Both failed; synthesize helpful message
                hints = (
                    "No local WebDriver found and online download failed. "
                    "Fix by either: (1) placing 'chromedriver.exe' or 'msedgedriver.exe' in the 'drivers/' folder, "
                    "(2) setting CHROMEDRIVER/EDGEDRIVER env vars to local driver paths, or "
                    "(3) enabling internet to let webdriver-manager fetch drivers."
                )
                details = f"ChromeErr={type(chrome_error).__name__}: {chrome_error}; EdgeErr={type(edge_error).__name__}: {edge_error}"
                raise RuntimeError(f"Selenium startup failed. {hints} Details: {details}")

    def stop(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    def open(self, url: str, proxy: Optional[str] = None, profile_dir: Optional[str] = None) -> None:
        # Restart with new proxy/profile if needed
        def norm_proxy(p: Optional[str]) -> Optional[str]:
            if not p:
                return None
            p = p.strip()
            if not p:
                return None
            if "://" not in p:
                p = "http://" + p
            return p
        desired = norm_proxy(proxy)
        desired_profile = profile_dir.strip() if isinstance(profile_dir, str) else None
        if not self.driver:
            self.start(proxy=desired, profile_dir=desired_profile)
        else:
            if (desired != self._proxy) or (desired_profile != self._profile_dir):
                # restart driver to apply changes
                try:
                    self.stop()
                except Exception:
                    pass
                self.start(proxy=desired, profile_dir=desired_profile)
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

    def is_playing(self) -> bool:
        if not self.driver:
            return False
        try:
            return bool(self.driver.execute_script("var v=document.querySelector('video'); return v ? !v.paused : false;"))
        except Exception:
            return False

    def toggle_play_pause(self) -> bool:
        """Toggle playback. Returns True if now playing, False if paused."""
        try:
            if self.is_playing():
                self.pause()
                return False
            else:
                self.play()
                return True
        except Exception:
            return False

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

    def get_title(self) -> str:
        """Return current tab title; strip common suffixes (e.g., ' - YouTube')."""
        if not self.driver:
            return ""
        try:
            title = self.driver.title or ""
            for suf in (" - YouTube", " - YouTube Music"):
                if title.endswith(suf):
                    title = title[: -len(suf)]
                    break
            return title.strip()
        except Exception:
            return ""

    def error_recover_tick(self) -> None:
        """
        Detect common YouTube error overlays and attempt controlled reloads with backoff.
        Also detects stuck playback (no currentTime progress for a while when not paused).
        Safe to call frequently; throttles internally.
        """
        if not self.driver:
            return
        now = time.monotonic()
        if now - self._last_check_ts < 1.0:
            return
        self._last_check_ts = now

        try:
            state = self.driver.execute_script(
                """
                var v=document.querySelector('video');
                var hasErr=!!(document.querySelector('.ytp-error, .ytp-error-content-wrap, ytd-player-error-message-renderer'));
                var txt='';
                if(hasErr){
                   try{ txt=(document.querySelector('.ytp-error-content-wrap')?.innerText||''); }catch(e){}
                }
                return {
                  hasErr: hasErr,
                  t: v? v.currentTime : null,
                  paused: v? v.paused : null,
                  rs: v? v.readyState : 0,
                  errText: txt
                };
                """
            )
        except Exception:
            return

        should_reload = False
        if isinstance(state, dict):
            has_err = bool(state.get('hasErr'))
            t = state.get('t')
            paused = state.get('paused')
            rs = int(state.get('rs') or 0)

            if has_err:
                should_reload = True
            else:
                # Detect stuck playback: no progress for 20s while supposed to be playing
                try:
                    t_f = float(t) if t is not None else None
                except Exception:
                    t_f = None
                if t_f is not None:
                    if self._last_video_time is None:
                        self._last_video_time = t_f
                        self._last_video_time_ts = now
                    else:
                        progressed = (t_f > self._last_video_time + 0.01)
                        if progressed:
                            # Reset backoff on progress
                            self._last_video_time = t_f
                            self._last_video_time_ts = now
                            if now - self._last_reload_ts > 15:
                                self._reload_backoff_s = 10.0
                        else:
                            # No progress; if not paused and data should be available, consider stuck
                            if (paused is False) and (rs >= 2) and (now - self._last_video_time_ts > 20):
                                should_reload = True

        if should_reload:
            if now - self._last_reload_ts >= self._reload_backoff_s:
                try:
                    self.driver.refresh()
                    self._last_reload_ts = now
                    self._reload_backoff_s = min(self._reload_backoff_s * 2.0, self._reload_backoff_max_s)
                except Exception:
                    pass
