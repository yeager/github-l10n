"""Main GTK4/Adwaita application for GitHub Translation Stats."""

import gettext
import locale
import os
import sys
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from github_l10n.api import GitHubClient, L10N_PATTERNS

# i18n
APP_ID = "se.danielnylander.github-l10n"
LOCALE_DIR = str(Path(__file__).parent.parent.parent / "po")
if not os.path.isdir(LOCALE_DIR):
    LOCALE_DIR = "/usr/share/locale"
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
gettext.bindtextdomain("github-l10n", LOCALE_DIR)
gettext.textdomain("github-l10n")
_ = gettext.gettext

LANGUAGES = sorted(L10N_PATTERNS.keys())

STATUS_LABELS = {
    "yes": _("Yes"),
    "no": _("No"),
    "partial": _("Partial"),
    "unknown": _("Unknown"),
    "scanning": _("Scanning…"),
}

STATUS_CSS = {
    "yes": "success",
    "no": "error",
    "partial": "warning",
    "unknown": "dim-label",
    "scanning": "dim-label",
}


class RepoRow(Gtk.ListBoxRow):
    """A row showing a single repo's l10n status."""

    def __init__(self, repo: dict):
        super().__init__()
        self.repo = repo
        self.set_activatable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Stars
        stars_label = Gtk.Label(label=self._format_stars(repo["stars"]))
        stars_label.set_width_chars(7)
        stars_label.set_xalign(1)
        stars_label.add_css_class("caption")
        box.append(stars_label)

        # Repo name + description
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        name_label = Gtk.Label(label=repo["full_name"])
        name_label.set_xalign(0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.add_css_class("heading")
        text_box.append(name_label)

        if repo.get("description"):
            desc_label = Gtk.Label(label=repo["description"])
            desc_label.set_xalign(0)
            desc_label.set_ellipsize(Pango.EllipsizeMode.END)
            desc_label.add_css_class("dim-label")
            desc_label.add_css_class("caption")
            text_box.append(desc_label)

        box.append(text_box)

        # L10n status badge
        status = repo.get("l10n_status", "unknown")
        self.status_label = Gtk.Label(label=STATUS_LABELS.get(status, status))
        self.status_label.add_css_class(STATUS_CSS.get(status, "dim-label"))
        self.status_label.set_width_chars(10)
        box.append(self.status_label)

        self.set_child(box)

    def update_status(self, status: str):
        self.repo["l10n_status"] = status
        self.status_label.set_label(STATUS_LABELS.get(status, status))
        # Remove old CSS classes
        for cls in STATUS_CSS.values():
            self.status_label.remove_css_class(cls)
        self.status_label.add_css_class(STATUS_CSS.get(status, "dim-label"))

    @staticmethod
    def _format_stars(n: int) -> str:
        if n >= 1000:
            return f"⭐ {n // 1000}k"
        return f"⭐ {n}"


class DetailDialog(Adw.Dialog):
    """Shows l10n details for a repo."""

    def __init__(self, repo: dict, l10n_data: dict):
        super().__init__()
        self.set_title(repo["full_name"])
        self.set_content_width(500)
        self.set_content_height(400)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        # Status
        status = l10n_data.get("status", "unknown")
        status_row = Adw.ActionRow(title=_("Translation Status"))
        status_row.set_subtitle(STATUS_LABELS.get(status, status))
        group1 = Adw.PreferencesGroup()
        group1.add(status_row)

        any_row = Adw.ActionRow(title=_("Has any l10n files"))
        any_row.set_subtitle(_("Yes") if l10n_data.get("any_l10n") else _("No"))
        group1.add(any_row)
        box.append(group1)

        # Files
        files = l10n_data.get("files", [])
        if files:
            group2 = Adw.PreferencesGroup(title=_("Translation Files"))
            for f in files:
                row = Adw.ActionRow(title=f["name"])
                row.set_subtitle(f["path"])
                link_btn = Gtk.LinkButton(uri=f["html_url"], label=_("Open"))
                link_btn.set_valign(Gtk.Align.CENTER)
                row.add_suffix(link_btn)
                group2.add(row)
            box.append(group2)

        # Link to repo
        group3 = Adw.PreferencesGroup()
        repo_row = Adw.ActionRow(title=_("Repository"))
        link_btn = Gtk.LinkButton(uri=repo["html_url"], label=_("Open on GitHub"))
        link_btn.set_valign(Gtk.Align.CENTER)
        repo_row.add_suffix(link_btn)
        group3.add(repo_row)
        box.append(group3)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(box)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        self.set_child(toolbar_view)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, default_width=900, default_height=700)
        self.set_title(_("GitHub Translation Stats"))
        self.set_default_size(900, 700)

        self.client = GitHubClient()
        self.repos = []
        self.l10n_data = {}
        self.current_lang = "sv"
        self.current_filter = "all"

        # Main layout
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()

        # Token button
        token_btn = Gtk.Button(icon_name="dialog-password-symbolic")
        token_btn.set_tooltip_text(_("Set GitHub Token"))
        token_btn.connect("clicked", self._on_token_clicked)
        header.pack_start(token_btn)

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(_("Refresh"))
        refresh_btn.connect("clicked", self._on_refresh)
        header.pack_start(refresh_btn)

        # Language dropdown
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lang_label = Gtk.Label(label=_("Language:"))
        lang_box.append(lang_label)

        self.lang_dropdown = Gtk.DropDown.new_from_strings(LANGUAGES)
        self.lang_dropdown.set_selected(LANGUAGES.index("sv") if "sv" in LANGUAGES else 0)
        self.lang_dropdown.connect("notify::selected", self._on_lang_changed)
        lang_box.append(self.lang_dropdown)
        header.pack_end(lang_box)

        # App menu
        app_menu = Gio.Menu()
        about_section = Gio.Menu()
        about_section.append(_("About"), "app.about")
        app_menu.append_section(None, about_section)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=app_menu)
        header.pack_end(menu_btn)

        # Filter dropdown
        filter_strings = [_("All"), _("Without translation"), _("With translation")]
        self.filter_dropdown = Gtk.DropDown.new_from_strings(filter_strings)
        self.filter_dropdown.connect("notify::selected", self._on_filter_changed)
        header.pack_end(self.filter_dropdown)

        toolbar_view.add_top_bar(header)

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Status bar
        self.status_label = Gtk.Label(label=_("Click Refresh to scan GitHub repos"))
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_top(4)
        self.status_label.set_margin_bottom(4)
        content_box.append(self.status_label)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_visible(False)
        content_box.append(self.progress)

        # List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_margin_start(16)
        self.listbox.set_margin_end(16)
        self.listbox.set_margin_top(8)
        self.listbox.set_margin_bottom(16)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.listbox.set_sort_func(self._sort_func)
        self.listbox.set_filter_func(self._filter_func)

        scrolled.set_child(self.listbox)
        content_box.append(scrolled)

        toolbar_view.set_content(content_box)
        self.set_content(toolbar_view)

    def _on_refresh(self, *_args):
        self.status_label.set_label(_("Fetching top repos…"))
        self.progress.set_visible(True)
        self.progress.set_fraction(0)

        def fetch():
            try:
                repos = self.client.get_top_repos(100)
                GLib.idle_add(self._populate_repos, repos)
            except Exception as e:
                GLib.idle_add(self.status_label.set_label, f"Error: {e}")
                GLib.idle_add(self.progress.set_visible, False)

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_repos(self, repos):
        self.repos = repos
        # Clear
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        for repo in repos:
            repo["l10n_status"] = "unknown"
            row = RepoRow(repo)
            self.listbox.append(row)

        self.status_label.set_label(_("Loaded %d repos. Scanning translations…") % len(repos))
        self.progress.set_fraction(0.1)

        # Start scanning l10n
        threading.Thread(target=self._scan_l10n, daemon=True).start()

    def _scan_l10n(self):
        total = len(self.repos)
        for i, repo in enumerate(self.repos):
            try:
                data = self.client.search_l10n_files(repo["full_name"], self.current_lang)
                self.l10n_data[repo["full_name"]] = data
                status = data["status"]
            except Exception:
                status = "unknown"
                self.l10n_data[repo["full_name"]] = {"status": "unknown", "files": [], "any_l10n": False}

            def update(idx=i, st=status):
                row = self.listbox.get_row_at_index(idx)
                if row and isinstance(row, RepoRow):
                    row.update_status(st)
                frac = (idx + 1) / total
                self.progress.set_fraction(frac)
                if idx == total - 1:
                    yes = sum(1 for r in self.repos if r.get("l10n_status") == "yes")
                    no = sum(1 for r in self.repos if r.get("l10n_status") == "no")
                    partial = sum(1 for r in self.repos if r.get("l10n_status") == "partial")
                    self.status_label.set_label(
                        _("%(total)d repos: %(yes)d with, %(no)d without, %(partial)d partial %(lang)s translation")
                        % {"total": total, "yes": yes, "no": no, "partial": partial, "lang": self.current_lang}
                    )
                    self.progress.set_visible(False)
                    self.listbox.invalidate_filter()
                    self.listbox.invalidate_sort()

            GLib.idle_add(update)
            # Rate limit: ~2 requests per repo, be gentle
            import time
            time.sleep(0.5 if self.client.token else 2.0)

    def _on_row_activated(self, _listbox, row):
        if not isinstance(row, RepoRow):
            return
        repo = row.repo
        data = self.l10n_data.get(repo["full_name"], {"status": "unknown", "files": [], "any_l10n": False})
        dialog = DetailDialog(repo, data)
        dialog.present(self)

    def _on_lang_changed(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        if 0 <= idx < len(LANGUAGES):
            self.current_lang = LANGUAGES[idx]
            # Re-scan if we have repos
            if self.repos:
                self.l10n_data.clear()
                self.status_label.set_label(_("Re-scanning for %s…") % self.current_lang)
                self.progress.set_visible(True)
                self.progress.set_fraction(0)
                # Reset statuses
                i = 0
                while True:
                    row = self.listbox.get_row_at_index(i)
                    if row is None:
                        break
                    if isinstance(row, RepoRow):
                        row.update_status("scanning")
                    i += 1
                threading.Thread(target=self._scan_l10n, daemon=True).start()

    def _on_filter_changed(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        self.current_filter = ["all", "no", "yes"][idx] if idx < 3 else "all"
        self.listbox.invalidate_filter()

    def _filter_func(self, row):
        if not isinstance(row, RepoRow):
            return True
        if self.current_filter == "all":
            return True
        status = row.repo.get("l10n_status", "unknown")
        if self.current_filter == "no":
            return status in ("no", "unknown")
        if self.current_filter == "yes":
            return status in ("yes", "partial")
        return True

    def _sort_func(self, row1, row2):
        if not isinstance(row1, RepoRow) or not isinstance(row2, RepoRow):
            return 0
        # Sort by stars descending
        return row2.repo["stars"] - row1.repo["stars"]

    def _on_token_clicked(self, *_args):
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("GitHub Token"))
        dialog.set_body(_("Enter a GitHub personal access token for higher rate limits (5000/h vs 60/h). Leave empty to use unauthenticated access."))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("ok", _("Save"))
        dialog.set_default_response("ok")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)

        entry = Gtk.Entry()
        entry.set_placeholder_text("ghp_xxxxxxxxxxxxxxxxxxxx")
        if self.client.token:
            entry.set_text(self.client.token)
        entry.set_margin_start(16)
        entry.set_margin_end(16)
        dialog.set_extra_child(entry)

        def on_response(_dialog, response):
            if response == "ok":
                token = entry.get_text().strip()
                self.client.token = token if token else None
                self.client.clear_cache()

        dialog.connect("response", on_response)
        dialog.present(self)


class GithubL10nApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = MainWindow(self)
        win.present()

    def _on_about(self, *_args):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name=_("GitHub Translation Stats"),
            application_icon="github-l10n",
            version="0.2.2",
            developer_name="Daniel Nylander",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2026 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/github-l10n",
            issue_url="https://github.com/yeager/github-l10n/issues",
            translator_credits="Daniel Nylander <daniel@danielnylander.se>",
            comments=_("Scan GitHub repositories for missing translations"),
        )
        about.present()


def main():
    app = GithubL10nApp()
    app.run(sys.argv)
