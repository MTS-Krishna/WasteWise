# generate_qrs.py

import qrcode
import os

# Your backend's URL for the collector app, with a placeholder for the bin_id
COLLECTOR_APP_URL_TEMPLATE = "http://localhost:8502/?bin_id={}"

# Your bin IDs
BINS = ["bin-A", "bin-B", "bin-C", "bin-D"]

# Create a directory to store the QR codes
qr_dir = "bin_qrs"
os.makedirs(qr_dir, exist_ok=True)

for bin_id in BINS:
    # Construct the unique URL for each bin
    bin_url = COLLECTOR_APP_URL_TEMPLATE.format(bin_id)
    
    # Generate the QR code
    qr_img = qrcode.make(bin_url)
    
    # Save the QR code as a PNG file
    file_path = os.path.join(qr_dir, f"qr_code_{bin_id}.png")
    qr_img.save(file_path)
    print(f"Generated QR code for {bin_id} at {file_path}")

print("QR code generation complete.")