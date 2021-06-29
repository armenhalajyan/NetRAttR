try:
    from intermine.webservice import Service
    from intermine.model import ModelError
    import os
    import pandas as pd
    import sys
    import tkinter as tk
    import tkinter.ttk as ttk
    import tkinter.filedialog as fd
    import tkinter.messagebox as messagebox

except ImportError as error:
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror(title=repr(error), message="One or more of the dependencies could not be imported\n"
                                                        "{}".format(repr(error)))
    except ImportError:
        raise SystemExit(repr(error))

service_urls = {
    'Drosophila melanogaster': "https://www.flymine.org/query/service",
    'Danio rerio': "https://zmine.zfin.org/service",
    'Caenorhabditis elegans': "https://intermine.wormbase.org/tools/wormmine/service",
    'Rattus norvegicus': "https://ratmine.org/ratmine/service",
    'Mus musculus': "https://www.mousemine.org/mousemine/service",
    'Homo sapiens': "https://www.humanmine.org/humanmine/service",
}


def intermine_query(ids, organism, *args):
    service = Service(service_urls[organism])
    query = service.new_query("Gene", case_sensitive=True)
    query.add_constraint("Gene", "LOOKUP", ids, code="A")
    query.add_constraint("organism.name", "=", organism, code="B")
    query.select(*args)
    return query


class Network:
    """
        Iterable container for wheels
        Organism will be set when the first element is added
        Download will be set when the first element is added (this way if the database does not have interaction
        data, we can turn off the integration and continue with the standalone mode)"""

    container = []
    index = -1

    def __init__(self, download=False):
        self.download = download

    def append(self, wheel):
        self.container.append(wheel)
        if len(self.container) == 1:
            self.organism = wheel.organism

    def __iter__(self):
        """Makes Network an Iterator"""
        return self

    def __next__(self):
        """Iterates over the container"""
        self.index += 1
        if self.index >= len(self.container):
            raise StopIteration
        return self.container[self.index]

    def __getitem__(self, item):
        return self.container[item]

    def __setitem__(self, key, value):
        self.container[key] = value


class Wheel:
    def __init__(self, info):
        self.organism = info['organism']
        self.core = info['core']
        self.technique = info['technique']
        self.ids = list(info['ids'])
        self.ids.append(self.core)
        self.download = info['download']

    def update_core(self):
        # make an intermine query with the core genes information
        query = intermine_query(self.core, self.organism, [
                                'primaryIdentifier', 'secondaryIdentifier', 'symbol'])

        self.core = pd.DataFrame(list(query.rows()), columns=[
                                 'primaryIdentifier', 'secondaryIdentifier', 'symbol'])

    def update_primaries(self):
        query = intermine_query(','.join(str(item) for item in list(self.ids)), self.organism,
                                ['symbol', 'secondaryIdentifier',
                                'primaryIdentifier'])

        self.primary_interactors_df = pd.DataFrame(list(query.rows()), columns=['symbol', 'secondaryIdentifier',
                                                                                'primaryIdentifier'])

        self.primary_interactors_df['interactions.details.type'] = self.technique

        new_cols = list(self.primary_interactors_df.columns)
        new_cols = new_cols[-1:] + new_cols[:-1]

        self.primary_interactors_df = self.primary_interactors_df[new_cols]

    def get_secondaries(self):
        query = intermine_query(','.join(str(item) for item in list(self.ids)), self.organism,
                                ['primaryIdentifier', 'secondaryIdentifier',
                                'symbol', 'interactions.details.type',
                                 'interactions.participant2.symbol',
                                 'interactions.participant2.'
                                 'secondaryIdentifier',
                                 'interactions.participant2.',
                                 'primaryIdentifier'])

        self.secondary_interactors_df = pd.DataFrame(list(query.rows()), columns=["Source Primary Identifier",
                                                                                  "Source Secondary Identifier",
                                                                                  "Source Symbol",
                                                                                  "Interaction",
                                                                                  "Target Symbol",
                                                                                  "Target Secondary Identifier",
                                                                                  "Target Primary Identifier"
                                                                                  ])

    def convert_to_dataframe(self):

        self.dataframe = pd.concat([pd.concat([self.core] * self.primary_interactors_df.shape[0], ignore_index=True),
                                    self.primary_interactors_df], axis=1, ignore_index=True)

        self.dataframe.columns = [
            "Source Primary Identifier",
            "Source Secondary Identifier",
            "Source Symbol",
            "Interaction",
            "Target Symbol",
            "Target Secondary Identifier",
            "Target Primary Identifier"
        ]

        if hasattr(self, 'secondary_interactors_df'):
            self.dataframe = self.dataframe.append(
                self.secondary_interactors_df, ignore_index=True)


class GUI(tk.Tk):
    """
    GUI is a tkinter graphical user interface
    """

    def __init__(self, controller, *args, **kwargs):
        # each frame is written as a separate method and called at initialization

        tk.Tk.__init__(self, *args, **kwargs)
        self.title("NetR")

        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.dataset_name(row=0, column=0)
        self.file_submission(row=1, column=0)
        self.combobox_organism(row=2, column=0)
        self.core(row=3, column=0)
        self.technique(row=4, column=0)
        self.header_checkbutton_frame(row=5, column=0)
        self.dataset_reference(row=6, column=0)
        self.buttons(row=7, column=0)

    def dataset_name(self, row, column):
        dn_frame = ttk.Frame(self)
        dn_frame.grid(row=row, column=column, sticky='nsew')
        ttk.Label(dn_frame, text="DataSet name:").grid(
            row=0, column=0, sticky='w')
        self.dataset_name_var = tk.StringVar()
        dataset_name_entry = ttk.Entry(
            dn_frame, textvariable=self.dataset_name_var)
        dataset_name_entry.grid(row=1, column=0, sticky='w')

    def file_submission(self, row, column):
        file_frame = ttk.Frame(self)
        file_frame.grid(row=row, column=column, sticky='nsew')
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path,
                  state='readonly').grid(row=0, column=0, sticky='w')
        ttk.Button(file_frame, text="Open File",
                   command=lambda: browse(self.file_path)).grid(row=0, column=1, sticky='e')

        def browse(text_var):
            file = fd.askopenfilename()
            if file:
                text_var.set(file)

    def combobox_organism(self, row, column):
        organism_frame = ttk.Frame(self)
        organism_frame.grid(row=row, column=column, sticky='nsew')
        ttk.Label(organism_frame, text="Organism:").grid(
            row=0, column=0, sticky='w')
        self.org_name = tk.StringVar()
        combobox_values = tuple(sorted(service_urls.keys()))
        self.organism_picker = ttk.Combobox(organism_frame, values=combobox_values,
                                            textvariable=self.org_name, width=18, state='readonly')

        self.organism_picker.set(
            combobox_values[combobox_values.index("Drosophila melanogaster")])
        self.organism_picker.grid(row=1, column=0, sticky='w')

    def core(self, row, column):
        c_frame = ttk.Frame(self)
        c_frame.grid(row=row, column=column, sticky='nsew')
        ttk.Label(c_frame, text="Core gene symbol:").grid(
            row=0, column=0, sticky='w')
        self.core_var = tk.StringVar()
        core_entry = ttk.Entry(c_frame, textvariable=self.core_var)
        core_entry.grid(row=1, column=0, sticky='ew')

    def technique(self, row, column):
        self.technique_frame = ttk.Frame(self)
        self.technique_frame.grid(row=row, column=column, sticky='nsew')
        ttk.Label(self.technique_frame, text="Technique:").grid(
            row=0, column=0, sticky='w')
        self.technique_var = tk.StringVar()
        self.technique_entry = ttk.Entry(
            self.technique_frame, textvariable=self.technique_var)
        self.technique_entry.grid(row=1, column=0, sticky='ew')

    def header_checkbutton_frame(self, row, column):
        frame = ttk.Frame(self)
        frame.grid(row=row, column=column, sticky='nsew', columnspan=3)

        self.header = tk.BooleanVar()
        self.header_checkbutton = ttk.Checkbutton(frame, variable=self.header,
                                                  text="Check if the file has a header.")
        self.header_checkbutton.grid(row=1, column=0, sticky='w')

    def dataset_reference(self, row, column):
        dataset_reference_frame = ttk.Frame(self)
        dataset_reference_frame.grid(row=row, column=column, sticky='nsew')
        self.dataset_ref = "Data sets added: "
        self.dataset_ref_label = ttk.Label(
            dataset_reference_frame, text=self.dataset_ref)
        self.dataset_ref_label.grid(row=0, column=0, sticky='w')

    def buttons(self, row, column):
        button_frame = ttk.Frame(self)
        button_frame.grid(row=row, column=column, sticky='nsew')

        ttk.Button(button_frame, text="Reset", command=self.controller.reset).grid(
            row=0, column=0, sticky='e')
        ttk.Button(button_frame, text="Clear", command=self.clear).grid(
            row=0, column=1, sticky='e')
        ttk.Button(button_frame, text="Submit", command=self.submit1).grid(
            row=0, column=2, sticky='e')

    def validate_core_gene(self):
        query = intermine_query(self.core_var.get(), self.org_name.get(),
                                ['primaryIdentifier', 'secondaryIdentifier', 'symbol'])

        if query.count == 0:
            messagebox.showinfo(
                message='Invalid core gene identifier. Please enter a valid core gene identifier.')
            self.core_var.set("")
            return False

        return True

    def submit1(self):
        """After the User has entered all the information and pressed submit1, this method is called. User-input is
        stored in the 'self.info' dictionary under the appropriate keys. The file is read and  converted to a dataframe
        and based on this dataframe a preview window is generated that allows the user to select the correct column(s).
        This column information is used to trim the dataframe and only include the selected columns. The trimmed
        dataframe is stored in self.info['DataFrame']. Finally, 'self.info' is passed to NetR for further processing"""

        if self.validate_core_gene():
            self.controller.info.update({
                'dataset_name': self.dataset_name_var.get(),
                'organism': self.org_name.get(),
                'core': self.core_var.get(),
                'technique': self.technique_var.get(),
                'ids': None,
            })

            # if the user has selected a file it is read into a DataFrame
            if self.file_path.get() is not None:
                if self.header.get():
                    df = pd.read_csv(self.file_path.get())
                else:
                    df = pd.read_csv(self.file_path.get(), header=None)
                Preview(self, df)

    def submit2(self):
        if 'download' not in self.controller.info.keys():
            self.controller.info['download'] = messagebox.askyesno(message="Would you like to integrate "
                                                                           "interaction data from InterMine?")

            # Check that the selected InterMine has interaction data
            if self.controller.info['download']:
                try:
                    intermine_query(self.controller.info['ids'], self.controller.info['organism'],
                                    ['primaryIdentifier', 'secondaryIdentifier',
                                     'symbol', 'interactions.details.type',
                                     'interactions.participant2.symbol',
                                     'interactions.participant2.'
                                     'secondaryIdentifier',
                                     'interactions.participant2.'
                                     'primaryIdentifier'])
                except ModelError:
                    self.controller.info['download'] = False
                    messagebox.showwarning(title="Interaction data not available for {organism}. "
                                                 "The network will be made without integrating "
                                                 "intermine data.".format(organism=self.controller.info['organism']))

            self.controller.wheels.download = self.controller.info['download']

        # a Wheel object is created based on self.info and stored in a Network object
        self.controller.add_wheel(self.controller.info)

        # a Label is displayed at the bottom of the GUI, listing all dataset names
        self.dataset_ref += self.controller.info['dataset_name'] + ","
        self.dataset_ref_label.config(text=self.dataset_ref)

        # the User is asked whether they want to add another dataset or start processing the data
        answer = messagebox.askyesno(message="You have submitted {}."
                                             " Would you like to add "
                                             "another one?".format(self.dataset_name_var.get()))

        self.clear()

        self.organism_picker.config(state='disabled')

        if not answer:
            # once the user has submitted all the datasets all fields are cleared and NetR
            # is signaled by calling the first method for processing the data

            self.controller.make_network()

    def clear(self):
        self.dataset_name_var.set("")
        self.file_path.set("")
        self.core_var.set("")
        self.technique_var.set("")
        self.header.set(False)


class Preview(tk.Toplevel):
    def __init__(self, parent, table):
        tk.Toplevel.__init__(self, parent)

        self.controller = parent
        self.table = table

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky='nsew')

        bottom_frame = ttk.Frame(self)
        bottom_frame.grid(row=2, column=0, sticky='nsew')

        self.columns = []
        self.columns_to_use = []

        for column in range(table.head().shape[1]):
            button = ttk.Button(table_frame, text=table.columns[column])
            button.configure(command=lambda x=button: self.toggle_column(x))
            self.columns.append(button)
            button.grid(row=0, column=column)

            for row in range(table.head().shape[0]):
                ttk.Label(table_frame, text=table.iloc[row, column]).grid(row=row + 1, column=column,
                                                                          padx=2, pady=2, sticky='nsew')

        ttk.Button(bottom_frame, text='Okay', command=self.okay).grid(
            row=0, column=table.head().shape[1], sticky='e')

    def select_column(self, button_ref):
        style = ttk.Style()

        self.columns_to_use.append(self.columns.index(button_ref))
        style.configure('selected.TButton', font=(
            'Sans', '12', 'bold underline'))
        button_ref.configure(style='selected.TButton')

    def deselect_column(self, button_ref):
        self.columns_to_use.remove(self.columns.index(button_ref))
        button_ref.configure(style='TButton')

    def toggle_column(self, button_ref):
        if self.columns.index(button_ref) in self.columns_to_use:
            self.deselect_column(button_ref)
        else:
            self.select_column(button_ref)

    def okay(self):
        self.controller.controller.info['ids'] = pd.concat((self.table.iloc[:,
                                                            col].str.strip() for col in self.columns_to_use),
                                                           ignore_index=True)
        self.state('withdrawn')
        self.controller.submit2()


class NetR:
    info = {}  # self.info stores all the information submitted by the user for the current dataset

    # a container for Wheels
    wheels = Network()

    def __init__(self):
        # The graphical interface is launched by instantiating a GUI object
        self.gui = GUI(self)
        self.gui.mainloop()

    def add_wheel(self, info):
        self.wheels.append(Wheel(info))

    def make_network(self):
        # for each user-submitted wheel
        try:
            for wheel in self.wheels:
                wheel.update_core()
                wheel.update_primaries()
                if self.wheels.download:
                    wheel.get_secondaries()
                wheel.convert_to_dataframe()

            self.master_dataframe = pd.concat(
                [wheel.dataframe for wheel in self.wheels.container])
        except ValueError as ve:
            if str(ve) == 'No objects to concatenate':
                self.master_dataframe = self.wheels[0].dataframe
            else:
                raise ve

        self.master_dataframe.to_csv(fd.asksaveasfilename(
            defaultextension='.csv'), index=False)
        self.reset()

    @staticmethod
    def reset():
        python = sys.executable
        sys.stdout.flush()
        os.execl(python, python, *sys.argv)


if __name__ == '__main__':
    # a NetR object is created
    run = NetR()
