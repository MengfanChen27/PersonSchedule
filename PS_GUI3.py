import tkinter as tk
from tkinter import ttk, messagebox, StringVar, DoubleVar, IntVar
import pandas as pd
from Formulation_PS import optimize_osd_schedule, optimize_osd_schedule_with_total, optimize_max_batches
from Dispensing_PS import optimize_dispensing
from Granulation_PS import optimize_granulation
from  Tab_PS import optimize_tableting
from Coating_PS import optimize_coating
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
from datetime import datetime

class ModernProductionSchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Production Scheduler Optimizer")
        
        # Set minimum window size
        self.root.minsize(1000, 600)
        
        # Set theme colors
        self.colors = {
            'primary': '#2c3e50',    # Dark blue-gray
            'secondary': '#3498db',   # Blue
            'accent': '#e74c3c',      # Red
            'bg': '#f5f6fa',         # Light gray
            'text': '#2c3e50',       # Dark blue-gray
            'success': '#2ecc71',    # Green
            'warning': '#f1c40f'     # Yellow
        }
        
        # Add default values
        self.default_values = {
            'buffer_percentage': 15.0,
            'days_limit': 30,
            'morning_weight': 0.0,
            'evening_weight': 0.01,
            'night_weight': 0.3,
            'max_staff': 30,
            'total_batches': 50
        }
        
        # Initialize variables BEFORE creating the layout
        self.initialize_variables()
        
        # Configure the root window
        self.root.configure(bg=self.colors['bg'])
        
        # Setup styles
        self.setup_styles()
        
        # Create main layout AFTER initializing variables
        self.create_main_layout()

        # Add dictionary to store scenarios
        self.scenarios = {}
        
        # Add scenario comparison button to each tab
        self.add_scenario_buttons()

    def setup_styles(self):
        """Configure ttk styles for widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure common styles
        style.configure('Main.TFrame', background=self.colors['bg'])
        style.configure('Header.TLabel', 
                       font=('Helvetica', 24, 'bold'),
                       foreground=self.colors['primary'],
                       background=self.colors['bg'])
        style.configure('Description.TLabel',
                       font=('Helvetica', 12),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        style.configure('Tab.TFrame', background=self.colors['bg'])
        
        # Configure Notebook style with larger font
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', 
                       padding=[12, 8],    # Increased padding
                       font=('Helvetica', 12, 'bold'))  # Increased font size and made bold

    def create_main_layout(self):
        """Create the main layout of the application"""
        # Create a canvas with scrollbar for the main content
        self.canvas = tk.Canvas(self.root, bg=self.colors['bg'])
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        
        # Main container that will hold all content
        self.main_frame = ttk.Frame(self.canvas, style='Main.TFrame')
        
        # Configure the canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create a window in the canvas for the main frame
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        
        # Header section
        self.create_header()
        
        # Notebook (tabs container)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create tabs
        self.create_individual_tab()
        self.create_uniform_tab()
        self.create_maximum_tab()
        
        # Configure scrolling
        self.main_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """When the canvas is resized, resize the window within it too"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_header(self):
        """Create the header section with title and description"""
        header_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        header_frame.pack(fill=tk.X, pady=10)
        
        # Title
        title = ttk.Label(header_frame, 
                         text="Production Scheduler Optimizer",
                         style='Header.TLabel')
        title.pack(anchor='center')
        
        # Description
        description = ttk.Label(header_frame,
                              text="Optimize your production scheduling with efficient staff allocation and resource management",
                              style='Description.TLabel',
                              wraplength=800)
        description.pack(anchor='center', pady=5)

    def create_individual_tab(self):
        """Create the Individual Processes tab"""
        tab = ttk.Frame(self.notebook, style='Tab.TFrame')
        self.notebook.add(tab, text='Individual Processes')
        
        # Add description
        desc = ttk.Label(tab,
                        text="Calculate minimum staff requirements for each process based on individual batch demands",
                        style='Description.TLabel',
                        wraplength=700)
        desc.pack(pady=10)
        
        # Content will be added later
        self.create_individual_content(tab)

    def create_uniform_tab(self):
        """Create the Uniform Production tab"""
        tab = ttk.Frame(self.notebook, style='Tab.TFrame')
        self.notebook.add(tab, text='Uniform Production')
        
        # Add description
        desc = ttk.Label(tab,
                        text="Calculate minimum staff requirements when all processes need to produce the same number of batches",
                        style='Description.TLabel',
                        wraplength=700)
        desc.pack(pady=10)
        
        # Content will be added later
        self.create_uniform_content(tab)

    def create_maximum_tab(self):
        """Create the Maximum Production tab"""
        tab = ttk.Frame(self.notebook, style='Tab.TFrame')
        self.notebook.add(tab, text='Maximum Production')
        
        # Add description
        desc = ttk.Label(tab,
                        text="Calculate the maximum number of batches that can be produced with given resources and time constraints",
                        style='Description.TLabel',
                        wraplength=700)
        desc.pack(pady=10)
        
        # Content will be added later
        self.create_maximum_content(tab)

    def initialize_variables(self):
        """Initialize all variables for input fields with validation"""
        # Process demands (positive integers)
        self.disp_batches_var = IntVar(value=10)
        self.gran_batches_var = IntVar(value=10)
        self.tab_batches_var = IntVar(value=10)
        self.coat_batches_var = IntVar(value=10)
        self.total_batches_var = IntVar(value=self.default_values['total_batches'])
        
        # Common parameters
        self.buffer_var = DoubleVar(value=self.default_values['buffer_percentage'])
        self.days_var = IntVar(value=self.default_values['days_limit'])
        self.max_staff_var = IntVar(value=self.default_values['max_staff'])
        
        # Shift weights (non-negative floats)
        self.morning_weight_var = DoubleVar(value=self.default_values['morning_weight'])
        self.evening_weight_var = DoubleVar(value=self.default_values['evening_weight'])
        self.night_weight_var = DoubleVar(value=self.default_values['night_weight'])
        
        # Machine selection variables
        self.machine_vars = {
            'p3030': tk.BooleanVar(value=True),
            'p3090i': tk.BooleanVar(value=True),
            'ima': tk.BooleanVar(value=True),
            'bosch': tk.BooleanVar(value=True),
            'glatt': tk.BooleanVar(value=True)
        }

    def create_input_field(self, parent, label, variable, default_value, tooltip=None, validation_type=None):
        """Create a labeled input field with validation and visual feedback"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        # Label
        ttk.Label(frame, text=label, width=20).pack(side='left')
        
        # Container for entry and validation icon
        entry_container = ttk.Frame(frame)
        entry_container.pack(side='left', fill='x', expand=True)
        
        # Entry field
        entry = ttk.Entry(entry_container, textvariable=variable)
        entry.pack(side='left', fill='x', expand=True)
        
        # Validation icon (initially hidden)
        validation_label = ttk.Label(entry_container, text='')
        validation_label.pack(side='left', padx=5)
        
        # Add validation based on type
        if validation_type:
            def validate(value=None):
                if value is None:
                    value = variable.get()
                
                try:
                    if validation_type == 'positive_int':
                        val = int(value)
                        if val < 0:
                            raise ValueError("Value must be positive")
                        validation_label.configure(text='✓', foreground='green')
                        return True
                        
                    elif validation_type == 'positive_float':
                        val = float(value)
                        if val < 0:
                            raise ValueError("Value cannot be negative")
                        validation_label.configure(text='✓', foreground='green')
                        return True
                        
                    elif validation_type == 'percentage':
                        val = float(value)
                        if val < 0 or val > 100:
                            raise ValueError("Percentage must be between 0 and 100")
                        validation_label.configure(text='✓', foreground='green')
                        return True
                        
                    elif validation_type == 'weight':
                        val = float(value)
                        if val < 0:
                            raise ValueError("Weight cannot be negative")
                        validation_label.configure(text='✓', foreground='green')
                        return True
                        
                except ValueError as e:
                    validation_label.configure(text='✗', foreground='red')
                    self.create_tooltip(validation_label, str(e))
                    return False
            
            # Register validation
            vcmd = (parent.register(validate), '%P')
            entry.configure(validate='key', validatecommand=vcmd)
            
            # Also validate initial value
            validate(variable.get())
            
            # Add trace to variable for continuous validation
            def trace_callback(*args):
                validate()
            variable.trace_add('write', trace_callback)
        
        # Add tooltip if provided
        if tooltip:
            self.create_tooltip(entry, tooltip)
        
        return entry

    def add_placeholder(self, entry, placeholder):
        """Add placeholder text behavior to entry widget"""
        if not entry.get():  # Only add placeholder if entry is empty
            entry.insert(0, placeholder)
            entry.configure(foreground='gray')
        
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, 'end')
                entry.configure(foreground='black')
                
        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(foreground='gray')
                
        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    def create_tooltip(self, widget, text):
        """Create tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background="#ffffe0", 
                            relief='solid', borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.after(2000, hide_tooltip)
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def create_individual_content(self, parent):
        """Create content for Individual Processes tab with validation"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Process demands section
        demands_frame = ttk.LabelFrame(content_frame, text="Process Demands")
        demands_frame.pack(fill='x', pady=10)
        
        self.create_input_field(
            demands_frame, 
            "Dispensing Batches:", 
            self.disp_batches_var, 
            10,
            "Number of batches required for Dispensing",
            validation_type='positive_int'
        )
        
        self.create_input_field(
            demands_frame, 
            "Granulation Batches:", 
            self.gran_batches_var, 
            10,
            "Number of batches required for Granulation",
            validation_type='positive_int'
        )
        
        self.create_input_field(
            demands_frame, 
            "Tableting Batches:", 
            self.tab_batches_var, 
            10,
            "Number of batches required for Tableting",
            validation_type='positive_int'
        )
        
        self.create_input_field(
            demands_frame, 
            "Coating Batches:", 
            self.coat_batches_var, 
            10,
            "Number of batches required for Coating",
            validation_type='positive_int'
        )
        
        # Common parameters section
        self.create_common_parameters(content_frame)
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x', pady=10)
        
        calculate_button = ttk.Button(
            button_frame, 
            text="Calculate", 
            command=self.calculate_individual
        )
        calculate_button.pack(side='left', padx=5)
        
        clear_button = ttk.Button(
            button_frame, 
            text="Clear", 
            command=self.clear_individual
        )
        clear_button.pack(side='left', padx=5)

    def create_uniform_content(self, parent):
        """Create content for Uniform Production tab"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Total batches section
        batches_frame = ttk.LabelFrame(content_frame, text="Total Production")
        batches_frame.pack(fill='x', pady=10)
        
        # Create entry field for total batches with integer validation
        total_batches_entry = self.create_input_field(
            batches_frame, 
            "Total Batches:", 
            self.total_batches_var, 
            50,
            "Total number of batches to produce (must be an integer)",
            validation_type='positive_int'
        )
        
        # Add integer validation
        def validate_integer(P):
            if P == "": return True
            try:
                int(P)
                return True
            except ValueError:
                return False
        
        vcmd = (self.root.register(validate_integer), '%P')
        total_batches_entry.configure(validate='key', validatecommand=vcmd)
        
        # Common parameters section
        self.create_common_parameters(content_frame)
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x', pady=10)
        ttk.Button(button_frame, text="Calculate", 
                  command=self.calculate_uniform).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_uniform).pack(side='left', padx=5)

    def create_maximum_content(self, parent):
        """Create content for Maximum Production tab"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Staff constraints section
        staff_frame = ttk.LabelFrame(content_frame, text="Staff Constraints")
        staff_frame.pack(fill='x', pady=10)
        
        self.create_input_field(staff_frame, "Maximum Staff:", 
                              self.max_staff_var, 30,
                              "Maximum number of staff available",
                              validation_type='positive_int'
        )
        
        # Common parameters section
        self.create_common_parameters(content_frame)
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x', pady=10)
        ttk.Button(button_frame, text="Calculate Maximum", 
                  command=self.calculate_maximum).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_maximum).pack(side='left', padx=5)

    def create_common_parameters(self, parent):
        """Create common parameters section with validation"""
        params_frame = ttk.LabelFrame(parent, text="Common Parameters")
        params_frame.pack(fill='x', pady=10)
        
        # Basic parameters with validation
        self.create_input_field(
            params_frame, 
            "Buffer Percentage (%):", 
            self.buffer_var, 
            15.0,
            "Extra staff percentage to add as buffer",
            validation_type='percentage'
        )
        
        self.create_input_field(
            params_frame, 
            "Days Limit:", 
            self.days_var, 
            30,
            "Maximum number of days for production",
            validation_type='positive_int'
        )
        
        # Machine selection section
        self.create_machine_selection(params_frame)
        
        # Shift weights with validation
        weights_frame = ttk.LabelFrame(params_frame, text="Shift Weights")
        weights_frame.pack(fill='x', padx=5, pady=5)
        
        self.create_input_field(
            weights_frame, 
            "Morning Weight:", 
            self.morning_weight_var, 
            0.0,
            "Cost multiplier for morning shifts (non-negative)",
            validation_type='weight'
        )
        
        self.create_input_field(
            weights_frame, 
            "Evening Weight:", 
            self.evening_weight_var, 
            0.01,
            "Cost multiplier for evening shifts (non-negative)",
            validation_type='weight'
        )
        
        self.create_input_field(
            weights_frame, 
            "Night Weight:", 
            self.night_weight_var, 
            0.3,
            "Cost multiplier for night shifts (non-negative)",
            validation_type='weight'
        )

    def create_machine_selection(self, parent):
        """Create machine selection section with checkboxes"""
        machines_frame = ttk.LabelFrame(parent, text="Machine Selection")
        machines_frame.pack(fill='x', padx=5, pady=5)
        
        # Create two sub-frames for Tableting and Coating machines
        tableting_frame = ttk.LabelFrame(machines_frame, text="Tableting Machines")
        tableting_frame.pack(fill='x', padx=5, pady=5)
        
        coating_frame = ttk.LabelFrame(machines_frame, text="Coating Machines")
        coating_frame.pack(fill='x', padx=5, pady=5)
        
        # Tableting machines
        ttk.Checkbutton(tableting_frame, text="P3030 (1 batch/shift)", 
                        variable=self.machine_vars['p3030']).pack(anchor='w', padx=5)
        ttk.Checkbutton(tableting_frame, text="P3090i (2 batches/shift)", 
                        variable=self.machine_vars['p3090i']).pack(anchor='w', padx=5)
        ttk.Checkbutton(tableting_frame, text="IMA (1 batch/shift)", 
                        variable=self.machine_vars['ima']).pack(anchor='w', padx=5)
        
        # Coating machines
        ttk.Checkbutton(coating_frame, text="BOSCH (2 batches/shift)", 
                        variable=self.machine_vars['bosch']).pack(anchor='w', padx=5)
        ttk.Checkbutton(coating_frame, text="GLATT (2 batches/shift)", 
                        variable=self.machine_vars['glatt']).pack(anchor='w', padx=5)

    def calculate_individual(self):
        """Calculate staff requirements for individual processes"""
        try:
            # Get input values
            disp_batches = self.disp_batches_var.get()
            gran_batches = self.gran_batches_var.get()
            tab_batches = self.tab_batches_var.get()
            coat_batches = self.coat_batches_var.get()
            days_limit = self.days_var.get()
            buffer_ratio = self.buffer_var.get() / 100.0  # Convert percentage to decimal
            
            # Get shift weights
            w_morning = self.morning_weight_var.get()
            w_evening = self.evening_weight_var.get()
            w_night = self.night_weight_var.get()
            
            # Get machine selections
            use_p3030 = self.machine_vars['p3030'].get()
            use_p3090i = self.machine_vars['p3090i'].get()
            use_ima = self.machine_vars['ima'].get()
            use_bosch = self.machine_vars['bosch'].get()
            use_glatt = self.machine_vars['glatt'].get()

            # Get the current tab
            current_tab = self.notebook.select()
            current_tab_index = self.notebook.index(current_tab)
            tab_widget = self.notebook.winfo_children()[current_tab_index]

            # Clear previous results if they exist
            self.clear_results()

            # Create new results frame
            self.results_frame = ttk.LabelFrame(tab_widget, text="Results")
            self.results_frame.pack(fill='x', padx=20, pady=10)

            # Run optimizations for each process
            results = {}
            
            # Dispensing
            disp_result = optimize_dispensing(
                batches_required=disp_batches,
                num_workdays=days_limit,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                print_solution=False
            )
            results['Dispensing'] = disp_result

            # Granulation
            gran_result = optimize_granulation(
                batches_required=gran_batches,
                num_workdays=days_limit,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                print_solution=False
            )
            results['Granulation'] = gran_result

            # Tableting
            tab_result = optimize_tableting(
                batches_required=tab_batches,
                num_workdays=days_limit,
                use_p3030=use_p3030,
                use_p3090i=use_p3090i,
                use_ima=use_ima,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                print_solution=False
            )
            results['Tableting'] = tab_result

            # Coating
            coat_result = optimize_coating(
                batches_required=coat_batches,
                num_workdays=days_limit,
                use_bosch=use_bosch,
                use_glatt=use_glatt,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                print_solution=False
            )
            results['Coating'] = coat_result

            # Display results in a table format
            self.create_results_table(results)

            # Update the GUI
            self.root.update_idletasks()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def create_results_table(self, results):
        """Create a table to display optimization results"""
        # Create a container frame for results
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create notebook for tabbed results
        results_notebook = ttk.Notebook(results_container)
        results_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Summary Tab
        summary_tab = ttk.Frame(results_notebook)
        results_notebook.add(summary_tab, text='Summary')
        
        # Create summary table frame
        table_frame = ttk.Frame(summary_tab)
        table_frame.pack(side='left', fill='both', expand=True)
        
        # Create summary Treeview
        columns = ('Process', 'Staff Required', 'With Buffer', 'Days Used', 'Batches Produced', 'Status')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=5)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor='center')
        
        # Add data
        total_staff = 0
        total_staff_with_buffer = 0
        
        for process, result in results.items():
            if result is None:
                tree.insert('', 'end', values=(
                    process, 'N/A', 'N/A', 'N/A', 'N/A', 'Infeasible'
                ))
            else:
                # Get batches produced (handle different key names)
                if process == 'Coating':
                    batches = result['final_batches_count']
                else:
                    batches = result['total_batches_produced']

                tree.insert('', 'end', values=(
                    process,
                    result['min_staff_required'],
                    result['staff_with_buffer'],
                    result['days_used'],
                    batches,
                    'Optimal'
                ))
                total_staff += result['min_staff_required']
                total_staff_with_buffer += result['staff_with_buffer']
        
        # Add scrollbar to summary table
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right side: Total Staff Cards
        cards_frame = ttk.Frame(summary_tab)
        cards_frame.pack(side='right', fill='y', padx=20)
        
        # Style for cards
        style = ttk.Style()
        style.configure('Card.TFrame', background=self.colors['bg'])
        style.configure('CardTitle.TLabel',
                       font=('Helvetica', 14, 'bold'),
                       foreground=self.colors['primary'],
                       background=self.colors['bg'])
        style.configure('CardValue.TLabel',
                       font=('Helvetica', 24, 'bold'),
                       foreground=self.colors['secondary'],
                       background=self.colors['bg'])
        
        # Cards for key metrics - removed Total Days Used as requested
        metrics = [
            ("Minimum Staff Required", total_staff),
            ("Staff with Buffer", total_staff_with_buffer)
        ]
        
        for title, value in metrics:
            card = ttk.Frame(cards_frame, style='Card.TFrame', relief='solid')
            card.pack(fill='x', pady=10, ipady=10)
            
            ttk.Label(card, text=title, style='CardTitle.TLabel').pack(pady=(5, 0))
            ttk.Label(card, text=str(value), style='CardValue.TLabel').pack(pady=5)
        
        # Detailed Results Tab
        detailed_tab = ttk.Frame(results_notebook)
        results_notebook.add(detailed_tab, text='Detailed Results')
        
        # Create detailed results table
        # Set a fixed row height for the treeview to accommodate multiline content
        style.configure("Multiline.Treeview", rowheight=60)  # Increased row height
        detailed_tree = ttk.Treeview(detailed_tab, show='headings', style="Multiline.Treeview", height=5)
        detailed_cols = ('Process', 'Morning Shifts', 'Evening Shifts', 'Night Shifts', 'Machine Details')
        detailed_tree['columns'] = detailed_cols
        
        for col in detailed_cols:
            detailed_tree.heading(col, text=col)
            if col == 'Machine Details':
                detailed_tree.column(col, width=150, anchor='w')  # Left align for better readability
            else:
                detailed_tree.column(col, width=120, anchor='center')
        
        # Add detailed data
        for process, result in results.items():
            if result and result.get('solver_status') == 'Optimal':
                # Get shift data based on process type
                if process in ['Dispensing', 'Granulation']:
                    # Direct access for Dispensing and Granulation
                    morning = result.get('morning_shifts', 0)
                    evening = result.get('evening_shifts', 0)
                    night = result.get('night_shifts', 0)
                    machine_details = "N/A"  # No machine details for these processes
                elif process == 'Tableting':
                    # For Tableting: Count shifts per machine
                    morning_shifts = result.get('morning_shifts', {})
                    evening_shifts = result.get('evening_shifts', {})
                    night_shifts = result.get('night_shifts', {})
                    
                    # Initialize total counts
                    if isinstance(morning_shifts, dict):
                        # Sum shifts per time period
                        morning = sum(morning_shifts.values())
                        evening = sum(evening_shifts.values())
                        night = sum(night_shifts.values())
                        
                        # Count total shifts per machine
                        machine_counts = {}
                        for machine in ['P3030', 'P3090i', 'IMA']:
                            if machine in morning_shifts:
                                machine_counts[machine] = morning_shifts.get(machine, 0) + evening_shifts.get(machine, 0) + night_shifts.get(machine, 0)
                        
                        # Format the machine details string with newlines
                        machine_details_parts = []
                        for machine, count in machine_counts.items():
                            if count > 0:
                                machine_details_parts.append(f"{machine}: {count}")
                        machine_details = "\n".join(machine_details_parts)
                    else:
                        morning = morning_shifts
                        evening = evening_shifts
                        night = night_shifts
                        machine_details = "N/A"
                elif process == 'Coating':
                    # For Coating: Count shifts per machine
                    morning_shifts = result.get('morning_shifts', {})
                    evening_shifts = result.get('evening_shifts', {})
                    night_shifts = result.get('night_shifts', {})
                    
                    if isinstance(morning_shifts, dict):
                        # Sum shifts per time period
                        morning = sum(morning_shifts.values())
                        evening = sum(evening_shifts.values())
                        night = sum(night_shifts.values())
                        
                        # Count total shifts per machine
                        machine_counts = {}
                        for machine in ['Solution', 'BOSCH', 'GLATT']:
                            if machine in morning_shifts:
                                machine_counts[machine] = morning_shifts.get(machine, 0) + evening_shifts.get(machine, 0) + night_shifts.get(machine, 0)
                        
                        # Format the machine details string with newlines
                        machine_details_parts = []
                        for machine, count in machine_counts.items():
                            if count > 0:
                                machine_details_parts.append(f"{machine}: {count}")
                        machine_details = "\n".join(machine_details_parts)
                    else:
                        morning = morning_shifts
                        evening = evening_shifts
                        night = night_shifts
                        machine_details = "N/A"
                
                detailed_tree.insert('', 'end', values=(
                    process,
                    morning,
                    evening,
                    night,
                    machine_details
                ))
        
        # Add scrollbar to detailed table
        detailed_scrollbar = ttk.Scrollbar(detailed_tab, orient='vertical', command=detailed_tree.yview)
        detailed_tree.configure(yscrollcommand=detailed_scrollbar.set)
        detailed_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        detailed_scrollbar.pack(side='right', fill='y')
        
        # Shift Distribution Tab
        shift_tab = ttk.Frame(results_notebook)
        results_notebook.add(shift_tab, text='Shift Distribution')
        
        # Create shift distribution table
        shift_tree = ttk.Treeview(shift_tab, show='headings', height=10)
        shift_cols = ('Process', 'Total Shifts', 'Morning %', 'Evening %', 'Night %')
        shift_tree['columns'] = shift_cols
        
        for col in shift_cols:
            shift_tree.heading(col, text=col)
            shift_tree.column(col, width=120, anchor='center')
        
        # Add shift distribution data
        for process, result in results.items():
            if result and result.get('solver_status') == 'Optimal':
                # Get shift data based on process type
                if process in ['Dispensing', 'Granulation']:
                    # Direct access for Dispensing and Granulation
                    morning = result.get('morning_shifts', 0)
                    evening = result.get('evening_shifts', 0)
                    night = result.get('night_shifts', 0)
                elif process == 'Tableting':
                    # Sum the machines for Tableting
                    morning_shifts = result.get('morning_shifts', {})
                    evening_shifts = result.get('evening_shifts', {})
                    night_shifts = result.get('night_shifts', {})
                    
                    if isinstance(morning_shifts, dict):
                        morning = sum(morning_shifts.values())
                        evening = sum(evening_shifts.values())
                        night = sum(night_shifts.values())
                    else:
                        morning = morning_shifts
                        evening = evening_shifts
                        night = night_shifts
                elif process == 'Coating':
                    # Sum the machines for Coating
                    morning_shifts = result.get('morning_shifts', {})
                    evening_shifts = result.get('evening_shifts', {})
                    night_shifts = result.get('night_shifts', {})
                    
                    if isinstance(morning_shifts, dict):
                        morning = sum(morning_shifts.values())
                        evening = sum(evening_shifts.values())
                        night = sum(night_shifts.values())
                    else:
                        morning = morning_shifts
                        evening = evening_shifts
                        night = night_shifts
                
                total = morning + evening + night
                
                if total > 0:
                    morning_pct = f"{(morning/total)*100:.1f}%"
                    evening_pct = f"{(evening/total)*100:.1f}%"
                    night_pct = f"{(night/total)*100:.1f}%"
                    
                    shift_tree.insert('', 'end', values=(
                        process,
                        total,
                        morning_pct,
                        evening_pct,
                        night_pct
                    ))
        
        # Add scrollbar to shift distribution table
        shift_scrollbar = ttk.Scrollbar(shift_tab, orient='vertical', command=shift_tree.yview)
        shift_tree.configure(yscrollcommand=shift_scrollbar.set)
        shift_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        shift_scrollbar.pack(side='right', fill='y')

    def calculate_uniform(self):
        """Calculate staff requirements for uniform production"""
        try:
            # Get input values
            total_batches = self.total_batches_var.get()
            days_limit = self.days_var.get()
            buffer_ratio = self.buffer_var.get() / 100.0  # Convert percentage to decimal
            
            # Get shift weights
            w_morning = self.morning_weight_var.get()
            w_evening = self.evening_weight_var.get()
            w_night = self.night_weight_var.get()
            
            # Get machine selections
            use_p3030 = self.machine_vars['p3030'].get()
            use_p3090i = self.machine_vars['p3090i'].get()
            use_ima = self.machine_vars['ima'].get()
            use_bosch = self.machine_vars['bosch'].get()
            use_glatt = self.machine_vars['glatt'].get()

            # Get the current tab
            current_tab = self.notebook.select()
            current_tab_index = self.notebook.index(current_tab)
            tab_widget = self.notebook.winfo_children()[current_tab_index]

            # Clear previous results if they exist
            self.clear_results()

            # Create new results frame
            self.results_frame = ttk.LabelFrame(tab_widget, text="Results")
            self.results_frame.pack(fill='x', padx=20, pady=10)

            # Run optimization for uniform production
            result = optimize_osd_schedule_with_total(
                total_batches=total_batches,
                initial_workdays=days_limit,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                use_p3030=use_p3030,
                use_p3090i=use_p3090i,
                use_ima=use_ima,
                use_bosch=use_bosch,
                use_glatt=use_glatt,
                print_combined=False
            )

            if result is None:
                messagebox.showerror("Error", "No feasible solution found. Try increasing the number of days or reducing the batch demand.")
                return

            # Create results container with notebook
            results_container = ttk.Frame(self.results_frame)
            results_container.pack(fill='both', expand=True, padx=5, pady=5)
            
            results_notebook = ttk.Notebook(results_container)
            results_notebook.pack(fill='both', expand=True, padx=5, pady=5)
            
            # Summary Tab
            summary_tab = ttk.Frame(results_notebook)
            results_notebook.add(summary_tab, text='Summary')
            
            # Create summary table frame
            table_frame = ttk.Frame(summary_tab)
            table_frame.pack(side='left', fill='both', expand=True)
            
            # Create summary Treeview
            columns = ('Process', 'Staff Required', 'With Buffer', 'Days Used', 'Batches Produced', 'Status')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=5)
            
            # Configure columns
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor='center')
            
            # Add data for each process
            processes = ['dispensing', 'granulation', 'tableting', 'coating']
            for process in processes:
                process_result = result[process]
                if process == 'coating':
                    batches = process_result['final_batches_count']
                else:
                    batches = process_result['total_batches_produced']
                
                tree.insert('', 'end', values=(
                    process.capitalize(),
                    process_result['min_staff_required'],
                    process_result['staff_with_buffer'],
                    process_result['days_used'],
                    batches,
                    'Optimal'
                ))
            
            # Add scrollbar to summary table
            scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Right side: Summary Cards
            cards_frame = ttk.Frame(summary_tab)
            cards_frame.pack(side='right', fill='y', padx=20)
            
            # Style for cards
            style = ttk.Style()
            style.configure('Card.TFrame', background=self.colors['bg'])
            style.configure('CardTitle.TLabel',
                           font=('Helvetica', 14, 'bold'),
                           foreground=self.colors['primary'],
                           background=self.colors['bg'])
            style.configure('CardValue.TLabel',
                           font=('Helvetica', 24, 'bold'),
                           foreground=self.colors['secondary'],
                           background=self.colors['bg'])
            
            # Cards for key metrics
            metrics = [
                ("Total Staff Required", result['total_min_staff_summed']),
                ("Staff with Buffer", result['total_staff_with_buffer_summed']),
                ("Total Days Needed", result['total_days_needed'])
            ]
            
            for title, value in metrics:
                card = ttk.Frame(cards_frame, style='Card.TFrame', relief='solid')
                card.pack(fill='x', pady=10, ipady=10)
                
                ttk.Label(card, text=title, style='CardTitle.TLabel').pack(pady=(5, 0))
                ttk.Label(card, text=str(value), style='CardValue.TLabel').pack(pady=5)
            
            # Detailed Results Tab
            detailed_tab = ttk.Frame(results_notebook)
            results_notebook.add(detailed_tab, text='Detailed Results')
            
            # Create detailed results table
            # Set a fixed row height for the treeview to accommodate multiline content
            style.configure("Multiline.Treeview", rowheight=60)  # Increased row height
            detailed_tree = ttk.Treeview(detailed_tab, show='headings', style="Multiline.Treeview", height=5)
            detailed_cols = ('Process', 'Morning Shifts', 'Evening Shifts', 'Night Shifts', 'Machine Details')
            detailed_tree['columns'] = detailed_cols
            
            for col in detailed_cols:
                detailed_tree.heading(col, text=col)
                if col == 'Machine Details':
                    detailed_tree.column(col, width=150, anchor='w')  # Left align for better readability
                else:
                    detailed_tree.column(col, width=120, anchor='center')
            
            # Add detailed data
            for process in processes:
                process_result = result[process]
                if process_result and process_result.get('solver_status') == 'Optimal':
                    # Get shift data based on process type
                    if process in ['dispensing', 'granulation']:
                        morning = process_result.get('morning_shifts', 0)
                        evening = process_result.get('evening_shifts', 0)
                        night = process_result.get('night_shifts', 0)
                        machine_details = "N/A"
                    else:
                        morning_shifts = process_result.get('morning_shifts', {})
                        evening_shifts = process_result.get('evening_shifts', {})
                        night_shifts = process_result.get('night_shifts', {})
                        
                        if isinstance(morning_shifts, dict):
                            morning = sum(morning_shifts.values())
                            evening = sum(evening_shifts.values())
                            night = sum(night_shifts.values())
                            
                            # Count total shifts per machine
                            machine_counts = {}
                            machines = ['P3030', 'P3090i', 'IMA'] if process == 'tableting' else ['Solution', 'BOSCH', 'GLATT']
                            for machine in machines:
                                if machine in morning_shifts:
                                    machine_counts[machine] = morning_shifts.get(machine, 0) + evening_shifts.get(machine, 0) + night_shifts.get(machine, 0)
                            
                            # Format machine details string with newlines
                            machine_details = ""
                            for machine, count in machine_counts.items():
                                if count > 0:
                                    if machine_details:
                                        machine_details += "\n"
                                    machine_details += f"{machine}: {count}"
                        else:
                            morning = morning_shifts
                            evening = evening_shifts
                            night = night_shifts
                            machine_details = "N/A"
                    
                    detailed_tree.insert('', 'end', values=(
                        process.capitalize(),
                        morning,
                        evening,
                        night,
                        machine_details
                    ))
            
            # Add scrollbar to detailed table
            detailed_scrollbar = ttk.Scrollbar(detailed_tab, orient='vertical', command=detailed_tree.yview)
            detailed_tree.configure(yscrollcommand=detailed_scrollbar.set)
            detailed_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
            detailed_scrollbar.pack(side='right', fill='y')
            
            # Shift Distribution Tab
            shift_tab = ttk.Frame(results_notebook)
            results_notebook.add(shift_tab, text='Shift Distribution')
            
            # Create shift distribution table
            shift_tree = ttk.Treeview(shift_tab, show='headings', height=10)
            shift_cols = ('Process', 'Total Shifts', 'Morning %', 'Evening %', 'Night %')
            shift_tree['columns'] = shift_cols
            
            for col in shift_cols:
                shift_tree.heading(col, text=col)
                shift_tree.column(col, width=120, anchor='center')
            
            # Add shift distribution data
            for process in processes:
                process_result = result[process]
                if process_result and process_result.get('solver_status') == 'Optimal':
                    if process in ['dispensing', 'granulation']:
                        morning = process_result.get('morning_shifts', 0)
                        evening = process_result.get('evening_shifts', 0)
                        night = process_result.get('night_shifts', 0)
                    else:
                        morning_shifts = process_result.get('morning_shifts', {})
                        evening_shifts = process_result.get('evening_shifts', {})
                        night_shifts = process_result.get('night_shifts', {})
                        
                        if isinstance(morning_shifts, dict):
                            morning = sum(morning_shifts.values())
                            evening = sum(evening_shifts.values())
                            night = sum(night_shifts.values())
                        else:
                            morning = morning_shifts
                            evening = evening_shifts
                            night = night_shifts
                    
                    total = morning + evening + night
                    
                    if total > 0:
                        morning_pct = f"{(morning/total)*100:.1f}%"
                        evening_pct = f"{(evening/total)*100:.1f}%"
                        night_pct = f"{(night/total)*100:.1f}%"
                        
                        shift_tree.insert('', 'end', values=(
                            process.capitalize(),
                            total,
                            morning_pct,
                            evening_pct,
                            night_pct
                        ))
            
            # Add scrollbar to shift distribution table
            shift_scrollbar = ttk.Scrollbar(shift_tab, orient='vertical', command=shift_tree.yview)
            shift_tree.configure(yscrollcommand=shift_scrollbar.set)
            shift_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
            shift_scrollbar.pack(side='right', fill='y')

            # Update the GUI
            self.root.update_idletasks()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def calculate_maximum(self):
        """Calculate maximum batch production with given constraints"""
        try:
            # Get input values
            max_staff = self.max_staff_var.get()
            days_limit = self.days_var.get()
            buffer_ratio = self.buffer_var.get() / 100.0  # Convert percentage to decimal
            
            # Get shift weights
            w_morning = self.morning_weight_var.get()
            w_evening = self.evening_weight_var.get()
            w_night = self.night_weight_var.get()
            
            # Get machine selections
            use_p3030 = self.machine_vars['p3030'].get()
            use_p3090i = self.machine_vars['p3090i'].get()
            use_ima = self.machine_vars['ima'].get()
            use_bosch = self.machine_vars['bosch'].get()
            use_glatt = self.machine_vars['glatt'].get()

            # Get the current tab
            current_tab = self.notebook.select()
            current_tab_index = self.notebook.index(current_tab)
            tab_widget = self.notebook.winfo_children()[current_tab_index]

            # Clear previous results if they exist
            self.clear_results()

            # Create new results frame
            self.results_frame = ttk.LabelFrame(tab_widget, text="Results")
            self.results_frame.pack(fill='x', padx=20, pady=10)

            # Run optimization for maximum production
            result = optimize_max_batches(
                num_workdays=days_limit,
                buffer_ratio=buffer_ratio,
                w_morning=w_morning,
                w_evening=w_evening,
                w_night=w_night,
                use_p3030=use_p3030,
                use_p3090i=use_p3090i,
                use_ima=use_ima,
                use_bosch=use_bosch,
                use_glatt=use_glatt,
                print_solution=False
            )

            if result is None:
                messagebox.showerror("Error", "No feasible solution found. Try adjusting machine selection or increasing the days limit.")
                return

            # Create results container with notebook
            results_container = ttk.Frame(self.results_frame)
            results_container.pack(fill='both', expand=True, padx=5, pady=5)
            
            results_notebook = ttk.Notebook(results_container)
            results_notebook.pack(fill='both', expand=True, padx=5, pady=5)
            
            # Summary Tab
            summary_tab = ttk.Frame(results_notebook)
            results_notebook.add(summary_tab, text='Summary')
            
            # Create summary table frame
            table_frame = ttk.Frame(summary_tab)
            table_frame.pack(side='left', fill='both', expand=True)
            
            # Create summary Treeview
            columns = ('Process', 'Staff Required', 'With Buffer', 'Days Used', 'Batches Produced', 'Status')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=5)
            
            # Configure columns
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor='center')
            
            # Add data for each process
            processes = ['dispensing', 'granulation', 'tableting', 'coating']
            for process in processes:
                process_result = result[process]
                if process == 'coating':
                    batches = process_result['final_batches_count']
                else:
                    batches = process_result['total_batches_produced']
                
                tree.insert('', 'end', values=(
                    process.capitalize(),
                    process_result['min_staff_required'],
                    process_result['staff_with_buffer'],
                    process_result['days_used'],
                    batches,
                    'Optimal'
                ))
            
            # Add scrollbar to summary table
            scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Right side: Summary Cards
            cards_frame = ttk.Frame(summary_tab)
            cards_frame.pack(side='right', fill='y', padx=20)
            
            # Style for cards
            style = ttk.Style()
            style.configure('Card.TFrame', background=self.colors['bg'])
            style.configure('CardTitle.TLabel',
                        font=('Helvetica', 14, 'bold'),
                        foreground=self.colors['primary'],
                        background=self.colors['bg'])
            style.configure('CardValue.TLabel',
                        font=('Helvetica', 24, 'bold'),
                        foreground=self.colors['secondary'],
                        background=self.colors['bg'])
            
            # Cards for key metrics
            metrics = [
                ("Maximum Batches", result['max_feasible_batches']),
                ("Total Staff Required", result['total_min_staff_summed']),
                ("Staff with Buffer", result['total_staff_with_buffer_summed'])
            ]
            
            for title, value in metrics:
                card = ttk.Frame(cards_frame, style='Card.TFrame', relief='solid')
                card.pack(fill='x', pady=10, ipady=10)
                
                ttk.Label(card, text=title, style='CardTitle.TLabel').pack(pady=(5, 0))
                ttk.Label(card, text=str(value), style='CardValue.TLabel').pack(pady=5)
            
            # Detailed Results Tab
            detailed_tab = ttk.Frame(results_notebook)
            results_notebook.add(detailed_tab, text='Detailed Results')
            
            # Create detailed results table
            # Set a fixed row height for the treeview to accommodate multiline content
            style.configure("Multiline.Treeview", rowheight=60)  # Increased row height
            detailed_tree = ttk.Treeview(detailed_tab, show='headings', style="Multiline.Treeview", height=5)
            detailed_cols = ('Process', 'Morning Shifts', 'Evening Shifts', 'Night Shifts', 'Machine Details')
            detailed_tree['columns'] = detailed_cols
            
            for col in detailed_cols:
                detailed_tree.heading(col, text=col)
                if col == 'Machine Details':
                    detailed_tree.column(col, width=150, anchor='w')  # Left align for better readability
                else:
                    detailed_tree.column(col, width=120, anchor='center')
            
            # Add detailed data
            for process in processes:
                process_result = result[process]
                if process_result and process_result.get('solver_status') == 'Optimal':
                    # Get shift data based on process type
                    if process in ['dispensing', 'granulation']:
                        morning = process_result.get('morning_shifts', 0)
                        evening = process_result.get('evening_shifts', 0)
                        night = process_result.get('night_shifts', 0)
                        machine_details = "N/A"
                    else:
                        morning_shifts = process_result.get('morning_shifts', {})
                        evening_shifts = process_result.get('evening_shifts', {})
                        night_shifts = process_result.get('night_shifts', {})
                        
                        if isinstance(morning_shifts, dict):
                            morning = sum(morning_shifts.values())
                            evening = sum(evening_shifts.values())
                            night = sum(night_shifts.values())
                            
                            # Count total shifts per machine
                            machine_counts = {}
                            machines = ['P3030', 'P3090i', 'IMA'] if process == 'tableting' else ['Solution', 'BOSCH', 'GLATT']
                            for machine in machines:
                                if machine in morning_shifts:
                                    machine_counts[machine] = morning_shifts.get(machine, 0) + evening_shifts.get(machine, 0) + night_shifts.get(machine, 0)
                            
                            # Format machine details string with newlines
                            machine_details = ""
                            for machine, count in machine_counts.items():
                                if count > 0:
                                    if machine_details:
                                        machine_details += "\n"
                                    machine_details += f"{machine}: {count}"
                        else:
                            morning = morning_shifts
                            evening = evening_shifts
                            night = night_shifts
                            machine_details = "N/A"
                    
                    detailed_tree.insert('', 'end', values=(
                        process.capitalize(),
                        morning,
                        evening,
                        night,
                        machine_details
                    ))
            
            # Add scrollbar to detailed table
            detailed_scrollbar = ttk.Scrollbar(detailed_tab, orient='vertical', command=detailed_tree.yview)
            detailed_tree.configure(yscrollcommand=detailed_scrollbar.set)
            detailed_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
            detailed_scrollbar.pack(side='right', fill='y')
            
            # Shift Distribution Tab
            shift_tab = ttk.Frame(results_notebook)
            results_notebook.add(shift_tab, text='Shift Distribution')
            
            # Create shift distribution table
            shift_tree = ttk.Treeview(shift_tab, show='headings', height=10)
            shift_cols = ('Process', 'Total Shifts', 'Morning %', 'Evening %', 'Night %')
            shift_tree['columns'] = shift_cols
            
            for col in shift_cols:
                shift_tree.heading(col, text=col)
                shift_tree.column(col, width=120, anchor='center')
            
            # Add shift distribution data
            for process in processes:
                process_result = result[process]
                if process_result and process_result.get('solver_status') == 'Optimal':
                    if process in ['dispensing', 'granulation']:
                        morning = process_result.get('morning_shifts', 0)
                        evening = process_result.get('evening_shifts', 0)
                        night = process_result.get('night_shifts', 0)
                    else:
                        morning_shifts = process_result.get('morning_shifts', {})
                        evening_shifts = process_result.get('evening_shifts', {})
                        night_shifts = process_result.get('night_shifts', {})
                        
                        if isinstance(morning_shifts, dict):
                            morning = sum(morning_shifts.values())
                            evening = sum(evening_shifts.values())
                            night = sum(night_shifts.values())
                        else:
                            morning = morning_shifts
                            evening = evening_shifts
                            night = night_shifts
                    
                    total = morning + evening + night
                    
                    if total > 0:
                        morning_pct = f"{(morning/total)*100:.1f}%"
                        evening_pct = f"{(evening/total)*100:.1f}%"
                        night_pct = f"{(night/total)*100:.1f}%"
                        
                        shift_tree.insert('', 'end', values=(
                            process.capitalize(),
                            total,
                            morning_pct,
                            evening_pct,
                            night_pct
                        ))
            
            # Add scrollbar to shift distribution table
            shift_scrollbar = ttk.Scrollbar(shift_tab, orient='vertical', command=shift_tree.yview)
            shift_tree.configure(yscrollcommand=shift_scrollbar.set)
            shift_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
            shift_scrollbar.pack(side='right', fill='y')

            # Update the GUI
            self.root.update_idletasks()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def clear_results(self):
        """Helper method to safely clear results frame"""
        try:
            if hasattr(self, 'results_frame') and self.results_frame is not None:
                if self.results_frame.winfo_exists():
                    self.results_frame.destroy()
                self.results_frame = None
        except Exception:
            # If any error occurs during cleanup, ensure results_frame is None
            self.results_frame = None

    def clear_individual(self):
        """Clear results and reset input fields for individual processes"""
        try:
            # Reset input fields to default values
            self.disp_batches_var.set(10)
            self.gran_batches_var.set(10)
            self.tab_batches_var.set(10)
            self.coat_batches_var.set(10)
            
            # Reset common parameters to defaults
            self.buffer_var.set(self.default_values['buffer_percentage'])
            self.days_var.set(self.default_values['days_limit'])
            
            # Reset shift weights to defaults
            self.morning_weight_var.set(self.default_values['morning_weight'])
            self.evening_weight_var.set(self.default_values['evening_weight'])
            self.night_weight_var.set(self.default_values['night_weight'])
            
            # Reset machine selections to checked
            for machine in self.machine_vars:
                self.machine_vars[machine].set(True)
            
            # Clear results
            self.clear_results()
            
            # Update the GUI
            self.root.update_idletasks()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while clearing: {str(e)}")

    def clear_uniform(self):
        """Clear results and reset input fields for uniform production"""
        try:
            # Reset input fields to default values
            self.total_batches_var.set(self.default_values['total_batches'])
            
            # Reset common parameters to defaults
            self.buffer_var.set(self.default_values['buffer_percentage'])
            self.days_var.set(self.default_values['days_limit'])
            
            # Reset shift weights to defaults
            self.morning_weight_var.set(self.default_values['morning_weight'])
            self.evening_weight_var.set(self.default_values['evening_weight'])
            self.night_weight_var.set(self.default_values['night_weight'])
            
            # Reset machine selections to checked
            for machine in self.machine_vars:
                self.machine_vars[machine].set(True)
            
            # Clear results
            self.clear_results()
            
            # Update the GUI
            self.root.update_idletasks()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while clearing: {str(e)}")

    def clear_maximum(self):
        """Clear results and reset input fields for maximum capacity calculation"""
        try:
            # Reset days limit to default
            self.days_var.set(self.default_values.get('days_limit', 30))
            
            # Reset buffer percentage to default
            self.buffer_var.set(self.default_values.get('buffer_percentage', 20))
            
            # Reset shift weights to defaults
            self.morning_weight_var.set(self.default_values.get('morning_weight', 0.0))
            self.evening_weight_var.set(self.default_values.get('evening_weight', 0.1))
            self.night_weight_var.set(self.default_values.get('night_weight', 2.0))
            
            # Reset machine selections to default (all True)
            for machine in ['p3030', 'p3090i', 'ima', 'bosch', 'glatt']:
                if hasattr(self, 'machine_vars') and machine in self.machine_vars:
                    self.machine_vars[machine].set(True)
            
            # Clear results
            self.clear_results()
            
            # Update the GUI
            self.root.update_idletasks()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while clearing: {str(e)}")

    def add_scenario_buttons(self):
        """Add Save, Compare, and Clear Scenarios buttons to each tab"""
        for tab_index in range(3):  # For each of our three tabs
            tab = self.notebook.winfo_children()[tab_index]
            button_frame = ttk.Frame(tab)
            button_frame.pack(side='bottom', fill='x', padx=20, pady=10)
            
            ttk.Button(
                button_frame,
                text="Save Scenario",
                command=lambda t=tab_index: self.save_scenario(t)
            ).pack(side='left', padx=5)
            
            ttk.Button(
                button_frame,
                text="Compare Scenarios",
                command=self.show_comparison
            ).pack(side='left', padx=5)
            
            ttk.Button(
                button_frame,
                text="Clear All Scenarios",
                command=self.clear_all_scenarios
            ).pack(side='left', padx=5)

    def save_scenario(self, tab_index):
        """Save current parameters and results as a scenario"""
        try:
            # Get current timestamp for scenario ID
            scenario_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get tab type
            tab_types = ['Individual', 'Uniform', 'Maximum']
            tab_type = tab_types[tab_index]
            
            # Create scenario data structure
            scenario = {
                'id': scenario_id,
                'type': tab_type,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'parameters': self.get_current_parameters(tab_type),
                'results': self.get_current_results()
            }
            
            # Save scenario
            self.scenarios[scenario_id] = scenario
            
            messagebox.showinfo(
                "Success",
                f"Scenario saved successfully!\nScenario ID: {scenario_id}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save scenario: {str(e)}")

    def get_current_parameters(self, tab_type):
        """Get current parameter values based on tab type"""
        params = {
            'buffer_percentage': self.buffer_var.get(),
            'days_limit': self.days_var.get(),
            'morning_weight': self.morning_weight_var.get(),
            'evening_weight': self.evening_weight_var.get(),
            'night_weight': self.night_weight_var.get(),
            'machine_selection': {
                name: var.get() for name, var in self.machine_vars.items()
            }
        }
        
        if tab_type == 'Individual':
            params.update({
                'disp_batches': self.disp_batches_var.get(),
                'gran_batches': self.gran_batches_var.get(),
                'tab_batches': self.tab_batches_var.get(),
                'coat_batches': self.coat_batches_var.get()
            })
        elif tab_type == 'Uniform':
            params['total_batches'] = self.total_batches_var.get()
        elif tab_type == 'Maximum':
            params['max_staff'] = self.max_staff_var.get()
        
        return params

    def get_current_results(self):
        """Get current results if available"""
        if not hasattr(self, 'results_frame') or self.results_frame is None:
            return None
        
        try:
            # Find the results notebook and get the summary tab
            for child in self.results_frame.winfo_children():
                if isinstance(child, ttk.Frame):  # Results container
                    for notebook_child in child.winfo_children():
                        if isinstance(notebook_child, ttk.Notebook):  # Results notebook
                            summary_tab = notebook_child.winfo_children()[0]  # First tab is summary
                            
                            # Find the treeview in the summary tab
                            for tab_child in summary_tab.winfo_children():
                                if isinstance(tab_child, ttk.Frame):  # Table frame
                                    for frame_child in tab_child.winfo_children():
                                        if isinstance(frame_child, ttk.Treeview):
                                            tree = frame_child
                                            
                                            # Get the total values from all processes
                                            total_staff = 0
                                            total_staff_buffer = 0
                                            total_days = 0
                                            total_batches = 0
                                            
                                            # Sum up values from each process
                                            for item in tree.get_children():
                                                values = tree.item(item)['values']
                                                if values[1] != 'N/A':  # Skip infeasible results
                                                    total_staff += int(values[1])  # Staff Required
                                                    total_staff_buffer += int(values[2])  # With Buffer
                                                    total_days = max(total_days, int(values[3]))  # Days Used
                                                    total_batches += int(values[4])  # Batches Produced
                                            
                                            return {
                                                'staff_required': total_staff,
                                                'staff_with_buffer': total_staff_buffer,
                                                'days_used': total_days,
                                                'batches_produced': total_batches
                                            }
        
            return None
        except Exception as e:
            print(f"Error extracting results: {str(e)}")
            return None

    def show_comparison(self):
        """Show comparison window for saved scenarios"""
        if not self.scenarios:
            messagebox.showwarning(
                "No Scenarios",
                "No scenarios have been saved yet. Please save some scenarios first."
            )
            return
        
        # Create comparison window
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title("Scenario Comparison")
        comparison_window.geometry("1000x800")
        
        # Create notebook for different comparison views
        notebook = ttk.Notebook(comparison_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs for different comparison views
        self.create_table_comparison_tab(notebook)
        self.create_chart_comparison_tab(notebook)

    def create_table_comparison_tab(self, notebook):
        """Create tab for table comparison view"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='Table View')
        
        # Create Treeview for comparison
        columns = ('Scenario', 'Type', 'Time', 'Staff Required', 'Staff with Buffer', 
                  'Days Used', 'Batches Produced')
        tree = ttk.Treeview(tab, columns=columns, show='headings')
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        # Add data
        for scenario_id, scenario in self.scenarios.items():
            results = scenario['results']
            if results:
                tree.insert('', 'end', values=(
                    scenario_id,
                    scenario['type'],
                    scenario['timestamp'],
                    results.get('staff_required', 'N/A'),
                    results.get('staff_with_buffer', 'N/A'),
                    results.get('days_used', 'N/A'),
                    results.get('batches_produced', 'N/A')
                ))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_chart_comparison_tab(self, notebook):
        """Create tab for chart comparison view"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text='Chart View')
        
        # Create Figure and Canvas
        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvasTkAgg(fig, master=tab)
        
        # Create subplots for different metrics
        axes = fig.subplots(2, 2)
        fig.suptitle('Scenario Comparison')
        
        # Plot data
        scenario_labels = list(self.scenarios.keys())
        metrics = {
            'Staff Required': [s['results'].get('staff_required', 0) for s in self.scenarios.values()],
            'Staff with Buffer': [s['results'].get('staff_with_buffer', 0) for s in self.scenarios.values()],
            'Days Used': [s['results'].get('days_used', 0) for s in self.scenarios.values()],
            'Batches Produced': [s['results'].get('batches_produced', 0) for s in self.scenarios.values()]
        }
        
        for (i, j), (metric, values) in zip([(0,0), (0,1), (1,0), (1,1)], metrics.items()):
            axes[i,j].bar(range(len(scenario_labels)), values)
            axes[i,j].set_title(metric)
            axes[i,j].set_xticks(range(len(scenario_labels)))
            axes[i,j].set_xticklabels(scenario_labels, rotation=45)
        
        fig.tight_layout()
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def clear_all_scenarios(self):
        """Clear all saved scenarios after confirmation"""
        if not self.scenarios:
            messagebox.showinfo("Info", "No scenarios to clear.")
            return
        
        # Ask for confirmation before clearing
        confirm = messagebox.askyesno(
            "Confirm Clear",
            "Are you sure you want to delete all saved scenarios? This action cannot be undone."
        )
        
        if confirm:
            # Clear the scenarios dictionary
            self.scenarios.clear()
            
            # Close any open comparison windows
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.winfo_name().startswith('!toplevel'):
                    widget.destroy()
            
            # Force garbage collection to free memory
            import gc
            gc.collect()
            
            messagebox.showinfo("Success", "All scenarios have been cleared.")

def main():
    """Main function to run the application"""
    try:
        # Create the root window
        root = tk.Tk()
        
        # Set window size and position
        window_width = 1200
        window_height = 800
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Create the application
        app = ModernProductionSchedulerGUI(root)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
