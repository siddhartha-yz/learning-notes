"""Window-manager smoke check using temporary app state; no API calls."""
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import app
from gi.repository import Gdk, Gtk


def settle():
    until = time.monotonic() + 0.7
    while time.monotonic() < until:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(0.01)


def main():
    with tempfile.TemporaryDirectory() as directory, patch.object(app, 'STATE', Path(directory)):
        window = app.Lab()
        try:
            window.show_all(); settle()
            for track in window.tracks:
                window.track_selector.set_active(window.tracks.index(track)); settle()
                minimum, _ = window.get_preferred_size()
                assert minimum.width < 1000 and minimum.height < 700, (minimum.width, minimum.height)
                window.maximize(); settle()
                assert window.get_window().get_state() & Gdk.WindowState.MAXIMIZED
                monitor = window.get_display().get_monitor_at_window(window.get_window())
                area = monitor.get_workarea()
                assert window.get_allocated_height() <= area.height
                assert window.get_allocated_width() <= area.width
                window.window_key(window, SimpleNamespace(keyval=Gdk.KEY_F11)); settle()
                assert window.get_window().get_state() & Gdk.WindowState.FULLSCREEN
                assert window.is_fullscreen
                window.window_key(window, SimpleNamespace(keyval=Gdk.KEY_Escape)); settle()
                assert not window.is_fullscreen
                assert window.get_window().get_state() & Gdk.WindowState.MAXIMIZED
                window.unmaximize(); settle()
                window.resize(1000, 700); settle()
                assert window.get_size().height <= 700
            window.torch_panel.pages.set_current_page(1); settle()
            assert window.get_size().height <= 700
            window.torch_panel.pages.set_current_page(0)
            window.fullscreen_button.emit('clicked'); settle()
            assert window.is_fullscreen
            image = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0,
                        window.get_allocated_width(), window.get_allocated_height())
            image.savev('/tmp/learning-notes-fullscreen.png', 'png', [], [])
            window.fullscreen_button.emit('clicked'); settle()
            assert not window.is_fullscreen
            print('PASS: Linux/PyTorch maximize, F11, Escape, button toggle, 1000x700 resize, both tutorial tabs')
        finally:
            window.session.close(); window.destroy()


if __name__ == '__main__': main()
