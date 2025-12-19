"""Утилиты для уведомлений и обратной связи."""
from kivymd.uix.snackbar import Snackbar
from kivy.metrics import dp
from kivy.utils import platform


def show_success(message: str):
    """Показывает уведомление об успешном действии."""
    Snackbar(
        text=message,
        snackbar_x="10dp",
        snackbar_y="10dp",
        size_hint_x=0.9,
        bg_color=(0.2, 0.7, 0.3, 1),  # Зеленый
        duration=2
    ).open()


def show_info(message: str):
    """Показывает информационное уведомление."""
    Snackbar(
        text=message,
        snackbar_x="10dp",
        snackbar_y="10dp",
        size_hint_x=0.9,
        bg_color=(0.2, 0.6, 0.8, 1),  # Синий
        duration=2
    ).open()


def show_error(message: str):
    """Показывает уведомление об ошибке."""
    Snackbar(
        text=message,
        snackbar_x="10dp",
        snackbar_y="10dp",
        size_hint_x=0.9,
        bg_color=(0.9, 0.3, 0.2, 1),  # Красный
        duration=3
    ).open()


def haptic_feedback():
    """Простой виброотклик для мобильных устройств."""
    if platform == 'android':
        try:
            from jnius import autoclass
            vibrator = autoclass('android.os.Vibrator')
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            vibrator_service = context.getSystemService(context.VIBRATOR_SERVICE)
            if vibrator_service:
                vibrator_service.vibrate(50)  # 50ms
        except Exception:
            pass
    elif platform == 'ios':
        # Для iOS можно использовать pyobjus
        pass


def set_status_bar_color(color_hex: str = "#6200EE"):
    """Устанавливает цвет статус бара для Android."""
    if platform == 'android':
        try:
            from android.runnable import run_on_ui_thread
            from jnius import autoclass
            
            @run_on_ui_thread
            def _set_color():
                Color = autoclass('android.graphics.Color')
                WindowManager = autoclass('android.view.WindowManager$LayoutParams')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                window = activity.getWindow()
                window.addFlags(WindowManager.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                window.setStatusBarColor(Color.parseColor(color_hex))
            
            _set_color()
        except Exception:
            pass

