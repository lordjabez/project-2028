#!/bin/bash

# This script downloads the public domain portraits for the
# Project 2028 application and saves them with the correct filenames.

# Set the target directory relative to the script's location
TARGET_DIR="images/portraits"

# Create the directory if it doesn't exist
echo "Creating directory '$TARGET_DIR'..."
mkdir -p "$TARGET_DIR"

# Define the images to download
# Format: "filename|url" on each line
images=(
  "kamala-harris|https://upload.wikimedia.org/wikipedia/commons/4/41/Kamala_Harris_Vice_Presidential_Portrait.jpg"
  "gavin-newsom|https://upload.wikimedia.org/wikipedia/commons/8/88/Governor_Gavin_Newsom_in_2025.jpg"
  "gretchen-whitmer|https://upload.wikimedia.org/wikipedia/commons/2/2e/2025_Gretchen_Whitmer_%28cropped%29.jpg"
  "jared-polis|https://upload.wikimedia.org/wikipedia/commons/5/53/Governor_Jared_Polis_2023.jpg"
  "jb-pritzker|https://upload.wikimedia.org/wikipedia/commons/a/af/J.B._Pritzker_April_2023.jpg"
  "andy-beshear|https://upload.wikimedia.org/wikipedia/commons/0/06/Andy_Beshear_2025.jpg"
  "wes-moore|https://upload.wikimedia.org/wikipedia/commons/c/c3/Wes_Moore_Official_Governor_Portrait.jpg"
  "roy-cooper|https://upload.wikimedia.org/wikipedia/commons/3/30/Roy_Cooper_in_November_2023_%28cropped2%29.jpg"
  "phil-murphy|https://upload.wikimedia.org/wikipedia/commons/e/e1/Gov._Phil_Murphy.jpg"
  "cory-booker|https://upload.wikimedia.org/wikipedia/commons/5/59/Cory_Booker%2C_official_portrait%2C_114th_Congress.jpg"
)

# Loop through the array and download each image using curl
for entry in "${images[@]}"; do
  filename="${entry%%|*}"
  url="${entry#*|}"
  output_path="$TARGET_DIR/$filename.jpg"

  echo "Downloading: $filename"
  
  # Use curl with:
  # -L to follow any redirects
  # -sS for silent mode but still show errors
  # -o to specify the output file
  curl -L -sS -o "$output_path" "$url"
  
  if [ $? -eq 0 ]; then
    echo " -> Successfully saved to $output_path"
  else
    echo " -> ERROR: Failed to download $filename"
  fi
done

echo ""
echo "Image download process complete."
