import os

import cv2
import fitz
import numpy as np
from PIL import Image


def preprocess_image_for_ocr(image_rgb, mode="balanced"):
    """
    Preprocesses one rendered PDF page image for OCR.

    Modes:
    - light: safer, keeps more original text detail
    - balanced: recommended first test
    - strong: stronger binarization, may remove noise but can damage thin text
    """

    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    if mode == "light":
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

        return sharpened

    if mode == "strong":
        denoised = cv2.fastNlMeansDenoising(
            gray,
            None,
            h=18,
            templateWindowSize=7,
            searchWindowSize=21,
        )

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        _, binary = cv2.threshold(
            enhanced,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return cleaned

    # balanced mode
    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=12,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    binary = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        15,
    )

    return binary


def preprocess_pdf_for_ocr(
    input_pdf_path,
    output_pdf_path,
    dpi=250,
    mode="balanced",
):
    """
    Converts a PDF into images, preprocesses each page, and saves a cleaned PDF.

    This function does not modify the original PDF.

    Parameters:
    - input_pdf_path: original PDF path
    - output_pdf_path: cleaned PDF output path
    - dpi: render resolution
    - mode: light, balanced, or strong
    """

    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    pdf_document = fitz.open(input_pdf_path)
    processed_pages = []

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_index in range(len(pdf_document)):
        page = pdf_document[page_index]
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        image_array = np.frombuffer(pixmap.samples, dtype=np.uint8)
        image_rgb = image_array.reshape(pixmap.height, pixmap.width, pixmap.n)

        processed_image = preprocess_image_for_ocr(image_rgb, mode=mode)

        pil_image = Image.fromarray(processed_image).convert("RGB")
        processed_pages.append(pil_image)

    pdf_document.close()

    if not processed_pages:
        raise ValueError("No pages were processed from the PDF.")

    first_page = processed_pages[0]
    remaining_pages = processed_pages[1:]

    first_page.save(
        output_pdf_path,
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=remaining_pages,
    )

    return output_pdf_path