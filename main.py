import streamlit as st
import pandas as pd
import pydeck as pdk
from shapely.geometry import Polygon

# ============================
# LOAD DATA
# ============================
df = pd.read_csv("data/india_wildlife_corridors_polygons.csv")
water_df = pd.read_csv("data/water_usage_india.csv")

# ============================
# PROCESS CORRIDORS
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
        "centroid": (poly.centroid.y, poly.centroid.x)
    })

# ============================
# STREAMLIT UI
# ============================
st.set_page_config(page_title="🌍 Clickable Wildlife Globe", layout="wide")
st.title("🦁 Wildlife Corridors — 3D Clickable Earth Globe")

# ============================
# STATE — CLICK RESULT
# ============================
if "clicked_corridor" not in st.session_state:
    st.session_state.clicked_corridor = corridors[0]["name"]

# ============================
# CREATE POLYGON DATA FOR GLOBE
# ============================
globe_polys = []

for c in corridors:
    polygon_json = [[lon, lat] for (lat, lon) in c["coords"]]
    globe_polys.append({
        "polygon": polygon_json,
        "name": c["name"],
        "states": c["states"],
        "species": c["species"],
        "area": c["area"]
    })

polygon_layer = pdk.Layer(
    "PolygonLayer",
    data=globe_polys,
    pickable=True,
    get_polygon="polygon",
    get_fill_color=[255, 0, 0, 70],
    get_line_color=[255, 255, 255],
    get_line_width=120,
    extruded=True,
    elevation_scale=200000,
)

view_state = pdk.ViewState(
    latitude=0,
    longitude=0,
    zoom=1,
    pitch=0,
)

globe_view = pdk.View(type="_GlobeView", controller=True)

# ============================
# CAPTURE CLICK EVENT
# ============================
r = pdk.Deck(
    map_style=None,
    initial_view_state=view_state,
    views=[globe_view],
    layers=[polygon_layer],
    tooltip={"text": "{name}"}
)

click_event = st.pydeck_chart(r, width='stretch')

# ============================
# Corridor selected from click:
# ============================
if click_event.json_value is not None:
    try:
        clicked = click_event.json_value["pickedObjects"][0]["object"]["name"]
        st.session_state.clicked_corridor = clicked
    except:
        pass

selected = st.session_state.clicked_corridor

# ============================
# DISPLAY SELECTED CORRIDOR DATA
# ============================
st.subheader(f"🧾 Selected Corridor: {selected}")

c = next(x for x in corridors if x["name"] == selected)

state = c["states"].split(",")[0].strip()
row = water_df[water_df["state"] == state]

if not row.empty:
    water = {
        "available": int(row["total_available_water_m3"].iloc[0]),
        "used": int(row["water_used_m3"].iloc[0]),
        "used_percent": float(row["water_used_percent"].iloc[0]),
        "wasted": int(row["water_wasted_m3"].iloc[0]),
        "wasted_percent": float(row["water_wasted_percent"].iloc[0]),
    }
else:
    water = None

st.write(f"**States:** {c['states']}")
st.write(f"**Area:** {c['area']} km²")
st.write(f"**Species:** {c['species']}")

st.subheader("💧 Water Info")
if water:
    st.write(f"Total Available: {water['available']:,} m³")
    st.write(f"Used: {water['used']:,} m³")
    st.write(f"Wasted: {water['wasted']:,} m³")
    st.write(f"Wasted %: {water['wasted_percent']}%")
else:
    st.write("⚠ No water data")
