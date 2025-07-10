import dolphin_memory_engine as dme
import re
import time
from pathlib import Path
import datetime
import pyautogui
import pygetwindow as gw
import win32gui  # Utilisé pour activer la fenêtre sans cliquer
import mss
import mss.tools
import base64
import json
import urllib.request
import urllib.error
from PIL import Image

# ---------------- WINDOW SELECTION ---------------- #
def get_dolphin_game_window():
    """Retourne l’objet Window correspondant à la fenêtre Dolphin où le jeu tourne.

    Priorité : titre contenant «Monopoly» (insensible à la casse). Si aucune, on
    renvoie la première fenêtre «Dolphin» ayant une taille non nulle.
    """
    try:
        windows = gw.getWindowsWithTitle("Dolphin")
        # On cherche d’abord une fenêtre dont le titre mentionne le jeu
        for w in windows:
            try:
                if "monopoly" in w.title.lower() and w.width > 0 and w.height > 0:
                    return w
            except Exception:
                continue

        # Sinon, on prend la première fenêtre valide Dolphin
        for w in windows:
            if w.width > 0 and w.height > 0:
                return w

        # En dernier ressort, on retourne la 1ʳᵉ si elle existe
        if windows:
            return windows[0]
    except Exception as e:
        print(f"⚠️  Erreur lors de la recherche des fenêtres Dolphin : {e}")
    return None

# ---------------- UTILITY: FOCUS DOLPHIN ---------------- #
def focus_dolphin_window():
    """Amène la fenêtre Dolphin au premier plan via un clic discret dans son coin supérieur gauche."""
    win = get_dolphin_game_window()
    if win is None:
        print("⚠️  Aucune fenêtre Dolphin trouvée pour focus.")
        return
    try:
        # Tente l'activation via l'API Win32
        try:
            win.activate()
        except Exception:
            try:
                win32gui.SetForegroundWindow(win._hWnd)
            except Exception:
                print(f"⚠️  focus_dolphin_window() a échoué : {e}")
                pass
        except Exception:
            print(f"⚠️  focus_dolphin_window() a échoué : {e}")
            pass

        # Délai léger pour assurer le focus complet
        time.sleep(0.1)
    except Exception as e:
        print(f"⚠️  Impossible de mettre Dolphin en focus : {e}")

# ------------- CONFIGURATION ------------- #
DEBUG = True               # Active les traces détaillées
DELAY_SECONDS = 2          # Pause entre deux balayages

# ----------------------------------------- #

print("🔌 Tentative de connexion à Dolphin…")
dme.hook()
print("✅ Connecté à Dolphin avec succès.")

# Plage mémoire à balayer (adresse et taille peuvent être ajustées au besoin)
RAM_START = 0x90000000  # Début typique de la RAM de la Wii/GameCube dans Dolphin
RAM_SIZE = 0x00200000   # 2 Mo pour couvrir plus large qu'avant


KEYWORDS = {
    "would you like to": {
        "text": ["would you like to"],
        "icon": [
            "accounts",
            "next turn",
            "roll again"
        ],
    },
    "you want to buy": {
        "text": ["you want to buy"],
        "icon": [
            "auction",
            "buy",
        ],
    },
    "a Property you own": {
        "text": ["a Property you own"],
        "icon": [
            "back",
            "trade",
        ],
    },
}
# --------- SCREENSHOT UTILITY --------- #
# Retourne désormais un tuple (chemin_image, bbox_fenetre)
# bbox_fenetre = (left, top, width, height)
def capture_dolphin_screenshot(prefix: str = "popup"):
    """
    Capture un screenshot de la fenêtre Dolphin et le sauvegarde dans un
    sous-dossier «captures». Si la fenêtre Dolphin n'est pas détectée, capture
    tout l'écran.

    Parameters
    ----------
    prefix : str
        Préfixe du nom de fichier (ex : "popup", "debug"…)

    Returns
    -------
    Path
        Chemin complet vers l'image PNG générée.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "captures"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{prefix}_{timestamp}.png"

    # Initialise la bbox (left, top, width, height) – sera définie plus tard
    bbox = None

    try:
        # Recherche de la fenêtre Dolphin jeu via helper
        win = get_dolphin_game_window()
        if win:
            # S'assure que la fenêtre est bien visible/active
            try:
                # Clique dans le coin de la fenêtre pour récupérer le focus et éloigner le curseur avant la capture
                focus_dolphin_window()
            except Exception as e:
                print(f"⚠️  focus_dolphin_window() a échoué : {e}")
            bbox = (win.left, win.top, win.width, win.height)
            # Utilise mss pour mieux supporter les fenêtres DirectX/OpenGL
            try:
                with mss.mss() as sct:
                    monitor = {
                        "left": bbox[0],
                        "top": bbox[1],
                        "width": bbox[2],
                        "height": bbox[3],
                    }
                    img = sct.grab(monitor)
                    mss.tools.to_png(img.rgb, img.size, output=str(out_path))
                    print(f"📸 Screenshot sauvegardé → {out_path}")
                    return out_path, bbox
            except Exception as e:
                print(f"⚠️  mss a échoué, fallback pyautogui: {e}")
                screenshot = pyautogui.screenshot(region=bbox)
        else:
            # Fallback : capture plein écran
            screenshot = pyautogui.screenshot()
    except Exception as e:
        print(f"⚠️  Impossible de cibler la fenêtre Dolphin : {e}")
        screenshot = pyautogui.screenshot()

    screenshot.save(out_path)
    print(f"📸 Screenshot sauvegardé → {out_path}")
    if bbox is None:
        bbox = (0, 0, screenshot.width, screenshot.height)
    return out_path, bbox

# --------- PARSE SCREENSHOT VIA API --------- #
# La fonction retourne désormais un dict {icon_name: (abs_x, abs_y)}
PARSE_API_URL = "http://127.0.0.1:8000/parse/"


def parse_and_display(image_path: Path, trigger: str, window_bbox=None):
    """Envoie l'image à l'API /parse/ et affiche les infos extraites."""
    try:
        if not image_path.exists():
            print(f"❌ Image introuvable: {image_path}")
            return

        with Image.open(image_path) as img:
            img_width, img_height = img.size

        with image_path.open("rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        payload = json.dumps({"base64_image": base64_image}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(PARSE_API_URL, data=payload, headers=headers, method="POST")

        print("🌐 Envoi de l'image pour parsing…")
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body)

        parsed_list = data.get("parsed_content_list", [])
        icon_positions = {}
        # Récupère les filtres spécifiques à ce trigger
        trigger_filters = KEYWORDS.get(trigger, {})
        wanted_texts = [t.lower() for t in trigger_filters.get("text", [])]
        wanted_icons = [i.lower() for i in trigger_filters.get("icon", [])]

        filtered = []
        for element in parsed_list:
            content_lc = element.get("content", "").lower()
            if element.get("type") == "text" and any(pat in content_lc for pat in wanted_texts):
                filtered.append(element)
            elif element.get("type") == "icon" and any(pat in content_lc for pat in wanted_icons):
                filtered.append(element)

        parsed_list = filtered
        if not parsed_list:
            print("🤔 Aucune donnée utile extraite par l'API.")
        else:
            print("📋 Contenu extrait:")
            for idx, element in enumerate(parsed_list):
                bbox = element.get("bbox", [])
                if len(bbox) == 4:
                    x1_norm, y1_norm, x2_norm, y2_norm = bbox
                    x1 = int(x1_norm * img_width)
                    y1 = int(y1_norm * img_height)
                    x2 = int(x2_norm * img_width)
                    y2 = int(y2_norm * img_height)
                    pos_str = f"(({x1},{y1})-({x2},{y2}))"
                else:
                    pos_str = "(no bbox)"

                if element.get("type") == "text":
                    print(f" • TXT {idx}: '{element['content']}' @ {pos_str}")
                elif element.get("type") == "icon":
                    print(f" • ICO {idx}: '{element['content']}' @ {pos_str}")
                    # Calcule la position absolue (centre de la bbox)
                    if len(bbox) == 4:
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        if window_bbox is not None:
                            abs_x = window_bbox[0] + cx
                            abs_y = window_bbox[1] + cy
                        else:
                            abs_x, abs_y = cx, cy
                        icon_key = element["content"].strip().lower()
                        icon_positions[icon_key] = (abs_x, abs_y)

        # Image parsée (overlay) si dispo
        base64_parsed = data.get("som_image_base64")
        if base64_parsed:
            parsed_dir = image_path.parent / "parsed"
            parsed_dir.mkdir(exist_ok=True)
            parsed_path = parsed_dir / (image_path.stem + "_parsed.png")
            with parsed_path.open("wb") as f_out:
                f_out.write(base64.b64decode(base64_parsed))
            print(f"🖼️  Image annotée enregistrée: {parsed_path}")
        return icon_positions
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code}: {e.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
    except Exception as e:
        print(f"⚠️  Erreur lors du parsing de l'image: {e}")
    return {}

# Transformation des triggers en regex UTF-16LE
patterns = [
    (trigger, re.compile(re.escape(trigger.encode("utf-16-le")), re.DOTALL))
    for trigger in KEYWORDS.keys()
]

already_seen = set()
print("🔍 Début de la recherche du popup…")
if DEBUG:
    for kw in KEYWORDS.keys():
        pbytes = kw.encode('utf-16-le')
        print(f"[DEBUG] Mot-clé '{kw}' => {pbytes.hex(' ')}")


def scan_memory_chunks():
    """Balaye la mémoire par chunks pour rechercher les triggers."""
    CHUNK_SIZE = 0x10000  # 64 Ko par chunk
    results = []  # (trigger, addr, message_bytes)

    for addr in range(RAM_START, RAM_START + RAM_SIZE, CHUNK_SIZE):
        try:
            chunk = dme.read_bytes(addr, CHUNK_SIZE)

            for trigger, pat in patterns:
                for match in pat.finditer(chunk):
                    start_pos = match.start()
                    match_addr = addr + start_pos

                    # On lit un peu plus loin pour capturer la phrase complète
                    end_offset = min(start_pos + 400, len(chunk))
                    message_bytes = chunk[start_pos:end_offset]

                    # Cherche le double NULL UTF-16 (0x00 00 00 00)
                    terminator = message_bytes.find(b"\x00\x00\x00\x00")
                    if terminator != -1:
                        message_bytes = message_bytes[:terminator]

                    results.append((trigger, match_addr, message_bytes))
        except Exception as e:
            print(f"⚠️  Erreur lors de la lecture à 0x{addr:08X}: {e}")

    return results


while True:
    print("\n⏳ Scan de la mémoire en cours…")
    matches = scan_memory_chunks()

    if matches:
        print(f"📢 {len(matches)} correspondance(s) trouvée(s):")
        for trigger, addr, message_bytes in matches:
            # Décodage UTF-16 LE avec tolérance d'erreur
            try:
                raw_text = message_bytes.decode('utf-16-le', errors='ignore')
                cleaned_text = ''.join(c for c in raw_text if 32 <= ord(c) < 127)

                key = f"{trigger}:{addr:08X}:{cleaned_text[:40]}"
                if key not in already_seen:
                    print(f"✨ Nouveau popup à 0x{addr:08X}: \"{cleaned_text}\"")
                    if DEBUG:
                        print(f"    [DEBUG] Bytes (hex) : {message_bytes.hex(' ')}")
                        print(f"    [DEBUG] Longueur bytes: {len(message_bytes)} | Longueur texte: {len(cleaned_text)}")
                    already_seen.add(key)
                    # Capture un screenshot et parse immédiatement
                    img_path, win_bbox = capture_dolphin_screenshot(prefix="popup")
                    icon_positions = parse_and_display(img_path, trigger, win_bbox)

                    if icon_positions:
                        print("📋 Options détectées: " + ", ".join(icon_positions.keys()))
                        try:
                            choice = input("👉 Quelle option choisir ? (laisser vide pour ignorer) : ").strip().lower()
                        except EOFError:
                            choice = ""

                        if choice in icon_positions:
                            x_click, y_click = icon_positions[choice]
                            print(f"🖱️  Clic sur '{choice}' à ({x_click},{y_click})…")
                            time.sleep(2)
                            focus_dolphin_window()
                            
                            # Premier clic : met la fenêtre active si besoin, deuxième clic : valide l'action
                            pyautogui.moveTo(x_click, y_click, duration=1.5)
                            focus_dolphin_window()
                            pyautogui.click()
                            time.sleep(0.2)
                            pyautogui.click()
                            
                            # Déplace la souris au centre supérieur de la fenêtre Dolphin (200 px du haut)
                            try:
                                if win_bbox is not None:
                                    target_x = win_bbox[0] + win_bbox[2] // 2
                                    target_y = win_bbox[1] + 200
                                else:
                                    screen_w, _ = pyautogui.size()
                                    target_x = screen_w // 2
                                    target_y = 200
                                pyautogui.moveTo(target_x, target_y, duration=1.0)
                            except Exception as e:
                                print(f"⚠️  Impossible de déplacer la souris : {e}")
                            
                            # Remove the already seen key
                            already_seen.remove(key)
                        else:
                            if choice:
                                print("❌ Option non reconnue ou non détectée, aucune action.")
                else:
                    print(f"♻️  Déjà détecté à 0x{addr:08X}: \"{cleaned_text}\"")
            except Exception as e:
                print(f"⚠️  Erreur de décodage à 0x{addr:08X}: {e}")


    else:
        print("⚠️  Aucune occurrence du popup trouvée.")

    print(f"⏲️  Pause de {DELAY_SECONDS} s avant le prochain scan…")
    time.sleep(DELAY_SECONDS) 