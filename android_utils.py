from kivy.utils import platform

if platform == "android":
    from jnius import autoclass
    from android import mActivity
    from android.runnable import run_on_ui_thread

    ActivityInfo = autoclass("android.content.pm.ActivityInfo")
    View = autoclass("android.view.View")
    WindowManager = autoclass("android.view.WindowManager")
    Color = autoclass("android.graphics.Color")
    Build = autoclass("android.os.Build")


def maximize_video():
    if platform == "android":

        @run_on_ui_thread
        def _maximize():
            mActivity.setRequestedOrientation(
                ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
            )

            window = mActivity.getWindow()

            window.addFlags(
                WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS
            )
            window.setNavigationBarColor(Color.TRANSPARENT)
            window.setStatusBarColor(Color.TRANSPARENT)

            if Build.VERSION.SDK_INT >= 28:
                attributes = window.getAttributes()
                attributes.layoutInDisplayCutoutMode = 1
                window.setAttributes(attributes)

            decor_view = window.getDecorView()
            decor_view.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )

        _maximize()


def minimize_video():
    if platform == "android":

        @run_on_ui_thread
        def _minimize():
            mActivity.setRequestedOrientation(
                ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            )

            window = mActivity.getWindow()

            window.setNavigationBarColor(Color.BLACK)
            window.setStatusBarColor(Color.BLACK)

            if Build.VERSION.SDK_INT >= 28:
                attributes = window.getAttributes()
                attributes.layoutInDisplayCutoutMode = 0
                window.setAttributes(attributes)

            decor_view = window.getDecorView()
            decor_view.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)

        _minimize()
