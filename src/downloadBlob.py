import os
from zipfile import ZipFile
from io import BytesIO
# Credentials URL from the VEC

def readBlob(container, blob_name):
    return container.download_blob(blob_name).readall()

def getAndReadFile(container, blob_name):
    zip_bytes = readBlob(container, f"{blob_name}.zip")
    input_zip = ZipFile(BytesIO(zip_bytes), 'r')
    ex_file = input_zip.open(f"{blob_name}.xml")
    content = ex_file.read()
    return content