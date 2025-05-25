# Hoztech Store Static Files

This directory contains all static files for the Hoztech Store application.

## Directory Structure

```
static/store/
├── css/
│   └── style.css          # Main stylesheet for the store
├── js/
│   └── store.js           # JavaScript functionality for the store
└── images/                # Product and category images
    ├── products/          # Product images
    ├── categories/        # Category images
    └── banners/           # Banner images for homepage and promotions
```

## Image Guidelines

### Product Images
- Recommended size: 800x800 pixels
- Format: JPG or PNG
- Maximum file size: 500KB
- Naming convention: `product-{slug}.jpg`

### Category Images
- Recommended size: 400x400 pixels
- Format: JPG or PNG
- Maximum file size: 200KB
- Naming convention: `category-{slug}.jpg`

### Banner Images
- Recommended size: 1920x600 pixels
- Format: JPG or PNG
- Maximum file size: 1MB
- Naming convention: `banner-{name}.jpg`

## CSS Usage

The main stylesheet (`style.css`) includes styles for:
- Product grid and cards
- Category badges
- Price displays
- Cart items
- Checkout forms
- Order status indicators
- Responsive design adjustments

## JavaScript Features

The main JavaScript file (`store.js`) provides:
- Product gallery image switching
- Quantity input handling
- Cart updates via AJAX
- Search functionality
- Newsletter form handling
- Notification system
- Add to cart animations

## Adding New Static Files

1. Place new images in the appropriate subdirectory under `images/`
2. Follow the naming conventions for each type of image
3. Optimize images before adding them to reduce file size
4. Update this README if adding new directories or changing the structure 