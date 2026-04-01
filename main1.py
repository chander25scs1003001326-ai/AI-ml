# ====================================
#  WILDLIFE CORRIDOR VISUALIZATION APP
#  With WATER + SPECIES IMAGES + POPUPS
# ====================================

import tkinter as tk
from tkintermapview import TkinterMapView
from shapely.geometry import Point, Polygon
import pandas as pd
from PIL import Image, ImageTk, ImageOps
import os

# ============================
# IMAGE SLIDER CONFIGURATION
# ============================
SLIDE_DELAY = 4000
FADE_STEPS = 10
FADE_SPEED = 60

# ============================
# LOAD CSV DATA
# ============================
df = pd.read_csv("data/india_wildlife_corridors_polygons.csv")
water_df = pd.read_csv("data/water_usage_india.csv")

# ============================
# PROCESS POLYGON LIST
# ============================
corridors = []
for _, row in df.iterrows():
    coords = eval(row["polygon"])
    poly = Polygon([(c[1], c[0]) for c in coords])
    corridors.append({
        "name": row["name"],
        "states": row["states"],
        "species": row["species"],
        "area": row["area_km2"],
        "coords": coords,
        "polygon": poly,
    })

# ============================
# LOAD SPECIES IMAGES
# ============================
species_images = {}
folder = os.path.abspath("species_images")
if os.path.exists(folder):
    for file in os.listdir(folder):
        key = file.split(".")[0].lower()
        species_images[key] = os.path.join(folder, file)

# ============================
# MAIN WINDOW
# ============================
root = tk.Tk()
root.title("🐯 Wildlife Corridor Map")
root.geometry("1300x750")

popup_corridor = None
popup_water = None
selected_polygon = None

# ============================
# MAP DISPLAY
# ============================
map_widget = TkinterMapView(root)
map_widget.pack(fill="both", expand=True)
map_widget.set_tile_server(
    "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
)
map_widget.set_position(22.5, 78.9)
map_widget.set_zoom(5)
map_widget.max_zoom = 5
map_widget.min_zoom = 5
map_widget.mouse_wheel_zoom = False
map_widget.zoom_keyboard = False

# ============================
# LOAD WATER ICON
# ============================
water_icon = None
water_img_path = os.path.abspath("species_images/water.jpg")
if os.path.exists(water_img_path):
    raw = Image.open(water_img_path)
    raw = ImageOps.fit(raw, (280, 280))
    raw = ImageOps.expand(raw, border=3, fill="#00A0FF")
    water_icon = ImageTk.PhotoImage(raw)

# ============================
# HELPERS
# ============================
def format_species_name(name_raw):
    return name_raw.replace("_", " ").title()


def detect_corridor(lat, lon):
    point = Point(lon, lat)
    return min(corridors, key=lambda c: c["polygon"].centroid.distance(point))


def get_water_data(states_text):
    state = states_text.split(",")[0].strip()
    row = water_df[water_df["state"] == state]
    if row.empty:
        return None
    return {
        "available": int(row["total_available_water_m3"].iloc[0]),
        "state": str(row["state"].iloc[0]),
        "used": int(row["water_used_m3"].iloc[0]),
        "used_percent": float(row["water_used_percent"].iloc[0]),
        "wasted": int(row["water_wasted_m3"].iloc[0]),
        "wasted_percent": float(row["water_wasted_percent"].iloc[0]),
    }


def create_popup(title, height):
    popup = tk.Toplevel(root)
    popup.title(title)
    popup.geometry(f"480x{height}")
    popup.config(bg="#181818")
    popup.wm_attributes("-topmost", True)
    popup.main_frame = tk.Frame(popup, bg="#232323", bd=3, relief="ridge")
    popup.main_frame.pack(fill="both", expand=True, padx=12, pady=12)
    return popup

# ============================
# IMAGE FADE ANIMATION
# ============================
def crossfade(old, new, step, lbl):
    if step > FADE_STEPS:
        final = ImageTk.PhotoImage(new)
        lbl.config(image=final)
        lbl.image = final
        return
    blend = Image.blend(old, new, step / FADE_STEPS)
    tk_img = ImageTk.PhotoImage(blend)
    lbl.config(image=tk_img)
    lbl.image = tk_img
    lbl.after(FADE_SPEED, lambda: crossfade(old, new, step+1, lbl))

# ============================
# CORRIDOR POPUP
# ============================
def update_corridor_popup(c):
    global popup_corridor

    if popup_corridor is None or not popup_corridor.winfo_exists():
        popup_corridor = create_popup("Wildlife Corridor", 560)
        popup_corridor.title_label = tk.Label(
            popup_corridor.main_frame, font=("Segoe UI", 16, "bold"),
            fg="#00FFAA", bg="#232323"
        ); popup_corridor.title_label.pack(pady=5)
        popup_corridor.info_label = tk.Label(
            popup_corridor.main_frame, font=("Segoe UI", 11),
            fg="#EEEEEE", bg="#232323", justify="left"
        ); popup_corridor.info_label.pack(pady=5)
        popup_corridor.image_label = tk.Label(popup_corridor.main_frame, bg="#232323")
        popup_corridor.image_label.pack(pady=6)
        popup_corridor.species_label = tk.Label(
            popup_corridor.main_frame, font=("Segoe UI", 13, "bold"),
            fg="#00FFAA", bg="#232323"
        ); popup_corridor.species_label.pack()

    popup_corridor.title_label.config(text=c["name"])
    popup_corridor.info_label.config(text=f"🌍 {c['states']}\n📐 {c['area']} km²")

    # Load species images
    popup_corridor.raw_images = []
    popup_corridor.names = []
    for sp in c["species"].split(","):
        s = sp.strip().lower().replace(" ", "_")
        if s in species_images:
            img = Image.open(species_images[s])
            img = ImageOps.fit(img, (280, 280))
            img = ImageOps.expand(img, border=3, fill="#00FFAA")
            popup_corridor.raw_images.append(img)
            popup_corridor.names.append(format_species_name(s))

    # No images → stop function safely
    if not popup_corridor.raw_images:
        popup_corridor.image_label.config(image='')
        popup_corridor.species_label.config(text="No Species Images")
        return

    popup_corridor.index = 0

    # Prevent stacking animation timers
    if hasattr(popup_corridor, "job"):
        popup_corridor.after_cancel(popup_corridor.job)

    def show_fade():
        if not popup_corridor.raw_images:
            return
        old = popup_corridor.raw_images[popup_corridor.index]
        popup_corridor.index = (popup_corridor.index + 1) % len(popup_corridor.raw_images)
        new = popup_corridor.raw_images[popup_corridor.index]
        popup_corridor.species_label.config(text=popup_corridor.names[popup_corridor.index])
        crossfade(old, new, 0, popup_corridor.image_label)
        popup_corridor.job = popup_corridor.after(SLIDE_DELAY, show_fade)

    show_fade()

# ============================
# WATER POPUP
# ============================
def update_water_popup(c):
    global popup_water

    if popup_water is None or not popup_water.winfo_exists():
        popup_water = create_popup("Water Shed Management", 430)
        popup_water.title_label = tk.Label(
            popup_water.main_frame, font=("Segoe UI", 16, "bold"),
            fg="#00A0FF", bg="#232323"); popup_water.title_label.pack(pady=5)
        popup_water.info_label = tk.Label(
            popup_water.main_frame, font=("Segoe UI", 11),
            fg="#EEEEEE", bg="#232323", justify="left"
        ); popup_water.info_label.pack(pady=6)
        popup_water.icon_label = tk.Label(popup_water.main_frame, bg="#232323")
        popup_water.icon_label.pack(pady=8)

    data = get_water_data(c["states"])
    popup_water.title_label.config(text="💧 Watershed Analysis")
    if data:
        popup_water.info_label.config(
            text = (f"State: {data.get('state', 'N/A')}\n"
                    f"Total Water: {data.get('available', 0):,.1f} m³\n"
                    f"Water Used: {data.get('used', 0):,.1f} m³ ({data.get('used_percent', 0)}%)\n"
                    f"Water Wasted: {data.get('wasted', 0):,.1f} m³ ({data.get('wasted_percent', 0)}%)"
)
        )
    else:
        popup_water.info_label.config(text="⚠ No Water Data Available")

    if water_icon:
        popup_water.icon_label.config(image=water_icon)
        popup_water.icon_label.image = water_icon

# ============================
# MAP CLICK HANDLER
# ============================
def on_click(coords):
    global selected_polygon
    lat, lon = coords
    c = detect_corridor(lat, lon)

    if selected_polygon:
        map_widget.delete(selected_polygon)

    selected_polygon = map_widget.set_polygon(
        c["coords"], outline_color="#00FFAA", border_width=3)
    update_corridor_popup(c)
    update_water_popup(c)

map_widget.add_left_click_map_command(on_click)

# ============================
# RUN APP
# ============================
root.mainloop() # i want this same code but in 3d map of india with same output