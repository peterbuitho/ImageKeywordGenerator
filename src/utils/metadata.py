from PIL import Image, PngImagePlugin
import piexif
from typing import Dict, List
from pathlib import Path
import json

def save_keywords(image_path: str, keywords: Dict[str, List[str]], output_dir: str, append: bool = False) -> None:
    """Save keywords to separate JSON files for each language"""
    image_name = Path(image_path).stem
    
    for lang, kw_list in keywords.items():
        output_path = Path(output_dir) / f"{image_name}_keywords_{lang}.json"
        
        if append and output_path.exists():
            # Load existing keywords
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_keywords = existing_data.get('keywords', [])
                
                # Merge keywords without duplicates
                merged_keywords = list(set(existing_keywords + kw_list))
                kw_list = merged_keywords
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'image': image_path,
                'language': lang,
                'keywords': kw_list
            }, f, indent=2, ensure_ascii=False)

def embed_keywords_in_image(image_path: str, keywords: Dict[str, List[str]], selected_languages: List[str]) -> bool:
    """Embed keywords into image metadata for selected languages only"""
    try:
        with Image.open(image_path) as img:
            # Create combined keyword string for all selected languages with UTF-8 encoding
            combined_keywords = []
            for lang in selected_languages:
                if lang in keywords and keywords[lang]:
                    lang_keywords = keywords[lang]
                    # Ensure proper UTF-8 encoding for each keyword
                    combined_keywords.extend([f"{lang}:{kw}".encode('utf-8').decode('utf-8') 
                                           for kw in lang_keywords])
            
            # Convert to string format with proper encoding
            keyword_string = ", ".join(combined_keywords)
            
            if img.format == 'JPEG':
                try:
                    exif_dict = piexif.load(img.info.get('exif', b''))
                except:
                    exif_dict = {'0th': {}, '1st': {}, 'Exif': {}, 'GPS': {}, 'Interop': {}}
                
                # Store all keywords in one UserComment tag with UTF-8 encoding
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = keyword_string.encode('utf-8')
                
                # Convert back to bytes
                exif_bytes = piexif.dump(exif_dict)
                
                # Save with new metadata
                img.save(image_path, 'JPEG', exif=exif_bytes, quality='keep')
            
            elif img.format == 'PNG':
                # Create new image with metadata
                new_img = Image.new(img.mode, img.size)
                new_img.putdata(list(img.getdata()))
                
                # Add metadata (PNG text chunks are UTF-8 by default)
                info = PngImagePlugin.PngInfo()
                info.add_text("Keywords", keyword_string)
                
                # Save with metadata
                new_img.save(image_path, 'PNG', pnginfo=info)
            
            else:
                raise ValueError(f"Unsupported image format: {img.format}")
            
        return True
    except Exception as e:
        print(f"Error embedding keywords in {image_path}: {str(e)}")
        return False
