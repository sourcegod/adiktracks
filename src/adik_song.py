#!/usr/bin/env python3
# adik_song.py

from typing import List, Optional
import uuid

# --- Classe Interne : SongEntry (L'événement d'arrangement) ---
class SongEntry:
    """
    Représente une entrée dans l'arrangement : quel pattern jouer, combien de fois.
    """
    def __init__(self, pattern_index: int, repetitions: int, pattern_length_bars: int, start_bar: int):
        """
        :param pattern_index: L'indice (index) du AdikPattern à jouer.
        :param repetitions: Le nombre de fois que le pattern doit être répété.
        :param pattern_length_bars: La durée en mesures du pattern de base (obtenue via le Player).
        :param start_bar: La mesure (bar) de début sur la Timeline globale du Song.
        """
        self.pattern_index = pattern_index
        self.repetitions = max(1, repetitions) # S'assurer d'au moins 1 répétition
        self.pattern_length_bars = max(1, pattern_length_bars) # Durée du pattern de base
        self.start_bar = start_bar
        self._id = str(uuid.uuid4())
        self.repetitions_done = 0

    #--------------------------------------------------------------------------

    @property
    def total_bars(self) -> int:
        """La durée totale de cet événement d'arrangement en mesures (calculée)."""
        return self.repetitions * self.pattern_length_bars

    #--------------------------------------------------------------------------

    @property
    def end_bar(self) -> int:
        """La mesure de fin (calculée : start_bar + total_bars)."""
        return self.start_bar + self.total_bars

    #--------------------------------------------------------------------------

    def __str__(self):
        return (f"SongEntry(PatternIdx={self.pattern_index}, Repetitions={self.repetitions}, "
                f"StartBar={self.start_bar}, TotalBars={self.total_bars})")

    #--------------------------------------------------------------------------

#--------------------------------------------------------------------------

# --- Classe Principale : AdikSong (Le Mode Song/Arrangement) ---
# --------------------------------------------------------------------------
class AdikSong:
    """
    Gère la séquence d'événements (SongEntry) qui composent l'arrangement du morceau.
    """
    
    def __init__(self, player):
        """
        :param player: Référence à l'instance AdikPlayer pour accéder aux Patterns et au BPM.
        """
        self.player = player
        self.event_list: List[SongEntry] = []
        self.current_entry_index = 0        
    

    # --- Propriétés de Durée ---
    
    @property
    def total_bars(self) -> int:
        """
        Calculé comme la mesure de fin la plus éloignée de toutes les entrées.
        """
        if not self.event_list:
            return 0
            
        last_entry = self.event_list[-1] # Les entrées sont ajoutées de manière séquentielle
        return last_entry.end_bar if last_entry else 0

    @property
    def total_duration_frames(self) -> int:
        """
        Calcule la durée totale de l'arrangement en frames, en utilisant le Player.
        """
        # Nécessite l'accès à la conversion bar_to_frame du Player/Metronome
        return self.player.bar_to_frame(self.total_bars)

    # --- Méthodes de Gestion de l'Arrangement ---
    def get_current_entry(self) -> Optional[SongEntry]:
        """ Retourne le SongEntry en cours de lecture. """
        if 0 <= self.current_entry_index < len(self.event_list):
            return self.event_list[self.current_entry_index]
        return None

    
    def add_entry(self, pattern_index: int, repetitions: int = 1):
        """
        Ajoute un Pattern à la fin de la séquence d'événements du Song.
        
        :param pattern_index: Index du Pattern à ajouter.
        :param repetitions: Nombre de fois que ce Pattern doit être joué.
        :return: Le nouvel SongEntry créé.
        """
        # 1. Validation de l'index du Pattern
        if pattern_index < 0 or pattern_index >= len(self.player.pattern_list):
             print(f"Erreur Song: L'index de pattern {pattern_index} est invalide.")
             return None
             
        # 2. Récupération de la durée du Pattern
        pattern = self.player.pattern_list[pattern_index]
        pattern_length_bars = pattern.length_bars # Assurez-vous que AdikPattern a bien cet attribut
             
        # 3. Calcul de la mesure de début et création de l'entrée
        start_bar = self.total_bars 
        
        new_entry = SongEntry(
            pattern_index=pattern_index,
            repetitions=repetitions,
            pattern_length_bars=pattern_length_bars,
            start_bar=start_bar
        )
        self.event_list.append(new_entry)
        
        # IMPORTANT : Si on ajoute une entrée, on réinitialise l'index
        self.current_entry_index = 0        
        
        print(f"Song: Pattern {pattern_index} ajouté {repetitions} fois (Durée: {new_entry.total_bars} bars). Début à la mesure {start_bar}.")
        return new_entry

    def get_entry_at_bar(self, current_bar: int) -> Optional[SongEntry]:
        """
        Retourne le SongEntry (et donc le Pattern à jouer) actif à une mesure donnée.
        """
        for entry in self.event_list:
            # Vérifie si la mesure actuelle est strictement entre la mesure de début et la mesure de fin (exclue)
            if entry.start_bar <= current_bar < entry.end_bar:
                return entry
        return None
        
    def get_pattern_and_repetition_info(self, current_bar: int) -> Optional[tuple[int, int]]:
        """
        Retourne l'index du pattern actif et le numéro de répétition en cours (1-indexé).
        
        :param current_bar: La mesure actuelle (0-indexée).
        :return: Tuple (pattern_index, repetition_number) ou None.
        """
        entry = self.get_entry_at_bar(current_bar)
        if entry is None:
            return None
            
        # 1. Mesure relative à l'événement (0 pour le début de l'événement)
        relative_bar = current_bar - entry.start_bar
        
        # 2. Calcul du numéro de répétition
        repetition_number = (relative_bar // entry.pattern_length_bars) + 1
        
        # Le numéro de répétition doit être borné entre 1 et repetitions max
        repetition_number = min(repetition_number, entry.repetitions)
        
        return entry.pattern_index, repetition_number

    def _recalculate_start_bars(self):
        """
        Utilitaire pour réinitialiser les start_bars après une modification (suppression ou insertion).
        """
        current_bar = 0
        for entry in self.event_list:
            entry.start_bar = current_bar
            current_bar += entry.bars
        print("Song réorganisé et start_bars recalculés.")
        
    def try_move_to_next_pattern(self, player):
        """
        Gère la fin d'un Pattern dans un Song : soit on répète, soit on passe au Pattern suivant, 
        soit on s'arrête.
        """
        if not self.event_list:
            return None

        current_entry = self.get_current_entry()
        
        if current_entry is None:
             # Si l'index est hors limite, cela signifie la fin du Song
             return None 

        # 1. Vérification de la répétition
        if current_entry.repetitions_done < current_entry.repetitions - 1: # -1 car la 1ère lecture est la répétition 0
            # Répéter le Pattern actuel
            current_entry.repetitions_done += 1
            print(f"Song: Répétition {current_entry.repetitions_done + 1}/{current_entry.repetitions} de Pattern {current_entry.pattern_index}.")
            # Retourner 0 pour commencer la répétition à la frame 0 du Pattern
            return 0  

        # 2. Si toutes les répétitions sont faites, passer à l'entrée suivante
        next_entry_index = self.current_entry_index + 1
        
        if next_entry_index < len(self.event_list):
            # Préparation de l'ancienne entrée avant de passer à la suivante
            current_entry.repetitions_done = 0 
            
            # Mise à jour des index et sélection du nouveau Pattern
            self.current_entry_index = next_entry_index
            new_entry = self.get_current_entry()
            
            # Réinitialiser la première répétition (la lecture actuelle sera la première)
            new_entry.repetitions_done = 0 
            
            # Sélection du Pattern dans le Player pour charger les pistes
            player.select_pattern(new_entry.pattern_index) 
            
            print(f"Song: Passage à la SongEntry {self.current_entry_index}. Nouveau Pattern Index {new_entry.pattern_index} sélectionné.")
            
            return 0  # Nouvelle frame de départ (début du nouveau Pattern)
        else:
            # 3. Fin du Song (dernière entrée jouée)
            # Réinitialiser l'index pour un prochain démarrage propre
            self.current_entry_index = 0
            current_entry.repetitions_done = 0 
            return None # Signal d'arrêt

    def __len__(self):
        return len(self.event_list)

    def __str__(self):
        return (f"AdikSong(Événements: {len(self)}, "
                f"Durée Totale: {self.total_bars} bars)")

