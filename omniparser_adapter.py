#!/usr/bin/env python3
"""
Adaptateur pour uniformiser les sorties d'OmniParser Lite et Official
"""
from typing import List, Dict, Any

def convert_normalized_to_absolute_bbox(bbox: List[float], image_width: int, image_height: int) -> List[float]:
    """
    Convertit une bbox normalisée (0-1) en coordonnées absolues
    
    Args:
        bbox: [x1, y1, x2, y2] normalisées entre 0 et 1
        image_width: Largeur de l'image en pixels
        image_height: Hauteur de l'image en pixels
    
    Returns:
        [x1, y1, x2, y2] en pixels absolus
    """
    return [
        bbox[0] * image_width,
        bbox[1] * image_height,
        bbox[2] * image_width,
        bbox[3] * image_height
    ]

def convert_absolute_to_normalized_bbox(bbox: List[float], image_width: int, image_height: int) -> List[float]:
    """
    Convertit une bbox absolue en coordonnées normalisées
    
    Args:
        bbox: [x1, y1, x2, y2] en pixels
        image_width: Largeur de l'image en pixels
        image_height: Hauteur de l'image en pixels
    
    Returns:
        [x1, y1, x2, y2] normalisées entre 0 et 1
    """
    return [
        bbox[0] / image_width,
        bbox[1] / image_height,
        bbox[2] / image_width,
        bbox[3] / image_height
    ]

def adapt_omniparser_response(response: Dict[str, Any],
                            image_width: int = None, image_height: int = None) -> Dict[str, Any]:
    """
    Adapte la réponse d'OmniParser pour avoir un format uniforme
    
    Args:
        response: Réponse brute de l'API OmniParser
        source: "lite", "official" ou "auto" pour détecter automatiquement
        image_width: Largeur de l'image (nécessaire pour conversion)
        image_height: Hauteur de l'image (nécessaire pour conversion)
    
    Returns:
        Réponse adaptée avec bbox en pixels absolus
    """
    # Copier la réponse pour ne pas la modifier
    adapted = response.copy()

    elements = response['raw_parsed_content']
    if image_width and image_height:
        adapted_elements = []
        for elem in elements:
            adapted_elem = elem.copy()

            # Convertir les bbox normalisées en absolues
            if 'bbox' in adapted_elem and len(adapted_elem['bbox']) == 4:
                # Vérifier si déjà en pixels absolus
                bbox = adapted_elem['bbox']
                if all(val <= 1.0 for val in bbox):
                    adapted_elem['bbox'] = convert_normalized_to_absolute_bbox(
                        adapted_elem['bbox'], 
                        image_width, 
                        image_height
                    )
            if 'content' in adapted_elem:
                adapted_elem['name'] = adapted_elem['content']
            
            # Ajouter le champ confidence s'il n'existe pas
            if 'confidence' not in adapted_elem:
                adapted_elem['confidence'] = 1.0
            
            adapted_elements.append(adapted_elem)
        
        adapted['raw_parsed_content'] = adapted_elements.copy()
        adapted['options'] = adapted_elements.copy()
    
    return adapted

def normalize_for_monopoly(response: Dict[str, Any], image_width: int, image_height: int) -> List[Dict[str, Any]]:
    """
    Normalise la réponse spécifiquement pour le système Monopoly
    
    Returns:
        Liste des éléments avec bbox en pixels absolus
    """
    # Adapter d'abord la réponse
    adapted = adapt_omniparser_response(response, "auto", image_width, image_height)
    
    # Extraire et formater les éléments
    elements = []
    for elem in adapted.get('parsed_content_list', []):
        element = {
            'type': elem.get('type', 'unknown'),
            'content': elem.get('content', ''),
            'bbox': elem.get('bbox', [0, 0, 0, 0]),
            'confidence': elem.get('confidence', 1.0),
            'interactivity': elem.get('interactivity', False)
        }
        elements.append(element)
    
    return elements

# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple avec réponse Official
    official_response = {
        "parsed_content_list": [
            {
                "type": "icon",
                "content": "Button",
                "bbox": [0.1, 0.2, 0.3, 0.4],  # Normalisé
                "interactivity": True,
                "source": "omniparser_official",
                "confidence": 0.95
            }
        ],
        "success": True,
        "message": "OK"
    }
    
    # Adapter pour une image 800x600
    adapted = adapt_omniparser_response(official_response, "official", 800, 600)
    print("Bbox adaptée:", adapted['parsed_content_list'][0]['bbox'])
    # Résultat: [80.0, 120.0, 240.0, 240.0]
    
    # Normaliser pour Monopoly
    elements = normalize_for_monopoly(official_response, 800, 600)
    print("Éléments normalisés:", elements[0])