import gi
gi.require_version('Gtk', '3.0')

from gi.repository import (Gtk, Gdk)
# import pandas

from editor import (Editor)


def idx_letters(i):
    s = ''
    while i != 0:
        i -= 1
        s = chr((i % 26) + ord('A')) + s
        i //= 26
    return s


class Status(Gtk.Statusbar):
    def __init__(self):
        super(Status, self).__init__()
        self._data = {}
        self.connect('realize', self.on_realize)

    def on_realize(self, widget):
        self.push(0, self.msg())

    def msg(self):
        return ' - '.join('{}: {}'.format(k, v) for k, v in self._data.items())

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.pop(0)
        self.push(0, self.msg())


class WorkSheetTopHeader(Gtk.ScrolledWindow):
    def __init__(self, hadjustment, columns):
        super(WorkSheetTopHeader, self).__init__()
        self.set_hadjustment(hadjustment)
        self.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        self._grid = Gtk.Grid()
        self.add(self._grid)
        self._columns = columns
        self._create_cells()
        self.show_all()

    def _create_cells(self):
        for i, c in enumerate(self._columns):
            label = Gtk.Label.new(c)
            label.set_alignment(0.5, 0.5)
            label.props.width_request = 100
            label.props.xpad = 2
            label.get_style_context().add_class('sheet')
            label.get_style_context().add_class('header')
            self._grid.attach(label, i, 0, 1, 1)


class WorkSheetLeftHeader(Gtk.ScrolledWindow):
    def __init__(self, vadjustment, n_rows):
        super(WorkSheetLeftHeader, self).__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        self.set_vadjustment(vadjustment)
        self._grid = Gtk.Grid()
        self.add(self._grid)
        self._n_rows = n_rows
        self._create_cells()
        self.show_all()

    def _create_cells(self):
        for i in range(self._n_rows):
            label = Gtk.Label.new(str(i + 1))
            label.set_alignment(1, 0.5)
            label.get_style_context().add_class('sheet')
            label.get_style_context().add_class('header')
            label.props.xpad = 5
            label.props.ypad = 1
            label.props.width_request = 100
            self._grid.attach(label, 0, i, 1, 1)


class WorkSheet(Gtk.Grid):
    def __init__(self, status, columns=1, n_rows=1):
        super(WorkSheet, self).__init__()
        self._status = status

        if isinstance(columns, int):
            self._columns = tuple(idx_letters(i) for i in range(1, columns+1))
        elif isinstance(columns, tuple):
            self._columns = columns
        else:
            raise TypeError('columns should be specified as tuple or int')

        self._n_rows = n_rows

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_hexpand(True)
        self._scrolled_window.set_vexpand(True)

        self._cell_grid = Gtk.Grid()
        self._scrolled_window.add(self._cell_grid)

        self._left_header = WorkSheetLeftHeader(self._scrolled_window.get_vadjustment(), self._n_rows)
        self._top_header = WorkSheetTopHeader(self._scrolled_window.get_hadjustment(), self._columns)

        self._entry = Gtk.Entry()
        self.attach(self._scrolled_window, 1, 1, 1, 1)
        self.attach(self._top_header, 1, 0, 1, 1)
        self.attach(self._left_header, 0, 1, 1, 1)
        self.attach(self._entry, 0, 2, 2, 1)

        self.create_cells()
        self._active = (1, 1)
        self._cell_grid.get_child_at(*self._active).get_style_context().add_class('active')

        self._mode = None
        self.mode = 'cell'

        self.props.can_focus = True
        self.connect('key-press-event', self.on_key_press)
        self.connect('realize', self.on_realize)
        self.show_all()

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        self._cell_grid.get_child_at(*self._active).get_style_context().remove_class('active')
        self._active = value
        self._cell_grid.get_child_at(*self._active).get_style_context().add_class('active')

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, m):
        if m not in ['cell', 'all', 'column', 'row']:
            raise RuntimeError('Worksheet mode should be one of'
                               '[\'cell\', \'column\', \'row\', \'all\']')

        self._mode = m
        self._status['mode'] = m


    def on_realize(self, widget):
        self.grab_focus()

    def on_key_press(self, widget, event):
        mode_change = {
            Gdk.KEY_c: 'column',
            Gdk.KEY_r: 'row',
            Gdk.KEY_a: 'all',
            Gdk.KEY_Escape: 'cell'
        }.get(event.keyval, None)

        if mode_change:
            self.mode = mode_change
            return True

        delta = {
            Gdk.KEY_Up:    ( 0, -1),
            Gdk.KEY_Down:  ( 0,  1),
            Gdk.KEY_Left:  (-1,  0),
            Gdk.KEY_Right: ( 1,  0)
        }.get(event.keyval, None)

        if delta:
            next = (
                max(0, min(len(self._columns) - 1, self._active[0] + delta[0])),
                max(0, min(    self._n_rows   - 1, self._active[1] + delta[1])))
            self.active = next
            return True
        else:
            return False

    def create_cells(self):
        for j in range(self._n_rows):
            for i in range(len(self._columns)):
                label = Gtk.Label.new('---')
                label.props.width_request = 100
                label.props.ypad = 1
                label.get_style_context().add_class('sheet')
                label.get_style_context().add_class('cell')
                self._cell_grid.attach(label, i, j, 1, 1)


class Window(Gtk.Window):
    def __init__(self):
        super(Window, self).__init__(title='Udon')
        self.set_default_size(1024, 720)

        # style
        self._style_provider = Gtk.CssProvider()
        self._style_provider.load_from_path('style.css')
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), self._style_provider, 0)

        # header bar
        self._header_bar = Gtk.HeaderBar()
        self._header_bar.set_show_close_button(True)
        self._header_bar.props.title = 'Udon Noodles'
        self._header_bar.props.subtitle = 'your reactive functional thought assistant'
        self.set_titlebar(self._header_bar)

        self._status_bar = Status()
        # work sheet
        self._work_sheet = WorkSheet(self._status_bar, 30, 100)

        # editor
        self._editor = Editor()

        # notebook
        self._notebook = Gtk.Notebook()
        self._notebook.append_page(self._work_sheet, Gtk.Label.new('Work sheet'))
        self._notebook.append_page(self._editor, Gtk.Label.new('Editor'))

        self._vbox = Gtk.VBox()
        self._vbox.pack_start(self._notebook, expand=True, fill=True, padding=0)
        self._vbox.pack_end(self._status_bar, expand=False, fill=True, padding=0)

        self.add(self._vbox)
        self.show_all()


if __name__ == '__main__':
    window = Window()
    window.connect('delete-event', Gtk.main_quit)
    Gtk.main()