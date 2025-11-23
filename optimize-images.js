#!/usr/bin/env node

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  inputDir: './images',
  outputDir: './images/optimized',
  maxWidth: 800,        // Maximum width in pixels
  maxHeight: 800,       // Maximum height in pixels
  quality: 85,          // JPEG quality (1-100)
  progressive: true,    // Use progressive JPEG
  formats: ['.jpg', '.jpeg', '.png', '.webp']
};

// Ensure output directory exists
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// Get all image files recursively
function getImageFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);

  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat.isDirectory()) {
      // Skip output directory to avoid processing optimized images
      if (!filePath.includes('optimized')) {
        getImageFiles(filePath, fileList);
      }
    } else {
      const ext = path.extname(file).toLowerCase();
      if (CONFIG.formats.includes(ext)) {
        fileList.push(filePath);
      }
    }
  });

  return fileList;
}

// Format bytes to human-readable size
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Optimize a single image
async function optimizeImage(inputPath) {
  const relativePath = path.relative(CONFIG.inputDir, inputPath);
  const outputPath = path.join(CONFIG.outputDir, relativePath);
  const outputDir = path.dirname(outputPath);

  // Ensure output subdirectory exists
  ensureDir(outputDir);

  try {
    const inputStats = fs.statSync(inputPath);
    const inputSize = inputStats.size;

    // Process image with sharp
    await sharp(inputPath)
      .resize(CONFIG.maxWidth, CONFIG.maxHeight, {
        fit: 'inside',           // Maintain aspect ratio
        withoutEnlargement: true // Don't upscale small images
      })
      .jpeg({
        quality: CONFIG.quality,
        progressive: CONFIG.progressive,
        mozjpeg: true            // Use mozjpeg for better compression
      })
      .toFile(outputPath);

    const outputStats = fs.statSync(outputPath);
    const outputSize = outputStats.size;
    const savings = ((inputSize - outputSize) / inputSize * 100).toFixed(1);

    console.log(`✓ ${relativePath}`);
    console.log(`  ${formatBytes(inputSize)} → ${formatBytes(outputSize)} (${savings}% reduction)`);

    return {
      file: relativePath,
      originalSize: inputSize,
      optimizedSize: outputSize,
      savings: parseFloat(savings)
    };
  } catch (error) {
    console.error(`✗ Failed to optimize ${relativePath}:`, error.message);
    return null;
  }
}

// Main function
async function main() {
  console.log('🖼️  Image Optimization Script');
  console.log('================================\n');
  console.log(`Input directory: ${CONFIG.inputDir}`);
  console.log(`Output directory: ${CONFIG.outputDir}`);
  console.log(`Max dimensions: ${CONFIG.maxWidth}x${CONFIG.maxHeight}px`);
  console.log(`JPEG quality: ${CONFIG.quality}%\n`);

  // Ensure output directory exists
  ensureDir(CONFIG.outputDir);

  // Get all image files
  const imageFiles = getImageFiles(CONFIG.inputDir);

  if (imageFiles.length === 0) {
    console.log('No image files found.');
    return;
  }

  console.log(`Found ${imageFiles.length} image(s) to optimize\n`);

  // Optimize all images
  const results = [];
  for (const file of imageFiles) {
    const result = await optimizeImage(file);
    if (result) {
      results.push(result);
    }
  }

  // Summary
  if (results.length > 0) {
    const totalOriginal = results.reduce((sum, r) => sum + r.originalSize, 0);
    const totalOptimized = results.reduce((sum, r) => sum + r.optimizedSize, 0);
    const totalSavings = ((totalOriginal - totalOptimized) / totalOriginal * 100).toFixed(1);

    console.log('\n================================');
    console.log('Summary:');
    console.log(`Total files: ${results.length}`);
    console.log(`Original size: ${formatBytes(totalOriginal)}`);
    console.log(`Optimized size: ${formatBytes(totalOptimized)}`);
    console.log(`Total savings: ${totalSavings}%`);
    console.log(`\n✨ Optimization complete! Optimized images saved to: ${CONFIG.outputDir}`);
  }
}

// Run the script
main().catch(error => {
  console.error('Error:', error);
  process.exit(1);
});
