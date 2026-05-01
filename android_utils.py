from kivy.utils import platform

if platform == "android":
    from jnius import autoclass
    from android import mActivity
    from android.runnable import run_on_ui_thread

    ActivityInfo = autoclass("android.content.pm.ActivityInfo")
    View = autoclass("android.view.View")


def maximize_video():
    """Forces landscape orientation and hides system UI (Immersive Mode)."""
    if platform == "android":

        @run_on_ui_thread
        def _maximize():
            mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE)

            window = mActivity.getWindow()
            decor_view = window.getDecorView()
            decor_view.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )

        _maximize()


def minimize_video():
    """Restores portrait/sensor orientation and shows system UI."""
    if platform == "android":

        @run_on_ui_thread
        def _minimize():
            mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED)

            window = mActivity.getWindow()
            decor_view = window.getDecorView()
            decor_view.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)

        _minimize()