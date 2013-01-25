#!/usr/bin/env python

try:
    from SettingsWidgets import *
    from Spices import Spice_Harvester
    #from Spices import *
    import pygtk
    pygtk.require('2.0')
    import gettext
    import locale
    import os.path
    import sys
    import time
    import urllib2
    import os
    import os.path
    from gi.repository import Gio, Gtk, GObject, Gdk
    import dbus
except Exception, detail:
    print detail
    sys.exit(1)

home = os.path.expanduser("~")

class Module:
    def __init__(self, content_box):
        sidePage = AppletViewSidePage(_("Applets"), "applets.svg", content_box)
        self.sidePage = sidePage
        self.name = "applets"

    def _set_parent_ref(self, window, builder):
        self.sidePage.window = window
        self.sidePage.builder = builder
class AppletViewSidePage (SidePage):
    SORT_NAME = 0
    SORT_RATING = 1
    SORT_DATE_EDITED = 2
    SORT_ENABLED = 3
    SORT_REMOVABLE = 4

    def __init__(self, name, icon, content_box):
        SidePage.__init__(self, name, icon, content_box)
        self.icons = []
    
    def build(self):
        # Clear all the widgets from the content box
        widgets = self.content_box.get_children()
        for widget in widgets:
            self.content_box.remove(widget)
        
        scrolledWindow = Gtk.ScrolledWindow()    
        notebook = Gtk.Notebook()
        applets_vbox = Gtk.VBox()
        
        self.search_entry = Gtk.Entry()
        self.search_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'edit-find')
        self.search_entry.set_placeholder_text(_("Search applets"))
        self.search_entry.connect('changed', self.on_entry_refilter)

        notebook.append_page(applets_vbox, Gtk.Label(_("Installed")))
        
        self.content_box.add(notebook)
        self.treeview = Gtk.TreeView()
        
        cr = Gtk.CellRendererToggle()
        cr.connect("toggled", self.toggled, self.treeview)
        column1 = Gtk.TreeViewColumn(_("Enable"), cr)
        column1.set_cell_data_func(cr, self.celldatafunction_checkbox)        
        column1.set_resizable(True)

        column2 = Gtk.TreeViewColumn(_("Icon"), Gtk.CellRendererPixbuf(), pixbuf=4)        
        column2.set_resizable(True)

        column3 = Gtk.TreeViewColumn(_("Description"), Gtk.CellRendererText(), markup=1)        
        column3.set_resizable(True)      
        column3.set_max_width(450)

        cr = Gtk.CellRendererText()
        actionColumn = Gtk.TreeViewColumn(_("Action"), cr)
        actionColumn.set_cell_data_func(cr, self._action_data_func)
        
        self.treeview.append_column(column2)
        self.treeview.append_column(column3)
        self.treeview.append_column(actionColumn)
        self.treeview.set_headers_visible(False)
        
        self.model = Gtk.TreeStore(str, str, int, int, GdkPixbuf.Pixbuf, str, int)
        #                          uuid, desc, enabled, max-instances, icon, name, read-only

        self.modelfilter = self.model.filter_new()
        self.onlyActive = True
        self.modelfilter.set_visible_func(self.only_active)
        
        self.treeview.set_model(self.modelfilter)
        self.treeview.set_search_column(5)
        self.treeview.set_search_entry(self.search_entry)
        # Find the enabled applets
        self.settings = Gio.Settings.new("org.cinnamon")
        self.enabled_applets = self.settings.get_strv("enabled-applets")
                         
        self.load_applets()

        self.model.set_sort_column_id(5, Gtk.SortType.ASCENDING) # Sort by name 
        
        self.settings.connect("changed::enabled-applets", lambda x,y: self._enabled_applets_changed())
        
        scrolledWindow.add(self.treeview)
        self.treeview.connect('button_press_event', self.on_button_press_event)

        self.instanceButton = Gtk.Button(_("Add to panel"))       
        self.instanceButton.connect("clicked", lambda x: self._add_another_instance())
        self.instanceButton.set_tooltip_text(_("Some applets can be added multiple times.\nUse this to add another instance. Use panel edit mode to remove a single instance."))
        self.instanceButton.set_sensitive(False);
        
        restoreButton = Gtk.Button(_("Restore to default"))       
        restoreButton.connect("clicked", lambda x: self._restore_default_applets())
        # Installed 
        hbox = Gtk.HBox()
        self.activeButton = Gtk.ToggleButton(_("Active"))
        self.inactiveButton = Gtk.ToggleButton(_("Inactive"))
        self.activeButton.set_active(True)
        self.inactiveButton.set_active(False)
        self.activeHandler = self.activeButton.connect("toggled", self._filter_toggle)
        self.inactiveHandler = self.inactiveButton.connect("toggled", self._filter_toggle)

        buttonbox = Gtk.ButtonBox.new(Gtk.Orientation.HORIZONTAL)
        buttonbox.pack_start(self.activeButton, False, False, 0)
        buttonbox.pack_start(self.inactiveButton, False, False, 0)
        hbox.pack_start(buttonbox, False, False, 4)

        hbox.pack_end(self.search_entry, False, False, 4)
        applets_vbox.pack_start(hbox, False, False, 4)
        hbox.show()
        self.search_entry.show()

        applets_vbox.pack_start(scrolledWindow, True, True, 0)
        hbox = Gtk.HBox()
        applets_vbox.pack_start(hbox, False, True, 5)

        align = Gtk.Alignment()
        align.set(1.0, 0.5, 0, 0)
        buttonbox = Gtk.ButtonBox.new(Gtk.Orientation.HORIZONTAL)
        buttonbox.pack_start(self.instanceButton, False, False, 0)
        buttonbox.pack_end(restoreButton, False, False, 0)
        hbox.pack_start(buttonbox, True, True, 5)
        hbox.xalign = 1.0
        
        link = Gtk.LinkButton("http://cinnamon-spices.linuxmint.com/applets")
        link.set_label(_("Get new applets"))                
                         
        self.content_box.pack_start(self.search_entry, False, False, 2)
        self.content_box.add(scrolledWindow)        
        self.content_box.pack_start(self.instanceButton, False, False, 2) 
        self.content_box.pack_start(restoreButton, False, False, 2) 
        self.content_box.pack_start(link, False, False, 2) 
        
        getmore_vbox.pack_start(hbox, False, False, 4)

        # MODEL
        self.gm_model = Gtk.TreeStore(str, str, int, GdkPixbuf.Pixbuf, int, str, int)
        #                            uuid, name, install, icon, score
        self.gm_model.set_sort_column_id(4, Gtk.SortType.DESCENDING)

        # TREE
        self.gm_modelfilter = self.gm_model.filter_new()
        self.gm_modelfilter.set_visible_func(self.gm_match_func)
        self.gm_treeview = Gtk.TreeView()
        
        gm_cr = Gtk.CellRendererToggle()
        gm_cr.connect("toggled", self.gm_toggled, self.gm_treeview)
        gm_column1 = Gtk.TreeViewColumn(_("Install"), gm_cr)
        gm_column1.set_cell_data_func(gm_cr, self.gm_celldatafunction_checkbox)
        gm_column1.set_resizable(True)

        gm_column2 = Gtk.TreeViewColumn(_("Icon"), Gtk.CellRendererPixbuf(), pixbuf=3)
        gm_column2.set_resizable(True)

        gm_column3 = Gtk.TreeViewColumn(_("Description"), Gtk.CellRendererText(), markup=1)
        gm_column3.set_resizable(True)
        gm_column3.set_max_width(400)
        
        cr = Gtk.CellRendererText()
        actionColumn = Gtk.TreeViewColumn(_("Action"), cr)
        actionColumn.set_cell_data_func(cr, self._gm_action_data_func)
        actionColumn.set_max_width(70)

        right = Gtk.CellRendererText()
        right.set_property('xalign', 1.0)
        gm_column4 = Gtk.TreeViewColumn(_("Score"), right, markup=4)
        gm_column4.set_resizable(True)
        gm_column4.set_alignment(1.0)

        self.gm_treeview.append_column(gm_column1)
        self.gm_treeview.append_column(gm_column2)
        self.gm_treeview.append_column(gm_column3)
        self.gm_treeview.append_column(actionColumn)
        self.gm_treeview.append_column(gm_column4)
        self.gm_treeview.set_headers_visible(False)

        self.gm_treeview.set_model(self.gm_modelfilter)
        self.gm_treeview.set_search_column(5)
        self.gm_treeview.set_search_entry(self.gm_search_entry)

        gm_scrolled_window.add(self.gm_treeview)
        self.gm_treeview.connect('motion_notify_event', self.gm_on_motion_notify_event)
        self.gm_treeview.connect('button_press_event', self.gm_on_button_press_event)

        getmore_vbox.add(gm_scrolled_window)

        hbox = Gtk.HBox()
        buttonbox = Gtk.ButtonBox.new(Gtk.Orientation.HORIZONTAL)
        self.install_button = Gtk.Button(_("Install selected"))
        reload_button = Gtk.Button(_("Refresh list"))
        buttonbox.pack_start(self.install_button, False, False, 2)
        buttonbox.pack_end(reload_button, False, False, 2)
        hbox.pack_start(buttonbox, True, True, 5)
        getmore_vbox.pack_end(hbox, False, True, 5)

        reload_button.connect("clicked", lambda x: self.load_spices(True))
        self.install_button.connect("clicked", lambda x: self.install_applets())
        self.content_box.show_all()   
        self.treeview.get_selection().connect("changed", lambda x: self._selection_changed());

    def _enabled_applets_changed(self):
        last_selection = ''
        model, treeiter = self.treeview.get_selection().get_selected()
        self.enabled_applets = self.settings.get_strv("enabled-applets")
        
        uuidCount = {}
        for enabled_applet in self.enabled_applets:
            try:
                panel, align, order, uuid, id = enabled_applet.split(":")
                if uuid in uuidCount:
                    uuidCount[uuid] += 1
                else:
                    uuidCount[uuid] = 1
            except:
                pass

        for row in self.model:
            uuid = self.model.get_value(row.iter, 0)
            if(uuid in uuidCount):
                self.model.set_value(row.iter, 2, uuidCount[uuid])
            else:
                self.model.set_value(row.iter, 2, 0)
        
    def _add_another_instance(self):
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter:
            self._add_another_instance_iter(treeiter)
        
    def _add_another_instance_iter(self, treeiter):
        uuid = self.modelfilter.get_value(treeiter, 0);
        self.instance_applet(uuid)
        
    def _selection_changed(self):
        model, treeiter = self.treeview.get_selection().get_selected()
        enabled = False;
        
        tip = _("Some applets can be added multiple times.\nUse this to add another instance. Use panel edit mode to remove a single instance.")
        if treeiter:
            checked = model.get_value(treeiter, 2);
            max_instances = model.get_value(treeiter, 3);
            enabled = max_instances == -1 or ((max_instances > 1) and (max_instances > checked))
            if max_instances == 1:
                tip += _("\nThis applet does not support multiple instances.")
            else:
                tip += _("\nThis applet supports max %d instances.") % max_instances
        self.instanceButton.set_sensitive(enabled);
        self.instanceButton.set_tooltip_text(tip)
    
    def _restore_default_applets(self):
        os.system('gsettings reset org.cinnamon next-applet-id')
        os.system('gsettings reset org.cinnamon enabled-applets')
    
    def load_applets(self):
        self.model.clear()
        self.load_applets_in('/usr/share/cinnamon/applets')
        self.load_applets_in('%s/.local/share/cinnamon/applets' % home)
    def load_applets_in(self, directory):
        if os.path.exists(directory) and os.path.isdir(directory):
            applets = os.listdir(directory)
            applets.sort()
            for applet in applets:
                try:           
                    if os.path.exists("%s/%s/metadata.json" % (directory, applet)):
                        json_data=open("%s/%s/metadata.json" % (directory, applet)).read()
                        data = json.loads(json_data)  
                        applet_uuid = data["uuid"]
                        applet_name = data["name"]                                        
                        applet_description = data["description"]                          
                        try: applet_max_instances = int(data["max-instances"])
                        except KeyError: applet_max_instances = -1
                        except ValueError: applet_max_instances = -1

                        try: applet_role = data["role"]
                        except KeyError: applet_role = None
                        except ValueError: applet_role = None

                        if applet_max_instances < -1:
                            applet_max_instances = -1
                            
                        if self.search_entry.get_text().upper() in (applet_name + applet_description).upper():
                            iter = self.model.insert_before(None, None)
                            found = 0
                            for enabled_applet in self.enabled_applets:
                                if applet_uuid in enabled_applet:
                                    found += 1

                            self.model.set_value(iter, 0, applet_uuid)                
                            self.model.set_value(iter, 1, '<b>%s</b>\n<b><span foreground="#333333" size="xx-small">%s</span></b>\n<i><span foreground="#555555" size="x-small">%s</span></i>' % (applet_name, applet_uuid, applet_description))                                  
                            self.model.set_value(iter, 2, found)
                            self.model.set_value(iter, 3, applet_max_instances)
                            img = None                            
                            if "icon" in data:
                                applet_icon = data["icon"]
                                theme = Gtk.IconTheme.get_default()                                                    
                                if theme.has_icon(applet_icon):
                                    img = theme.load_icon(applet_icon, 32, 0)
                            elif os.path.exists("%s/%s/icon.png" % (directory, applet)):
                                img = GdkPixbuf.Pixbuf.new_from_file_at_size("%s/%s/icon.png" % (directory, applet), 32, 32)                            
                            
                            if img is None:                                                
                                img = GdkPixbuf.Pixbuf.new_from_file_at_size( "/usr/lib/cinnamon-settings/data/icons/applets.svg", 32, 32)
                                
                            self.model.set_value(iter, 4, img)
                            self.model.set_value(iter, 5, applet_name)
                            self.model.set_value(iter, 6, os.access(directory, os.W_OK))
                except Exception, detail:
                    print "Failed to load applet %s: %s" % (applet, detail)

    def show_prompt(self, msg):
        dialog = Gtk.MessageDialog(None,
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.QUESTION,
                    Gtk.ButtonsType.YES_NO,
                    None)
        dialog.set_default_size(400, 200)
        dialog.set_markup(msg)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
                            
    def toggled(self, renderer, path, treeview):        
        iter = self.model.get_iter(path)
        if (iter != None):
            uuid = self.model.get_value(iter, 0)
            checked = self.model.get_value(iter, 2)
            if checked == 0:
                self._add_another_instance_iter(iter)
                return
            
            if (checked > 1):
                msg = _("There are multiple instances of this applet, do you want to remove them all?\n\n")
                msg += _("You can remove specific instances in panel edit mode via the context menu.")
                if self.show_prompt(msg) == False:
                    return
                    
            self.model.set_value(iter, 2, 0)
            newApplets = []
            for enabled_applet in self.enabled_applets:
                if uuid not in enabled_applet:
                    newApplets.append(enabled_applet)
            self.enabled_applets = newApplets
            self.settings.set_strv("enabled-applets", self.enabled_applets)
    
    def celldatafunction_checkbox(self, column, cell, model, iter, data=None):
        cell.set_property("activatable", True)
        checked = model.get_value(iter, 2)
        if (checked > 0):
            cell.set_property("active", True)
        else:
            cell.set_property("active", False)
