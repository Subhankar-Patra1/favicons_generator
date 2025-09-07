import streamlit as st

# Hide Streamlit main menu, footer, and header
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
import os
import io
import zipfile
import requests
import base64
import json
import streamlit as st
import cairosvg
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse
from bs4 import BeautifulSoup

favicon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
formats = ["png", "jpg", "jpeg", "ico"]
FORMAT_MAP = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "ico": "ICO"}
OUTPUT_FOLDER = "downloaded_favicons"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_base_domain(url):
    if not url.startswith("http"):
        url = "http://" + url
    parsed = urlparse(url)
    return parsed.scheme + "://" + parsed.netloc

def get_website_name(url):
    try:
        html = requests.get(url, timeout=5).text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip()
        return "".join(c if c.isalnum() else "_" for c in title)[:30]
    except:
        parsed = urlparse(url)
        return parsed.netloc.replace(".", "_")

def try_favicon_urls(base_url):
    urls = []
    for size in favicon_sizes:
        urls.append(f"{base_url}/favicon-{size}x{size}.png")
        urls.append(f"{base_url}/icons/icon-{size}x{size}.png")
    urls.append(f"{base_url}/favicon.ico")
    return urls

def get_dominant_color(image):
    small = image.resize((1, 1))
    return small.getpixel((0, 0))

def add_overlay_text(img, text="A"):
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((5, 5), text, fill="white", font=font)
    return img

def svg_to_png(file):
    png_data = cairosvg.svg2png(bytestring=file.read())
    return Image.open(io.BytesIO(png_data))

def download_favicons_from_url(urls):
    all_downloaded = []
    for url in urls:
        base_url = get_base_domain(url)
        name_prefix = get_website_name(url)
        tried_urls = try_favicon_urls(base_url)
        for try_url in tried_urls:
            try:
                res = requests.get(try_url, timeout=5)
                if res.status_code == 200 and 'image' in res.headers.get("Content-Type", ""):
                    filename = os.path.join(OUTPUT_FOLDER, f"{name_prefix}_{try_url.split('/')[-1]}")
                    with open(filename, 'wb') as f:
                        f.write(res.content)
                    all_downloaded.append(filename)
            except:
                continue
    return all_downloaded

def resize_and_convert(image, prefix="favicon", overlay_text=""):
    result_files = {}
    for size in favicon_sizes:
        resized = image.resize((size, size))
        if overlay_text:
            resized = add_overlay_text(resized, overlay_text)
        result_files[size] = {}
        for fmt in formats:
            filename = f"{prefix}_{size}x{size}.{fmt}"
            filepath = os.path.join(OUTPUT_FOLDER, filename)
            if fmt == "ico":
                resized.save(filepath, format=FORMAT_MAP[fmt])
            else:
                bg = Image.new("RGBA", resized.size, (255, 255, 255, 0))
                bg.paste(resized, (0, 0), resized if resized.mode == 'RGBA' else None)
                if fmt in ["jpg", "jpeg"]:
                    bg.convert("RGB").save(filepath, format=FORMAT_MAP[fmt])
                else:
                    bg.save(filepath, format=FORMAT_MAP[fmt])
            result_files[size][fmt] = filepath
    return result_files

def generate_zip_file(file_dict, format_filter, zip_name="favicons"):
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w') as zipf:
        for size, fmt_dict in file_dict.items():
            if format_filter in fmt_dict:
                path = fmt_dict[format_filter]
                arcname = os.path.basename(path)
                zipf.write(path, arcname=arcname)
        manifest = {
            "name": zip_name,
            "icons": [
                {
                    "src": f"{zip_name}_{size}x{size}.{format_filter}",
                    "sizes": f"{size}x{size}",
                    "type": f"image/{format_filter if format_filter != 'jpg' else 'jpeg'}"
                } for size in file_dict
            ]
        }
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
    mem_zip.seek(0)
    return mem_zip

st.set_page_config(page_title="Favicon Generator", layout="centered")
st.title("🎯 Multi-format Favicon Generator")
st.markdown("Upload an **image (PNG, JPG, JPEG, GIF, SVG)** or enter **one or more website URLs** to generate favicons.")

uploaded_file = st.file_uploader("📁 Upload Image File", type=["png", "jpg", "jpeg", "gif", "svg"])
input_urls = st.text_area("🔗 Enter Website URLs (one per line)").splitlines()
overlay_text = st.text_input("🖍️ Optional Overlay Text (e.g., initials)", "")
add_confetti = st.checkbox("🎉 Show Confetti After Generation", value=True)

if "generated_files" not in st.session_state:
    st.session_state.generated_files = {}
    st.session_state.generated_name = "favicon"

if st.button("🚀 Generate / Download Favicons"):
    st.session_state.generated_files = {}
    with st.spinner("Processing..."):
        image_set = {}
        progress = st.progress(0)
        if uploaded_file:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            name_prefix = os.path.splitext(uploaded_file.name)[0]
            st.session_state.generated_name = name_prefix
            try:
                if ext == ".svg":
                    image = svg_to_png(uploaded_file)
                elif ext == ".gif":
                    image = Image.open(uploaded_file).convert("RGBA")
                    image.seek(0)
                else:
                    image = Image.open(uploaded_file).convert("RGBA")
                dominant_color = get_dominant_color(image)
                st.markdown(f"🎨 **Dominant Color:** `{dominant_color}`")
                st.session_state.generated_files = resize_and_convert(image, prefix=name_prefix, overlay_text=overlay_text)
                st.success("✅ Favicons generated from uploaded image.")
                if add_confetti:
                    st.balloons()
                st.snow()
            except Exception as e:
                st.error(f"❌ Error processing image: {e}")
            progress.progress(100)
        elif input_urls:
            downloaded = download_favicons_from_url(input_urls)
            if downloaded:
                for i, file in enumerate(downloaded):
                    try:
                        img = Image.open(file).convert("RGBA")
                        resized_set = resize_and_convert(img, prefix=os.path.splitext(os.path.basename(file))[0], overlay_text=overlay_text)
                        for size, fmt_files in resized_set.items():
                            if size not in image_set:
                                image_set[size] = {}
                            image_set[size].update(fmt_files)
                    except:
                        continue
                    progress.progress(int((i + 1) / len(downloaded) * 100))
                st.session_state.generated_files = image_set
                st.success("✅ Favicons downloaded & resized.")
                if add_confetti:
                    st.balloons()
            else:
                st.warning("⚠️ No favicons found at standard paths.")
        else:
            st.error("❌ Please upload an image or enter at least one website URL.")

if st.session_state.generated_files:
    st.subheader("🖼️ Preview of Generated Icons")
    for size, fmt_files in st.session_state.generated_files.items():
        st.markdown(f"**🔹 Size: {size}x{size}**")
        cols = st.columns(len(fmt_files))
        for i, (fmt, path) in enumerate(fmt_files.items()):
            with cols[i]:
                st.image(path, caption=fmt.upper(), use_container_width=True)
                with open(path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {fmt.upper()}",
                        data=f,
                        file_name=os.path.basename(path),
                        mime=f"image/{'jpeg' if fmt == 'jpg' else fmt}"
                    )
    st.subheader("🧪 Browser Tab Preview")
    preview_path = list(st.session_state.generated_files.values())[0].get("png")
    if preview_path:
        with open(preview_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 10px;">
                    <img src="data:image/png;base64,{img_base64}" width="32" />
                    <span style="font-size: 18px; font-weight: bold;">My Website</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    st.subheader("📦 Download All Icons as ZIP")
    zip_format = st.selectbox("Choose a format for ZIP download:", formats, index=0)
    zip_data = generate_zip_file(
        st.session_state.generated_files,
        format_filter=zip_format,
        zip_name=st.session_state.generated_name
    )
    st.download_button(
        label=f"⬇️ Download ZIP ({zip_format.upper()})",
        data=zip_data,
        file_name=f"{st.session_state.generated_name}_favicons_{zip_format}.zip",
        mime="application/zip"
    )