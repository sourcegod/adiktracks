#!/usr/bin/env python3
"""
    # adik_pattern.py
    Pattern object management
    Date: Mon, 13/10/2025
    Author: Coolbrother
"""

from adik_track import AdikTrack # Assurez-vous d'importer la classe AdikTrack

class AdikPattern:
    """
    Représente un motif ou une scène musicale (comme un clip ou une scène dans une groovebox).
    Un Pattern est un conteneur pour un ensemble de pistes (AdikTrack)
    qui définissent le contenu musical d'une section du morceau.
    """
    def __init__(self, player, name="New Pattern"):
        """
        Initialise un nouveau Pattern.

        :param player: Référence à l'instance AdikPlayer (pour l'accès aux paramètres globaux).
        :param name: Nom du Pattern (ex: "Intro", "Couplet 1").
        """
        self.player = player
        self.name = name
        
        # Le Pattern contient sa propre liste de pistes AdikTrack.
        # C'est la liste des pistes qui sera jouée lorsque ce pattern est actif.
        self.track_list = []
        self.selected_track_idx = -1 # Index de la piste sélectionnée dans ce Pattern
        
        # Longueur du pattern, en bars. Par défaut à 4 mesures.
        self.length_bars = 4 
        
        print(f"AdikPattern '{self.name}' créé.")

    #----------------------------------------    

    # --- Méthodes pour gérer les pistes à l'intérieur de ce Pattern ---
    def add_track(self, name=None):
        """
        Ajoute une nouvelle piste à ce Pattern.
        
        ATTENTION : Adapte les arguments passés à AdikTrack en fonction de
        sa signature: __init__(self, name=None, sample_rate=44100, num_channels=2)
        """
        if name is None:
            # Génère un nom par défaut si non fourni
            name = f"Track {len(self.track_list) + 1}"
            
        # 1. Extrait les paramètres du Player (qui sont les paramètres du système)
        sample_rate = self.player.sample_rate
        num_output_channels = self.player.num_output_channels

        # 2. Instancie AdikTrack en utilisant les arguments nommés corrects
        # L'objet 'self.player' n'est PAS passé directement à AdikTrack.
        new_track = AdikTrack(
            name=name, 
            sample_rate=sample_rate, 
            num_channels=num_output_channels
        )
        
        self.track_list.append(new_track)
        self.selected_track_idx = len(self.track_list) - 1 # Sélectionne la nouvelle piste
        print(f"Piste '{name}' ajoutée à Pattern '{self.name}'.")
        return new_track

    #----------------------------------------    
        
    def get_tracks(self):
        """
        Retourne la liste des pistes de ce Pattern.
        """
        return self.track_list

    #----------------------------------------    
        
    def get_track_by_index(self, index: int):
        """
        Retourne une piste par son index, si elle existe.
        """
        if 0 <= index < len(self.track_list):
            return self.track_list[index]
        return None

    #----------------------------------------    

    def delete_track(self, track_idx: int):
        """
        Supprime une piste par son index.
        """
        if 0 <= track_idx < len(self.track_list):
            name = self.track_list[track_idx].name
            del self.track_list[track_idx]
            if self.selected_track_idx >= track_idx:
                self.selected_track_idx = max(-1, self.selected_track_idx - 1)
            print(f"Piste '{name}' supprimée de Pattern '{self.name}'.")

    #----------------------------------------    
        
    def get_selected_track(self):
        """
        Retourne la piste actuellement sélectionnée dans ce Pattern.
        """
        return self.get_track_by_index(self.selected_track_idx)

    #----------------------------------------    

    # --- Propriétés de temps (pour la lecture) ---
    @property
    def length_frames(self):
        """
        Calcule la longueur du Pattern en frames.
        """
        beats_per_bar = self.player.time_signature[0]
        frames_per_beat = self.player.metronome.frames_per_beat
        frames_per_bar = beats_per_bar * frames_per_beat
        
        # La longueur est la longueur en bars multipliée par les frames par bar.
        return self.length_bars * frames_per_bar
        
    #----------------------------------------    

    # Vous pouvez ajouter ici la logique de mixage/lecture pour le callback audio.
    # Par exemple, une méthode 'render_audio_block(start_frame, frame_count)'
