from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai


def process_pdf_with_document_ai(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
):
    """
    Sends a local PDF file to Document AI and returns the extracted document object.
    """

    api_endpoint = f"{location}-documentai.googleapis.com"

    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=api_endpoint)
    )

    processor_name = client.processor_path(project_id, location, processor_id)

    with open(file_path, "rb") as file:
        file_content = file.read()

    raw_document = documentai.RawDocument(
        content=file_content,
        mime_type="application/pdf",
    )

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document,
    )

    result = client.process_document(request=request)

    return result.document