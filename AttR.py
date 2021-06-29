from intermine.webservice import Service
from intermine.model import ModelError
import os
import pandas as pd
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox

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


class GUI(tk.Tk):
    def __init__(self, controller, *args, **kwargs):
        # each frame is written as a separate method and called at initialization

        tk.Tk.__init__(self, *args, **kwargs)
        self.title("AttR")

        self.container = ttk.Frame(self)
        self.container.grid(row=0, column=0, sticky='nsew')

        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.combobox_organism(0, 0)
        self.netr_submission(1, 0)
        self.attribute_submission(2, 0)
        self.table_type_radiobuttons(3, 0)
        self.header_checkbutton_frame(4, 0)
        self.buttons(5, 0)

    @staticmethod
    def browse(text_var):
        file = fd.askopenfilename()
        if file:
            text_var.set(file)

    def combobox_organism(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='nsew')
        ttk.Label(frame, text="Organism:        ").grid(
            row=0, column=0, sticky='w')
        self.org_name = tk.StringVar()
        combobox_values = tuple(sorted(service_urls.keys()))
        self.organism_picker = ttk.Combobox(frame, values=combobox_values,
                                            textvariable=self.org_name, width=39, state='readonly')

        self.organism_picker.set(
            combobox_values[combobox_values.index("Drosophila melanogaster")])
        self.organism_picker.grid(row=0, column=1, sticky='w')

    def netr_submission(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='nsew')

        ttk.Label(frame, text="NetR Table:      ").grid(
            row=0, column=0, sticky='w')

        self.netr_filepath = tk.StringVar()
        ttk.Entry(frame, textvariable=self.netr_filepath,
                  state='readonly', width=30).grid(row=0, column=1, sticky='w')

        self.netr_submission_button = ttk.Button(frame, text="Open File",
                                                 command=lambda: self.browse(self.netr_filepath))
        self.netr_submission_button.grid(row=0, column=2, sticky='e')

    def attribute_submission(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='nsew')

        ttk.Label(frame, text="Attribute Table:").grid(
            row=0, column=0, sticky='w')

        self.attribute_filepath = tk.StringVar()
        ttk.Entry(frame, textvariable=self.attribute_filepath, state='readonly', width=30).grid(row=0, column=1,
                                                                                                sticky='w')

        ttk.Button(frame, text="Open File",
                   command=lambda: self.browse(self.attribute_filepath)).grid(row=0, column=2, sticky='e')

    def table_type_radiobuttons(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='nsew')

        ttk.Label(frame, text="Please select the type of attribute table you are submitting.").grid(row=0, column=0,
                                                                                                    sticky='nsew')

        self.table_type = tk.StringVar()

        self.radiobuttons = (ttk.Radiobutton(frame,
                                             text="List (Each column in the table represents a list of genes that "
                                                  "share a\ngiven attribute)",
                                             variable=self.table_type, value='List'),
                             ttk.Radiobutton(frame,
                                             text="\nDiscrete/Continuous values (One of the columns represents\nthe "
                                                  "Mapping Key and the "
                                                  "rest of the columns contain either discrete\nor continuous "
                                                  "values associated with "
                                                  "the gene on that row.)\n",
                                             variable=self.table_type, value='Discrete/Continuous'))
        for row, radiobutton in enumerate(self.radiobuttons):
            radiobutton.grid(row=row + 1, column=0, sticky='nsew')

    def header_checkbutton_frame(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='nsew', columnspan=3)

        ttk.Separator(frame).grid(row=0, column=0, sticky='nsew', columnspan=3)

        self.header = tk.BooleanVar()
        self.header_checkbutton = ttk.Checkbutton(frame, variable=self.header,
                                                  text="Check if the attribute table has a header.")
        self.header_checkbutton.grid(row=1, column=0, sticky='w')

    def buttons(self, row, column):
        frame = ttk.Frame(self.container)
        frame.grid(row=row, column=column, sticky='e')

        ttk.Button(frame, text="Reset", command=self.controller.reset).grid(
            row=0, column=0, sticky='e')
        ttk.Button(frame, text="Clear", command=self.clear).grid(
            row=0, column=1, sticky='e')
        ttk.Button(frame, text="Submit", command=self.submit1).grid(
            row=0, column=2, sticky='e')

    def clear(self):
        self.netr_filepath.set('')
        self.attribute_filepath.set('')
        self.header_checkbutton.state(['!selected'])
        for radiobutton in self.radiobuttons:
            radiobutton.state(['!selected'])

    def submit1(self):
        if self.netr_filepath.get():
            netr_df = pd.read_csv(self.netr_filepath.get())
            self.controller.info['NetR DataFrame'] = netr_df
            self.controller.info['Organism'] = self.org_name.get()

            if self.attribute_filepath.get():
                if self.header.get():
                    attribute_df = pd.read_csv(self.attribute_filepath.get())
                else:
                    attribute_df = pd.read_csv(
                        self.attribute_filepath.get(), header=None)
                AttributePreview(self, attribute_df,
                                 self.header.get(), self.table_type.get())

            else:
                messagebox.showwarning(
                    message="Please, provide a valid path to the Attribute table")
                self.netr_filepath.set('')
                self.attribute_filepath.set('')

        else:
            messagebox.showwarning(
                message="Please, provide a valid path to the NetR table")
            self.netr_filepath.set('')
            self.attribute_filepath.set('')

    def submit2(self):
        another_attribute_table = messagebox.askyesno(
            message="Would you like to add another attribute table?")

        if another_attribute_table:
            self.organism_picker.state(['disabled'])
            self.netr_submission_button.state(['disabled'])
            self.attribute_filepath.set('')
            self.header_checkbutton.state(['!selected'])

            for radiobutton in self.radiobuttons:
                radiobutton.state(['!selected'])

        else:
            self.controller.make_attribute_table()


class AttributePreview(tk.Toplevel):
    def __init__(self, parent, table, header, table_type):
        tk.Toplevel.__init__(self, parent)

        self.controller = parent

        self.container = ttk.Frame(self)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(1, weight=1)
        self.container.pack(fill='both', expand=True)

        self.table = table
        self.table_type = table_type
        self.header = header

        self.mapping_key_column = tk.IntVar()

        self.column_names = []

        self.table_preview(1, 0)

        self.bottom_frame(3, 0)

    def table_preview(self, row, col):
        # https://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-group-of-widgets-in-tkinter

        canvas = tk.Canvas(self.container, width='2i', height='2i')

        frame = ttk.Frame(canvas)

        self.horizontal_scrollbar = ttk.Scrollbar(
            self.container, orient='horizontal', command=canvas.xview)
        self.horizontal_scrollbar.grid(row=2, column=0, sticky='ew')

        canvas.configure(xscrollcommand=self.horizontal_scrollbar.set)

        for table_column in range(self.table.head().shape[1]):
            headings_frame = ttk.Frame(frame)
            headings_frame.grid(row=1, column=table_column)

            entry_var = tk.StringVar()
            entry = ttk.Entry(headings_frame, textvariable=entry_var)
            entry.grid(row=0, column=1, sticky='e')

            if self.header:
                entry_var.set(self.table.columns[table_column])

            self.column_names.append(entry_var)

            if self.table_type == 'Discrete/Continuous':
                ttk.Radiobutton(headings_frame, variable=self.mapping_key_column, value=table_column).grid(row=0,
                                                                                                           column=0,
                                                                                                           sticky='w')

            for table_row in range(self.table.head().shape[0]):
                ttk.Label(frame, text=self.table.iat[table_row, table_column]).grid(row=table_row + 2,
                                                                                    column=table_column,
                                                                                    padx=2, pady=2)

        def onFrameConfigure(event):
            """Reset the scroll region to encompass the inner frame"""
            canvas.configure(scrollregion=canvas.bbox('all'))

        canvas.bind("<Configure>", onFrameConfigure)

        canvas.create_window((0, 0), window=frame, tags='frame', anchor='nw')

        print(canvas.bbox('all'))

        canvas.grid(row=row, column=col, sticky='nsew')

    def bottom_frame(self, row, column):
        frame = ttk.Frame(self.container)

        frame.grid(row=row, column=column, sticky='e')

        ttk.Button(frame, text='Okay', command=self.okay).grid(row=0, column=1)

    def okay(self):
        # For Lists we just need the user to name the columns (if they want to exclude a column, leave blank ).
        # and for Discrete/Continuous we will need the user to name the column and pick the Mapping Key

        # CONSIDER moving this to submit1
        self.controller.controller.create_node_dataframe()

        def create_mapping_key_synonym_dataframe():
            mapping_key = self.table['Mapping Key'].tolist()
            query = intermine_query(','.join(mapping_key),
                                    self.controller.controller.info['Organism'], 'synonyms.value',
                                    'symbol')

            synonym_dataframe = pd.DataFrame(list(query.rows()), columns=[
                                             'Synonyms', 'Updated Mapping Key'])

            symbol_df = pd.concat(
                [synonym_dataframe['Updated Mapping Key']] * 2, axis=1)
            symbol_df.columns = ['Synonyms', 'Updated Mapping Key']

            synonym_dataframe = pd.concat([synonym_dataframe, symbol_df], axis=0,
                                          ignore_index=True)
            synonym_dataframe.drop_duplicates(subset='Synonyms', inplace=True)

            return synonym_dataframe

        def remove_unnamed_columns():
            try:
                # try to drop any columns with blank names
                self.table.drop([''], axis=1, inplace=True)

            except ValueError:
                # if there are no blank column names, do nothing
                pass

            except KeyError:
                pass

        def list_attributes():
            # if the table is a List

            # remove unnamed columns
            self.table.columns = [name.get() for name in self.column_names]
            remove_unnamed_columns()

            # update the ids and append the attribute to List attributes
            for column, name in enumerate(self.table.columns):
                query = intermine_query(','.join(str(item) for item in list(self.table.iloc[:, column])),
                                        self.controller.controller.info['Organism'], 'symbol')

                self.controller.controller.info['List Attributes'].append(
                    pd.Series([row['symbol'] for row in query.rows()],
                              name=name))

        def discrete_continuous_attributes():
            # if table type is Discrete/Continuous

            # change the column name of the Mapping key column to 'Mapping Key' and remove unnamed columns
            self.column_names[self.mapping_key_column.get()].set('Mapping Key')
            self.table.columns = [name.get() for name in self.column_names]
            remove_unnamed_columns()

            nodes = self.controller.controller.nodes

            # reduces the attribute table to rows relevant for the  provided network table
            self.table = self.table[self.table['Mapping Key'].isin(nodes['Synonyms']) |
                                    self.table['Mapping Key'].isin(nodes['Symbol'])]

            # update gene ids
            updated_key = create_mapping_key_synonym_dataframe()
            self.table = self.table.merge(updated_key, how='left', left_on='Mapping Key',
                                          right_on='Synonyms')
            self.table.drop(['Mapping Key', 'Synonyms'], axis=1, inplace=True)
            self.table.rename(
                columns={'Updated Mapping Key': 'Mapping Key'}, inplace=True)

            # store
            self.controller.controller.info['Discrete and Continuous Attributes'] = self.controller.controller.info[
                'Discrete and Continuous Attributes'].merge(self.table, how='outer', on='Mapping Key')

        if self.table_type == 'List':
            list_attributes()
        elif self.table_type == 'Discrete/Continuous':
            discrete_continuous_attributes()

        self.withdraw()
        self.controller.submit2()


class AttR:
    """ info contains:
       'Organism' (string),
       'NetR DataFrame' (pandas dataframe)
       'List Attributes' (list of pandas Series each of which is a list of gene identifiers)
       'Discrete and Continuous Attributes' (pandas DataFrame which has a mix of discrete and/or
                                             continuous values along with the corresponding Mapping Key column as
                                             index)"""
    info = {'NetR DataFrame': pd.DataFrame(),
            'List Attributes': [],
            'Discrete and Continuous Attributes': pd.DataFrame(columns=['Mapping Key']),
            'Organism': ''}

    def __init__(self):
        # The graphical interface is launched by instantiating a GUI object
        self.gui = GUI(self)
        self.gui.mainloop()

    @staticmethod
    def reset():
        python = sys.executable
        sys.stdout.flush()
        os.execl(python, python, *sys.argv)

    def extract_primary_ids_from_netr(self):
        primary_ids_df = pd.concat([self.info['NetR DataFrame'].iloc[:, 0],
                                    self.info['NetR DataFrame'].iloc[:, 6]],
                                   ignore_index=True)
        primary_ids_list = primary_ids_df.tolist()

        return ','.join(str(this_id) for this_id in primary_ids_list)

    def create_node_dataframe(self):
        query = intermine_query(self.extract_primary_ids_from_netr(),
                                self.info['Organism'], 'synonyms.value', 'symbol')

        self.nodes = pd.DataFrame(list(query.rows()), columns=[
                                  'Synonyms', 'Symbol'])

    def make_attribute_table(self):

        self.output = self.nodes['Symbol'].to_frame(
            name='Mapping Key').drop_duplicates()

        # if there is at least 1 submitted Discrete/Continuous Dataset, left merge the output and combined
        # discrete/continuous dataframe (all discrete/continuous dataframes were combined into a single dataframe as
        # they were being submitted
        if not self.info['Discrete and Continuous Attributes'].empty:
            self.output = self.output.merge(self.info['Discrete and Continuous Attributes'], how='left',
                                            on='Mapping Key')

        # for each list attribute add a new column to the output dataframe, containing boolean values, indicating
        # whether the given gene was found in the submitted attribute list
        for attribute in self.info['List Attributes']:
            result = self.output['Mapping Key'].isin(attribute)
            result.name = attribute.name

            self.output = pd.concat([self.output, result], axis=1)

        # export the dataframe as a CSV file
        self.export_table()

    def export_table(self):
        self.output.set_index('Mapping Key', inplace=True)
        self.output.to_csv(fd.asksaveasfile(defaultextension='csv'))

        self.reset()


if __name__ == '__main__':
    # an AttR object is created
    run = AttR()
