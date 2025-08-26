import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import ctypes # For DPI awareness on Windows
import sys # Added for PyInstaller path handling

# --- DPI Awareness for Windows ---
try:
    # This makes the app DPI aware, preventing blurring on high-DPI screens
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # Or 2 for Per Monitor DPI Aware
except AttributeError:
    pass # Not on Windows or pre-Windows 8.1, so ignore

# --- Tooltip Class ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Arial", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tw:
            self.tw.destroy()
        self.tw = None

# --- Main Application Class ---
class DPSCalculatorApp:
    def __init__(self, master):
        self.master = master
        master.title("DPS Calculator")
        master.geometry("580x700") # Changed default window size to 580x700

        self.themes = {
            "light": {
                "root_bg": "#f0f0f0", "fg_color": "black", "frame_bg": "#f0f0f0",
                "entry_bg": "white", "entry_fg": "black", "button_bg": "#e0e0e0",
                "button_fg": "black", "tree_bg": "#f0f0f0", "tree_fg": "black",
                "tree_heading_bg": "#cccccc", "tree_heading_fg": "black",
                "tree_even_row": "#e6e6e6", "tree_odd_row": "#f2f2f2",
                "tree_selected_bg": "#aed6f1",
                "info_text_fg": "#555555"
            }
        }
        self.current_theme = "light"

        self.header_font = ("Arial", 12, "bold")
        self.label_font = ("Arial", 10)
        self.info_label_font = ("Arial", 9, "italic")
        self.result_font = ("Consolas", 9)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        master.configure(bg=self.themes[self.current_theme]["root_bg"])

        self.modifications = {
            "Powerful (+50% damage)": {"type": "DMG", "value": 0.50},
            "Lightning (-35% cooldown)": {"type": "CD", "value": 0.35},
            "Executor (+60% crit dmg)": {"type": "CDMG", "value": 0.60},
            "Assassin (+35% crit chance)": {"type": "CC", "value": 0.35},
            "Trickster (-20% cooldown)": {"type": "CD", "value": 0.20},
            "BodyBuilder (+25% damage)": {"type": "DMG", "value": 0.25},
            "Accurate (+20% crit chance)": {"type": "CC", "value": 0.20},
            "Strong (+10% damage)": {"type": "DMG", "value": 0.10},
            "Fast (-10% cooldown)": {"type": "CD", "value": 0.10},
        }

        self.default_units_config = {
            "Medusa lvl 25": {
                "dmg": 145.0,
                "atk_speed": 0.04,
                "crit_chance": 30.0,
                "crit_dmg": 175.0
            },
            # --- FUTURE PRESETS GO HERE ---
            # "Warrior lvl 50": {
            #     "dmg": 180.0,
            #     "atk_speed": 0.06,
            #     "crit_chance": 15.0,
            #     "crit_dmg": 160.0
            # },
        }

        # Determine the correct base path for read/write files when bundled by PyInstaller
        # This will point to the directory where the .exe is located when running as a frozen app.
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(__file__)

        self.units_file = os.path.join(self.app_dir, "dps_units.json")
        self.load_units()
        
        # --- CRITICAL CHANGE: create_widgets() must be called BEFORE functions that use the widgets ---
        self.create_widgets()
        
        self.ensure_default_units()
        self.save_units()
        self.update_unit_combobox() # This line ensures combobox is populated on startup
        self.apply_theme()
        self.calculate_dps()


    def create_widgets(self):
        # --- Section 1: Base Unit Stats ---
        self.stats_frame = tk.LabelFrame(self.master, text="Base Unit Stats", font=self.header_font, padx=10, pady=10)
        self.stats_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.dmg_var = tk.DoubleVar(value=145.0)
        self.atk_speed_var = tk.DoubleVar(value=0.04)
        self.crit_chance_var = tk.DoubleVar(value=30.0)
        self.crit_dmg_var = tk.DoubleVar(value=175.0) # as percentage

        labels_texts = [
            ("Base DMG per hit:", self.dmg_var, "Base damage per hit."),
            ("Attack Speed (s):", self.atk_speed_var, "Time in seconds between attacks (e.g., 0.04s)."),
            ("Crit Chance (%):", self.crit_chance_var, "Critical hit chance in percentage (e.g., 30 for 30%)."),
            ("Crit Damage (%):", self.crit_dmg_var, "Critical damage multiplier in percentage (e.g., 175 for 1.75x base damage).")
        ]

        self.stat_labels = []
        self.stat_entries = []
        for i, (text, var, tooltip_text) in enumerate(labels_texts):
            label = ttk.Label(self.stats_frame, text=text, font=self.label_font)
            label.grid(row=i, column=0, sticky="w", pady=2)
            self.stat_labels.append(label)
            entry = ttk.Entry(self.stats_frame, textvariable=var, width=15, font=self.label_font, style="TEntry")
            entry.grid(row=i, column=1, sticky="ew", pady=2)
            self.stat_entries.append(entry)
            Tooltip(entry, tooltip_text)

        self.calculate_button = ttk.Button(self.stats_frame, text="Calculate All DPS", command=self.calculate_dps, style="TButton")
        self.calculate_button.grid(row=len(labels_texts), column=0, columnspan=2, pady=10, sticky="ew")
        self.clear_button = ttk.Button(self.stats_frame, text="Clear Fields", command=self.clear_fields, style="TButton")
        self.clear_button.grid(row=len(labels_texts)+1, column=0, columnspan=2, pady=5, sticky="ew")


        # --- Section 2: Unit Selector ---
        self.units_frame = tk.LabelFrame(self.master, text="Unit Selector", font=self.header_font, padx=10, pady=10)
        self.units_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ttk.Label(self.units_frame, text="Unit Name:", font=self.label_font).grid(row=0, column=0, sticky="w", pady=2)
        self.unit_name_entry = ttk.Entry(self.units_frame, width=25, font=self.label_font, style="TEntry")
        self.unit_name_entry.grid(row=0, column=1, sticky="ew", pady=2)
        Tooltip(self.unit_name_entry, "Enter a name to save current stats as a new unit configuration.")

        ttk.Label(self.units_frame, text="Select Unit:", font=self.label_font).grid(row=1, column=0, sticky="w", pady=2)
        self.unit_combobox = ttk.Combobox(self.units_frame, width=23, font=self.label_font, state="readonly", style="TCombobox")
        self.unit_combobox.grid(row=1, column=1, sticky="ew", pady=2)
        self.unit_combobox.bind("<<ComboboxSelected>>", self.on_unit_select)

        self.load_unit_button = ttk.Button(self.units_frame, text="Load Unit", command=self.load_selected_unit, style="TButton")
        self.load_unit_button.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        self.save_unit_button = ttk.Button(self.units_frame, text="Save Current Unit", command=self.save_current_unit, style="TButton")
        self.save_unit_button.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        self.delete_unit_button = ttk.Button(self.units_frame, text="Delete Selected Unit", command=self.delete_selected_unit, style="TButton")
        self.delete_unit_button.grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")

        self.units_frame.grid_columnconfigure(1, weight=1)
        self.units_frame.grid_columnconfigure(0, weight=0)

        # --- Section 3: DPS Results (now spanning across full bottom) ---
        self.results_frame = tk.LabelFrame(self.master, text="DPS Results", font=self.header_font, padx=10, pady=10)
        self.results_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.results_info_label = ttk.Label(self.results_frame,
                                            text="All DPS values in this tier list (including 'No Modification') are calculated considering the unit's Critical Chance and Critical Damage.",
                                            font=self.info_label_font,
                                            anchor="w",
                                            wraplength=520) # Adjusted wraplength for 580px width
        self.results_info_label.pack(fill="x", padx=5, pady=(0,5))

        self.base_dps_header_container = tk.Frame(self.results_frame)
        self.base_dps_header_container.pack(fill="x", pady=(0, 5))

        self.base_dps_no_crit_label = ttk.Label(self.base_dps_header_container, text="", font=self.label_font, anchor="w")
        self.base_dps_no_crit_label.pack(fill="x", pady=1)
        self.base_dps_with_crit_label = ttk.Label(self.base_dps_header_container, text="", font=self.label_font, anchor="w")
        self.base_dps_with_crit_label.pack(fill="x", pady=1)

        tree_columns = ("tier", "modification", "total_dps", "percent_change")
        self.results_tree = ttk.Treeview(self.results_frame, columns=tree_columns, show="headings")
        
        self.style.configure("Treeview", font=("Arial", 9))
        self.style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        self.results_tree.tag_configure("evenrow", background=self.themes[self.current_theme]["tree_even_row"], foreground=self.themes[self.current_theme]["tree_fg"])
        self.results_tree.tag_configure("oddrow", background=self.themes[self.current_theme]["tree_odd_row"], foreground=self.themes[self.current_theme]["tree_fg"])
        
        self.results_tree.heading("tier", text="Tier")
        self.results_tree.heading("modification", text="Modification")
        self.results_tree.heading("total_dps", text="Total DPS")
        self.results_tree.heading("percent_change", text="% Change vs Base")

        # Adjusted column widths for the new window size (580px) as per screenshots
        self.results_tree.column("tier", width=40, anchor="center") # Smaller
        self.results_tree.column("modification", width=200, anchor="w")
        self.results_tree.column("total_dps", width=120, anchor="e")
        self.results_tree.column("percent_change", width=160, anchor="e") # Wider

        # --- Dynamic Scrollbars ---
        # Create scrollbars but do not pack/grid them by default.
        vsb = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_tree.yview)
        hsb = ttk.Scrollbar(self.results_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.results_tree.pack(side="left", fill="both", expand=True)

        self.vsb_widget = vsb
        self.hsb_widget = hsb

        self.results_tree.bind("<Configure>", self.check_scrollbars)


        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=2)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        self.stats_frame.grid_columnconfigure(1, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

    def check_scrollbars(self, event=None):
        # Vertical scrollbar
        num_items = len(self.results_tree.get_children())
        row_height = int(self.style.lookup("Treeview", "rowheight")) # Get row height from style
        if row_height == 0: row_height = 25 # Fallback if style not ready

        tree_visible_height = self.results_tree.winfo_height()
        
        # Add a small buffer to prevent scrollbar from flickering
        buffer_rows = 1 # Allow for 1 extra row of content before showing scrollbar

        if num_items * row_height > tree_visible_height + (buffer_rows * row_height): # Check if content overflows significantly
            if not self.vsb_widget.winfo_ismapped():
                self.vsb_widget.pack(side="right", fill="y")
        else:
            if self.vsb_widget.winfo_ismapped():
                self.vsb_widget.pack_forget()

        # Horizontal scrollbar
        total_column_width = sum([self.results_tree.column(col, 'width') for col in self.results_tree['columns']])
        treeview_width = self.results_tree.winfo_width()

        # Add a small buffer to prevent scrollbar from appearing too early/disappearing too late
        buffer_width = 10
        if total_column_width > (treeview_width + buffer_width): # Check if content overflows significantly
            if not self.hsb_widget.winfo_ismapped():
                self.hsb_widget.pack(side="bottom", fill="x")
        else:
            if self.hsb_widget.winfo_ismapped():
                self.hsb_widget.pack_forget()


    def apply_theme(self):
        theme_colors = self.themes[self.current_theme]

        self.master.configure(bg=theme_colors["root_bg"])

        for frame in [self.stats_frame, self.units_frame, self.results_frame]:
            frame.config(bg=theme_colors["frame_bg"], fg=theme_colors["fg_color"])

        for label in self.stat_labels:
            label.config(background=theme_colors["frame_bg"], foreground=theme_colors["fg_color"])
        for widget in self.units_frame.winfo_children():
            if isinstance(widget, ttk.Label):
                widget.config(background=theme_colors["frame_bg"], foreground=theme_colors["fg_color"])
        
        self.results_info_label.config(background=theme_colors["frame_bg"], foreground=theme_colors["info_text_fg"])
        self.base_dps_no_crit_label.config(background=theme_colors["frame_bg"], foreground=theme_colors["fg_color"])
        self.base_dps_with_crit_label.config(background=theme_colors["frame_bg"], foreground=theme_colors["fg_color"])
        self.base_dps_header_container.config(bg=theme_colors["frame_bg"])


        self.style.configure('TEntry',
                             fieldbackground=theme_colors["entry_bg"],
                             foreground=theme_colors["entry_fg"],
                             insertbackground=theme_colors["entry_fg"])
        for entry in self.stat_entries:
            entry.update_idletasks()
        self.unit_name_entry.update_idletasks()


        self.style.configure('TButton',
                             background=theme_colors["button_bg"],
                             foreground=theme_colors["button_fg"],
                             font=self.label_font,
                             relief="raised",
                             borderwidth=1)
        self.style.map('TButton',
                       background=[('active', theme_colors["tree_selected_bg"])],
                       foreground=[('active', theme_colors["fg_color"])])

        self.style.configure('TCombobox',
                             fieldbackground=theme_colors["entry_bg"],
                             background=theme_colors["button_bg"],
                             foreground=theme_colors["entry_fg"],
                             selectbackground=theme_colors["tree_selected_bg"],
                             selectforeground=theme_colors["entry_fg"],
                             arrowcolor=theme_colors["fg_color"],
                             font=self.label_font)
        self.style.map('TCombobox', fieldbackground=[('readonly', theme_colors["entry_bg"])])
        self.style.map('TCombobox', selectbackground=[('readonly', theme_colors["tree_selected_bg"])])
        self.style.map('TCombobox', background=[('readonly', theme_colors["button_bg"])])


        self.style.configure("Treeview",
                             background=theme_colors["tree_bg"],
                             foreground=theme_colors["tree_fg"],
                             fieldbackground=theme_colors["tree_bg"],
                             bordercolor=theme_colors["fg_color"],
                             font=("Arial", 9))
        self.style.configure("Treeview.Heading",
                             background=theme_colors["tree_heading_bg"],
                             foreground=theme_colors["tree_heading_fg"],
                             bordercolor=theme_colors["fg_color"],
                             font=("Arial", 10, "bold"))
        self.style.map('Treeview', background=[('selected', theme_colors["tree_selected_bg"])])

        self.results_tree.tag_configure("evenrow", background=theme_colors["tree_even_row"], foreground=theme_colors["tree_fg"])
        self.results_tree.tag_configure("oddrow", background=theme_colors["tree_odd_row"], foreground=theme_colors["tree_fg"])
        
        self.style.configure("Vertical.TScrollbar", background=theme_colors["button_bg"], troughcolor=theme_colors["frame_bg"], bordercolor=theme_colors["frame_bg"])
        self.style.map("Vertical.TScrollbar", background=[('active', theme_colors["tree_selected_bg"])])
        self.style.configure("Horizontal.TScrollbar", background=theme_colors["button_bg"], troughcolor=theme_colors["frame_bg"], bordercolor=theme_colors["frame_bg"])
        self.style.map("Horizontal.TScrollbar", background=[('active', theme_colors["tree_selected_bg"])])

        self.calculate_dps()


    def clear_fields(self):
        self.dmg_var.set(0.0)
        self.atk_speed_var.set(0.0)
        self.crit_chance_var.set(0.0)
        self.crit_dmg_var.set(0.0)
        self.base_dps_no_crit_label.config(text="")
        self.base_dps_with_crit_label.config(text="")
        self.results_tree.delete(*self.results_tree.get_children())

    def load_units(self):
        if os.path.exists(self.units_file):
            with open(self.units_file, "r") as f:
                try:
                    self.units = json.load(f)
                except json.JSONDecodeError: # Handle empty or corrupt JSON
                    self.units = {}
        else:
            self.units = {}

    def save_units(self):
        with open(self.units_file, "w") as f:
            json.dump(self.units, f, indent=4)

    def ensure_default_units(self):
        default_units_to_ensure = {
            "Medusa lvl 25": {
                "dmg": 145.0,
                "atk_speed": 0.04,
                "crit_chance": 30.0,
                "crit_dmg": 175.0
            },
            # --- FUTURE PRESETS GO HERE ---
            # "Warrior lvl 50": {
            #     "dmg": 180.0,
            #     "atk_speed": 0.06,
            #     "crit_chance": 15.0,
            #     "crit_dmg": 160.0
            # },
        }

        changes_made = False
        for unit_name, unit_stats in default_units_to_ensure.items():
            if unit_name not in self.units:
                self.units[unit_name] = unit_stats
                changes_made = True
        
        if changes_made:
            self.save_units()
            self.update_unit_combobox()
            

    def update_unit_combobox(self):
        self.unit_combobox['values'] = list(self.units.keys())
        if self.units:
            if "Medusa lvl 25" in self.units:
                self.unit_combobox.set("Medusa lvl 25")
            elif list(self.units.keys()):
                self.unit_combobox.set(list(self.units.keys())[0])
            else:
                self.unit_combobox.set("")

    def on_unit_select(self, event):
        pass

    def load_selected_unit(self):
        unit_name = self.unit_combobox.get()
        if unit_name in self.units:
            stats = self.units[unit_name]
            self.dmg_var.set(stats.get("dmg", 0.0))
            self.atk_speed_var.set(stats.get("atk_speed", 0.0))
            self.crit_chance_var.set(stats.get("crit_chance", 0.0))
            self.crit_dmg_var.set(stats.get("crit_dmg", 0.0))
            self.calculate_dps()
        else:
            messagebox.showerror("Error", "Please select a unit to load.")

    def save_current_unit(self):
        unit_name = self.unit_name_entry.get().strip()
        if not unit_name:
            messagebox.showerror("Error", "Please enter a unit name to save.")
            return

        try:
            current_stats = {
                "dmg": self.dmg_var.get(),
                "atk_speed": self.atk_speed_var.get(),
                "crit_chance": self.crit_chance_var.get(),
                "crit_dmg": self.crit_dmg_var.get()
            }
            self.units[unit_name] = current_stats
            self.save_units()
            self.update_unit_combobox()
            self.unit_name_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save unit: {e}")

    def delete_selected_unit(self):
        unit_name = self.unit_combobox.get()
        if unit_name == "Medusa lvl 25":
            messagebox.showwarning("Warning", "The 'Medusa lvl 25' unit cannot be deleted.")
            return

        if unit_name and unit_name in self.units:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete unit '{unit_name}'?"):
                del self.units[unit_name]
                self.save_units()
                self.update_unit_combobox()
                self.clear_fields()
                messagebox.showinfo("Unit Deleted", f"Unit '{unit_name}' has been deleted.")
        else:
            messagebox.showerror("Error", "Please select a unit to delete.")


    def calculate_dps(self):
        try:
            base_dmg = self.dmg_var.get()
            atk_speed = self.atk_speed_var.get()
            crit_chance = self.crit_chance_var.get() / 100.0
            crit_dmg_multiplier = self.crit_dmg_var.get() / 100.0

            if base_dmg <= 0: raise ValueError("Base DMG must be positive.")
            if atk_speed <= 0: raise ValueError("Attack Speed must be positive.")
            if not (0 <= crit_chance <= 1): raise ValueError("Crit Chance must be between 0% and 100%.")
            if crit_dmg_multiplier <= 0: raise ValueError("Crit Damage must be positive.")

            aps_base = 1 / atk_speed
            dps_base_no_crit = base_dmg * aps_base
            crit_dmg_value_base = base_dmg * crit_dmg_multiplier
            dpa_avg_base = ((1 - crit_chance) * base_dmg) + (crit_chance * crit_dmg_value_base)
            dps_base_with_crit = dpa_avg_base * aps_base

            results = []

            for mod_name, mod_data in self.modifications.items():
                temp_dmg = base_dmg
                temp_atk_speed = atk_speed
                temp_crit_chance = crit_chance
                temp_crit_dmg_multiplier = crit_dmg_multiplier

                mod_type = mod_data["type"]
                mod_value = mod_data["value"]

                if mod_type == "DMG":
                    temp_dmg *= (1 + mod_value)
                elif mod_type == "CD":
                    temp_atk_speed *= (1 - mod_value)
                elif mod_type == "CC":
                    temp_crit_chance += mod_value
                    if temp_crit_chance > 1.0: temp_crit_chance = 1.0
                elif mod_type == "CDMG":
                    temp_crit_dmg_multiplier += mod_value
                
                current_aps = 1 / temp_atk_speed
                current_crit_dmg_value = temp_dmg * temp_crit_dmg_multiplier
                current_dpa_avg = ((1 - temp_crit_chance) * temp_dmg) + (temp_crit_chance * current_crit_dmg_value)
                current_dps = current_dpa_avg * current_aps
                
                results.append({"name": mod_name, "dps": current_dps})

            results.append({"name": "No Modification", "dps": dps_base_with_crit})

            results_sorted = sorted(results, key=lambda x: x["dps"], reverse=True)

            self.base_dps_no_crit_label.config(text=f"Base DPS (without crit): {dps_base_no_crit:.2f}")
            self.base_dps_with_crit_label.config(text=f"Base DPS (with crit): {dps_base_with_crit:.2f} (Avg. DPS including critical hit frequency)")

            self.results_tree.delete(*self.results_tree.get_children())

            tiers = ["S", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]
            
            for i, res in enumerate(results_sorted):
                mod_name = res["name"]
                dps = res["dps"]
                
                if dps_base_with_crit == 0:
                    percentage_change = 0.0
                else:
                    percentage_change = ((dps - dps_base_with_crit) / dps_base_with_crit) * 100
                
                tier_to_display = tiers[i] if i < len(tiers) else "-"
                
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                self.results_tree.insert("", "end", iid=i, tags=(tag,), values=(
                    tier_to_display,
                    mod_name,
                    f"{dps:.2f}",
                    f"{percentage_change:>+8.2f}%"
                ))
            
            self.master.after(100, self.check_scrollbars)


        except ValueError as e:
            messagebox.showerror("Data Input Error", str(e))
        except ZeroDivisionError:
            messagebox.showerror("Calculation Error", "Attack Speed cannot be zero.")
        except Exception as e:
            messagebox.showerror("An Error Occurred", f"Unexpected error: {e}")

# --- Run the application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = DPSCalculatorApp(root)
    root.mainloop()