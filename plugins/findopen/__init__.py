import gedit, gtk, gtk.glade
import gconf
import gnomevfs
import pygtk
pygtk.require('2.0')
import os, os.path, gobject
import locale

###############################
# CUSTOM VALUES

# Set this to true for gedit versions before 2.16
pre216_version = False

# Limit the number of matches
max_result = 50
limit_total_results = "head -n " + repr(max_result)

# Set this to true if you have grep < 2.5.3
# Useful to search by content (with some ignore dirs) - require grep 2.5.3 or higher http://www.zulius.com/how-to/grep-skip-svn-directories/
preGrep253_version = False

# Ignore those directories
ignore_dirs = '--exclude-dir="./.*" --exclude-dir="./public/productshots" --exclude-dir="./log" --exclude-dir="./vendor" --exclude-dir="./legacy" --exclude-dir="./coverage" --exclude-dir="./log"'

# Ignore not text files
#ignore_images = " ! -iname '*.jpg' ! -iname '*.jpeg' ! -iname '*.gif' ! -iname '*.png' ! -iname '*.psd' ! -iname '*.tif' "
        
###############################

# Get the current locale
lc, encoding = locale.getdefaultlocale()

label_title = ("Find a file by content", "Encuentra un archivo por su contenido")[lc=="es_MX"]
label_menu = ('Go to File by content...', 'Buscar por contenido...')[lc=="es_MX"]
label_searching = ("Searching... ", "Buscando... ")[lc=="es_MX"]
label_instructions = ("Write the text to find:", "Escribe el texto a buscar:")[lc=="es_MX"]
label_max_results = ("* too many hits", "* demasiados")[lc=="es_MX"]

ui_str="""<ui>
<menubar name="MenuBar">
    <menu name="SearchMenu" action="Search">
        <placeholder name="SearchOps_7">
            <menuitem name="GoToFileByContent" action="GoToFileByContentAction"/>
        </placeholder>
    </menu>
</menubar>
</ui>
"""

# essential interface
class FindOpenPluginInstance:
    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        if pre216_version:
            self._encoding = gedit.gedit_encoding_get_current()
        else:
            self._encoding = gedit.encoding_get_current()
        self._rootdir = "file://" + os.getcwd()
        self._show_hidden = False
        self._liststore = None;
        self._init_glade()
        self._insert_menu()

    def deactivate(self):
        self._remove_menu()
        self._action_group = None
        self._window = None
        self._plugin = None
        self._liststore = None;

    def update_ui(self):
        return

    # MENU STUFF
    def _insert_menu(self):
        manager = self._window.get_ui_manager()
        actions = [
            ('GoToFileByContentAction', gtk.STOCK_JUMP_TO, label_menu, '<Ctrl><Alt>f', label_menu, self.on_findopen_action)
        ]
        self._action_group = gtk.ActionGroup("FindOpenPluginActions")
        self._action_group.add_actions(actions, self._window)

        manager.insert_action_group(self._action_group, -1)
        manager.add_ui_from_string(ui_str)
        self._ui_id = manager.new_merge_id()

    def _remove_menu(self):
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        manager.remove_action_group(self._action_group)

    # UI DIALOGUES
    def _init_glade(self):
        self._findopen_glade = gtk.glade.XML(os.path.dirname(__file__) + "/findopen.glade")
        #setup window
        self._findopen_window = self._findopen_glade.get_widget("FindOpenWindow")
        self._findopen_window.connect("key-release-event", self.on_window_key)
        self._findopen_window.set_transient_for(self._window)
        #setup buttons
        self._findopen_glade.get_widget("ok_button").connect("clicked", self.open_selected_item)
        self._findopen_glade.get_widget("cancel_button").connect("clicked", lambda a: self._findopen_window.hide())
        #setup entry field
        self._glade_entry_name = self._findopen_glade.get_widget("entry_name")
        self._glade_entry_name.connect("key-release-event", self.on_pattern_entry)
        #setup list field
        self._hit_list = self._findopen_glade.get_widget("hit_list")
        self._hit_list.connect("select-cursor-row", self.on_select_from_list)
        self._hit_list.connect("button_press_event", self.on_list_mouse)
        self._liststore = gtk.ListStore(str, str, str)
        self._hit_list.set_model(self._liststore)
        column = gtk.TreeViewColumn("Name" , gtk.CellRendererText(), markup=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column2 = gtk.TreeViewColumn("File", gtk.CellRendererText(), markup=1)
        column2.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._hit_list.append_column(column)
        self._hit_list.append_column(column2)
        self._hit_list.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

    #mouse event on list
    def on_list_mouse(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.open_selected_item(event)

    #key selects from list (passthrough 3 args)
    def on_select_from_list(self, widget, event):
        self.open_selected_item(event)

    #keyboard event on entry field
    def on_pattern_entry(self, widget, event):
        oldtitle = self._findopen_window.get_title().replace( label_max_results, "" )
        if event.keyval == gtk.keysyms.Return:
            self.open_selected_item(event)
            return
        pattern = self._glade_entry_name.get_text()
        pattern = pattern.replace(" ",".")
        #modify lines below as needed, these defaults work pretty well
        search_path = self._rootdir.replace("file://", "")
        ignore_hidden = "grep -v ~$ | grep -s -v \"/\.\"" # Ignore hidden files, like ".git/config"
        cmd = ""
        if self._show_hidden:
            ignore_hidden = ""
        if len(pattern) > 3: # We start to search if there is more than 3 letters.
            
            ###############################
            if preGrep253_version:
                # To search by content
                cmd = "cd " + search_path + "; grep -RIsilE '" + pattern + "' . | " + ignore_hidden + " | " + limit_total_results + " | sort "
            else:
                # To search by content (with some ignore dirs)
                cmd = "cd " + search_path + "; grep -RIsilE " + ignore_dirs + " '" + pattern + "' . | " + ignore_hidden + " | " + limit_total_results + " | sort "

            print "Running:\n" + cmd
            ###############################
            self._findopen_window.set_title( label_searching )
        else:
            self._findopen_window.set_title( label_instructions )

        self._liststore.clear()
        maxcount = 0
        hits = os.popen(cmd).readlines()
        for file in hits:
            file = file.rstrip().replace("./", "")
            name = os.path.basename(file)

            self._liststore.append([self.highlight_pattern(name, pattern), self.highlight_pattern(file, pattern), file])
            if maxcount > max_result:
                break
            maxcount = maxcount + 1
        if maxcount > max_result:
            oldtitle = oldtitle + label_max_results
        self._findopen_window.set_title(oldtitle)

        selected = []
        self._hit_list.get_selection().selected_foreach(self.foreach, selected)

        if len(selected) == 0:
            iter = self._liststore.get_iter_first()
            if iter != None:
                self._hit_list.get_selection().select_iter(iter)


    def highlight_pattern(self, path, pattern):
        query_list = pattern.lower().split("*")
        last_postion = 0
        for word in query_list:
            location = path.lower().find(word, last_postion)
            if location > -1:
                last_postion = (location + len(word) + 3)
                a_path = list(path)
                a_path.insert(location, "<b>")
                a_path.insert(location + len(word) + 1, "</b>")
                path = "".join(a_path)
        return path


    #on menuitem activation (incl. shortcut)
    def on_findopen_action(self, *args):
        fbroot = self.get_filebrowser_root()
        if fbroot != "" and fbroot is not None:
            self._rootdir = fbroot
            self._findopen_window.set_title(label_title + " (" + self._rootdir.replace("file://", "") + ")")
        else:
            eddtroot = self.get_eddt_root()
            if eddtroot != "" and eddtroot is not None:
                self._rootdir = eddtroot
                self._findopen_window.set_title(label_title + + " (" + self._rootdir.replace("file://", "") + ")")
            else:
                self._findopen_window.set_title(label_title + + " (" + self._rootdir.replace("file://", "") + ")")
        self._findopen_window.show()
        self._glade_entry_name.select_region(0,-1)
        self._glade_entry_name.grab_focus()

    #on any keyboard event in main window
    def on_window_key(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self._findopen_window.hide()

    def foreach(self, model, path, iter, selected):
        selected.append(model.get_value(iter, 2))

    #open file in selection and hide window
    def open_selected_item(self, event):
        selected = []
        self._hit_list.get_selection().selected_foreach(self.foreach, selected)
        for selected_file in	selected:
            self._open_file (selected_file)
        self._findopen_window.hide()

    #gedit < 2.16 version (get_tab_from_uri)
    def old_get_tab_from_uri(self, window, uri):
        docs = window.get_documents()
        for doc in docs:
            if doc.get_uri() == uri:
                return gedit.tab_get_from_document(doc)
            return None

    #opens (or switches to) the given file
    def _open_file(self, filename):
        uri = self._rootdir + "/" + filename
        if pre216_version:
            tab = self.old_get_tab_from_uri(self._window, uri)
        else:
            tab = self._window.get_tab_from_uri(uri)
        if tab == None:
            tab = self._window.create_tab_from_uri(uri, self._encoding, 0, False, False)
        self._window.set_active_tab(tab)

    # EDDT integration
    def get_eddt_root(self):
        base = u'/apps/gedit-2/plugins/eddt'
        client = gconf.client_get_default()
        client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
        path = os.path.join(base, u'repository')
        val = client.get(path)
        if val is not None:
            return val.get_string()

    # FILEBROWSER integration
    def get_filebrowser_root(self):
        base = u'/apps/gedit-2/plugins/filebrowser/on_load'
        client = gconf.client_get_default()
        client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
        path = os.path.join(base, u'virtual_root')
        val = client.get(path)
        if val is not None:
            #also read hidden files setting
            base = u'/apps/gedit-2/plugins/filebrowser'
            client = gconf.client_get_default()
            client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
            path = os.path.join(base, u'filter_mode')
            try:
                fbfilter = client.get(path).get_string()
            except AttributeError:
                fbfilter = "hidden"
            if fbfilter.find("hidden") == -1:
                self._show_hidden = True
            else:
                self._show_hidden = False
            return val.get_string()

# STANDARD PLUMMING
class FindOpenPlugin(gedit.Plugin):
    DATA_TAG = "FindOpenPluginInstance"

    def __init__(self):
        gedit.Plugin.__init__(self)

    def _get_instance(self, window):
        return window.get_data(self.DATA_TAG)

    def _set_instance(self, window, instance):
        window.set_data(self.DATA_TAG, instance)

    def activate(self, window):
        self._set_instance(window, FindOpenPluginInstance(self, window))

    def deactivate(self, window):
        self._get_instance(window).deactivate()
        self._set_instance(window, None)

    def update_ui(self, window):
        self._get_instance(window).update_ui()

