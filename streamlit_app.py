import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import tempfile
import fitz  # PyMuPDF for PDF handling
from PIL import Image
import io

# Define enhanced prompts for better information extraction
DOCUMENT_ANALYSIS_PROMPT = """
Analyze this declassified JFK assassination document image in detail:

1. DOCUMENT IDENTIFICATION:
   - Document type (memo, report, telegram, etc.)
   - Classification level (Top Secret, Secret, Confidential, etc.)
   - Document date and reference numbers
   - Originating agency or department

2. KEY ENTITIES:
   - All individuals mentioned (full names and positions if available)
   - Organizations, agencies, and departments
   - Locations mentioned (cities, countries, specific places)

3. SUBJECT MATTER:
   - Main topic or purpose of the document
   - Key events described or referenced
   - Connections to the Kennedy assassination (if explicit)
   - Any mentioned dates of significance

4. INTELLIGENCE VALUE:
   - Notable facts or claims presented
   - Any redactions or apparent omissions
   - Connections to other known intelligence operations
   - Unusual or seemingly significant details

Format your response in clear sections using the categories above.
"""

SUMMARY_PROMPT_TEMPLATE = """
Create a comprehensive summary of this declassified JFK document based on the following page-by-page analysis:

{all_analysis}

Your summary should:
1. Identify the document type, date, and originating agency
2. Explain the primary subject matter and purpose
3. List all key individuals mentioned and their roles
4. Highlight the most significant revelations or intelligence
5. Note any apparent redactions or missing information
6. Explain connections to the Kennedy assassination investigation
7. Identify any notable inconsistencies or areas requiring further research

Format your summary with clear headings and bullet points for key findings.
"""

# Page configuration
st.set_page_config(
    page_title="JFK Files Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize Gemini client if API key is available
if api_key:
    client = genai.Client(api_key=api_key)
else:
    st.error("Gemini API key not found. Please add it to your .env file or Streamlit secrets.")
    st.stop()

# App title and description
st.title("JFK Assassination Files Analyzer")
st.markdown("""
This app helps you analyze declassified JFK assassination files from the National Archives.
Upload a PDF file, and the AI will extract and analyze the information for you using specialized prompts designed for intelligence documents.
""")

# Sidebar for configuration options
with st.sidebar:
    st.header("Configuration")
    model_choice = st.selectbox(
        "Select Gemini Model",
        ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro-vision"]
    )
    
    max_pages = st.number_input(
        "Max pages to analyze (0 for all)",
        min_value=0,
        value=5
    )
    
    custom_prompt = st.checkbox("Use custom prompt", value=False)
    
    if custom_prompt:
        user_prompt = st.text_area(
            "Custom analysis prompt",
            value=DOCUMENT_ANALYSIS_PROMPT,
            height=300
        )
    else:
        user_prompt = DOCUMENT_ANALYSIS_PROMPT
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    This application uses Google's Gemini multimodal model to analyze 
    declassified JFK assassination files. The files are sourced from the 
    [National Archives](https://www.archives.gov/research/jfk/release).
    """)

# Main function to process PDFs
def process_pdf(pdf_file, max_pages=5, prompt=DOCUMENT_ANALYSIS_PROMPT):
    results = []
    
    # Create a temporary file to save the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Open the PDF using PyMuPDF
        doc = fitz.open(tmp_path)
        total_pages = doc.page_count
        
        # Limit pages to analyze
        pages_to_analyze = total_pages if max_pages == 0 else min(max_pages, total_pages)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page_num in range(pages_to_analyze):
            status_text.text(f"Processing page {page_num + 1} of {pages_to_analyze}...")
            
            # Get the page
            page = doc.load_page(page_num)
            
            # Render page to an image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
            img_bytes = pix.tobytes("png")
            
            # Convert to PIL Image for Gemini
            image = Image.open(io.BytesIO(img_bytes))
            
            # Send to Gemini for analysis
            try:
                response = client.models.generate_content(
                    model=model_choice,
                    contents=[prompt, image]
                )
                
                results.append({
                    "page_num": page_num + 1,
                    "analysis": response.text,
                    "image": img_bytes
                })
            except Exception as e:
                results.append({
                    "page_num": page_num + 1,
                    "analysis": f"Error analyzing this page: {str(e)}",
                    "image": img_bytes
                })
            
            # Update progress bar
            progress_bar.progress((page_num + 1) / pages_to_analyze)
        
        status_text.text("Processing complete!")
        
        # Close and clean up
        doc.close()
        os.unlink(tmp_path)
        
        return results
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return []

# Upload section with tabs for different input types
st.write("### Upload Document")
input_type = st.radio("Choose input type:", ["PDF Document", "Single Image"], horizontal=True)

if input_type == "PDF Document":
    uploaded_file = st.file_uploader("Upload a JFK file (PDF format)", type=["pdf"])

    if uploaded_file:
        # Display file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.write(file_details)
        
        # Process button
        if st.button("Analyze Document"):
            with st.spinner("Processing document..."):
                results = process_pdf(uploaded_file, max_pages=max_pages, prompt=user_prompt)
            
            if results:
                # Display results in tabs for each page
                tabs = st.tabs([f"Page {r['page_num']}" for r in results])
                
                for i, tab in enumerate(tabs):
                    with tab:
                        # Create two columns for side-by-side display
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.image(results[i]["image"], caption=f"Page {results[i]['page_num']}", use_column_width=True)
                        
                        with col2:
                            st.markdown("### AI Analysis")
                            st.markdown(results[i]["analysis"])
                            
                            # Download button for the analysis
                            text_data = f"# Analysis of Page {results[i]['page_num']}\n\n{results[i]['analysis']}"
                            st.download_button(
                                label="Download Analysis",
                                data=text_data,
                                file_name=f"analysis_page_{results[i]['page_num']}.txt",
                                mime="text/plain"
                            )
                
                # Full document summary at the bottom
                st.markdown("---")
                st.markdown("## Document Summary")
                
                # Combine all the analysis text
                all_analysis = "\n\n".join([f"**Page {r['page_num']}**:\n{r['analysis']}" for r in results])
                
                # Generate a summary using Gemini
                try:
                    summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(all_analysis=all_analysis)
                    
                    summary_response = client.models.generate_content(
                        model=model_choice,
                        contents=[summary_prompt]
                    )
                    st.markdown(summary_response.text)
                    
                    # Download full report button
                    full_report = f"# JFK Document Analysis: {uploaded_file.name}\n\n## Summary\n\n{summary_response.text}\n\n## Page-by-Page Analysis\n\n{all_analysis}"
                    st.download_button(
                        label="Download Full Report",
                        data=full_report,
                        file_name=f"jfk_analysis_{uploaded_file.name}.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error generating summary: {str(e)}")
else:  # Single Image option
    uploaded_image = st.file_uploader("Upload an image of a JFK document", type=["png", "jpg", "jpeg"])
    
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Analyze Image"):
            with st.spinner("Analyzing image..."):
                try:
                    # Load the image
                    image = Image.open(uploaded_image)
                    
                    # Send to Gemini for analysis
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=[user_prompt, image]
                    )
                    
                    # Display the analysis
                    st.markdown("### AI Analysis")
                    st.markdown(response.text)
                    
                    # Download button
                    st.download_button(
                        label="Download Analysis",
                        data=response.text,
                        file_name=f"jfk_image_analysis.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error analyzing image: {str(e)}")

# Add footer with version info
st.markdown("---")
st.caption("JFK Files Analyzer v1.1 | Built with Streamlit & Google Gemini")