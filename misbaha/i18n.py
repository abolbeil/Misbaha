# -*- coding: utf-8 -*-
"""Interface language. Arabic is the source language; EN maps it to English.

Adhkar, virtues and sources are always shown in Arabic.
To add a language: add a dict like EN, register it in LANGS and TABLES.
"""

from PySide6.QtCore import Qt

SETTINGS = {"ui_lang": "en", "arabic_digits": False}   # re-pointed to State.settings at start-up

APP_TITLE = "مِسبحة"

HINT_AR = ("على الودجت: نقرة يمين = القائمة، اسحب لتحريكه، Ctrl + العجلة = الشفافية.<br>"
           "«إيقاف العدّ مؤقتًا» يعيد للأزرار الجانبية وظيفتها الأصلية.")
STATS_HEAD_AR = ("مجموع اليوم: <b>%s</b>  &nbsp;&nbsp;•&nbsp;&nbsp; أيام متتالية: <b>%s</b>"
                 "  &nbsp;&nbsp;•&nbsp;&nbsp; كل الأيام: <b>%s</b>")
WELCOME_AR = ("المِسبحة جاهزة — اضغط زر الفأرة الجانبي الأمامي للعدّ دون ترك عملك.\n"
              "انقر بالزر الأيمن على الودجت لاختيار وردك.")
ADMIN_HINT_AR = ("البرنامج الذي تعمل عليه الآن يعمل كمسؤول، لذلك لا تصل إليه ضغطات أزرار الفأرة. "
                 "اختر «إعادة التشغيل كمسؤول» من القائمة، أو استخدم اختصارات لوحة المفاتيح.")
ELEVATE_AR = ("ستُغلق المِسبحة وتُفتح كمسؤول (سيطلب Windows التأكيد).\n"
              "اختصارات لوحة المفاتيح تعمل دون ذلك.\n"
              "للاستخدام الدائم كمسؤول يُفضَّل تثبيت المِسبحة في مجلد Program Files.\n\nمتابعة؟")
WELCOME_CARD_AR = ("<b>أهلًا بك في المِسبحة</b><br>اضغط أزرار الفأرة الجانبية الآن — ستظهر علامة ✔ "
                   "بجانب كل زر يصل إلى المِسبحة. كل ضغطة تُحتسب أيضًا.")
HELP_AR = (
    "<h3>طرق العدّ</h3>"
    "• أزرار الفأرة الجانبية (X1 / X2) — تعمل من داخل أي برنامج دون تحريك الفأرة.<br>"
    "• يمكن أيضًا ربط زر العجلة الأوسط أو إمالة العجلة يمينًا/يسارًا من الإعدادات.<br>"
    "• اختصارات لوحة المفاتيح: <b>+١</b> = <span dir='ltr'>%s</span> ، <b>التالي</b> = <span dir='ltr'>%s</span><br>"
    "• على الودجت: نقرة يمين = القائمة، اسحب لتحريكه، Ctrl + العجلة = الشفافية.<br>"
    "<h3>وضع تمرير النقرات</h3>"
    "عندما يكون مفعّلًا لا يعترض الودجت الفأرة أبدًا. <b>اضغط Ctrl مع الوقوف على الودجت</b> لاستخدامه مؤقتًا "
    "(سحب، قائمة)، أو استخدم أيقونة شريط المهام.<br>"
    "<h3>إذا توقفت الأزرار الجانبية عن العدّ</h3>"
    "• من القائمة اختر <b>«إعادة تشغيل التقاط أزرار الفأرة»</b>.<br>"
    "• إذا كان Revit أو البرنامج الذي تعمل عليه يعمل <b>كمسؤول</b>، اختر <b>«إعادة التشغيل كمسؤول»</b>. "
    "اختصارات لوحة المفاتيح تعمل في الحالتين.<br>"
    "<h3>عندك برنامج آخر للفأرة أو للاختصارات؟</h3>"
    "برامج مثل <b>Logitech Options+ / G HUB</b> أو <b>Razer Synapse</b> أو <b>X-Mouse Button Control</b> "
    "قد تلتقط الأزرار الجانبية قبل المسبحة. الحل: اجعل الزر الجانبي في ذلك البرنامج <b>يرسل ضغطة مفاتيح</b>:<br>"
    "&nbsp;&nbsp;• زيادة +١ ← <span dir='ltr'><b>%s</b></span><br>"
    "&nbsp;&nbsp;• الذكر التالي ← <span dir='ltr'><b>%s</b></span><br>"
    "مثال AutoHotkey: <span dir='ltr'><code>XButton2::Send %s</code></span> و "
    "<span dir='ltr'><code>XButton1::Send %s</code></span>")
HELP_EN = (
    "<h3>Ways to count</h3>"
    "• Mouse side buttons (X1 / X2) — work inside any program, without moving the mouse.<br>"
    "• The middle (wheel) button and wheel tilt left/right can also be bound in Settings.<br>"
    "• Keyboard shortcuts: <b>+1</b> = %s, <b>next</b> = %s<br>"
    "• On the widget: right-click = menu, drag = move, Ctrl + wheel = opacity.<br>"
    "<h3>Click-through mode</h3>"
    "When it is on, the widget never blocks the mouse. <b>Hold Ctrl while the pointer is over the widget</b> "
    "to use it for a moment (drag, menu), or use the tray icon.<br>"
    "<h3>If the side buttons stop counting</h3>"
    "• Choose <b>“Restart mouse-button capture”</b> from the menu.<br>"
    "• If Revit (or the program you work in) runs <b>as Administrator</b>, choose "
    "<b>“Restart as administrator”</b>. Keyboard shortcuts work either way.<br>"
    "<h3>Do you use another mouse or hotkey program?</h3>"
    "Programs such as <b>Logitech Options+ / G HUB</b>, <b>Razer Synapse</b> or <b>X-Mouse Button Control</b> "
    "can catch the side buttons first. Solution: set the side button in that program to "
    "<b>send a keystroke</b>:<br>"
    "&nbsp;&nbsp;• count +1 → <b>%s</b><br>"
    "&nbsp;&nbsp;• next dhikr → <b>%s</b><br>"
    "AutoHotkey example: <code>XButton2::Send %s</code> and <code>XButton1::Send %s</code>")
ABOUT_AR = ("✔ مجاني ومفتوح المصدر.<br>✔ يعمل دون إنترنت. الاتصال الوحيد: التحقق من وجود إصدار جديد على GitHub "
            "مرة يوميًا (يمكن إيقافه من الإعدادات) — دون إرسال أي بيانات شخصية.<br>"
            "✔ بدون حساب، بدون إعلانات، بدون تتبّع.<br>✔ عدّاداتك وإعداداتك محفوظة على هذا الجهاز فقط:<br>"
            "<span dir='ltr'>%s</span><br>✔ لا يقرأ البرنامج لوحة المفاتيح أبدًا — الاختصارات تُسجَّل لدى Windows مباشرة.")
ABOUT_EN = ("✔ Free and open source.<br>✔ Works offline. Its only connection is a once-a-day check of GitHub for a "
            "new version (can be turned off in Settings) — no personal data is sent.<br>"
            "✔ No account, no ads, no tracking.<br>✔ Your counts and settings are stored only on this PC:<br>%s<br>"
            "✔ Misbaha never reads your keyboard — shortcuts are registered directly with Windows.")

EN = {
    APP_TITLE: "Misbaha",
    # actions
    "زيادة +١": "Count +1", "الذكر التالي": "Next dhikr", "الذكر السابق": "Previous dhikr",
    "إنقاص −١": "Undo −1", "لا شيء": "Nothing",
    "لا شيء (موصى به)": "Nothing (recommended)", "نقرة واحدة = +١": "Single click = +1",
    "نقرة مزدوجة = +١": "Double-click = +1",
    # themes
    "زمردي وذهبي": "Emerald and Gold", "أزرق ملكي": "Royal Blue", "كحلي وذهبي": "Navy and Gold",
    "أسود وذهبي": "Black and Gold", "أسود وفضي": "Black and Silver", "أسود وأزرق": "Black and Blue",
    "عنابي وذهبي": "Burgundy and Gold", "بنفسجي": "Purple", "فيروزي": "Turquoise",
    "فاتح (عاجي)": "Light (Ivory)", "مخصص…": "Custom…",
    # categories
    "الاستغفار": "Istighfar", "التسبيح والتحميد": "Tasbih and Tahmid", "التهليل والحوقلة": "Tahlil and Hawqala",
    "الصلاة على النبي ﷺ": "Salawat on the Prophet ﷺ", "أدعية وأذكار جامعة": "Duas and General Adhkar",
    "أذكاري الخاصة": "My Custom Adhkar",
    # input errors
    "تعذّر تشغيل التقاط أزرار الفأرة: %s": "Could not start mouse-button capture: %s",
    "تعذّر تسجيل الاختصار %s: %s": "Could not register shortcut %s: %s",
    "الاختصار مستخدم من برنامج آخر": "it is already used by another program",
    "اختصار غير صالح": "invalid shortcut",
    # widget
    "⏸ موقوف   ": "⏸ Paused   ", "الشفافية: %s%%": "Opacity: %s%%",
    # library dialog
    "مكتبة الأذكار — اختر وردك": "Adhkar Library — build your wird",
    "المكتبة  (انقر مرتين للإضافة)": "Library  (double-click to add)",
    "الذكر": "Dhikr", "العدد": "Count", "الهدف": "Goal", "اليوم": "Today",
    "اختر ذكرًا لعرض فضله ومصدره": "Select a dhikr to see its virtue and source",
    "إضافة ذكر خاص": "Add a custom dhikr", "اكتب الذكر هنا…": "Type the dhikr here…",
    "إضافة للمكتبة": "Add to library", "حذف الخاص المحدد": "Delete selected custom",
    "⟵ إضافة": "Add ⟶", "وِردي وأهدافي": "My wird and goals",
    "▲ أعلى": "▲ Up", "▼ أسفل": "▼ Down", "✕ حذف": "✕ Remove", "مسح الكل": "Clear all",
    "قوالب جاهزة:": "Presets:", "تسبيح الصلاة": "After-prayer tasbih", "ورد الاستغفار": "Istighfar wird",
    "ورد الصلاة على النبي": "Salawat wird", "ورد يومي شامل": "Full daily wird",
    "حفظ وبدء الورد": "Save and start", "إلغاء": "Cancel", "ذكر خاص": "Custom dhikr",
    "اختر ذكرًا من «أذكاري الخاصة» لحذفه.": "Select a dhikr under “My Custom Adhkar” to delete it.",
    "أضف ذكرًا واحدًا على الأقل إلى وردك.": "Add at least one dhikr to your wird.",
    "هذا الذكر موجود بالفعل في المكتبة.": "This dhikr is already in the library.",
    # settings
    "الإعدادات": "Settings",
    "زر الفأرة الجانبي الخلفي (X1 / Back):": "Mouse back side button (X1):",
    "زر الفأرة الجانبي الأمامي (X2 / Forward):": "Mouse forward side button (X2):",
    "زر العجلة الأوسط (يُستخدم للتحريك في Revit):": "Middle (wheel) button — pans in Revit:",
    "إمالة العجلة لليسار:": "Wheel tilt left:", "إمالة العجلة لليمين:": "Wheel tilt right:",
    "منع الأزرار المربوطة من الوصول للبرامج الأخرى (مثل «رجوع» في المتصفح)":
        "Block bound buttons from reaching other apps (e.g. browser “Back”)",
    "تفعيل اختصارات لوحة المفاتيح العامة": "Enable global keyboard shortcuts",
    "اختصار الزيادة:": "Count +1 shortcut:", "اختصار الذكر التالي:": "Next dhikr shortcut:",
    "اختصار الإنقاص −١:": "Undo −1 shortcut:",
    "انقر ثم اضغط الاختصار…": "Click, then press the shortcut…",
    "اضغط الاختصار الآن (Backspace للمسح)": "Press the shortcut now (Backspace clears)",
    "مسح": "Clear",
    "الاختصارات تُسجَّل لدى Windows مباشرة وتعمل حتى في البرامج التي تعمل كمسؤول. "
    "يُفضَّل استخدام Ctrl + Alt مع مفتاح خاص (PgUp، PgDn، Space، F9…).":
        "Shortcuts are registered directly with Windows and also work in programs running as administrator. "
        "Prefer Ctrl + Alt with a special key (PgUp, PgDn, Space, F9…).",
    HINT_AR: ("On the widget: right-click = menu, drag = move, Ctrl + wheel = opacity.<br>"
              "“Pause counting” gives the side buttons back their normal function."),
    "العدّ": "Counting",
    "العدّ بعجلة الفأرة عند الوقوف على الودجت (الإيقاف أكثر أمانًا)":
        "Count with the mouse wheel over the widget (off = safer)",
    "النقر على الودجت:": "Left-click on the widget:",
    "الانتقال تلقائيًا للذكر التالي عند بلوغ الهدف": "Move to the next dhikr automatically when the goal is reached",
    "إعادة الورد من البداية بعد إتمامه": "Restart the wird after completing it",
    "تصفير العداد مع بداية كل يوم": "Reset counters every new day",
    "التحكم": "Controls", "اللغة / Language:": "Language:",
    "لون الواجهة:": "Theme:", "لون الخلفية": "Background colour", "لون التمييز": "Accent colour",
    "ألوان مخصصة:": "Custom colours:", "خط الذكر:": "Dhikr font:",
    "استخدام الأرقام العربية (١٢٣)": "Use Arabic-Indic digits (١٢٣)",
    "الوضع المصغّر (الرقم فقط)": "Mini mode (number only)",
    "الودجت": "Widget",
    "تمرير النقرات عبر الودجت (لا يعترض الفأرة — اضغط Ctrl فوقه لاستخدامه)":
        "Click-through widget (never blocks the mouse — hold Ctrl over it to use it)",
    "إخفاء الودجت فوق البرامج بملء الشاشة (فيديو، عروض تقديمية)":
        "Hide the widget over full-screen apps (videos, slideshows)",
    "الشفافية:": "Opacity:", "الحجم:": "Size:", "المظهر": "Appearance",
    "تعتيم الودجت تلقائيًا عند عدم الاستخدام": "Auto-dim the widget when not in use",
    "الشفافية عند الخمول:": "Idle opacity:", "التعتيم بعد:": "Dim after:", " ثانية": " s",
    "تلميح: Ctrl + عجلة الفأرة على الودجت لتغيير الشفافية بسرعة.":
        "Tip: Ctrl + mouse wheel on the widget changes opacity quickly.",
    "تذكيري بذكر الله": "Remind me to remember Allah", " دقيقة": " min",
    "ذكّرني إذا لم أذكر منذ:": "Remind me if idle for:", "أوقات الهدوء (بدون تذكير)": "Quiet hours (no reminders)",
    "من:": "From:", "إلى:": "To:", "إشعار عند بلوغ الهدف": "Notify when a goal is reached",
    "تجربة إشعار الآن": "Test notification now", "التذكير": "Reminders",
    "لا تذكير أثناء غيابك عن الجهاز أو أثناء البرامج بملء الشاشة.":
        "No reminders while you are away from the PC or a full-screen app is in front.",
    "التشغيل مع بدء Windows": "Start with Windows",
    "فتح مجلد البيانات": "Open data folder", "حالة الالتقاط": "Capture status",
    "التقاط أزرار الفأرة: %s": "Mouse-button capture: %s", "يعمل": "active", "متوقف": "stopped",
    "غير متاح على هذا النظام": "not available on this system",
    "الاختصارات: %s": "Shortcuts: %s", "مسجّلة": "registered", "معطّلة": "disabled",
    "يعمل كمسؤول: %s": "Running as administrator: %s", "نعم": "yes", "لا": "no",
    "ملف البيانات:\n%s\n\nسجل الأخطاء:\n%s\n\nالإصدار %s": "Data file:\n%s\n\nError log:\n%s\n\nVersion %s",
    "النظام": "System", "حفظ": "Save", "اختر اللون": "Choose colour",
    # stats
    "إحصائياتي": "My statistics",
    STATS_HEAD_AR: ("Today: <b>%s</b>  &nbsp;&nbsp;•&nbsp;&nbsp; Day streak: <b>%s</b>"
                    "  &nbsp;&nbsp;•&nbsp;&nbsp; All time: <b>%s</b>"),
    "أذكار اليوم:": "Today's adhkar:", "(ذكر محذوف)": "(deleted dhikr)", "آخر ٧ أيام:": "Last 7 days:",
    "المجموع": "Total", "التاريخ": "Date", "الاثنين": "Monday", "الثلاثاء": "Tuesday", "الأربعاء": "Wednesday",
    "الخميس": "Thursday", "الجمعة": "Friday", "السبت": "Saturday", "الأحد": "Sunday", "إغلاق": "Close",
    # help / about
    "مساعدة ونصائح": "Help & tips", HELP_AR: HELP_EN, "عن المِسبحة": "About Misbaha", ABOUT_AR: ABOUT_EN,
    # app / menu / notifications
    "بسم الله": "Bismillah",
    WELCOME_AR: "Misbaha is ready — press the mouse forward side button to count without leaving your work.\n"
                "Right-click the widget to choose your wird.",
    ADMIN_HINT_AR: "The program you are working in runs as administrator, so mouse-button presses can't reach "
                   "Misbaha there. Choose “Restart as administrator” from the menu, or use the keyboard shortcuts.",
    ELEVATE_AR: "Misbaha will close and reopen as administrator (Windows will ask you to confirm).\n"
                "Keyboard shortcuts already work without this.\n"
                "For regular use as administrator, install Misbaha in the Program Files folder.\n\nContinue?",
    "تراجع عن التصفير": "Undo reset",
    WELCOME_CARD_AR: "<b>Welcome to Misbaha</b><br>Press your mouse's side buttons now — a ✔ appears next to each "
                     "button that reaches Misbaha. Each press also counts.",
    "مرحبًا بك في المِسبحة": "Welcome to Misbaha",
    "الزر الجانبي الأمامي (X2)": "Forward side button (X2)", "الزر الجانبي الخلفي (X1)": "Back side button (X1)",
    "لم يُكتشف أي زر؟ قد يكون برنامج الفأرة (Logitech، Razer…) يلتقطه. "
    "افتح «مساعدة ونصائح»، أو استخدم اختصارات لوحة المفاتيح.":
        "No button detected? Mouse software (Logitech, Razer…) may be catching it. "
        "Open “Help & tips”, or use the keyboard shortcuts.",
    "اختيار وردي…": "Choose my wird…",
    "لوحة المفاتيح: %s = زيادة +١ ، %s = الذكر التالي": "Keyboard: %s = count +1, %s = next dhikr", "ابدأ": "Start",
    "🖱  اختبار أزرار الفأرة…": "🖱  Test mouse buttons…",
    "تعديل الخاص المحدد": "Edit selected custom", "حفظ التعديل": "Save changes",
    "التحقق من وجود إصدار جديد على GitHub مرة يوميًا": "Check GitHub for a new version once a day",
    "تحقق الآن": "Check now", "جارٍ التحقق…": "Checking…",
    "يفتح صفحة الإصدار فقط — لا يُنزَّل أو يُثبَّت شيء تلقائيًا، ولا تُرسل أي بيانات شخصية.":
        "It only opens the release page — nothing is downloaded or installed automatically, and no personal data is sent.",
    "التحقق من التحديثات متاح في الإصدارات الرسمية فقط.": "Update checks are available in official release builds only.",
    "⬆  إصدار جديد متاح: %s — فتح صفحة التنزيل": "⬆  New version %s available — open download page",
    "إصدار جديد متاح: %s — من القائمة اختر «فتح صفحة التنزيل».":
        "New version %s is available — choose “open download page” from the menu.",
    "تعذّر التحقق (لا يوجد اتصال أو لم تُنشر إصدارات بعد).":
        "Couldn't check (no connection, or no release published yet).",
    "لديك أحدث إصدار (%s).": "You have the latest version (%s).",
    "المِسبحة ما زالت تعمل — انقر أيقونة شريط المهام لإظهارها.":
        "Misbaha is still running — click the tray icon to show it.",
    "تنبيه": "Warning", "تمت إعادة تشغيل التقاط أزرار الفأرة.": "Mouse-button capture restarted.",
    "الذكر التالي  ⟵": "Next dhikr", "الذكر السابق  ⟶": "Previous dhikr", "إنقاص واحد  −١": "Undo −1",
    "تصفير الذكر الحالي": "Reset current dhikr", "تصفير الورد كله…": "Reset whole wird…",
    "📿  مكتبة الأذكار / وردي…": "📿  Adhkar library / my wird…", "📊  إحصائياتي…": "📊  My statistics…",
    "⚙  الإعدادات…": "⚙  Settings…", "❓  مساعدة ونصائح…": "❓  Help & tips…", "ℹ  عن المِسبحة…": "ℹ  About Misbaha…",
    "🎨  لون الواجهة": "🎨  Theme", "🔅  الشفافية": "🔅  Opacity",
    "إيقاف العدّ مؤقتًا": "Pause counting", "الوضع المصغّر": "Mini mode",
    "تمرير النقرات عبر الودجت": "Click-through widget", "إخفاء الودجت": "Hide widget",
    "إظهار الودجت": "Show widget", "إعادة تشغيل التقاط أزرار الفأرة": "Restart mouse-button capture",
    "إعادة التشغيل كمسؤول": "Restart as administrator",
    "خروج": "Exit",
    "ما شاء الله تبارك الله 🌿": "Masha'Allah 🌿",
    "أتممتَ وردك كاملًا، تقبّل الله منك.": "You completed your whole wird — may Allah accept it.",
    "تقبّل الله": "May Allah accept", "أتممت «%s» %s مرة": "Completed “%s” × %s",
    "تصفير عدّادات الورد كله؟\n(الإحصائيات لا تُحذف)": "Reset all wird counters?\n(Statistics are kept)",
    "الودجت الآن لا يعترض الفأرة. اضغط Ctrl فوقه لاستخدامه، أو استخدم أيقونة شريط المهام.":
        "The widget now ignores the mouse. Hold Ctrl over it to use it, or use the tray icon.",
    "  (باقٍ %s)": "  (%s left)", "اذكر الله 🤍": "Remember Allah 🤍",
    "المِسبحة تعمل بالفعل (انظر أيقونة شريط المهام).": "Misbaha is already running (see the tray icon).",
    "المِسبحة تعمل بالفعل — تم إظهار الودجت.": "Misbaha is already running — the widget has been shown.",
    "تعذّر حفظ البيانات: %s": "Could not save your data: %s",
}

LANGS = [("en", "English"), ("ar", "العربية")]
TABLES = {"en": EN, "ar": None}

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def tr(s):
    """Translate an interface string (Arabic source -> current language)."""
    table = TABLES.get(SETTINGS.get("ui_lang", "en"))
    return table.get(s, s) if table else s


def is_rtl():
    return SETTINGS.get("ui_lang", "en") == "ar"


def ui_dir():
    return Qt.RightToLeft if is_rtl() else Qt.LeftToRight


def ar(n):
    return str(n).translate(AR_DIGITS)


def fmt(n):
    """Number in the chosen digit style (5/100 or ٥/١٠٠)."""
    return ar(n) if SETTINGS.get("arabic_digits") else str(n)


def num_dir():
    return Qt.RightToLeft if SETTINGS.get("arabic_digits") else Qt.LeftToRight
