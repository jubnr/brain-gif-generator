import streamlit as st
import mne, os, tempfile, glob
import imageio.v2 as imageio
from pathlib import Path

# --- Page Configuration ---
st.set_page_config(
    page_title="Brain GIF Generator",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Caching Functions ---
@st.cache_resource
def get_fsaverage_path():
    """Fetches fsaverage files and returns the subjects_dir path."""
    fs_dir = mne.datasets.fetch_fsaverage(verbose=False)
    return Path(fs_dir).parent

# --- Main App Logic ---
st.title("🧠 Brain GIF Generator")
st.markdown("""
Upload your source estimate file (`.stc` or `.stc.h5`) and customize the visualization 
to generate an animated GIF of brain activity over time.
""")

# --- Sidebar for User Controls ---
with st.sidebar:
    st.header("⚙️ Controls")

    # 1. File Uploader
    uploaded_file = st.file_uploader(
        "Upload your .stc or .stc.h5 file",
        type=['stc', 'h5']
    )

    # 2. GIF Customization
    st.subheader("Display Customization 🎨")
    
    transparent_bg = st.toggle(
        "Transparent Background",
        value=False,
        help="Make the plot background transparent. This is great for overlays!"
    )

    colormap_selection = st.selectbox(
        "Colormap",
        ['hot', 'viridis', 'plasma', 'inferno', 'magma', 'coolwarm', 'RdBu_r'],
        index=0,
        help="Color palette for the brain activity."
    )

    background_color = st.selectbox(
        "Background Color",
        ('white', 'black'),
        index=0,
        help="Set the background color of the plot. This is ignored if 'Transparent Background' is on.",
        disabled=transparent_bg 
    )
    
    show_colorbar = st.toggle(
        "Show Colorbar", 
        value=False,
        help="Display the colorbar next to the brain plot."
    )

    cortex_selection = st.selectbox(
        "Cortex Style",
        ('low_contrast', 'classic', 'high_contrast'),
        index=0,
        help="Choose the style of the cortex surface."
    )

    hemi_selection = st.selectbox(
        "Hemisphere",
        ('split', 'lh', 'rh'),
        index=0,
        help="Select which hemisphere(s) to visualize. 'lh' for left, 'rh' for right, and 'split' for separate views (both)."
    )
    view_selection = st.multiselect(
        "View(s)",
        ['lateral', 'medial', 'rostral', 'caudal', 'dorsal', 'ventral', 'frontal', 'parietal'],
        default=['lateral'],
        help="Select one or more views. They will be arranged side-by-side."
    )
    smoothing_steps = st.slider(
        "Smoothing Steps",
        min_value=1,
        max_value=20,
        value=5,
        help="Number of smoothing steps to apply to the surface."
    )
    
    # 3. Time and GIF settings
    st.subheader("Animation Settings 🎬")
    frame_step = st.slider(
        "Time Step for Frames",
        min_value=1,
        max_value=50,
        value=20,
        help="Sample every Nth time point to create a frame. Smaller values mean a smoother but larger GIF."
    )
    gif_duration = st.slider(
        "Frame Duration (seconds)",
        min_value=0.05,
        max_value=0.5,
        value=0.1,
        step=0.01,
        help="How long each frame is shown in the final GIF."
    )

    generate_button = st.button("Generate GIF", type="primary")

# --- Main Panel for Output ---
if generate_button and uploaded_file is not None:
    
    if transparent_bg:
        os.environ['PYVISTA_TRANSPARENT_PLOTTER'] = 'True'
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            temp_stc_path = temp_dir_path / uploaded_file.name
            with open(temp_stc_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # --- Core MNE Logic ---
            with st.spinner("Loading data and preparing visualization..."):
                mne.viz.set_3d_backend("pyvista")
                subjects_dir = get_fsaverage_path()
                stc = mne.read_source_estimate(temp_stc_path)
                times_to_sample = stc.times[::frame_step]

                plot_kwargs = {
                    'subject': 'fsaverage',
                    'subjects_dir': subjects_dir,
                    'hemi': hemi_selection,
                    'views': view_selection,
                    'smoothing_steps': smoothing_steps,
                    'time_viewer': False,
                    'show_traces': False,
                    'colormap': colormap_selection,
                    'colorbar': show_colorbar,
                    'cortex': cortex_selection,
                    'size': (1600, 800)
                }
                
                if transparent_bg:
                    plot_kwargs['transparent'] = True
                else:
                    plot_kwargs['background'] = background_color
                
                brain = stc.plot(**plot_kwargs)

            st.info(f"Generating {len(times_to_sample)} frames...")
            progress_bar = st.progress(0)
            frames_dir = temp_dir_path / "frames"
            frames_dir.mkdir()

            for i, t in enumerate(times_to_sample):
                brain.set_time(t)
                screenshot_path = frames_dir / f'frame_{i:03d}.png'
                brain.save_image(screenshot_path)
                progress_bar.progress((i + 1) / len(times_to_sample))

            brain.close()
            
            # --- GIF Creation ---
            with st.spinner("Assembling GIF..."):
                frame_files = sorted(glob.glob(str(frames_dir / 'frame_*.png')))
                images = [imageio.imread(filename) for filename in frame_files]
                
                gif_path = temp_dir_path / "brain_animation.gif"

                imageio.mimsave(
                    gif_path, 
                    images, 
                    duration=gif_duration, 
                    loop=0,      
                    disposal=2   
                )

            # --- Display and Download ---
            st.success("🎉 GIF Generated Successfully!")
            
            st.image(str(gif_path), caption=f"Brain activity | Hemi: {hemi_selection} | View: {', '.join(view_selection)}")

            with open(gif_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download GIF",
                    data=f,
                    file_name=f"brain_animation_{hemi_selection}.gif",
                    mime="image/gif"
                )
    
    except Exception as e:
        st.error(f"An error occurred during GIF generation: {e}")

    finally:
        if 'PYVISTA_TRANSPARENT_PLOTTER' in os.environ:
            del os.environ['PYVISTA_TRANSPARENT_PLOTTER']

elif generate_button and uploaded_file is None:
    st.error("Please upload a file first.")