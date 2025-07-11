# Utilise une image plus récente de PyTorch avec CUDA 12.4
FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime



# Set non interactive mode
ENV DEBIAN_FRONTEND=noninteractive

# Met à jour la liste des paquets et installe git, libgl1-mesa-glx et libglib2.0-0, puis nettoie
RUN apt-get update && \
    apt-get install -y git libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Définit le répertoire de travail
WORKDIR /app

# Clone le dépôt OmniParser
RUN git clone https://github.com/microsoft/OmniParser.git


# Se positionne dans le dossier cloné
WORKDIR /app/OmniParser

RUN pip install uv

# Met à jour pip et installe les dépendances du projet
RUN pip install --upgrade pip && uv pip install -r requirements.txt --system


# Télécharge les poids V2 (si non présents) et ajuste le nom du dossier de caption
RUN rm -rf weights/icon_detect weights/icon_caption weights/icon_caption_florence \
 && for folder in icon_caption icon_detect; do \
      huggingface-cli download microsoft/OmniParser-v2.0 --local-dir weights --repo-type model --include "$folder/*"; \
    done \
 && mv weights/icon_caption weights/icon_caption_florence

 # Met à jour la liste des paquets, installe git et libgl1-mesa-glx, puis nettoie
RUN apt-get update && \
apt-get install -y libgl1-mesa-glx libglib2.0-0

# Se positionne dans le répertoire du serveur
WORKDIR /app/OmniParser/omnitool/omniparserserver

# Expose le port (à ajuster si nécessaire)
EXPOSE 8000

# Commande pour démarrer le serveur
CMD ["python", "-m", "omniparserserver"]
