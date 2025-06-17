import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from PyPDF2 import PdfMerger
from ebooklib import epub
from bs4 import BeautifulSoup
from io import BytesIO
import yfinance as yf
import matplotlib.pyplot as plt
import datetime
import os

# ----------------------------
# Invoice Generator Functions
# ----------------------------

def generate_invoice_pdf(client_name, items, total):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 50, f"Invoice for {client_name}")
    c.drawString(50, height - 70, "----------------------------------------")
    y = height - 100
    for i, item in enumerate(items, 1):
        desc, price = item
        c.drawString(50, y, f"{i}. {desc} - ${price:.2f}")
        y -= 20
    c.drawString(50, y - 20, f"Total: ${total:.2f}")
    c.save()
    buffer.seek(0)
    return buffer

def merge_pdfs(main_pdf, extra_pdfs):
    merger = PdfMerger()
    merger.append(main_pdf)
    for pdf in extra_pdfs:
        merger.append(pdf)
    merged = BytesIO()
    merger.write(merged)
    merger.close()
    merged.seek(0)
    return merged

# ----------------------------
# ePub Formatter Functions
# ----------------------------

def load_epub(file):
    return epub.read_epub(file)

def format_epub(book):
    for item in book.get_items():
        if item.get_type() == epub.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.content, "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            item.content = str(soup).encode()
    return book

def export_epub(book):
    buffer = BytesIO()
    epub.write_epub(buffer, book)
    buffer.seek(0)
    return buffer

# ----------------------------
# Stock Viewer Functions
# ----------------------------

def create_stock_pdf(ticker, df, chart_img):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"Stock Report: {ticker}")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Data from {df.index[0].date()} to {df.index[-1].date()}")
    c.drawString(50, height - 100, f"Latest Close: ${df['Close'].iloc[-1]:.2f}")

    chart_path = "/tmp/stock_chart.png"
    with open(chart_path, "wb") as f:
        f.write(chart_img.getbuffer())

    c.drawImage(chart_path, 50, height - 400, width=500, preserveAspectRatio=True, mask='auto')
    c.save()
    buffer.seek(0)
    return buffer

# ----------------------------
# Streamlit App UI
# ----------------------------

st.set_page_config(page_title="Multi-Tool App", layout="centered")
st.sidebar.title("📚 Navigation")
page = st.sidebar.radio("Select a page:", [
    "Invoice Generator",
    "ePub Formatter",
    "Stock Viewer"
])

# ----------------------------
# Page 1: Invoice Generator
# ----------------------------

if page == "Invoice Generator":
    st.title("🧾 Invoice Generator")

    client_name = st.text_input("Client Name")
    item_count = st.number_input("Number of items", min_value=1, max_value=10, step=1)
    items = []

    for i in range(item_count):
        col1, col2 = st.columns([3, 1])
        with col1:
            desc = st.text_input(f"Description #{i+1}", key=f"desc_{i}")
        with col2:
            price = st.number_input(f"Price #{i+1}", key=f"price_{i}", min_value=0.0)
        items.append((desc, price))

    extra_pdfs = st.file_uploader("Optional: Merge extra PDFs", type="pdf", accept_multiple_files=True)

    if st.button("Generate Invoice"):
        total = sum(price for _, price in items)
        invoice_pdf = generate_invoice_pdf(client_name, items, total)
        if extra_pdfs:
            merged = merge_pdfs(invoice_pdf, extra_pdfs)
            st.download_button("Download Merged Invoice PDF", merged, "merged_invoice.pdf")
        else:
            st.download_button("Download Invoice PDF", invoice_pdf, "invoice.pdf")

# ----------------------------
# Page 2: ePub Formatter
# ----------------------------

elif page == "ePub Formatter":
    st.title("📖 ePub Formatter")

    epub_file = st.file_uploader("Upload .epub file", type="epub")
    if epub_file:
        st.success("File uploaded successfully!")
        book = load_epub(epub_file)

        st.subheader("Chapters in Book:")
        chapters = [item for item in book.get_items_of_type(epub.ITEM_DOCUMENT)]
        for i, chap in enumerate(chapters, 1):
            st.markdown(f"**{i}. {chap.get_name()}**")

        if st.button("Format and Export"):
            updated_book = format_epub(book)
            output_epub = export_epub(updated_book)
            st.download_button("Download Formatted ePub", output_epub, "formatted_book.epub")

# ----------------------------
# Page 3: Stock Viewer
# ----------------------------

elif page == "Stock Viewer":
    st.title("📈 Stock Viewer")

    ticker = st.text_input("Enter stock ticker (e.g., AAPL, MSFT):")
    start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
    end_date = st.date_input("End Date", datetime.date.today())

    if ticker:
        df = yf.download(ticker, start=start_date, end=end_date)
        if not df.empty:
            st.subheader(f"{ticker} - Closing Prices")
            fig, ax = plt.subplots()
            df['Close'].plot(ax=ax, title=f"{ticker} Closing Prices")
            st.pyplot(fig)

            chart_buf = BytesIO()
            fig.savefig(chart_buf, format='png')
            chart_buf.seek(0)

            if st.button("Export PDF Report"):
                stock_pdf = create_stock_pdf(ticker, df, chart_buf)
                st.download_button("Download Stock PDF", stock_pdf, f"{ticker}_report.pdf")
        else:
            st.error("No data found for the ticker and date range.")
