#!/usr/bin/env python3
"""
OmniParser Lite - Version simplifiée sans dépendance au repo complet
"""
import os
import sys
import torch
import base64
import json
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import numpy as np
from datetime import datetime

# Vérifier le GPU
print("=== OmniParser Lite Server ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA disponible: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Mémoire GPU: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

app = FastAPI(title="OmniParser Lite API", version="1.0.0")

# Configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"\n✅ Utilisation du {DEVICE.upper()}")

# Créer le dossier pour sauvegarder les détections
DETECTIONS_DIR = Path("detections")
DETECTIONS_DIR.mkdir(exist_ok=True)
print(f"📁 Dossier de détections: {DETECTIONS_DIR}")

# Import des modèles
try:
    from ultralytics import YOLO
    from transformers import AutoProcessor, AutoModelForCausalLM
    import easyocr
    import cv2
    print("✅ Modules importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Installez les dépendances: pip install ultralytics transformers==4.49.0 easyocr opencv-python")
    sys.exit(1)

# Initialisation des modèles
print("\n📥 Chargement des modèles...")

# OCR
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
print("✅ EasyOCR initialisé")

# YOLO pour la détection d'icônes
yolo_model = None
# Le modèle OmniParser pour la détection d'UI
UI_MODEL_PATH = 'weights/icon_detect/model.pt'

if os.path.exists(UI_MODEL_PATH):
    try:
        yolo_model = YOLO(UI_MODEL_PATH)
        yolo_model.to(DEVICE)
        print(f"✅ YOLO UI Model chargé depuis: {UI_MODEL_PATH}")
        print(f"   Classes: {len(yolo_model.names) if hasattr(yolo_model, 'names') else 'N/A'}")
        if hasattr(yolo_model, 'names'):
            print(f"   Types détectés: {list(yolo_model.names.values())}")
    except Exception as e:
        print(f"❌ Erreur chargement du modèle UI: {e}")
        # Fallback sur YOLOv8s standard
        try:
            yolo_model = YOLO('yolov8s.pt')
            yolo_model.to(DEVICE)
            print("⚠️ Utilisation du modèle YOLO standard (pas optimisé pour UI)")
        except:
            pass
else:
    print(f"⚠️ Modèle UI non trouvé à {UI_MODEL_PATH}")
    # Essayer YOLOv8s standard
    try:
        yolo_model = YOLO('yolov8s.pt')
        yolo_model.to(DEVICE)
        print("⚠️ Utilisation du modèle YOLO standard (pas optimisé pour UI)")
    except Exception as e:
        print(f"❌ Impossible de charger YOLO: {e}")

# Florence-2 pour les captions (optionnel)
processor = None
caption_model = None
try:
    # Essayer d'abord le dossier local
    if os.path.exists("weights/icon_caption_florence"):
        print("📁 Dossier Florence-2 trouvé, chargement...")
        # Vérifier si les fichiers Python nécessaires existent
        if os.path.exists("weights/icon_caption_florence/modeling_florence2.py"):
            processor = AutoProcessor.from_pretrained("weights/icon_caption_florence", trust_remote_code=True)
            caption_model = AutoModelForCausalLM.from_pretrained("weights/icon_caption_florence", trust_remote_code=True).to(DEVICE)
            print("✅ Florence-2 chargé depuis le dossier local")
        else:
            print("⚠️ Florence-2 incomplet - fichiers Python manquants")
            print("   Essai de chargement depuis Hugging Face...")
            # Essayer de charger depuis Hugging Face directement
            processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base-ft", trust_remote_code=True)
            caption_model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base-ft", trust_remote_code=True).to(DEVICE)
            print("✅ Florence-2 chargé depuis Hugging Face")
    else:
        print("⚠️ Florence-2 non disponible - dossier non trouvé")
except Exception as e:
    print(f"⚠️ Florence-2 non chargé - Erreur: {e}")
    print("   Le système fonctionnera sans génération de captions pour les icônes")

class ImageRequest(BaseModel):
    base64_image: str

class ParsedElement(BaseModel):
    type: str
    content: str = ""
    bbox: List[float]
    confidence: float = 1.0

class ParseResponse(BaseModel):
    parsed_content_list: List[Dict[str, Any]]
    success: bool = True
    message: str = "OK"
    detection_image_path: str = ""
    labeled_image: str = ""  # Image annotée en base64

def get_color_luminance(color_rgb):
    """Calcule la luminance d'une couleur RGB"""
    if isinstance(color_rgb, str):
        # Convertir les noms de couleur en RGB
        color_map = {
            "green": (0, 128, 0),
            "red": (255, 0, 0),
            "blue": (0, 0, 255),
            "orange": (255, 165, 0),
            "yellow": (255, 255, 0)
        }
        color_rgb = color_map.get(color_rgb, (128, 128, 128))
    
    r, g, b = color_rgb
    return 0.299 * r + 0.587 * g + 0.114 * b

def find_best_label_position(bbox, label_width, label_height, image_width, image_height, all_boxes):
    """Trouve la meilleure position pour un label sans chevauchement"""
    padding = 5
    positions = []
    
    # Position 1: Au-dessus à gauche
    x1 = bbox[0]
    y1 = bbox[1] - label_height - padding
    if y1 >= 0:
        positions.append((x1, y1, x1 + label_width, y1 + label_height))
    
    # Position 2: À l'intérieur en haut à gauche
    x2 = bbox[0] + padding
    y2 = bbox[1] + padding + label_height
    if y2 < bbox[3]:
        positions.append((x2, y2 - label_height, x2 + label_width, y2))
    
    # Position 3: À droite
    x3 = bbox[2] + padding
    y3 = bbox[1] + padding + label_height
    if x3 + label_width <= image_width:
        positions.append((x3, y3 - label_height, x3 + label_width, y3))
    
    # Position 4: En dessous
    x4 = bbox[0]
    y4 = bbox[3] + padding
    if y4 + label_height <= image_height:
        positions.append((x4, y4, x4 + label_width, y4 + label_height))
    
    # Choisir la position avec le moins de chevauchement
    best_pos = None
    min_overlap = float('inf')
    
    for pos in positions:
        overlap = 0
        for other_box in all_boxes:
            if other_box != bbox:
                # Calculer l'intersection
                x1 = max(pos[0], other_box[0])
                y1 = max(pos[1], other_box[1])
                x2 = min(pos[2], other_box[2])
                y2 = min(pos[3], other_box[3])
                if x1 < x2 and y1 < y2:
                    overlap += (x2 - x1) * (y2 - y1)
        
        if overlap < min_overlap:
            min_overlap = overlap
            best_pos = pos
    
    return best_pos if best_pos else (bbox[0], bbox[1] - label_height - padding, bbox[0] + label_width, bbox[1] - padding)

def save_detection_image(image: Image.Image, elements: List[ParsedElement], prefix: str = "detection") -> str:
    """Sauvegarde une image avec les bounding boxes détectées"""
    # Créer une copie de l'image pour dessiner
    img_with_boxes = image.copy()
    draw = ImageDraw.Draw(img_with_boxes)
    img_width, img_height = image.size
    
    # Couleurs pour différents types
    colors = {
        "text": (0, 200, 0),      # Vert
        "icon": (255, 0, 0),       # Rouge
        "object": (0, 0, 255),     # Bleu
        "button": (255, 165, 0)    # Orange
    }
    
    # Essayer de charger une police, sinon utiliser la police par défaut
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    # Collecter toutes les bounding boxes pour éviter les chevauchements
    all_boxes = [elem.bbox for elem in elements if len(elem.bbox) == 4]
    
    # Dessiner les bounding boxes avec leurs labels
    for i, elem in enumerate(elements):
        # Ne pas dessiner les bounding boxes pour le texte
        if elem.type == "text":
            continue
            
        bbox = elem.bbox
        color = colors.get(elem.type, (128, 128, 128))
        
        # Vérifier que la bbox est valide
        if len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            print(f"⚠️ Bbox invalide ignorée: {bbox}")
            continue
        
        # Dessiner le rectangle
        try:
            draw.rectangle(bbox, outline=color, width=3)
        except Exception as e:
            print(f"⚠️ Erreur dessin bbox: {e}")
            continue
        
        # Préparer le label
        if elem.type == "button":
            label = f"{i}"  # Juste le numéro pour les boutons
        elif elem.type == "text":
            label = f"{i}: {elem.content[:15]}"
        else:
            label = f"{i}"
        
        if font:
            # Calculer la taille du label
            try:
                bbox_label = draw.textbbox((0, 0), label, font=font)
                label_width = bbox_label[2] - bbox_label[0] + 10
                label_height = bbox_label[3] - bbox_label[1] + 4
            except:
                label_width = len(label) * 8 + 10
                label_height = 20
            
            # Trouver la meilleure position pour le label
            label_pos = find_best_label_position(
                bbox, label_width, label_height, 
                img_width, img_height, all_boxes
            )
            
            # Dessiner le fond du label
            draw.rectangle(label_pos, fill=color)
            
            # Choisir la couleur du texte selon la luminance
            luminance = get_color_luminance(color)
            text_color = "black" if luminance > 160 else "white"
            
            # Dessiner le texte
            draw.text((label_pos[0] + 5, label_pos[1] + 2), label, fill=text_color, font=font)
    
    # Sauvegarder l'image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"
    filepath = DETECTIONS_DIR / filename
    img_with_boxes.save(filepath)
    
    return str(filepath)

def remove_overlap_new(boxes, iou_threshold, ocr_bbox=None):
    """Fonction de suppression de chevauchement compatible avec OmniParser original"""
    assert ocr_bbox is None or isinstance(ocr_bbox, list)

    def box_area(box):
        return (box[2] - box[0]) * (box[3] - box[1])

    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    def IoU(box1, box2):
        intersection = intersection_area(box1, box2)
        union = box_area(box1) + box_area(box2) - intersection + 1e-6
        if box_area(box1) > 0 and box_area(box2) > 0:
            ratio1 = intersection / box_area(box1)
            ratio2 = intersection / box_area(box2)
        else:
            ratio1, ratio2 = 0, 0
        return max(intersection / union, ratio1, ratio2)

    def is_inside(box1, box2):
        intersection = intersection_area(box1, box2)
        ratio1 = intersection / box_area(box1)
        return ratio1 > 0.80

    filtered_boxes = []
    if ocr_bbox:
        filtered_boxes.extend(ocr_bbox)
    
    for i, box1_elem in enumerate(boxes):
        box1 = box1_elem['bbox']
        is_valid_box = True
        for j, box2_elem in enumerate(boxes):
            box2 = box2_elem['bbox']
            if i != j and IoU(box1, box2) > iou_threshold and box_area(box1) > box_area(box2):
                is_valid_box = False
                break
        if is_valid_box:
            if ocr_bbox:
                box_added = False
                ocr_labels = ''
                for box3_elem in ocr_bbox:
                    if not box_added:
                        box3 = box3_elem['bbox']
                        if is_inside(box3, box1):
                            try:
                                ocr_labels += box3_elem['content'] + ' '
                                filtered_boxes.remove(box3_elem)
                            except:
                                continue
                        elif is_inside(box1, box3):
                            box_added = True
                            break
                        else:
                            continue
                if not box_added:
                    if ocr_labels:
                        filtered_boxes.append({'type': 'icon', 'bbox': box1_elem['bbox'], 'interactivity': True, 'content': ocr_labels})
                    else:
                        filtered_boxes.append({'type': 'icon', 'bbox': box1_elem['bbox'], 'interactivity': True, 'content': None})
            else:
                filtered_boxes.append(box1_elem)
    return filtered_boxes

def parse_image_lite(base64_img: str, save_detection: bool = True, return_annotated: bool = True) -> tuple[List[Dict], str, str]:
    """Parse une image suivant la logique OmniParser"""
    # Décoder l'image
    image_data = base64.b64decode(base64_img)
    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    image_np = np.array(image)
    w, h = image.size
    
    # Configuration comme OmniParser
    box_overlay_ratio = max(w, h) / 3200
    draw_bbox_config = {
        'text_scale': 0.8 * box_overlay_ratio,
        'text_thickness': max(int(2 * box_overlay_ratio), 1),
        'text_padding': max(int(3 * box_overlay_ratio), 1),
        'thickness': max(int(3 * box_overlay_ratio), 1),
    }
    
    # 1. OCR (check_ocr_box)
    ocr_text = []
    ocr_bbox = []
    try:
        result = reader.readtext(image_np, text_threshold=0.8)
        for item in result:
            bbox = item[0]
            text = item[1]
            conf = item[2]
            x1, y1 = bbox[0]
            x2, y2 = bbox[2]
            ocr_bbox.append([float(x1), float(y1), float(x2), float(y2)])
            ocr_text.append(text)
    except Exception as e:
        print(f"Erreur OCR: {e}")
    
    # 2. YOLO (predict_yolo)
    xyxy = []
    if yolo_model:
        try:
            BOX_TRESHOLD = 0.01
            imgsz = (h, w)
            results = yolo_model.predict(
                source=image,
                conf=BOX_TRESHOLD,
                iou=0.1,
                imgsz=imgsz
            )
            
            if results[0].boxes is not None:
                xyxy = results[0].boxes.xyxy
                print(f"YOLO détections: {len(xyxy)}")
        except Exception as e:
            print(f"Erreur YOLO: {e}")
    
    # 3. Conversion et filtrage comme OmniParser
    # Normaliser les coordonnées
    if len(xyxy) > 0:
        xyxy_normalized = xyxy / torch.Tensor([w, h, w, h]).to(xyxy.device)
        xyxy_normalized = xyxy_normalized.tolist()
    else:
        xyxy_normalized = []
    
    if ocr_bbox:
        ocr_bbox_normalized = torch.tensor(ocr_bbox) / torch.Tensor([w, h, w, h])
        ocr_bbox_normalized = ocr_bbox_normalized.tolist()
    else:
        ocr_bbox_normalized = []
    
    # Créer les éléments au format OmniParser
    ocr_bbox_elem = [{'type': 'text', 'bbox': box, 'interactivity': False, 'content': txt} 
                     for box, txt in zip(ocr_bbox_normalized, ocr_text) 
                     if (box[2] - box[0]) * (box[3] - box[1]) * w * h > 0]
    
    xyxy_elem = [{'type': 'icon', 'bbox': box, 'interactivity': True, 'content': None} 
                 for box in xyxy_normalized 
                 if (box[2] - box[0]) * (box[3] - box[1]) * w * h > 0]
    
    # Remove overlap
    filtered_boxes = remove_overlap_new(boxes=xyxy_elem, iou_threshold=0.9, ocr_bbox=ocr_bbox_elem)
    
    # Trier pour avoir les icônes sans contenu à la fin (comme OmniParser)
    filtered_boxes_sorted = sorted(filtered_boxes, key=lambda x: x.get('content') is None)
    starting_idx = next((i for i, box in enumerate(filtered_boxes_sorted) if box.get('content') is None), -1)
    
    print(f"Éléments après overlap: {len(filtered_boxes)} (OCR: {len([x for x in filtered_boxes if x['type'] == 'text'])}, Icons: {len([x for x in filtered_boxes if x['type'] == 'icon'])})")
    
    # Générer les captions pour les icônes (si Florence-2 disponible)
    if caption_model and processor and starting_idx > -1:
        print("Génération des captions pour les icônes...")
        try:
            # Extraire les icônes sans contenu
            icons_to_caption = [box for box in filtered_boxes_sorted if box.get('content') is None]
            
            if icons_to_caption:
                # Préparer les crops d'images
                cropped_images = []
                for box_elem in icons_to_caption:
                    bbox = box_elem['bbox']
                    # Convertir de ratio à pixels
                    x1 = int(bbox[0] * w)
                    y1 = int(bbox[1] * h)
                    x2 = int(bbox[2] * w)
                    y2 = int(bbox[3] * h)
                    
                    # Crop et resize
                    cropped = image_np[y1:y2, x1:x2]
                    if cropped.size > 0:
                        cropped_resized = cv2.resize(cropped, (64, 64))
                        cropped_pil = Image.fromarray(cropped_resized)
                        cropped_images.append(cropped_pil)
                
                # Générer les captions par batch
                if cropped_images:
                    model = caption_model
                    device = model.device
                    
                    prompt = "<CAPTION>" if 'florence' in model.config.name_or_path else "The image shows"
                    batch_size = 32
                    generated_captions = []
                    
                    for i in range(0, len(cropped_images), batch_size):
                        batch = cropped_images[i:i+batch_size]
                        inputs = processor(images=batch, text=[prompt]*len(batch), return_tensors="pt", do_resize=False)
                        
                        # Déplacer vers le device avec le bon type
                        if device.type == 'cuda':
                            # Pour Florence-2, utiliser float32 même sur GPU
                            inputs = {k: v.to(device=device, dtype=torch.float32 if k == 'pixel_values' else v.dtype) if torch.is_tensor(v) else v 
                                     for k, v in inputs.items()}
                        else:
                            inputs = {k: v.to(device=device) if torch.is_tensor(v) else v 
                                     for k, v in inputs.items()}
                        
                        generated_ids = model.generate(
                            input_ids=inputs.get("input_ids"),
                            pixel_values=inputs.get("pixel_values"),
                            max_new_tokens=20,
                            num_beams=1,
                            do_sample=False
                        )
                        
                        captions = processor.batch_decode(generated_ids, skip_special_tokens=True)
                        captions = [cap.strip() for cap in captions]
                        generated_captions.extend(captions)
                    
                    # Assigner les captions aux icônes
                    caption_idx = 0
                    for box_elem in filtered_boxes_sorted:
                        if box_elem.get('content') is None and caption_idx < len(generated_captions):
                            box_elem['content'] = generated_captions[caption_idx]
                            caption_idx += 1
                    
                    print(f"Captions générées: {len(generated_captions)}")
        except Exception as e:
            print(f"Erreur génération captions: {e}")
            import traceback
            traceback.print_exc()
    
    filtered_boxes = filtered_boxes_sorted
    print(f"Éléments finaux: {len(filtered_boxes)}")
    
    # Afficher les détails des éléments finaux
    print("\n📋 Détails des éléments détectés:")
    for i, elem in enumerate(filtered_boxes):
        elem_type = elem.get('type', 'unknown')
        content = elem.get('content', '')
        bbox = elem.get('bbox', [])
        
        if elem_type == 'text':
            print(f"  [{i}] TEXT: '{content}'")
        elif elem_type == 'icon':
            if content:
                print(f"  [{i}] ICON: {content}")
            else:
                print(f"  [{i}] ICON: (no caption)")
        else:
            print(f"  [{i}] {elem_type.upper()}: {content}")
    print("")
    
    # Convertir les coordonnées normalisées en pixels pour la sauvegarde
    filtered_boxes_pixels = []
    for elem in filtered_boxes:
        bbox_norm = elem['bbox']
        bbox_pixels = [
            bbox_norm[0] * w,
            bbox_norm[1] * h,
            bbox_norm[2] * w,
            bbox_norm[3] * h
        ]
        filtered_boxes_pixels.append({
            'type': elem['type'],
            'bbox': bbox_pixels,
            'content': elem.get('content', ''),
            'interactivity': elem.get('interactivity', False)
        })
    
    # Sauvegarder l'image avec les détections si demandé
    detection_path = None
    if save_detection and filtered_boxes_pixels:
        try:
            # Convertir en ParsedElement pour la compatibilité
            elements_for_save = [
                ParsedElement(
                    type=elem['type'],
                    content=elem.get('content') or '',
                    bbox=elem['bbox'],
                    confidence=1.0
                ) for elem in filtered_boxes_pixels
            ]
            detection_path = save_detection_image(image, elements_for_save)
            print(f"💾 Détection sauvegardée: {detection_path}")
        except Exception as e:
            print(f"⚠️ Erreur lors de la sauvegarde de l'image: {e}")
    
    # Créer l'image annotée en base64 (comme OmniParser)
    annotated_base64 = None
    if return_annotated:
        try:
            # Créer une copie pour annotation
            annotated_frame = np.array(image)
            
            # Dessiner les boîtes
            for i, elem in enumerate(filtered_boxes_pixels):
                # Ne pas dessiner les bounding boxes pour le texte
                if elem['type'] == 'text':
                    continue
                    
                bbox = elem['bbox']
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                
                # Couleur selon le type
                color = (255, 0, 0)  # Rouge pour icons
                
                # Dessiner rectangle et numéro
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, draw_bbox_config['thickness'])
                cv2.putText(annotated_frame, str(i), (x1 + 5, y1 + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, draw_bbox_config['text_scale'], 
                           color, draw_bbox_config['text_thickness'])
            
            # Convertir en base64
            pil_img = Image.fromarray(annotated_frame)
            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            annotated_base64 = base64.b64encode(buffered.getvalue()).decode('ascii')
        except Exception as e:
            print(f"⚠️ Erreur création image annotée: {e}")
            import traceback
            traceback.print_exc()
    
    return filtered_boxes, detection_path, annotated_base64

@app.get("/")
async def root():
    return {
        "message": "OmniParser Lite Server", 
        "status": "running",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "models": {
            "ocr": True,
            "yolo": yolo_model is not None,
            "florence": caption_model is not None
        }
    }

@app.get("/probe/")
async def probe():
    return {"message": "Omniparser API ready"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "omniparser-lite",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }

@app.post("/parse/", response_model=ParseResponse)
async def parse_image(request: ImageRequest):
    """Parse une image et retourne les éléments UI"""
    try:
        # Parser l'image avec sauvegarde de la détection et image annotée
        parsed_elements, detection_path, annotated_base64 = parse_image_lite(
            request.base64_image, 
            save_detection=True,
            return_annotated=True
        )

        # Convertir en format attendu (comme OmniParser original)
        parsed_content_list = []
        for elem in parsed_elements:
            # Filtrer les éléments avec content "unanswerable"
            content = elem.get('content', '')
            if content and content.lower().strip() == 'unanswerable':
                continue
                
            # Convertir bbox de ratio à pixels si nécessaire
            bbox = elem['bbox']
            if all(0 <= coord <= 1 for coord in bbox):
                # Coordonnées en ratio, convertir en pixels
                bbox_pixels = [
                    bbox[0] * 1829,  # Utiliser la taille de la dernière calibration
                    bbox[1] * 1012,
                    bbox[2] * 1829,
                    bbox[3] * 1012
                ]
            else:
                bbox_pixels = bbox
            
            parsed_content_list.append({
                "type": elem['type'],
                "content": content,
                "bbox": bbox_pixels,
                "interactivity": elem.get('interactivity', False),
                "source": elem.get('source', 'omniparser_lite')
            })
        
        response = ParseResponse(
            parsed_content_list=parsed_content_list,
            success=True,
            message=f"Found {len(parsed_elements)} elements",
            detection_image_path=detection_path or "",
            labeled_image=annotated_base64 or ""
        )
        
        # Afficher le JSON de réponse
        print("\n📤 JSON Response:")
        response_dict = response.dict()
        # Ne pas afficher l'image base64 complète (trop longue)
        if response_dict.get('labeled_image'):
            response_dict['labeled_image'] = f"<base64 image - {len(response_dict['labeled_image'])} chars>"
        print(json.dumps(response_dict, indent=2, ensure_ascii=False))
        print("")
        
        return response
        
    except Exception as e:
        print(f"Erreur lors du parsing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error parsing image: {str(e)}")

if __name__ == "__main__":
    print("\n🚀 Démarrage du serveur OmniParser Lite sur http://localhost:8000")
    print("   Appuyez sur Ctrl+C pour arrêter\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)