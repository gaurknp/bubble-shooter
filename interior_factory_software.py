#!/usr/bin/env python3
"""Interior Factory Software Starter

A simplified all-in-one desktop tool that connects:
- AutoCAD quantity extractor (CSV import)
- BOM calculator
- Production planner
- Inventory tracker
- Dashboard + report export
"""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

DB_PATH = Path("interior_factory.db")


@dataclass
class QuantityItem:
    item: str
    quantity: float
    unit: str


class InteriorFactoryService:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS extraction_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extracted_quantities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                FOREIGN KEY(batch_id) REFERENCES extraction_batches(id)
            );

            CREATE TABLE IF NOT EXISTS bom_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                item TEXT NOT NULL,
                base_quantity REAL NOT NULL,
                waste_percent REAL NOT NULL,
                final_quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS production_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                item TEXT NOT NULL,
                quantity REAL NOT NULL,
                day_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL UNIQUE,
                stock REAL NOT NULL,
                unit TEXT NOT NULL,
                reorder_level REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                qty_change REAL NOT NULL,
                unit TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def import_autocad_csv(self, csv_path: Path) -> list[QuantityItem]:
        aggregated: dict[tuple[str, str], float] = defaultdict(float)

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file has no headers.")

            normalized = {h.strip().lower(): h for h in reader.fieldnames}
            item_key = normalized.get("item") or normalized.get("layer") or normalized.get("name")
            qty_key = normalized.get("quantity") or normalized.get("qty")
            unit_key = normalized.get("unit")

            if not item_key or not qty_key:
                raise ValueError(
                    "CSV must include item/layer and quantity columns. Optional: unit."
                )

            for row in reader:
                item = (row.get(item_key) or "").strip()
                qty_raw = (row.get(qty_key) or "0").strip()
                unit = (row.get(unit_key) or "nos").strip() if unit_key else "nos"
                if not item:
                    continue
                try:
                    qty = float(qty_raw)
                except ValueError:
                    continue
                aggregated[(item, unit)] += qty

        if not aggregated:
            raise ValueError("No valid quantity rows were found in CSV.")

        now = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO extraction_batches(source_file, created_at) VALUES(?, ?)",
            (str(csv_path), now),
        )
        batch_id = cur.lastrowid

        items = [QuantityItem(item=k[0], unit=k[1], quantity=v) for k, v in sorted(aggregated.items())]
        cur.executemany(
            "INSERT INTO extracted_quantities(batch_id, item, quantity, unit) VALUES(?, ?, ?, ?)",
            [(batch_id, it.item, it.quantity, it.unit) for it in items],
        )
        self.conn.commit()
        return items

    def latest_extraction(self) -> list[QuantityItem]:
        row = self.conn.execute("SELECT id FROM extraction_batches ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return []
        records = self.conn.execute(
            "SELECT item, quantity, unit FROM extracted_quantities WHERE batch_id = ? ORDER BY item",
            (row["id"],),
        ).fetchall()
        return [QuantityItem(item=r["item"], quantity=r["quantity"], unit=r["unit"]) for r in records]

    def generate_bom(self, project_name: str, waste_percent: float) -> list[sqlite3.Row]:
        extracted = self.latest_extraction()
        if not extracted:
            raise ValueError("Import AutoCAD quantities first.")
        if not project_name.strip():
            raise ValueError("Project name is required.")

        now = datetime.now().isoformat(timespec="seconds")
        factor = 1 + waste_percent / 100.0
        self.conn.execute("DELETE FROM bom_items WHERE project_name = ?", (project_name,))

        self.conn.executemany(
            """
            INSERT INTO bom_items(project_name, item, base_quantity, waste_percent, final_quantity, unit, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    project_name,
                    it.item,
                    it.quantity,
                    waste_percent,
                    round(it.quantity * factor, 2),
                    it.unit,
                    now,
                )
                for it in extracted
            ],
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT item, base_quantity, waste_percent, final_quantity, unit FROM bom_items WHERE project_name = ? ORDER BY item",
            (project_name,),
        ).fetchall()

    def generate_production_plan(
        self,
        project_name: str,
        start_day: date,
        daily_capacity: float,
    ) -> list[sqlite3.Row]:
        if daily_capacity <= 0:
            raise ValueError("Daily capacity must be greater than zero.")

        rows = self.conn.execute(
            "SELECT item, final_quantity FROM bom_items WHERE project_name = ? ORDER BY item",
            (project_name,),
        ).fetchall()
        if not rows:
            raise ValueError("Generate BOM first for this project.")

        self.conn.execute("DELETE FROM production_plan WHERE project_name = ?", (project_name,))

        out_rows = []
        now = datetime.now().isoformat(timespec="seconds")
        for r in rows:
            remaining = float(r["final_quantity"])
            day = start_day
            while remaining > 0:
                qty = round(min(remaining, daily_capacity), 2)
                out_rows.append((project_name, r["item"], qty, day.isoformat(), now))
                remaining = round(remaining - qty, 2)
                day += timedelta(days=1)

        self.conn.executemany(
            "INSERT INTO production_plan(project_name, item, quantity, day_date, created_at) VALUES(?, ?, ?, ?, ?)",
            out_rows,
        )
        self.conn.commit()

        return self.conn.execute(
            "SELECT item, quantity, day_date FROM production_plan WHERE project_name = ? ORDER BY day_date, item",
            (project_name,),
        ).fetchall()

    def upsert_inventory(self, item: str, stock: float, unit: str, reorder_level: float) -> None:
        if stock < 0 or reorder_level < 0:
            raise ValueError("Stock and reorder level cannot be negative.")
        self.conn.execute(
            """
            INSERT INTO inventory(item, stock, unit, reorder_level)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(item) DO UPDATE SET stock=excluded.stock, unit=excluded.unit, reorder_level=excluded.reorder_level
            """,
            (item.strip(), stock, unit.strip() or "nos", reorder_level),
        )
        self.conn.commit()

    def adjust_inventory(self, item: str, qty_change: float, note: str = "manual adjustment") -> None:
        rec = self.conn.execute("SELECT stock, unit FROM inventory WHERE item = ?", (item,)).fetchone()
        if not rec:
            raise ValueError(f"Item '{item}' does not exist in inventory.")
        new_stock = round(float(rec["stock"]) + qty_change, 2)
        if new_stock < 0:
            raise ValueError("Adjustment would result in negative stock.")
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute("UPDATE inventory SET stock = ? WHERE item = ?", (new_stock, item))
        self.conn.execute(
            "INSERT INTO inventory_transactions(item, qty_change, unit, note, created_at) VALUES(?, ?, ?, ?, ?)",
            (item, qty_change, rec["unit"], note, now),
        )
        self.conn.commit()

    def dashboard_metrics(self) -> dict[str, object]:
        latest_project = self.conn.execute(
            "SELECT project_name FROM bom_items ORDER BY id DESC LIMIT 1"
        ).fetchone()
        low_stock = self.conn.execute(
            "SELECT item, stock, reorder_level, unit FROM inventory WHERE stock <= reorder_level ORDER BY item"
        ).fetchall()
        total_bom = self.conn.execute("SELECT COUNT(*) AS c FROM bom_items").fetchone()["c"]
        total_plan = self.conn.execute("SELECT COUNT(*) AS c FROM production_plan").fetchone()["c"]
        total_inv = self.conn.execute("SELECT COUNT(*) AS c FROM inventory").fetchone()["c"]

        return {
            "latest_project": latest_project["project_name"] if latest_project else "N/A",
            "total_bom_lines": total_bom,
            "total_plan_lines": total_plan,
            "inventory_items": total_inv,
            "low_stock": low_stock,
        }

    def export_report(self, out_path: Path) -> Path:
        m = self.dashboard_metrics()
        lines = [
            "# Interior Factory Report",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            f"Latest project: {m['latest_project']}",
            f"BOM lines: {m['total_bom_lines']}",
            f"Production plan rows: {m['total_plan_lines']}",
            f"Inventory SKUs: {m['inventory_items']}",
            "",
            "## Low stock items",
        ]
        if m["low_stock"]:
            for row in m["low_stock"]:
                lines.append(
                    f"- {row['item']}: {row['stock']} {row['unit']} (reorder <= {row['reorder_level']})"
                )
        else:
            lines.append("- None")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path


class InteriorFactoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Interior Factory Software Starter")
        self.geometry("980x650")
        self.service = InteriorFactoryService()

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.extract_tab = ttk.Frame(notebook)
        self.bom_tab = ttk.Frame(notebook)
        self.production_tab = ttk.Frame(notebook)
        self.inventory_tab = ttk.Frame(notebook)
        self.dashboard_tab = ttk.Frame(notebook)

        notebook.add(self.extract_tab, text="AutoCAD Extractor")
        notebook.add(self.bom_tab, text="BOM Calculator")
        notebook.add(self.production_tab, text="Production Planner")
        notebook.add(self.inventory_tab, text="Inventory Tracker")
        notebook.add(self.dashboard_tab, text="Dashboard")

        self._build_extractor_tab()
        self._build_bom_tab()
        self._build_production_tab()
        self._build_inventory_tab()
        self._build_dashboard_tab()

    def _new_tree(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=18)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=170)
        return tree

    def _build_extractor_tab(self):
        top = ttk.Frame(self.extract_tab, padding=10)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Import AutoCAD CSV", command=self.import_csv).pack(side=tk.LEFT)
        ttk.Label(
            top,
            text="CSV columns: item/layer,name + quantity/qty + optional unit",
        ).pack(side=tk.LEFT, padx=10)
        self.extract_tree = self._new_tree(self.extract_tab, ("Item", "Quantity", "Unit"))
        self.extract_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_bom_tab(self):
        top = ttk.Frame(self.bom_tab, padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Project").pack(side=tk.LEFT)
        self.project_entry = ttk.Entry(top, width=20)
        self.project_entry.pack(side=tk.LEFT, padx=8)
        ttk.Label(top, text="Waste %").pack(side=tk.LEFT)
        self.waste_entry = ttk.Entry(top, width=8)
        self.waste_entry.insert(0, "8")
        self.waste_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Generate BOM", command=self.generate_bom).pack(side=tk.LEFT)

        self.bom_tree = self._new_tree(
            self.bom_tab,
            ("Item", "Base Qty", "Waste %", "Final Qty", "Unit"),
        )
        self.bom_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_production_tab(self):
        top = ttk.Frame(self.production_tab, padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Start Date (YYYY-MM-DD)").pack(side=tk.LEFT)
        self.start_entry = ttk.Entry(top, width=12)
        self.start_entry.insert(0, date.today().isoformat())
        self.start_entry.pack(side=tk.LEFT, padx=8)
        ttk.Label(top, text="Daily Capacity").pack(side=tk.LEFT)
        self.capacity_entry = ttk.Entry(top, width=8)
        self.capacity_entry.insert(0, "25")
        self.capacity_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Generate Plan", command=self.generate_plan).pack(side=tk.LEFT)

        self.plan_tree = self._new_tree(self.production_tab, ("Item", "Quantity", "Day"))
        self.plan_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_inventory_tab(self):
        form = ttk.Frame(self.inventory_tab, padding=10)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Item").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Stock").grid(row=0, column=2, sticky="w")
        ttk.Label(form, text="Unit").grid(row=0, column=4, sticky="w")
        ttk.Label(form, text="Reorder Level").grid(row=0, column=6, sticky="w")

        self.inv_item = ttk.Entry(form, width=20)
        self.inv_stock = ttk.Entry(form, width=10)
        self.inv_unit = ttk.Entry(form, width=8)
        self.inv_rl = ttk.Entry(form, width=10)

        self.inv_item.grid(row=0, column=1, padx=6)
        self.inv_stock.grid(row=0, column=3, padx=6)
        self.inv_unit.grid(row=0, column=5, padx=6)
        self.inv_rl.grid(row=0, column=7, padx=6)

        ttk.Button(form, text="Save/Update", command=self.save_inventory).grid(row=0, column=8, padx=8)

        adj = ttk.Frame(self.inventory_tab, padding=10)
        adj.pack(fill=tk.X)
        ttk.Label(adj, text="Adjust Item").pack(side=tk.LEFT)
        self.adj_item = ttk.Entry(adj, width=20)
        self.adj_item.pack(side=tk.LEFT, padx=6)
        ttk.Label(adj, text="Qty Change (+/-)").pack(side=tk.LEFT)
        self.adj_qty = ttk.Entry(adj, width=10)
        self.adj_qty.pack(side=tk.LEFT, padx=6)
        ttk.Button(adj, text="Apply", command=self.adjust_inventory).pack(side=tk.LEFT, padx=8)

        self.inv_tree = self._new_tree(
            self.inventory_tab,
            ("Item", "Stock", "Unit", "Reorder Level", "Status"),
        )
        self.inv_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_inventory_tree()

    def _build_dashboard_tab(self):
        top = ttk.Frame(self.dashboard_tab, padding=10)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Refresh Dashboard", command=self.refresh_dashboard).pack(side=tk.LEFT)
        ttk.Button(top, text="Export Report", command=self.export_report).pack(side=tk.LEFT, padx=10)
        self.dashboard_text = tk.Text(self.dashboard_tab, wrap="word", height=30)
        self.dashboard_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_dashboard()

    def _clear_tree(self, tree):
        for row in tree.get_children():
            tree.delete(row)

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            items = self.service.import_autocad_csv(Path(path))
            self._clear_tree(self.extract_tree)
            for i in items:
                self.extract_tree.insert("", tk.END, values=(i.item, i.quantity, i.unit))
            messagebox.showinfo("Imported", f"Imported {len(items)} quantity lines.")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def generate_bom(self):
        try:
            project = self.project_entry.get().strip()
            waste = float(self.waste_entry.get())
            rows = self.service.generate_bom(project, waste)
            self._clear_tree(self.bom_tree)
            for r in rows:
                self.bom_tree.insert(
                    "",
                    tk.END,
                    values=(r["item"], r["base_quantity"], r["waste_percent"], r["final_quantity"], r["unit"]),
                )
            messagebox.showinfo("BOM", f"BOM generated for {project} ({len(rows)} rows).")
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("BOM Error", str(e))

    def generate_plan(self):
        try:
            project = self.project_entry.get().strip()
            start = date.fromisoformat(self.start_entry.get().strip())
            capacity = float(self.capacity_entry.get())
            rows = self.service.generate_production_plan(project, start, capacity)
            self._clear_tree(self.plan_tree)
            for r in rows:
                self.plan_tree.insert("", tk.END, values=(r["item"], r["quantity"], r["day_date"]))
            messagebox.showinfo("Plan", f"Production plan generated ({len(rows)} rows).")
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("Plan Error", str(e))

    def save_inventory(self):
        try:
            self.service.upsert_inventory(
                item=self.inv_item.get().strip(),
                stock=float(self.inv_stock.get()),
                unit=self.inv_unit.get().strip() or "nos",
                reorder_level=float(self.inv_rl.get() or 0),
            )
            self.refresh_inventory_tree()
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("Inventory Error", str(e))

    def adjust_inventory(self):
        try:
            self.service.adjust_inventory(
                item=self.adj_item.get().strip(),
                qty_change=float(self.adj_qty.get()),
            )
            self.refresh_inventory_tree()
            self.refresh_dashboard()
        except Exception as e:
            messagebox.showerror("Adjust Error", str(e))

    def refresh_inventory_tree(self):
        self._clear_tree(self.inv_tree)
        rows = self.service.conn.execute(
            "SELECT item, stock, unit, reorder_level FROM inventory ORDER BY item"
        ).fetchall()
        for r in rows:
            status = "LOW" if float(r["stock"]) <= float(r["reorder_level"]) else "OK"
            self.inv_tree.insert(
                "", tk.END, values=(r["item"], r["stock"], r["unit"], r["reorder_level"], status)
            )

    def refresh_dashboard(self):
        m = self.service.dashboard_metrics()
        self.dashboard_text.delete("1.0", tk.END)
        self.dashboard_text.insert(tk.END, "Interior Factory Dashboard\n")
        self.dashboard_text.insert(tk.END, "=" * 40 + "\n")
        self.dashboard_text.insert(tk.END, f"Latest Project: {m['latest_project']}\n")
        self.dashboard_text.insert(tk.END, f"BOM Lines: {m['total_bom_lines']}\n")
        self.dashboard_text.insert(tk.END, f"Production Plan Rows: {m['total_plan_lines']}\n")
        self.dashboard_text.insert(tk.END, f"Inventory Items: {m['inventory_items']}\n\n")
        self.dashboard_text.insert(tk.END, "Low Stock Items:\n")
        if m["low_stock"]:
            for row in m["low_stock"]:
                self.dashboard_text.insert(
                    tk.END,
                    f"- {row['item']}: {row['stock']} {row['unit']} (<= {row['reorder_level']})\n",
                )
        else:
            self.dashboard_text.insert(tk.END, "- None\n")

    def export_report(self):
        out = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md")], initialfile="factory_report.md"
        )
        if not out:
            return
        try:
            path = self.service.export_report(Path(out))
            messagebox.showinfo("Exported", f"Report exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


if __name__ == "__main__":
    app = InteriorFactoryApp()
    app.mainloop()
