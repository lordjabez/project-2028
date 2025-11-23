const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const IMAGES_DIR = './images';
const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif'];
const WEBP_QUALITY = 85;

function getAllImageFiles(dir) {
  const files = [];

  function traverse(currentPath) {
    const items = fs.readdirSync(currentPath);

    for (const item of items) {
      const fullPath = path.join(currentPath, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        traverse(fullPath);
      } else {
        const ext = path.extname(item).toLowerCase();
        if (IMAGE_EXTENSIONS.includes(ext)) {
          files.push(fullPath);
        }
      }
    }
  }

  traverse(dir);
  return files;
}

async function convertToWebP(imagePath) {
  const ext = path.extname(imagePath);
  const webpPath = imagePath.replace(ext, '.webp');

  console.log(`Converting: ${imagePath} -> ${webpPath}`);

  try {
    await sharp(imagePath)
      .webp({ quality: WEBP_QUALITY })
      .toFile(webpPath);

    // Get file sizes for comparison
    const originalSize = fs.statSync(imagePath).size;
    const webpSize = fs.statSync(webpPath).size;
    const savings = ((originalSize - webpSize) / originalSize * 100).toFixed(1);

    console.log(`  Original: ${(originalSize / 1024).toFixed(1)}KB -> WebP: ${(webpSize / 1024).toFixed(1)}KB (${savings}% reduction)\n`);

    return true;
  } catch (error) {
    console.error(`  Error converting ${imagePath}:`, error.message);
    return false;
  }
}

async function main() {
  console.log('Finding images to convert...\n');
  const imageFiles = getAllImageFiles(IMAGES_DIR);

  if (imageFiles.length === 0) {
    console.log('No images found to convert.');
    process.exit(0);
  }

  console.log(`Found ${imageFiles.length} image(s) to convert.\n`);

  let converted = 0;
  let failed = 0;

  for (const imagePath of imageFiles) {
    if (await convertToWebP(imagePath)) {
      converted++;
    } else {
      failed++;
    }
  }

  console.log('='.repeat(50));
  console.log(`Conversion complete!`);
  console.log(`  Converted: ${converted}`);
  console.log(`  Failed: ${failed}`);
  console.log('='.repeat(50));

  if (converted > 0) {
    console.log('\nNote: Original files have been preserved.');
    console.log('To remove original files after verification, run:');
    console.log(`  find ${IMAGES_DIR} -type f \\( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" \\) -delete`);
  }
}

main().catch(console.error);
