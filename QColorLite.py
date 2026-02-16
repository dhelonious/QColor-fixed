import sublime
import sublime_plugin
import os
import subprocess
from datetime import datetime
from .lib.qutils import QColorUtils

# GLOBALS
APPNAME = "QColorLite"
VERSION = "1.1.0"
SETTINGSFILE = "QColorLite.sublime-settings"
CONF_KEY = "q_color"


def GenPhantomHTML(color, phantom_shape='circle'):
    style = """
        *       {{ background-color:transparent; border-width:0; margin:0; padding:0; }}
        html    {{ background-color:transparent;  }}
        body    {{ font-size: inherit; border-color: inherit; display:block; line-height: 1em; }}
        .circle {{ border-radius: 0.5em; }}
        div     {{ border: 0.05rem solid; border-color: color({0} l(+90%) s(0%) a(0.15));
                     border-radius: 0.0em; display:block; text-decoration:none; padding:-0px;
                     width: 0.95rem; height:0.95rem; margin-top: 0.01rem; background-color:{0}; }}
        img     {{ width: inherit; height: inherit; display:inline; position: relative; }}
    """
    content = '<div class="{0}"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="></div>'  # noqa
    html = '<body id="qcolor_phantom"><style>{0}</style>{1}</body>'
    clsname = phantom_shape.lower()
    return html.format(style.format(color), content.format(clsname))


class QColor(sublime_plugin.ViewEventListener):
    key_conf = CONF_KEY
    key_ctrl = 'phantoms_enabled'

    def __init__(self, view):
        self.view = view
        self.view.QColor = self
        self.settings = sublime.load_settings(SETTINGSFILE)
        self.enabled = self.settings.get("_enabled")
        self.set_conf_change()
        self.on_conf_change()

    def isEnabled(self):
        """ Returns True if the full plugin is enabled. """
        if not self.enabled: return False
        return self.settings.get(self.key_ctrl, False)

    def start(self):
        # Load Settings
        self.phantom_shape = self.settings.get('phantom_shape', 'circle')
        self.show_on_minimap = self.settings.get('show_on_minimap', True)
        self.underline_style = self.settings.get('underline_style', 'stippled')
        self.underline_color = self.settings.get('underline_color', 'purple')
        # Util settings
        named_colors = self.settings.get('named_colors', False)
        hsl_precision = self.settings.get('hsl_precision', True)
        hex_upper = self.settings.get('hex_upper_case', False)
        QColorUtils.set_conf(hsl_precision, hex_upper, named_colors)
        # Restart Binds
        self.pset = sublime.PhantomSet(self.view, self.key_conf)
        self.set_view_change()
        self.on_view_change()

    # File Conf Handlers

    def on_conf_change(self):
        self.start()

    def set_conf_change(self):
        self.clear_conf_change()
        key_id = "{0}_{1}".format(self.key_conf, self.view.id())
        self.settings.add_on_change(key_id, self.on_conf_change)

    def clear_conf_change(self):
        key_id = "{0}_{1}".format(self.key_conf, self.view.id())
        self.settings.clear_on_change(key_id)

    # View Conf Handlers

    def on_view_change(self):
        self.show_phantoms()

    def set_view_change(self):
        self.clear_view_change()
        key_id = "{0}_{1}".format(self.key_conf, self.view.id())
        self.view.settings().add_on_change(key_id, self.on_view_change)

    def clear_view_change(self):
        key_id = "{0}_{1}".format(self.key_conf, self.view.id())
        self.view.settings().clear_on_change(key_id)

    # Functions

    def getColorRegions(self):
        c_regions = []
        for key, value in QColorUtils.regex.items():
            c_regions += self.view.find_all(value, sublime.IGNORECASE)
        return c_regions

    def phantom_show(self, view, reg):
        selected = view.substr(reg).strip()
        view.add_phantom(self.key_conf,
            sublime.Region(reg.b, reg.b),
            GenPhantomHTML(selected, self.phantom_shape),
            sublime.LAYOUT_INLINE,
        )

    def show_phantoms(self, only_regions=False):
        self.view.erase_regions(self.key_conf)
        self.view.erase_phantoms(self.key_conf)
        if not self.isEnabled():
            return False
        c_regions = self.getColorRegions()
        underline_color = self.get_region_underline_color()
        flags = self.get_region_flags()
        self.view.add_regions(self.key_conf, c_regions, underline_color, '', flags)
        if not only_regions:
            for reg in c_regions:
                self.phantom_show(self.view, reg)

    def get_region_underline_color(self):
        if self.underline_color == 'red': return 'region.redish'
        elif self.underline_color == 'orange': return 'region.orangish'
        elif self.underline_color == 'yellow': return 'region.yellowish'
        elif self.underline_color == 'green': return 'region.greenish'
        elif self.underline_color == 'blue': return 'region.bluish'
        elif self.underline_color == 'pink': return 'region.pinkish'
        elif self.underline_color == 'black': return 'region.blackish'
        else: return 'region.purplish'

    def get_region_flags(self):
        # Make sure the underline style is one we understand
        style = self.underline_style.lower()
        flags = sublime.DRAW_NO_FILL      # Disable filling the regions, leaving only the outline.
        flags |= sublime.DRAW_NO_OUTLINE  # Disable drawing the outline of the regions.
        # flags |= sublime.PERSISTENT       # Save the regions in the session.
        flags |= sublime.DRAW_SOLID_UNDERLINE if style == 'solid' else 0
        flags |= sublime.DRAW_STIPPLED_UNDERLINE if style == 'stippled' else 0
        flags |= sublime.HIDE_ON_MINIMAP if not self.show_on_minimap else 0
        return flags

    def find_region(self, position):
        regions = self.view.get_regions(self.key_conf)
        for creg in regions:
            if creg.contains(position):
                return creg
        return None


class QColorVersion(sublime_plugin.ApplicationCommand):
    
    def time(self):
        return datetime.now().strftime("%H:%M:%S")

    def get_msg(self):
        return "{0} {1}".format(APPNAME,VERSION)

    def run(self):
        for win in sublime.windows():
            win.status_message(self.get_msg())

    def description(self):
        return self.get_msg()

    def is_enabled(self):
        return False


class QColorEnabled(sublime_plugin.ApplicationCommand):
    key_conf = CONF_KEY
    key_ctrl = '_enabled'

    def __init__(self):
        self.settings = sublime.load_settings(SETTINGSFILE)

    def run(self, toggle=True):
        if toggle:
            value = self.settings.get(self.key_ctrl, False)
            self.settings.set(self.key_ctrl, not value)
            sublime.save_settings(SETTINGSFILE)

    def description(self):
        return ""

    def is_checked(self):
        return self.settings.get(self.key_ctrl, False)


class QColorShow(sublime_plugin.ApplicationCommand):
    key_conf = CONF_KEY
    key_ctrl = 'phantoms_enabled'

    def __init__(self):
        self.settings = sublime.load_settings(SETTINGSFILE)

    def active_view(self):
        return sublime.active_window().active_view()

    def run(self, show=None):
        value = self.settings.get(self.key_ctrl, False)
        newvalue = show if show is not None else not value
        self.settings.set(self.key_ctrl, newvalue)
        sublime.save_settings(SETTINGSFILE)

    def description(self):
        return ""

    def is_checked(self):
        return self.settings.get(self.key_ctrl, False)

    def is_enabled(self):
        return self.settings.get("_enabled")

    def is_visible(self):
        return True


class QColorConverter(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.settings = sublime.load_settings(SETTINGSFILE)
        self.view = view

    def description(self):
        return ""

    def is_enabled(self):
        return self.settings.get("_enabled") and self.find_region() is not None

    def is_visible(self):
        return True

    def find_region(self):
        sel = self.view.sel()
        region = sel[0]
        regions = self.view.get_regions(CONF_KEY)
        for creg in regions:
            if creg.contains(region):
                return creg
        return None

    def run(self, edit, mode=None):
        region = self.find_region()
        if not region:
            return

        color = self.view.substr(region).strip()
        converter = QColorUtils().parse(color)

        if converter.in_mode:
            sel = self.view.sel()
            sel.clear()
            sel.add(region)
            ncolor = converter.get(mode)
            print("QColorLite {} to {}: {} -> {}".format(
                converter.in_mode, mode, color, ncolor
            ))
            self.view.replace(edit, region, ncolor)
        else:
            print("QColorLite: '{color}' is not a supported color")
