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
            window = mActivity.getWindow()
            decor_view = window.getDecorView()

            if Build.VERSION.SDK_INT >= 35:
                decor_view.setOnApplyWindowInsetsListener(None)
            
            mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE)

            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
            window.setNavigationBarColor(Color.TRANSPARENT)
            window.setStatusBarColor(Color.TRANSPARENT)

            if Build.VERSION.SDK_INT >= 28:
                attributes = window.getAttributes()
                attributes.layoutInDisplayCutoutMode = 1
                window.setAttributes(attributes)

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
    if platform == "android":
        listener_ref = None
        if Build.VERSION.SDK_INT >= 35:
            try:
                from carbonkivy.utils import _global_listener
                listener_ref = _global_listener
            except ImportError:
                pass

        @run_on_ui_thread
        def _minimize():
            window = mActivity.getWindow()
            decor_view = window.getDecorView()

            mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED)

            if Build.VERSION.SDK_INT >= 28:
                attributes = window.getAttributes()
                attributes.layoutInDisplayCutoutMode = 0
                window.setAttributes(attributes)

            decor_view.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE)

            if Build.VERSION.SDK_INT >= 35 and listener_ref is not None:
                decor_view.setOnApplyWindowInsetsListener(listener_ref)
                decor_view.requestApplyInsets()
            else:
                window.setNavigationBarColor(Color.BLACK)
                window.setStatusBarColor(Color.BLACK)

        _minimize()
