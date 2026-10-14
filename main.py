import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class InterferenceSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Interference Lab | Fabry–Pérot & Michelson")
        self.root.geometry("1450x900")
        self.root.minsize(1100, 720)
        self.defaults = {
            "wavelength_nm": 632.8,
            "separation_um": 100.0,
            "focal_length_cm": 20.0,
            "refractive_index": 1.0,
            "reflectivity_pct": 90.0,
            "visibility_pct": 95.0,
            "tilt_mrad": 0.0,
            "phase_deg": 0.0,
            "screen_mm": 20.0,
            "resolution": 500,
        }
        self.vars = {}
        self.value_labels = {}
        self.pending_update = None
        self.image_artist = None
        self.radial_line = None
        self.cross_line = None
        self.colorbar = None
        self._build_ui()
        self.schedule_update(immediate=True)

    def _build_ui(self):
        self.bg = "#111827"
        self.panel = "#1b2638"
        self.panel_alt = "#253349"
        self.text = "#e5edf8"
        self.muted = "#9aabc2"
        self.accent = "#60a5fa"
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg=self.bg)
        style.configure(".", background=self.bg, foreground=self.text, font=("TkDefaultFont", 10))
        style.configure("TFrame", background=self.bg)
        style.configure("TLabel", background=self.bg, foreground=self.text)
        style.configure("Muted.TLabel", background=self.bg, foreground=self.muted)
        style.configure("Header.TLabel", background=self.bg, foreground=self.text, font=("TkDefaultFont", 18, "bold"))
        style.configure("Section.TLabel", background=self.bg, foreground=self.accent, font=("TkDefaultFont", 10, "bold"))
        style.configure("TButton", background=self.panel_alt, foreground=self.text, padding=(10, 7), borderwidth=0)
        style.map("TButton", background=[("active", "#344762")])
        style.configure("TCombobox", fieldbackground=self.panel_alt, background=self.panel_alt, foreground=self.text, arrowcolor=self.text)
        style.map("TCombobox", fieldbackground=[("readonly", self.panel_alt)], foreground=[("readonly", self.text)])
        style.configure("TSeparator", background="#344258")
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="INTERFERENCE LAB", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Circular fringes • live controls • radial intensity", style="Muted.TLabel").pack(side=tk.LEFT, padx=18)
        ttk.Button(header, text="Export plots", command=self.export_plot).pack(side=tk.RIGHT)
        ttk.Button(header, text="Reset", command=self.reset).pack(side=tk.RIGHT, padx=8)
        body = ttk.Frame(outer)
        body.pack(fill=tk.BOTH, expand=True)
        controls = ttk.Frame(body, padding=(4, 4, 14, 4))
        controls.pack(side=tk.LEFT, fill=tk.Y)
        controls.configure(width=325)
        controls.pack_propagate(False)
        plot_frame = ttk.Frame(body)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ttk.Label(controls, text="SIMULATION", font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 5))
        self.instrument = tk.StringVar(value="Fabry–Pérot")
        selector = ttk.Combobox(controls, textvariable=self.instrument, values=("Fabry–Pérot", "Michelson"), state="readonly")
        selector.pack(fill=tk.X, pady=(0, 12))
        selector.bind("<<ComboboxSelected>>", lambda _e: self.update_plot())
        ttk.Label(controls, text="OPTICAL PARAMETERS", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self._add_slider(controls, "wavelength_nm", "Wavelength λ (nm)", 400, 800, 0.1)
        self._add_slider(controls, "separation_um", "Cavity / effective gap d (µm)", 1, 1000, 1)
        self._add_slider(controls, "focal_length_cm", "Lens focal length f (cm)", 5, 100, 1)
        self._add_slider(controls, "refractive_index", "Refractive index n", 1.0, 1.5, 0.01)
        ttk.Separator(controls).pack(fill=tk.X, pady=8)
        ttk.Label(controls, text="MIRROR / BEAM PARAMETERS", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self._add_slider(controls, "reflectivity_pct", "Mirror intensity reflectivity (%)", 10, 99.5, 0.5)
        self._add_slider(controls, "visibility_pct", "Michelson visibility (%)", 0, 100, 1)
        self._add_slider(controls, "tilt_mrad", "Relative tilt (mrad)", -2, 2, 0.01)
        self._add_slider(controls, "phase_deg", "Phase offset (degrees)", 0, 360, 1)
        ttk.Separator(controls).pack(fill=tk.X, pady=8)
        ttk.Label(controls, text="DETECTOR", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self._add_slider(controls, "screen_mm", "Detector width (mm)", 2, 30, 0.5)
        self._add_slider(controls, "resolution", "Resolution (pixels per side)", 200, 800, 50)
        self.status = tk.StringVar(value="")
        ttk.Label(controls, textvariable=self.status, wraplength=300, justify=tk.LEFT, font=("TkDefaultFont", 9)).pack(fill=tk.X, pady=(12, 0))
        self.fig = Figure(figsize=(10, 7), dpi=100, constrained_layout=True, facecolor=self.panel)
        grid = self.fig.add_gridspec(2, 2, height_ratios=[1.0, 0.62], wspace=0.28, hspace=0.32)
        self.ax_image = self.fig.add_subplot(grid[:, 0])
        self.ax_profile = self.fig.add_subplot(grid[0, 1])
        self.ax_phase = self.fig.add_subplot(grid[1, 1])
        for ax in (self.ax_image, self.ax_profile, self.ax_phase):
            ax.set_facecolor("#0b1220")
            ax.tick_params(colors=self.muted, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#344258")
            ax.xaxis.label.set_color(self.text)
            ax.yaxis.label.set_color(self.text)
            ax.title.set_color(self.text)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _add_slider(self, parent, key, label, minimum, maximum, resolution):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        top = ttk.Frame(frame)
        top.pack(fill=tk.X)
        ttk.Label(top, text=label).pack(side=tk.LEFT)
        value = tk.StringVar()
        self.value_labels[key] = value
        ttk.Label(top, textvariable=value, font=("TkDefaultFont", 9, "bold")).pack(side=tk.RIGHT)
        var = tk.DoubleVar(value=self.defaults[key])
        self.vars[key] = var
        scale = tk.Scale(frame, variable=var, from_=minimum, to=maximum, resolution=resolution, orient=tk.HORIZONTAL, showvalue=False, length=285, highlightthickness=0, bd=0, bg=self.bg, fg=self.text, troughcolor="#344258", activebackground=self.accent, sliderlength=16, command=lambda _v, k=key: self._slider_changed(k))
        scale.pack(fill=tk.X)
        self._format_value(key)

    def _format_value(self, key):
        val = self.vars[key].get()
        formats = {
            "wavelength_nm": f"{val:.1f} nm",
            "separation_um": f"{val:.1f} µm",
            "focal_length_cm": f"{val:.1f} cm",
            "refractive_index": f"{val:.2f}",
            "reflectivity_pct": f"{val:.1f}%",
            "visibility_pct": f"{val:.0f}%",
            "tilt_mrad": f"{val:+.2f} mrad",
            "phase_deg": f"{val:.0f}°",
            "screen_mm": f"{val:.1f} mm",
            "resolution": f"{int(round(val))} px",
        }
        self.value_labels[key].set(formats[key])

    def _slider_changed(self, key):
        self._format_value(key)
        self.schedule_update()

    def schedule_update(self, immediate=False):
        if self.pending_update is not None:
            try:
                self.root.after_cancel(self.pending_update)
            except tk.TclError:
                pass
        self.pending_update = self.root.after(0 if immediate else 75, self.update_plot)

    def _calculate(self):
        p = {k: v.get() for k, v in self.vars.items()}
        N = int(round(p["resolution"]))
        lam = p["wavelength_nm"] * 1e-9
        d = p["separation_um"] * 1e-6
        f = p["focal_length_cm"] * 1e-2
        n = p["refractive_index"]
        tilt = p["tilt_mrad"] * 1e-3
        phase_offset = np.deg2rad(p["phase_deg"])
        screen_width = p["screen_mm"] * 1e-3
        coord = np.linspace(-screen_width / 2, screen_width / 2, N)
        X, Y = np.meshgrid(coord, coord)
        radius = np.hypot(X, Y)
        theta = np.arctan2(radius, f)
        delta = (4 * np.pi * n * d / lam) * np.cos(theta)
        delta += (4 * np.pi * n * tilt * X / lam)
        delta += phase_offset
        instrument = self.instrument.get()
        if instrument == "Fabry–Pérot":
            R = np.clip(p["reflectivity_pct"] / 100.0, 0.001, 0.9995)
            airy_coefficient = 4 * R / (1 - R) ** 2
            intensity = 1.0 / (1.0 + airy_coefficient * np.sin(delta / 2) ** 2)
            model_note = "Airy transmission • multiple-beam interference"
        else:
            visibility = p["visibility_pct"] / 100.0
            intensity = 0.5 * (1 + visibility * np.cos(delta))
            model_note = "Two-beam interference • adjustable visibility"
        intensity = np.clip(intensity, 0, None)
        intensity /= max(float(intensity.max()), 1e-15)
        bins = max(100, N // 2)
        r_flat = radius.ravel()
        i_flat = intensity.ravel()
        edges = np.linspace(0, screen_width / np.sqrt(2), bins + 1)
        which = np.digitize(r_flat, edges) - 1
        valid = (which >= 0) & (which < bins)
        sums = np.bincount(which[valid], weights=i_flat[valid], minlength=bins)
        counts = np.bincount(which[valid], minlength=bins)
        radial = np.divide(sums, counts, out=np.full(bins, np.nan), where=counts > 0)
        r_centres_mm = (edges[:-1] + edges[1:]) * 500
        return p, intensity, coord * 1e3, r_centres_mm, radial, model_note

    def update_plot(self):
        self.pending_update = None
        if not self.vars:
            return
        try:
            p, intensity, coord_mm, r_mm, radial, model_note = self._calculate()
            instrument = self.instrument.get()
            extent = [coord_mm[0], coord_mm[-1], coord_mm[0], coord_mm[-1]]
            if self.image_artist is None:
                self.image_artist = self.ax_image.imshow(intensity, origin="lower", extent=extent, cmap="inferno", vmin=0, vmax=1, interpolation="bilinear", aspect="equal")
                self.colorbar = self.fig.colorbar(self.image_artist, ax=self.ax_image, fraction=0.046, pad=0.04)
                self.colorbar.set_label("Normalized intensity", color=self.text)
                self.colorbar.ax.tick_params(colors=self.muted, labelsize=8)
            else:
                self.image_artist.set_data(intensity)
                self.image_artist.set_extent(extent)
            self.ax_image.set_title(f"{instrument} · detector intensity", fontsize=11, pad=10)
            self.ax_image.set_xlabel("x (mm)")
            self.ax_image.set_ylabel("y (mm)")
            good = np.isfinite(radial)
            if self.radial_line is None:
                (self.radial_line,) = self.ax_profile.plot(r_mm[good], radial[good], color="#60a5fa", lw=1.6)
            else:
                self.radial_line.set_data(r_mm[good], radial[good])
            self.ax_profile.set_title("Radial intensity profile", fontsize=10, pad=8)
            self.ax_profile.set_xlabel("Radius (mm)")
            self.ax_profile.set_ylabel("Normalized intensity")
            self.ax_profile.set_ylim(-0.03, 1.05)
            self.ax_profile.set_xlim(0, max(r_mm[good]) if np.any(good) else 1)
            self.ax_profile.grid(True, alpha=0.18, color=self.muted)
            centre = intensity.shape[0] // 2
            if self.cross_line is None:
                (self.cross_line,) = self.ax_phase.plot(coord_mm, intensity[centre, :], color="#fbbf24", lw=1.4)
            else:
                self.cross_line.set_data(coord_mm, intensity[centre, :])
            self.ax_phase.set_title("Horizontal cross-section", fontsize=10, pad=8)
            self.ax_phase.set_xlabel("x (mm)")
            self.ax_phase.set_ylabel("Normalized intensity")
            self.ax_phase.set_ylim(-0.03, 1.05)
            self.ax_phase.set_xlim(coord_mm[0], coord_mm[-1])
            self.ax_phase.grid(True, alpha=0.18, color=self.muted)
            self.fig.suptitle(model_note, color=self.muted, fontsize=9)
            self.canvas.draw_idle()
            if abs(p["tilt_mrad"]) < 0.001:
                rings_hint = "Concentric rings · tilt = 0"
            else:
                rings_hint = "Tilt applied · rings shift or distort"
            self.status.set(f"λ {p['wavelength_nm']:.1f} nm   ·   d {p['separation_um']:.1f} µm   ·   f {p['focal_length_cm']:.1f} cm   ·   {rings_hint}")
        except Exception as exc:
            self.status.set(f"Plot update error: {exc}")

    def reset(self):
        for key, value in self.defaults.items():
            self.vars[key].set(value)
            self._format_value(key)
        self.instrument.set("Fabry–Pérot")
        self.schedule_update(immediate=True)

    def export_plot(self):
        filename = filedialog.asksaveasfilename(title="Export interference plots", defaultextension=".png", filetypes=[("PNG image", "*.png"), ("PDF document", "*.pdf"), ("SVG image", "*.svg")])
        if not filename:
            return
        try:
            self.fig.savefig(filename, dpi=240, bbox_inches="tight", facecolor=self.fig.get_facecolor())
            messagebox.showinfo("Export complete", f"Saved plot to:\n{filename}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

def main():
    root = tk.Tk()
    InterferenceSimulator(root)
    root.mainloop()

if __name__ == "__main__": main()